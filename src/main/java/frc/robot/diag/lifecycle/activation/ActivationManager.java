package frc.robot.diag.lifecycle.activation;

import frc.robot.diag.lifecycle.devices.DeviceCatalog;
import frc.robot.diag.lifecycle.devices.DeviceLifecycleKind;
import frc.robot.diag.lifecycle.devices.DeviceRecord;
import frc.robot.diag.lifecycle.factory.DeviceFactory;
import frc.robot.diag.lifecycle.factory.LiveDevice;
import frc.robot.diag.lifecycle.labels.LabelResolver;
import frc.robot.diag.lifecycle.runtime.DeviceRuntimeState;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * NAME
 *     ActivationManager - own lifecycle activation, rollback, singleton reuse, and deactivation.
 *
 * DESCRIPTION
 *     ActivationManager is the first robot-side runtime owner for lifecycle semantics. It enforces
 *     the single-session rule, performs all-or-nothing activation, and records runtime-state proof.
 */
public final class ActivationManager {
    private static final String ERROR_SESSION_NOT_INACTIVE = "SESSION_NOT_INACTIVE";
    private static final String ERROR_LABEL_RESOLUTION_FAILED = "LABEL_RESOLUTION_FAILED";
    private static final String ERROR_EMPTY_GROUP = "EMPTY_GROUP";
    private static final String ERROR_ACTIVATION_FAILED = "ACTIVATION_FAILED";
    private static final String ERROR_NO_ACTIVE_SESSION = "NO_ACTIVE_SESSION";
    private static final String ERROR_LABEL_MISMATCH = "LABEL_MISMATCH";
    private static final String MESSAGE_ACTIVATE_ONLY_IN_INACTIVE =
            "activate() is only legal in INACTIVE";
    private static final String MESSAGE_EMPTY_GROUP =
            "Activation of an empty group is not allowed";
    private static final String MESSAGE_DEACTIVATE_ONLY_WHEN_ACTIVE =
            "deactivate(label) is only legal when a session is ACTIVE";
    private static final String MESSAGE_DEACTIVATE_ACTIVE_ONLY_WHEN_ACTIVE =
            "deactivateActive() is only legal when a session is ACTIVE";
    private static final String MESSAGE_DEACTIVATE_LABEL_MISMATCH =
            "Deactivate label does not match the active session requested label";

    private final DeviceCatalog deviceCatalog;
    private final LabelResolver labelResolver;
    private final DeviceFactory deviceFactory;

    private ActivationSession activeSession;
    private final Map<String, LiveDevice> activeDevicesByLabel = new LinkedHashMap<>();
    private final Map<String, LiveDevice> singletonDevicesByLabel = new LinkedHashMap<>();
    private LifecycleState lifecycleState = LifecycleState.INACTIVE;

    public ActivationManager(
            DeviceCatalog deviceCatalog, LabelResolver labelResolver, DeviceFactory deviceFactory) {
        this.deviceCatalog = deviceCatalog;
        this.labelResolver = labelResolver;
        this.deviceFactory = deviceFactory;
    }

    /**
     * NAME
     *     activate - activate one device label or group label into the sole active session.
     *
     * PARAMETERS
     *     label - target device or group label.
     *     mode - session-level activation mode.
     *
     * RETURNS
     *     ActivationResult describing success or rollback failure details.
     */
    public ActivationResult activate(String label, ActivationMode mode) {
        if (lifecycleState != LifecycleState.INACTIVE) {
            return failedActivation(
                    label,
                    null,
                    mode,
                    List.of(),
                    List.of(),
                    ERROR_SESSION_NOT_INACTIVE,
                    MESSAGE_ACTIVATE_ONLY_IN_INACTIVE);
        }

        List<String> requestedDeviceLabels;
        try {
            requestedDeviceLabels = labelResolver.resolveToDeviceLabels(label);
        } catch (RuntimeException exception) {
            return failedActivation(
                    label,
                    null,
                    mode,
                    List.of(),
                    List.of(),
                    ERROR_LABEL_RESOLUTION_FAILED,
                    exception.getMessage());
        }

        if (requestedDeviceLabels.isEmpty()) {
            return failedActivation(
                    label,
                    null,
                    mode,
                    requestedDeviceLabels,
                    requestedDeviceLabels,
                    ERROR_EMPTY_GROUP,
                    MESSAGE_EMPTY_GROUP);
        }

        lifecycleState = LifecycleState.ACTIVATING;
        String sessionId = UUID.randomUUID().toString();
        List<String> instantiatedLabels = new ArrayList<>();
        Map<String, LiveDevice> createdDevices = new LinkedHashMap<>();

        try {
            for (String deviceLabel : requestedDeviceLabels) {
                DeviceRecord deviceRecord = deviceCatalog.deviceRecord(deviceLabel);
                LiveDevice liveDevice = activateDevice(deviceRecord);
                createdDevices.put(deviceLabel, liveDevice);
                instantiatedLabels.add(deviceLabel);
            }
        } catch (RuntimeException exception) {
            lifecycleState = LifecycleState.FAILED;
            rollback(createdDevices, requestedDeviceLabels, ERROR_ACTIVATION_FAILED);
            List<String> failedLabels = requestedDeviceLabels.stream()
                    .filter(labelCandidate -> !instantiatedLabels.contains(labelCandidate))
                    .toList();
            ActivationResult result =
                    new ActivationResult(
                            false,
                            label,
                            null,
                            mode,
                            requestedDeviceLabels,
                            List.of(),
                            failedLabels,
                            LifecycleState.FAILED,
                            ERROR_ACTIVATION_FAILED,
                            exception.getMessage());
            lifecycleState = LifecycleState.INACTIVE;
            return result;
        }

        activeDevicesByLabel.clear();
        activeDevicesByLabel.putAll(createdDevices);
        activeSession = new ActivationSession(sessionId, label, requestedDeviceLabels, mode);
        updateRuntimeStateForSuccessfulActivation(activeSession);
        lifecycleState = LifecycleState.ACTIVE;

        return new ActivationResult(
                true,
                label,
                sessionId,
                mode,
                requestedDeviceLabels,
                requestedDeviceLabels,
                List.of(),
                lifecycleState,
                null,
                null);
    }

    public DeactivateResult deactivate(String label) {
        if (lifecycleState != LifecycleState.ACTIVE || activeSession == null) {
            return failedDeactivate(
                    label,
                    ERROR_NO_ACTIVE_SESSION,
                    MESSAGE_DEACTIVATE_ONLY_WHEN_ACTIVE);
        }
        if (!activeSession.requestedLabel().equals(label)) {
            return failedDeactivate(
                    label,
                    ERROR_LABEL_MISMATCH,
                    MESSAGE_DEACTIVATE_LABEL_MISMATCH);
        }
        return performDeactivate();
    }

    public DeactivateResult deactivateActive() {
        if (lifecycleState != LifecycleState.ACTIVE || activeSession == null) {
            return failedDeactivate(
                    null,
                    ERROR_NO_ACTIVE_SESSION,
                    MESSAGE_DEACTIVATE_ACTIVE_ONLY_WHEN_ACTIVE);
        }
        return performDeactivate();
    }

    public Optional<ActivationSession> getActiveSession() {
        return Optional.ofNullable(activeSession);
    }

    public LifecycleState lifecycleState() {
        return lifecycleState;
    }

    public List<String> activeDeviceLabels() {
        return deviceCatalog.deviceRecords().stream()
                .map(DeviceRecord::label)
                .filter(label -> deviceCatalog.runtimeState(label).isActive())
                .toList();
    }

    private DeactivateResult performDeactivate() {
        lifecycleState = LifecycleState.DEACTIVATING;
        List<String> deactivatedLabels = new ArrayList<>(activeDevicesByLabel.keySet());
        for (Map.Entry<String, LiveDevice> entry : new ArrayList<>(activeDevicesByLabel.entrySet())) {
            DeviceRecord deviceRecord = deviceCatalog.deviceRecord(entry.getKey());
            if (deviceRecord.lifecycleKind() == DeviceLifecycleKind.SINGLETON) {
                continue;
            }
            entry.getValue().close();
        }
        String requestedLabel = activeSession.requestedLabel();
        String sessionId = activeSession.sessionId();
        updateRuntimeStateForDeactivate(activeSession);
        activeDevicesByLabel.clear();
        activeSession = null;
        lifecycleState = LifecycleState.INACTIVE;

        return new DeactivateResult(
                true,
                requestedLabel,
                sessionId,
                deactivatedLabels,
                lifecycleState,
                null,
                null);
    }

    private void rollback(
            Map<String, LiveDevice> createdDevices, Iterable<String> requestedLabels, String error) {
        List<Map.Entry<String, LiveDevice>> devicesToClose = new ArrayList<>(createdDevices.entrySet());
        for (int i = devicesToClose.size() - 1; i >= 0; i--) {
            Map.Entry<String, LiveDevice> entry = devicesToClose.get(i);
            DeviceRecord deviceRecord = deviceCatalog.deviceRecord(entry.getKey());
            if (deviceRecord.lifecycleKind() == DeviceLifecycleKind.SINGLETON) {
                continue;
            }
            entry.getValue().close();
        }
        updateRuntimeStateForFailedActivation(requestedLabels, error);
        createdDevices.clear();
        activeDevicesByLabel.clear();
        activeSession = null;
    }

    private LiveDevice activateDevice(DeviceRecord deviceRecord) {
        if (deviceRecord.lifecycleKind() == DeviceLifecycleKind.SINGLETON) {
            LiveDevice existingSingleton = singletonDevicesByLabel.get(deviceRecord.label());
            if (existingSingleton != null) {
                return existingSingleton;
            }
        }

        LiveDevice liveDevice = deviceFactory.create(deviceRecord);
        if (deviceRecord.lifecycleKind() == DeviceLifecycleKind.SINGLETON) {
            singletonDevicesByLabel.put(deviceRecord.label(), liveDevice);
        }
        return liveDevice;
    }

    private ActivationResult failedActivation(
            String requestedLabel,
            String sessionId,
            ActivationMode mode,
            List<String> requestedDeviceLabels,
            List<String> failedDeviceLabels,
            String errorCode,
            String errorMessage) {
        return new ActivationResult(
                false,
                requestedLabel,
                sessionId,
                mode,
                requestedDeviceLabels,
                List.of(),
                failedDeviceLabels,
                lifecycleState,
                errorCode,
                errorMessage);
    }

    private DeactivateResult failedDeactivate(
            String requestedLabel, String errorCode, String errorMessage) {
        return new DeactivateResult(
                false,
                requestedLabel,
                activeSession == null ? null : activeSession.sessionId(),
                List.of(),
                lifecycleState,
                errorCode,
                errorMessage);
    }

    private void updateRuntimeStateForSuccessfulActivation(ActivationSession session) {
        for (String label : session.requestedDeviceLabels()) {
            DeviceRuntimeState runtimeState = deviceCatalog.runtimeState(label);
            runtimeState.markActivated(
                    session.sessionId(), session.requestedLabel(), session.mode().name());
        }
    }

    private void updateRuntimeStateForDeactivate(ActivationSession session) {
        for (String label : session.requestedDeviceLabels()) {
            DeviceRecord deviceRecord = deviceCatalog.deviceRecord(label);
            DeviceRuntimeState runtimeState = deviceCatalog.runtimeState(label);
            runtimeState.markDeactivated(
                    deviceRecord.lifecycleKind() == DeviceLifecycleKind.SINGLETON);
        }
    }

    private void updateRuntimeStateForFailedActivation(Iterable<String> requestedLabels, String error) {
        for (String label : requestedLabels) {
            deviceCatalog.runtimeState(label).markActivationFailed(error);
        }
    }
}
