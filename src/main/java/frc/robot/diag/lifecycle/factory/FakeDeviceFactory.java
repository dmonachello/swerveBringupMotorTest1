package frc.robot.diag.lifecycle.factory;

import frc.robot.diag.lifecycle.devices.DeviceRecord;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * NAME
 *     FakeDeviceFactory - fake lifecycle device factory used for activation and rollback tests.
 *
 * DESCRIPTION
 *     This factory records creation attempts, active devices, and close events so the activation
 *     manager tests can prove lifecycle behavior without vendor APIs.
 */
public final class FakeDeviceFactory implements DeviceFactory {
    private final List<String> createdLabels = new ArrayList<>();
    private final List<String> closedLabels = new ArrayList<>();
    private final Map<String, FakeLiveDevice> activeDevicesByLabel = new LinkedHashMap<>();
    private final Set<String> labelsConfiguredToFail = new LinkedHashSet<>();
    private final Map<String, Integer> creationAttemptsByLabel = new LinkedHashMap<>();

    @Override
    public LiveDevice create(DeviceRecord deviceRecord) {
        String label = deviceRecord.label();
        creationAttemptsByLabel.merge(label, 1, Integer::sum);

        if (labelsConfiguredToFail.contains(label)) {
            throw new FakeDeviceConstructionException(label);
        }

        FakeLiveDevice liveDevice =
                new FakeLiveDevice(
                        label,
                        () -> {
                            closedLabels.add(label);
                            activeDevicesByLabel.remove(label);
                        });
        createdLabels.add(label);
        activeDevicesByLabel.put(label, liveDevice);
        return liveDevice;
    }

    public void configureFailure(String label) {
        labelsConfiguredToFail.add(label);
    }

    public void clearFailure(String label) {
        labelsConfiguredToFail.remove(label);
    }

    public List<String> createdLabels() {
        return List.copyOf(createdLabels);
    }

    public List<String> closedLabels() {
        return List.copyOf(closedLabels);
    }

    public List<String> activeLabels() {
        return List.copyOf(activeDevicesByLabel.keySet());
    }

    public int activeDeviceCount() {
        return activeDevicesByLabel.size();
    }

    public int creationAttemptsFor(String label) {
        return creationAttemptsByLabel.getOrDefault(label, 0);
    }

    public int totalCreationAttempts() {
        return creationAttemptsByLabel.values().stream().mapToInt(Integer::intValue).sum();
    }
}
