package frc.robot;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import edu.wpi.first.wpilibj.DriverStation;
import frc.robot.diag.lifecycle.activation.ActivationMode;
import frc.robot.diag.lifecycle.activation.ActivationMembershipMode;
import frc.robot.diag.lifecycle.activation.ActivationResult;
import frc.robot.diag.lifecycle.activation.ActivationSession;
import frc.robot.diag.lifecycle.activation.DeactivateResult;
import frc.robot.diag.lifecycle.activation.LifecycleState;
import frc.robot.diag.lifecycle.devices.DeviceRecord;
import frc.robot.diag.lifecycle.integration.ControlledBringupLifecycleRuntime;
import frc.robot.diag.lifecycle.integration.LifecycleCatalogBundle;
import frc.robot.diag.lifecycle.integration.LifecycleProfileTopologyAdapter;
import frc.robot.diag.probe.ActiveDevicePresenceProbe;
import frc.robot.diag.lifecycle.runtime.DeviceRuntimeState;
import frc.robot.telemetry.SampledTelemetrySampler;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import frc.robot.devices.DeviceUnit;

/**
 * NAME
 *   BringupRuntime - Shared owner for active bringup runtime state.
 *
 * DESCRIPTION
 *   Provides the single current BringupCore, DiagnosticsReporter, bridge group
 *   state, and selected-device state used by Xbox, CLI, and UI entry points.
 */
public final class BringupRuntime {
  private static final String COMMAND_RUN_TEST = "runTest";
  private static final String GROUP_ACTIVE = "active-group";
  private static final String GROUP_DEFAULT = "defaultGroup";
  private static final String SCOPE_LABEL_SELECTED_TEST_PREFIX = "selected-test:";
  private static final String TYPE_PDH = "PDH";
  private static final String TYPE_PDP = "PDP";
  private static final String TYPE_ROBORIO = "roboRIO";
  private static final String TYPE_XBOX_CONTROLLER = "xboxController";
  private static final String TEXT_EMPTY = "";
  private static final double BINDING_VALUE_ANALOG = 0.0;
  private static final String JSON_KEY_AVAILABLE = "available";
  private static final String JSON_KEY_PROFILE = "profile";
  private static final String JSON_KEY_STATE = "state";
  private static final String JSON_KEY_ACTIVE_SESSION = "activeSession";
  private static final String JSON_KEY_SESSION_ID = "sessionId";
  private static final String JSON_KEY_REQUESTED_LABEL = "requestedLabel";
  private static final String JSON_KEY_REQUESTED_DEVICE_LABELS = "requestedDeviceLabels";
  private static final String JSON_KEY_MODE = "mode";
  private static final String JSON_KEY_ACTIVE_DEVICE_LABELS = "activeDeviceLabels";
  private static final String JSON_KEY_DEVICES = "devices";
  private static final String JSON_KEY_LABEL = "label";
  private static final String JSON_KEY_LIFECYCLE_KIND = "lifecycleKind";
  private static final String JSON_KEY_INSTANTIATED = "instantiated";
  private static final String JSON_KEY_ACTIVE = "active";
  private static final String JSON_KEY_ACTIVE_SESSION_ID = "activeSessionId";
  private static final String JSON_KEY_ACTIVE_GROUP_LABEL = "activeGroupLabel";
  private static final String JSON_KEY_LAST_ACTIVATION_MODE = "lastActivationMode";
  private static final String JSON_KEY_LAST_ERROR = "lastError";
  private static final String JSON_KEY_PRESENCE_STATE = "presenceState";
  private static final String JSON_KEY_HEALTH_STATE = "healthState";
  private static final String TEXT_LIFECYCLE_HEADER = "=== Controlled Lifecycle ===";
  private static final String TEXT_LIFECYCLE_FOOTER = "============================";
  private static final String TEXT_LIFECYCLE_UNAVAILABLE = "Controlled lifecycle unavailable.";
  private static final String TEXT_ACTIVE_DEVICES_PREFIX = "activeDevices=";
  private static final String TEXT_SESSION_PREFIX = "session=";
  private static final String TEXT_MODE_PREFIX = " mode=";
  private static final String TEXT_REQUESTED_LABEL_PREFIX = " requestedLabel=";
  private static final String TEXT_STATE_PREFIX = "state=";
  private static final String TEXT_PROFILE_PREFIX = "profile=";
  private static final String TEXT_AVAILABLE_PREFIX = "available=";
  private static final String TEXT_DEVICE_PREFIX = "  ";
  private static final String TEXT_KIND_PREFIX = " kind=";
  private static final String TEXT_INSTANTIATED_PREFIX = " instantiated=";
  private static final String TEXT_ACTIVE_PREFIX = " active=";
  private static final String TEXT_LAST_ERROR_PREFIX = " lastError=";
  private static final String TEXT_NONE = "(none)";
  private static final String ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE =
      "Controlled lifecycle runtime unavailable.";
  private static final String ERROR_NO_SELECTED_TEST = "no selected test";
  private static final String ERROR_NO_RUNNABLE_REQUESTED_DEVICES =
      "NO_RUNNABLE_REQUESTED_DEVICES";
  private static final String ERROR_REQUESTED_DEVICES_NOT_RUNNABLE =
      "REQUESTED_DEVICES_NOT_RUNNABLE";
  private static final String ERROR_WRONG_SCOPE_OWNER_PREFIX = "wrong scope owner - ";
  private static final String ERROR_WRONG_SCOPE_OWNER_ACTIVE_GROUP = "active-group is active";
  private static final String ERROR_WRONG_SCOPE_OWNER_NO_ACTIVE_SCOPE = "no active scope";
  private static final String TEXT_UNAVAILABLE_MEMBERS_PREFIX = "Unavailable members: ";
  private static final String TEXT_EXCLUDED_MEMBERS_PREFIX = "Excluded members: ";
  private static final String TEXT_LIFECYCLE_REASON_NOT_IN_SCOPE =
      "Device is not in scope.";
  private static final String TEXT_LIFECYCLE_REASON_NO_PRESENCE =
      "Presence score below threshold; device is not present.";
  private static final String TEXT_LIFECYCLE_REASON_NOT_INSTANTIATED =
      "Runtime object is not instantiated.";
  private static final String TEXT_LIFECYCLE_STATE_DEFINED = "defined";
  private static final String TEXT_LIFECYCLE_STATE_DEFINED_PRESENT = "defined-present";
  private static final String TEXT_LIFECYCLE_STATE_DEFINED_STALE = "defined-stale";
  private static final String TEXT_LIFECYCLE_STATE_IN_SCOPE = "in-scope";
  private static final String TEXT_LIFECYCLE_STATE_IN_SCOPE_PRESENT = "in-scope-present";
  private static final int ACTIVATION_MEMBER_MESSAGE_LIMIT = 3;
  private static final long PERIODIC_LIFECYCLE_REFRESH_ENABLED_MS = 250L;
  private static final long PERIODIC_LIFECYCLE_REFRESH_DISABLED_MS = 1000L;

  private final CanBusHealth canHealth;
  private final String runTestBindingLabel;
  private final BridgeGroupManager bridgeGroups = new BridgeGroupManager();
  private final BridgeGroupManager.SelectedState bridgeSelected =
      new BridgeGroupManager.SelectedState();
  private final SampledTelemetrySampler sampledTelemetry = new SampledTelemetrySampler();
  private final DeviceLifecycleRegistry deviceLifecycle = new DeviceLifecycleRegistry();
  private LifecycleCatalogBundle controlledBringupLifecycle;
  private ControlledBringupLifecycleRuntime controlledBringupLifecycleRuntime;
  private long lastPeriodicLifecycleRefreshMs = Long.MIN_VALUE;

  private BringupCore core;
  private DiagnosticsReporter diagnostics;

  /**
   * NAME
   *   BringupRuntime - Construct runtime state around diagnostics dependencies.
   *
   * PARAMETERS
   *   canHealth - CAN health sampler.
   *   runTestBindingLabel - Human-readable hold-to-run binding label.
   */
  public BringupRuntime(
      CanBusHealth canHealth,
      String runTestBindingLabel) {
    this.canHealth = canHealth;
    this.runTestBindingLabel =
        runTestBindingLabel != null && !runTestBindingLabel.isBlank()
            ? runTestBindingLabel
            : COMMAND_RUN_TEST;
    replaceCore();
  }

  /**
   * NAME
   *   getCore - Return the current active BringupCore.
   */
  public BringupCore getCore() {
    return core;
  }

  /**
   * NAME
   *   getDiagnostics - Return the current diagnostics reporter.
   */
  public DiagnosticsReporter getDiagnostics() {
    return diagnostics;
  }

  /**
   * NAME
   *   getSampledTelemetry - Return the shared sampled-telemetry service.
   */
  public SampledTelemetrySampler getSampledTelemetry() {
    return sampledTelemetry;
  }

  /**
   * NAME
   *   getDeviceLifecycle - Return the shared device lifecycle registry.
   */
  public DeviceLifecycleRegistry getDeviceLifecycle() {
    return deviceLifecycle;
  }

  /**
   * NAME
   *   getControlledBringupLifecycle - Return the passive controlled-bringup lifecycle catalogs.
   *
   * RETURNS
   *   Current lifecycle catalog bundle rebuilt from the selected or active profile.
   */
  public LifecycleCatalogBundle getControlledBringupLifecycle() {
    return controlledBringupLifecycle;
  }

  /**
   * NAME
   *   getControlledBringupLifecycleRuntime - Return the internal lifecycle runtime wrapper.
   *
   * RETURNS
   *   Internal activation-manager wrapper bound to the current core and profile catalogs.
   */
  public ControlledBringupLifecycleRuntime getControlledBringupLifecycleRuntime() {
    return controlledBringupLifecycleRuntime;
  }

  /**
   * NAME
   *   activateControlledBringupLifecycle - Activate one lifecycle device/group label.
   *
   * PARAMETERS
   *   label - Requested lifecycle label.
   *   mode - Requested activation mode.
   *
   * RETURNS
   *   Activation result from the controlled lifecycle runtime.
   */
  public ActivationResult activateControlledBringupLifecycle(
      String label, ActivationMode mode, ActivationMembershipMode membershipMode) {
    synchronizeControlledBringupLifecycleGroups();
    ControlledBringupLifecycleRuntime lifecycleRuntime = controlledBringupLifecycleRuntime;
    if (lifecycleRuntime == null) {
      return new ActivationResult(
          false,
          label,
          null,
          mode,
          membershipMode,
          List.of(),
          List.of(),
          List.of(),
          List.of(),
          LifecycleState.INACTIVE,
          ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE,
          ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE);
    }
    refreshDeviceLifecycle(System.currentTimeMillis());
    List<String> requestedDeviceLabels;
    try {
      requestedDeviceLabels = lifecycleRuntime.activationManager().resolveRequestedDeviceLabels(label);
    } catch (RuntimeException exception) {
      return new ActivationResult(
          false,
          label,
          null,
          mode,
          membershipMode,
          List.of(),
          List.of(),
          List.of(),
          List.of(),
          currentLifecycleState(),
          ERROR_REQUESTED_DEVICES_NOT_RUNNABLE,
          exception.getMessage());
    }
    ActivationMemberSelection selection =
        selectActivationMembers(
            membershipMode,
            requestedDeviceLabels,
            this::isLifecycleDeviceEligibleForActivation);
    if (!selection.allowActivation()) {
      return new ActivationResult(
          false,
          label,
          null,
          mode,
          membershipMode,
          requestedDeviceLabels,
          List.of(),
          List.of(),
          selection.skippedDeviceLabels(),
          currentLifecycleState(),
          selection.errorCode(),
          selection.errorMessage());
    }
    ActivationResult result =
        lifecycleRuntime
            .activationManager()
            .activateResolved(
                label,
                selection.attemptedDeviceLabels(),
                mode,
                membershipMode,
                selection.skippedDeviceLabels());
    refreshDeviceLifecycle(System.currentTimeMillis());
    return result;
  }

  /**
   * NAME
   *   activateSelectedTestDevices - Reconcile lifecycle scope to the currently selected test.
   *
   * PARAMETERS
   *   mode - Requested activation mode.
   *
   * RETURNS
   *   Activation result for the transient selected-test lifecycle scope.
   */
  public ActivationResult activateSelectedTestDevices(
      ActivationMode mode, ActivationMembershipMode membershipMode) {
    synchronizeControlledBringupLifecycleGroups();
    ControlledBringupLifecycleRuntime lifecycleRuntime = controlledBringupLifecycleRuntime;
    String selectedTestName = selectedBringupTestName();
    if (selectedTestName.isBlank()) {
      return new ActivationResult(
          false,
          buildSelectedTestScopeLabel(TEXT_EMPTY),
          null,
          mode,
          membershipMode,
          List.of(),
          List.of(),
          List.of(),
          List.of(),
          currentLifecycleState(),
          ERROR_NO_SELECTED_TEST,
          ERROR_NO_SELECTED_TEST);
    }
    if (lifecycleRuntime == null) {
      return new ActivationResult(
          false,
          buildSelectedTestScopeLabel(selectedTestName),
          null,
          mode,
          membershipMode,
          List.of(),
          List.of(),
          List.of(),
          List.of(),
          LifecycleState.INACTIVE,
          ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE,
          ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE);
    }
    if (lifecycleRuntime.activationManager().getActiveSession().isPresent()) {
      DeactivateResult deactivateResult = lifecycleRuntime.activationManager().deactivateActive();
      if (!deactivateResult.success()) {
        refreshDeviceLifecycle(System.currentTimeMillis());
        return new ActivationResult(
            false,
            buildSelectedTestScopeLabel(selectedTestName),
            deactivateResult.sessionId(),
            mode,
            membershipMode,
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            currentLifecycleState(),
            deactivateResult.errorCode(),
            deactivateResult.errorMessage());
      }
    }
    String scopeLabel = buildSelectedTestScopeLabel(selectedTestName);
    List<String> requiredDevices = selectedBringupTestRequiredDevices();
    refreshDeviceLifecycle(System.currentTimeMillis());
    ActivationMemberSelection selection =
        selectActivationMembers(
            membershipMode,
            requiredDevices,
            this::isLifecycleDeviceEligibleForActivation);
    if (!selection.allowActivation()) {
      return new ActivationResult(
          false,
          scopeLabel,
          null,
          mode,
          membershipMode,
          requiredDevices,
          List.of(),
          List.of(),
          selection.skippedDeviceLabels(),
          currentLifecycleState(),
          selection.errorCode(),
          selection.errorMessage());
    }
    ensureDynamicLifecycleGroup(scopeLabel, selection.attemptedDeviceLabels());
    ActivationResult result =
        lifecycleRuntime
            .activationManager()
            .activateResolved(
                scopeLabel,
                selection.attemptedDeviceLabels(),
                mode,
                membershipMode,
                selection.skippedDeviceLabels());
    refreshDeviceLifecycle(System.currentTimeMillis());
    return result;
  }

  /**
   * NAME
   *   deactivateControlledBringupLifecycle - Deactivate the lifecycle session matching one label.
   *
   * PARAMETERS
   *   label - Requested lifecycle label.
   *
   * RETURNS
   *   Deactivation result from the controlled lifecycle runtime.
   */
  public DeactivateResult deactivateControlledBringupLifecycle(String label) {
    synchronizeControlledBringupLifecycleGroups();
    ControlledBringupLifecycleRuntime lifecycleRuntime = controlledBringupLifecycleRuntime;
    if (lifecycleRuntime == null) {
      return new DeactivateResult(
          false,
          label,
          null,
          List.of(),
          LifecycleState.INACTIVE,
          ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE,
          ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE);
    }
    DeactivateResult result = lifecycleRuntime.activationManager().deactivate(label);
    refreshDeviceLifecycle(System.currentTimeMillis());
    return result;
  }

  /**
   * NAME
   *   deactivateActiveControlledBringupLifecycle - Deactivate the current active lifecycle session.
   *
   * RETURNS
   *   Deactivation result from the controlled lifecycle runtime.
   */
  public DeactivateResult deactivateActiveControlledBringupLifecycle() {
    synchronizeControlledBringupLifecycleGroups();
    ControlledBringupLifecycleRuntime lifecycleRuntime = controlledBringupLifecycleRuntime;
    if (lifecycleRuntime == null) {
      return new DeactivateResult(
          false,
          null,
          null,
          List.of(),
          LifecycleState.INACTIVE,
          ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE,
          ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE);
    }
    if (lifecycleRuntime.activationManager().lifecycleState() == LifecycleState.INACTIVE) {
      return new DeactivateResult(
          true,
          GROUP_ACTIVE,
          null,
          List.of(),
          LifecycleState.INACTIVE,
          null,
          null);
    }
    DeactivateResult result = lifecycleRuntime.activationManager().deactivateActive();
    refreshDeviceLifecycle(System.currentTimeMillis());
    return result;
  }

  /**
   * NAME
   *   deactivateSelectedTestDevices - Deactivate the current selected-test-owned lifecycle scope.
   *
   * RETURNS
   *   Deactivation result or a wrong-owner failure when manual scope owns runtime.
   */
  public DeactivateResult deactivateSelectedTestDevices() {
    synchronizeControlledBringupLifecycleGroups();
    ControlledBringupLifecycleRuntime lifecycleRuntime = controlledBringupLifecycleRuntime;
    if (lifecycleRuntime == null) {
      return new DeactivateResult(
          false,
          null,
          null,
          List.of(),
          LifecycleState.INACTIVE,
          ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE,
          ERROR_CONTROLLED_LIFECYCLE_UNAVAILABLE);
    }
    String activeLabel = activeLifecycleRequestedLabel();
    if (!isSelectedTestScopeLabel(activeLabel)) {
      return new DeactivateResult(
          false,
          activeLabel,
          null,
          List.of(),
          currentLifecycleState(),
          ERROR_WRONG_SCOPE_OWNER_PREFIX + activeScopeOwnerText(activeLabel),
          ERROR_WRONG_SCOPE_OWNER_PREFIX + activeScopeOwnerText(activeLabel));
    }
    DeactivateResult result = lifecycleRuntime.activationManager().deactivateActive();
    refreshDeviceLifecycle(System.currentTimeMillis());
    cleanupInactiveSelectedTestLifecycleGroups();
    return result;
  }

  /**
   * NAME
   *   buildControlledBringupLifecycleText - Build human-readable controlled lifecycle state.
   *
   * RETURNS
   *   Multiline text snapshot of the current internal lifecycle runtime.
   */
  public String buildControlledBringupLifecycleText() {
    synchronizeControlledBringupLifecycleGroups();
    ControlledBringupLifecycleRuntime lifecycleRuntime = controlledBringupLifecycleRuntime;
    StringBuilder sb = new StringBuilder(512);
    ReportTextUtil.appendLine(sb, TEXT_LIFECYCLE_HEADER);
    if (lifecycleRuntime == null) {
      ReportTextUtil.appendLine(sb, TEXT_LIFECYCLE_UNAVAILABLE);
      ReportTextUtil.appendLine(sb, TEXT_LIFECYCLE_FOOTER);
      return sb.toString();
    }
    ReportTextUtil.appendLine(
        sb,
        TEXT_AVAILABLE_PREFIX + true);
    ReportTextUtil.appendLine(
        sb,
        TEXT_PROFILE_PREFIX + (lifecycleRuntime.catalogBundle().profileName() != null
            ? lifecycleRuntime.catalogBundle().profileName()
            : TEXT_EMPTY));
    ReportTextUtil.appendLine(
        sb,
        TEXT_STATE_PREFIX + lifecycleRuntime.activationManager().lifecycleState().name());
    ActivationSession activeSession =
        lifecycleRuntime.activationManager().getActiveSession().orElse(null);
    if (activeSession == null) {
      ReportTextUtil.appendLine(sb, TEXT_SESSION_PREFIX + TEXT_NONE);
    } else {
      ReportTextUtil.appendLine(
          sb,
          TEXT_SESSION_PREFIX
              + activeSession.sessionId()
              + TEXT_REQUESTED_LABEL_PREFIX
              + activeSession.requestedLabel()
              + TEXT_MODE_PREFIX
              + activeSession.mode().name());
    }
    ReportTextUtil.appendLine(
        sb,
        TEXT_ACTIVE_DEVICES_PREFIX + formatLabelList(lifecycleRuntime.activationManager().activeDeviceLabels()));
    for (DeviceRecord record : lifecycleRuntime.catalogBundle().deviceCatalog().deviceRecords()) {
      DeviceRuntimeState runtimeState =
          lifecycleRuntime.catalogBundle().deviceCatalog().runtimeState(record.label());
      ReportTextUtil.appendLine(
          sb,
          TEXT_DEVICE_PREFIX
              + record.label()
              + TEXT_KIND_PREFIX
              + record.lifecycleKind().name()
              + TEXT_INSTANTIATED_PREFIX
              + runtimeState.isInstantiated()
              + TEXT_ACTIVE_PREFIX
              + runtimeState.isActive()
              + TEXT_LAST_ERROR_PREFIX
              + (runtimeState.lastError() != null ? runtimeState.lastError() : TEXT_EMPTY));
    }
    ReportTextUtil.appendLine(sb, TEXT_LIFECYCLE_FOOTER);
    return sb.toString();
  }

  /**
   * NAME
   *   buildControlledBringupLifecycleJson - Build machine-readable controlled lifecycle state.
   *
   * RETURNS
   *   JSON snapshot of the current internal lifecycle runtime.
   */
  public JsonObject buildControlledBringupLifecycleJson() {
    synchronizeControlledBringupLifecycleGroups();
    JsonObject root = new JsonObject();
    ControlledBringupLifecycleRuntime lifecycleRuntime = controlledBringupLifecycleRuntime;
    root.addProperty(JSON_KEY_AVAILABLE, lifecycleRuntime != null);
    if (lifecycleRuntime == null) {
      root.addProperty(JSON_KEY_STATE, LifecycleState.INACTIVE.name());
      return root;
    }
    root.addProperty(
        JSON_KEY_PROFILE,
        lifecycleRuntime.catalogBundle().profileName() != null
            ? lifecycleRuntime.catalogBundle().profileName()
            : TEXT_EMPTY);
    root.addProperty(JSON_KEY_STATE, lifecycleRuntime.activationManager().lifecycleState().name());
    ActivationSession activeSession =
        lifecycleRuntime.activationManager().getActiveSession().orElse(null);
    if (activeSession != null) {
      JsonObject session = new JsonObject();
      session.addProperty(JSON_KEY_SESSION_ID, activeSession.sessionId());
      session.addProperty(JSON_KEY_REQUESTED_LABEL, activeSession.requestedLabel());
      session.addProperty(JSON_KEY_MODE, activeSession.mode().name());
      session.add(JSON_KEY_REQUESTED_DEVICE_LABELS, toJsonArray(activeSession.requestedDeviceLabels()));
      root.add(JSON_KEY_ACTIVE_SESSION, session);
    }
    root.add(
        JSON_KEY_ACTIVE_DEVICE_LABELS,
        toJsonArray(lifecycleRuntime.activationManager().activeDeviceLabels()));
    JsonArray devices = new JsonArray();
    for (DeviceRecord record : lifecycleRuntime.catalogBundle().deviceCatalog().deviceRecords()) {
      DeviceRuntimeState runtimeState =
          lifecycleRuntime.catalogBundle().deviceCatalog().runtimeState(record.label());
      JsonObject device = new JsonObject();
      device.addProperty(JSON_KEY_LABEL, record.label());
      device.addProperty(JSON_KEY_LIFECYCLE_KIND, record.lifecycleKind().name());
      device.addProperty(JSON_KEY_INSTANTIATED, runtimeState.isInstantiated());
      device.addProperty(JSON_KEY_ACTIVE, runtimeState.isActive());
      device.addProperty(JSON_KEY_ACTIVE_SESSION_ID, safeText(runtimeState.activeSessionId()));
      device.addProperty(JSON_KEY_ACTIVE_GROUP_LABEL, safeText(runtimeState.activeGroupLabel()));
      device.addProperty(JSON_KEY_LAST_ACTIVATION_MODE, safeText(runtimeState.lastActivationMode()));
      device.addProperty(JSON_KEY_LAST_ERROR, safeText(runtimeState.lastError()));
      device.addProperty(JSON_KEY_PRESENCE_STATE, runtimeState.presenceState().name());
      device.addProperty(JSON_KEY_HEALTH_STATE, runtimeState.healthState().name());
      devices.add(device);
    }
    root.add(JSON_KEY_DEVICES, devices);
    return root;
  }

  /**
   * NAME
   *   getBridgeGroups - Return shared bridge group state.
   */
  public BridgeGroupManager getBridgeGroups() {
    return bridgeGroups;
  }

  /**
   * NAME
   *   getBridgeSelected - Return shared selected-device state.
   */
  public BridgeGroupManager.SelectedState getBridgeSelected() {
    return bridgeSelected;
  }

  /**
   * NAME
   *   resetDiagnostics - Clear diagnostics accumulators.
   */
  public void resetDiagnostics() {
    if (diagnostics != null) {
      diagnostics.resetState();
    }
  }

  /**
   * NAME
   *   isRuntimeDeclaredActive - Return whether profile metadata marks runtime active.
   *
   * RETURNS
   *   True when BringupUtil currently marks an active runtime profile.
   */
  public boolean isRuntimeDeclaredActive() {
    return BringupUtil.isProfileActive();
  }

  /**
   * NAME
   *   isRuntimeReady - Return whether runtime is active and usable for actuation.
   *
   * RETURNS
   *   True when runtime metadata is active and the current core has realized
   *   the active profile into instantiated devices for every configured active
   *   device. Profiles with zero active devices are treated as ready once
   *   activated.
   */
  public boolean isRuntimeReady() {
    if (!BringupUtil.isProfileActive()) {
      return false;
    }
    if (BringupUtil.getActiveDevicesSorted().isEmpty()) {
      return true;
    }
    return core != null && core.hasAllActiveDevicesCreated();
  }

  /**
   * NAME
   *   isControlledLifecycleActive - Return whether a controlled lifecycle session is active.
   *
   * RETURNS
   *   True when the controlled lifecycle activation manager currently reports
   *   ACTIVE.
   */
  public boolean isControlledLifecycleActive() {
    ControlledBringupLifecycleRuntime lifecycleRuntime = controlledBringupLifecycleRuntime;
    return lifecycleRuntime != null
        && lifecycleRuntime.activationManager().lifecycleState() == LifecycleState.ACTIVE;
  }

  /**
   * NAME
   *   isSelectedProfileRuntimeReady - Return whether the selected profile is already active and usable.
   *
   * RETURNS
   *   True when the selected profile matches the active runtime profile and the
   *   runtime is ready for use.
   */
  public boolean isSelectedProfileRuntimeReady() {
    String selectedProfile = BringupUtil.getSelectedCanProfile();
    String activeProfile = BringupUtil.getActiveRuntimeProfileLabel();
    if (selectedProfile == null || selectedProfile.isBlank()) {
      return false;
    }
    if (!selectedProfile.equals(activeProfile)) {
      return false;
    }
    return isRuntimeReady();
  }

  /**
   * NAME
   *   updateDiagnostics - Update diagnostics publishers.
   */
  public void updateDiagnostics() {
    if (diagnostics != null) {
      diagnostics.update();
    }
  }

  /**
   * NAME
   *   sampleTelemetry - Advance robot-side sampled telemetry for active devices.
   */
  public void sampleTelemetry(long nowMs) {
    List<DeviceUnit> devices = Collections.emptyList();
    if (core != null && BringupUtil.isProfileActive()) {
      List<DeviceUnit> activeDevices = new java.util.ArrayList<>();
      for (BringupUtil.DeviceEntry entry : BringupUtil.getActiveDevicesSorted()) {
        if (entry == null || entry.label == null || entry.label.isBlank()) {
          continue;
        }
        DeviceUnit device = core.findDeviceByLabel(entry.label);
        if (device == null || !device.isCreated()) {
          continue;
        }
        activeDevices.add(device);
      }
      devices = activeDevices;
    }
    sampledTelemetry.sampleDevices(devices, nowMs);
    long refreshPeriodMs = DriverStation.isEnabled()
        ? PERIODIC_LIFECYCLE_REFRESH_ENABLED_MS
        : PERIODIC_LIFECYCLE_REFRESH_DISABLED_MS;
    if (lastPeriodicLifecycleRefreshMs == Long.MIN_VALUE
        || (nowMs - lastPeriodicLifecycleRefreshMs) >= refreshPeriodMs) {
      refreshDeviceLifecycle(nowMs);
      lastPeriodicLifecycleRefreshMs = nowMs;
    }
  }

  /**
   * NAME
   *   addMotor - Apply the add-next-motor action.
   */
  public void addMotor(boolean addNow) {
    if (core != null) {
      core.handleAdd(addNow);
    }
  }

  /**
   * NAME
   *   addAllDevices - Apply the add-all-devices action.
   */
  public void addAllDevices(boolean addAllNow) {
    if (core != null) {
      core.handleAddAll(addAllNow);
    }
  }

  /**
   * NAME
   *   addNextMotorCommand - Instantiate the next configured motor.
   */
  public void addNextMotorCommand() {
    if (core != null) {
      core.addNextMotorCommand();
    }
  }

  /**
   * NAME
   *   addAllDevicesCommand - Instantiate all configured devices.
   */
  public void addAllDevicesCommand() {
    if (core != null) {
      core.addAllDevicesCommand();
    }
  }

  /**
   * NAME
   *   selectPreviousTest - Select previous bringup test.
   */
  public void selectPreviousTest() {
    if (core != null) {
      core.selectPrevBringupTest();
    }
  }

  /**
   * NAME
   *   selectNextTest - Select next bringup test.
   */
  public void selectNextTest() {
    if (core != null) {
      core.selectNextBringupTest();
    }
  }

  /**
   * NAME
   *   selectTestByName - Select bringup test by name.
   */
  public boolean selectTestByName(String testName) {
    return core != null && core.selectBringupTestByName(testName);
  }

  /**
   * NAME
   *   toggleSelectedTestEnabled - Toggle selected test enable state.
   */
  public Boolean toggleSelectedTestEnabled() {
    return core != null ? core.toggleSelectedBringupTestEnabled() : null;
  }

  /**
   * NAME
   *   runSelectedTest - Run the selected bringup test.
   */
  public BringupCore.TestRunSnapshot runSelectedTest() {
    if (core != null) {
      return core.runSelectedBringupTest();
    }
    return BringupCore.TestRunSnapshot.idle();
  }

  /**
   * NAME
   *   runAllTests - Run all enabled bringup tests.
   */
  public void runAllTests() {
    if (core != null) {
      core.runAllBringupTests();
    }
  }

  /**
   * NAME
   *   printNextTestReport - Queue the selected test report.
   */
  public void printNextTestReport() {
    if (core != null) {
      core.printNextTestReport();
    }
  }

  /**
   * NAME
   *   runActivePresenceProbe - Execute the one-shot active presence probe on the active runtime.
   *
   * RETURNS
   *   Probe session result, or null when no core is available.
   */
  public ActiveDevicePresenceProbe.ProbeSessionResult runActivePresenceProbe() {
    return core != null ? core.runActivePresenceProbe() : null;
  }

  /**
   * NAME
   *   clearAllFaults - Clear device faults.
   */
  public void clearAllFaults() {
    if (core != null) {
      core.clearAllFaults();
    }
  }

  /**
   * NAME
   *   runCanPingSweep - Queue a CAN ping sweep report.
   */
  public void runCanPingSweep() {
    if (core != null) {
      core.runCanPingSweep();
    }
  }

  /**
   * NAME
   *   handlePrint - Apply print-state input action.
   */
  public void handlePrint(boolean printNow) {
    if (core != null) {
      core.handlePrint(printNow);
    }
  }

  /**
   * NAME
   *   handleHealth - Apply health-report input action.
   */
  public void handleHealth(boolean healthNow) {
    if (core != null) {
      core.handleHealth(healthNow);
    }
  }

  /**
   * NAME
   *   handleCANCoder - Apply CANCoder-report input action.
   */
  public void handleCANCoder(boolean printNow) {
    if (core != null) {
      core.handleCANCoder(printNow);
    }
  }

  /**
   * NAME
   *   updateReportsAndTests - Advance report and test state machines.
   */
  public void updateReportsAndTests(boolean runHeld) {
    if (core != null) {
      core.updateReports();
      core.updateTests(runHeld);
    }
  }

  /**
   * NAME
   *   requestTextReport - Queue a report through the current core.
   */
  public void requestTextReport(String text, int batchSize) {
    if (core != null) {
      core.requestTextReport(text, batchSize);
    }
  }

  /**
   * NAME
   *   resetForProfile - Clear and rebuild all profile-derived runtime state.
   *
   * PARAMETERS
   *   reason - Reset reason label.
   *
   * SIDE EFFECTS
   *   Stops current devices/tests, replaces the core, clears runtime groups
   *   and selected device state, resets diagnostics, and validates CAN IDs.
   */
  public void resetForProfile(String reason) {
    if (core != null) {
      core.resetState(reason);
    }
    sampledTelemetry.clearAll();
    replaceCore();
    clearProfileScopedBridgeRuntimeState();
    if (diagnostics != null) {
      diagnostics.resetState();
    }
    BringupUtil.validateCanIds(BringupUtil.getActiveDevices());
  }

  /**
   * NAME
   *   resetAndInstantiateForProfile - Rebuild runtime and instantiate devices.
   *
   * PARAMETERS
   *   reason - Reset reason label.
   *
   * SIDE EFFECTS
   *   Performs a full profile runtime reset and creates every device in the
   *   active profile.
   */
  public void resetAndInstantiateForProfile(String reason) {
    PreservedActiveGroup preservedActiveGroup = preserveActiveGroup(bridgeGroups.getGroup(GROUP_ACTIVE));
    resetForProfile(reason);
    synchronizeProfileBridgeRuntimeConfig();
    restoreActiveGroup(bridgeGroups, preservedActiveGroup);
    if (core != null) {
      core.addAllDevicesCommand();
    }
    long nowMs = System.currentTimeMillis();
    initializeDeviceLifecycle(nowMs);
    refreshDeviceLifecycle(nowMs);
  }

  /**
   * NAME
   *   stageSelectedProfileForBringup - Load selected-profile device configs for incremental bringup.
   *
   * RETURNS
   *   Empty string on success, or an error message when staging fails.
   */
  public String stageSelectedProfileForBringup() {
    String error = BringupUtil.stageSelectedProfileForBringup();
    if (error != null && !error.isBlank()) {
      return error;
    }
    if (!BringupUtil.isProfileActive() && core != null) {
      core.syncProfileTopologyFromRegistry();
    }
    synchronizeProfileBridgeRuntimeConfig();
    return TEXT_EMPTY;
  }

  /**
   * NAME
   *   clearProfileScopedBridgeRuntimeState - Clear runtime-only bridge/group state.
   *
   * SIDE EFFECTS
   *   Removes dynamic group membership and selected-device runtime state so a
   *   profile reset or restart does not inherit stale session-scoped data.
   */
  public void clearProfileScopedBridgeRuntimeState() {
    bridgeGroups.clear();
    bridgeSelected.device = TEXT_EMPTY;
    bridgeSelected.enabled = false;
  }

  /**
   * NAME
   *   resetUiSessionRuntimeContext - Clear session-scoped bridge and lifecycle runtime state.
   *
   * SIDE EFFECTS
   *   Deactivates any active controlled lifecycle session, drops dynamic bridge
   *   runtime groups/selection, and rebuilds lifecycle catalogs from the current
   *   profile so a new UI session starts from a clean runtime context.
   */
  public void resetUiSessionRuntimeContext() {
    deactivateActiveControlledBringupLifecycle();
    clearProfileScopedBridgeRuntimeState();
    initializeDeviceLifecycle(System.currentTimeMillis());
  }

  /**
   * NAME
   *   applyAndActivateRegistry - Apply registry JSON and fully activate runtime.
   *
   * PARAMETERS
   *   rawJson - Full registry payload.
   *   activateProfile - Optional profile to activate.
   *
   * RETURNS
   *   Registry apply report.
   *
   * SIDE EFFECTS
   *   On successful activation, clears and rebuilds runtime state and
   *   instantiates every active profile device.
   */
  public BringupUtil.RegistryApplyReport applyAndActivateRegistry(
      String rawJson,
      String activateProfile,
      String reason) {
    BringupUtil.RegistryApplyReport report =
        BringupUtil.applyRegistryJson(rawJson, activateProfile);
    if (report.overallOk && activateProfile != null && !activateProfile.isBlank()) {
      resetAndInstantiateForProfile(reason);
    }
    return report;
  }

  /**
   * NAME
   *   activateSelectedProfile - Activate selected profile and rebuild runtime.
   *
   * PARAMETERS
   *   reason - Reset reason label.
   */
  public void activateSelectedProfile(String reason) {
    if (isSelectedProfileRuntimeReady()) {
      return;
    }
    BringupUtil.prepareActivationForSelectedProfile();
    BringupUtil.activateSelectedProfile();
    if (BringupUtil.isProfileActive()) {
      resetAndInstantiateForProfile(reason);
    }
  }

  /**
   * NAME
   *   ensureSelectedProfileRuntime - Activate selected profile when runtime is not ready.
   *
   * PARAMETERS
   *   reason - Reset reason label.
   *
   * RETURNS
   *   True when the selected profile ends in a ready runtime state.
   */
  public boolean ensureSelectedProfileRuntime(String reason) {
    if (!isSelectedProfileRuntimeReady()) {
      activateSelectedProfile(reason);
    }
    return isSelectedProfileRuntimeReady();
  }

  /**
   * NAME
   *   deactivateActiveProfile - Stop runtime-owned state and clear active runtime profile.
   *
   * PARAMETERS
   *   reason - Reset reason label.
   */
  public void deactivateActiveProfile(String reason) {
    deactivateActiveControlledBringupLifecycle();
    if (core != null) {
      core.resetState(reason);
    }
    BringupUtil.deactivateActiveProfile();
    sampledTelemetry.clearAll();
    replaceCore();
    bridgeSelected.device = TEXT_EMPTY;
    bridgeSelected.enabled = false;
    if (diagnostics != null) {
      diagnostics.resetState();
    }
    BringupUtil.validateCanIds(BringupUtil.getSelectedDevicesSorted());
  }

  /**
   * NAME
   *   initializeDeviceLifecycle - Rebuild lifecycle registry from profile devices plus runtime
   *   dynamic groups.
   *
   * PARAMETERS
   *   nowMs - Event timestamp.
   */
  public void initializeDeviceLifecycle(long nowMs) {
    String lifecycleProfileName = currentLifecycleProfileName();
    List<BringupUtil.DeviceEntry> entries = currentLifecycleProfileDevices();
    synchronizeBridgeRuntimeConfig(
        bridgeGroups,
        bridgeSelected,
        BringupUtil.getProfileBridgeConfig(lifecycleProfileName),
        entries);
    controlledBringupLifecycle =
        LifecycleProfileTopologyAdapter.build(
            lifecycleProfileName,
            entries,
            BringupUtil.getProfileBridgeConfig(lifecycleProfileName),
            bridgeGroups.getGroups());
    controlledBringupLifecycleRuntime =
        core != null
            ? ControlledBringupLifecycleRuntime.fromBringupCore(core, controlledBringupLifecycle)
            : null;
    deviceLifecycle.resetForProfile(lifecycleProfileName, entries, nowMs);
    refreshDeviceLifecycle(nowMs);
  }

  /**
   * NAME
   *   synchronizeControlledBringupLifecycleGroups - Sync runtime-only bridge groups into the
   *   current lifecycle catalogs without resetting lifecycle activation state.
   */
  public void synchronizeControlledBringupLifecycleGroups() {
    ensureLifecycleRuntimeGroupsDefined();
    if (controlledBringupLifecycle == null) {
      initializeDeviceLifecycle(System.currentTimeMillis());
      return;
    }
    LifecycleProfileTopologyAdapter.syncRuntimeGroups(
        controlledBringupLifecycle.groupCatalog(),
        bridgeGroups.getGroups(),
        preservedDynamicLifecycleLabels());
  }

  private void ensureLifecycleRuntimeGroupsDefined() {
    if (bridgeGroups.getGroup(GROUP_ACTIVE) == null) {
      bridgeGroups.createGroup(GROUP_ACTIVE);
    }
  }

  private List<String> preservedDynamicLifecycleLabels() {
    String activeLabel = activeLifecycleRequestedLabel();
    if (!isSelectedTestScopeLabel(activeLabel)) {
      return List.of();
    }
    return List.of(activeLabel);
  }

  private void ensureDynamicLifecycleGroup(String label, List<String> memberLabels) {
    if (controlledBringupLifecycle == null || label == null || label.isBlank()) {
      return;
    }
    if (!controlledBringupLifecycle.groupCatalog().hasGroupLabel(label)) {
      controlledBringupLifecycle.groupCatalog().createDynamicGroup(label);
    }
    controlledBringupLifecycle.groupCatalog().setDynamicGroupMembers(label, memberLabels);
  }

  private void cleanupInactiveSelectedTestLifecycleGroups() {
    if (controlledBringupLifecycle == null) {
      return;
    }
    for (frc.robot.diag.lifecycle.groups.GroupRecord groupRecord
        : controlledBringupLifecycle.groupCatalog().groupRecords()) {
      if (groupRecord == null || !isSelectedTestScopeLabel(groupRecord.label())) {
        continue;
      }
      if (groupRecord.state() == frc.robot.diag.lifecycle.groups.GroupState.INACTIVE) {
        controlledBringupLifecycle.groupCatalog().deleteDynamicGroup(groupRecord.label());
      }
    }
  }

  private String selectedBringupTestName() {
    if (core == null) {
      return TEXT_EMPTY;
    }
    String selectedName = core.getSelectedBringupTestName();
    return selectedName != null ? selectedName.trim() : TEXT_EMPTY;
  }

  private List<String> selectedBringupTestRequiredDevices() {
    if (core == null) {
      return List.of();
    }
    BringupCore.TestsOverview overview = core.buildTestsOverview();
    if (overview == null || overview.rows == null) {
      return List.of();
    }
    for (BringupCore.TestRow row : overview.rows) {
      if (row != null && row.selected && row.requiredDevices != null) {
        return List.copyOf(row.requiredDevices);
      }
    }
    return List.of();
  }

  private String buildSelectedTestScopeLabel(String testName) {
    return SCOPE_LABEL_SELECTED_TEST_PREFIX + safeText(testName);
  }

  private static boolean isSelectedTestScopeLabel(String label) {
    return label != null && label.startsWith(SCOPE_LABEL_SELECTED_TEST_PREFIX);
  }

  private String activeLifecycleRequestedLabel() {
    ControlledBringupLifecycleRuntime lifecycleRuntime = controlledBringupLifecycleRuntime;
    if (lifecycleRuntime == null) {
      return TEXT_EMPTY;
    }
    return lifecycleRuntime
        .activationManager()
        .getActiveSession()
        .map(ActivationSession::requestedLabel)
        .orElse(TEXT_EMPTY);
  }

  private LifecycleState currentLifecycleState() {
    ControlledBringupLifecycleRuntime lifecycleRuntime = controlledBringupLifecycleRuntime;
    if (lifecycleRuntime == null) {
      return LifecycleState.INACTIVE;
    }
    return lifecycleRuntime.activationManager().lifecycleState();
  }

  private String activeScopeOwnerText(String activeLabel) {
    if (activeLabel == null || activeLabel.isBlank()) {
      return ERROR_WRONG_SCOPE_OWNER_NO_ACTIVE_SCOPE;
    }
    if (GROUP_ACTIVE.equals(activeLabel)) {
      return ERROR_WRONG_SCOPE_OWNER_ACTIVE_GROUP;
    }
    return activeLabel + " is active";
  }

  /**
   * NAME
   *   synchronizeProfileBridgeRuntimeConfig - Rebuild bridge runtime groups from the current
   *   lifecycle profile config.
   *
   * SIDE EFFECTS
   *   Clears prior group/selected-device state, loads all profile-defined groups, falls back to
   *   the legacy default group when no groups are defined, and always recreates active-group.
   */
  private void synchronizeProfileBridgeRuntimeConfig() {
    synchronizeBridgeRuntimeConfig(
        bridgeGroups,
        bridgeSelected,
        BringupUtil.getProfileBridgeConfig(currentLifecycleProfileName()),
        currentLifecycleProfileDevices());
  }

  /**
   * NAME
   *   synchronizeBridgeRuntimeConfig - Rebuild runtime bridge groups from one profile config.
   *
   * PARAMETERS
   *   bridgeGroups - Runtime group manager to populate.
   *   bridgeSelected - Runtime selected-device state to populate.
   *   config - Profile-defined runtime group configuration.
   *   fallbackDevices - Device order used for the legacy default group when no groups are defined.
   */
  static void synchronizeBridgeRuntimeConfig(
      BridgeGroupManager bridgeGroups,
      BridgeGroupManager.SelectedState bridgeSelected,
      BringupUtil.BridgeProfileRuntimeConfig config,
      List<BringupUtil.DeviceEntry> fallbackDevices) {
    if (bridgeGroups == null || bridgeSelected == null) {
      return;
    }
    PreservedActiveGroup preservedActiveGroup = preserveActiveGroup(bridgeGroups.getGroup(GROUP_ACTIVE));
    bridgeGroups.clear();
    bridgeSelected.device = TEXT_EMPTY;
    bridgeSelected.enabled = false;
    BringupUtil.BridgeProfileRuntimeConfig resolvedConfig =
        config != null ? config : BringupUtil.BridgeProfileRuntimeConfig.empty();
    boolean loadedGroups = false;
    for (BringupUtil.BridgeProfileGroupConfig group : resolvedConfig.groups) {
      if (group == null || group.name == null || group.name.isBlank()) {
        continue;
      }
      bridgeGroups.createGroup(group.name);
      for (BringupUtil.BridgeProfileMemberConfig member : group.members) {
        if (member == null || member.label == null || member.label.isBlank()) {
          continue;
        }
        bridgeGroups.addMember(group.name, member.label, true);
        if (!member.enabled) {
          bridgeGroups.setMemberEnabled(group.name, member.label, false);
        }
      }
      for (BringupUtil.BridgeProfileBindingConfig binding : group.bindings) {
        if (binding == null || binding.input == null || binding.kind == null) {
          continue;
        }
        BridgeGroupManager.BindingKind kind = BridgeGroupManager.BindingKind.parse(binding.kind);
        if (kind == null) {
          continue;
        }
        double value = binding.hasValue ? binding.value : BINDING_VALUE_ANALOG;
        bridgeGroups.addBinding(group.name, binding.input, kind, value);
      }
      if (!group.enabled) {
        bridgeGroups.setGroupEnabled(group.name, false);
      }
      loadedGroups = true;
    }
    if (resolvedConfig.selectedDevice != null
        && resolvedConfig.selectedDevice.device != null
        && !resolvedConfig.selectedDevice.device.isBlank()) {
      bridgeSelected.device = resolvedConfig.selectedDevice.device;
      bridgeSelected.enabled = resolvedConfig.selectedDevice.enabled;
    }
    if (!loadedGroups) {
      bridgeGroups.syncGroupMembers(GROUP_DEFAULT, extractBridgeLabels(fallbackDevices));
    }
    if (bridgeGroups.getGroup(GROUP_ACTIVE) == null) {
      bridgeGroups.createGroup(GROUP_ACTIVE);
    }
    restoreActiveGroup(bridgeGroups, preservedActiveGroup);
  }

  static PreservedActiveGroup preserveActiveGroup(BridgeGroupManager.Group group) {
    if (group == null) {
      return PreservedActiveGroup.empty();
    }
    java.util.List<PreservedActiveMember> members = new java.util.ArrayList<>();
    for (BridgeGroupManager.MemberState member : group.members.values()) {
      if (member == null || member.label == null || member.label.isBlank()) {
        continue;
      }
      members.add(new PreservedActiveMember(member.label, member.enabled));
    }
    return new PreservedActiveGroup(group.enabled, members);
  }

  static void restoreActiveGroup(
      BridgeGroupManager bridgeGroups,
      PreservedActiveGroup preservedActiveGroup) {
    if (bridgeGroups == null || preservedActiveGroup == null || preservedActiveGroup.members.isEmpty()) {
      return;
    }
    BridgeGroupManager.Group activeGroup = bridgeGroups.getGroup(GROUP_ACTIVE);
    if (activeGroup == null || !activeGroup.members.isEmpty()) {
      return;
    }
    bridgeGroups.setGroupEnabled(GROUP_ACTIVE, preservedActiveGroup.enabled);
    for (PreservedActiveMember member : preservedActiveGroup.members) {
      if (member == null || member.label == null || member.label.isBlank()) {
        continue;
      }
      bridgeGroups.addMember(GROUP_ACTIVE, member.label, true);
      if (!member.enabled) {
        bridgeGroups.setMemberEnabled(GROUP_ACTIVE, member.label, false);
      }
    }
  }

  static final class PreservedActiveGroup {
    final boolean enabled;
    final java.util.List<PreservedActiveMember> members;

    PreservedActiveGroup(boolean enabled, java.util.List<PreservedActiveMember> members) {
      this.enabled = enabled;
      this.members = members != null ? members : java.util.List.of();
    }

    static PreservedActiveGroup empty() {
      return new PreservedActiveGroup(true, java.util.List.of());
    }
  }

  static final class PreservedActiveMember {
    final String label;
    final boolean enabled;

    PreservedActiveMember(String label, boolean enabled) {
      this.label = label;
      this.enabled = enabled;
    }
  }

  private static List<String> extractBridgeLabels(List<BringupUtil.DeviceEntry> devices) {
    List<String> labels = new java.util.ArrayList<>();
    if (devices == null) {
      return labels;
    }
    for (BringupUtil.DeviceEntry entry : devices) {
      if (entry == null || entry.label == null) {
        continue;
      }
      String label = entry.label.trim();
      if (!label.isBlank()) {
        labels.add(label);
      }
    }
    return labels;
  }

  /**
   * NAME
   *   refreshDeviceLifecycle - Refresh lifecycle states from current core snapshots.
   *
   * PARAMETERS
   *   nowMs - Event timestamp.
   */
  public void refreshDeviceLifecycle(long nowMs) {
    List<BringupUtil.DeviceEntry> entries = currentLifecycleProfileDevices();
    java.util.Map<String, frc.robot.diag.snapshots.DeviceSnapshot> snapshotsByLabel =
        new java.util.LinkedHashMap<>();
    java.util.Map<String, Boolean> instantiatedByLabel = new java.util.LinkedHashMap<>();
    java.util.Map<String, Boolean> inScopeByLabel = new java.util.LinkedHashMap<>();
    boolean runtimeActive = BringupUtil.isProfileActive();
    boolean controlledLifecycleActive =
        controlledBringupLifecycleRuntime != null
            && controlledBringupLifecycleRuntime.activationManager().lifecycleState()
                == LifecycleState.ACTIVE;
    for (BringupUtil.DeviceEntry entry : entries) {
      if (entry == null || entry.label == null || entry.label.isBlank()) {
        continue;
      }
      boolean singletonSupport = isLifecycleSingletonEntry(entry);
      frc.robot.diag.lifecycle.runtime.DeviceRuntimeState controlledState =
          controlledLifecycleRuntimeStateForLabel(entry.label);
      if (singletonSupport) {
        ensureSingletonLifecycleDeviceCreated(
            entry.label,
            shouldInstantiateLifecycleSingleton(
                runtimeActive, controlledLifecycleActive, controlledState));
      }
      inScopeByLabel.put(
          entry.label.trim().toLowerCase(),
          singletonSupport
              || resolveLifecycleDeviceInScope(
                  runtimeActive, controlledLifecycleActive, controlledState));
    }
    if (core != null) {
      for (BringupUtil.DeviceEntry entry : entries) {
        if (entry == null || entry.label == null || entry.label.isBlank()) {
          continue;
        }
        boolean singletonSupport = isLifecycleSingletonEntry(entry);
        frc.robot.devices.DeviceUnit device = core.findDeviceByLabel(entry.label);
        frc.robot.diag.lifecycle.runtime.DeviceRuntimeState controlledState =
            controlledLifecycleRuntimeStateForLabel(entry.label);
        String normalized = entry.label.trim().toLowerCase();
        boolean instantiated = isLifecycleDeviceInstantiated(entry, device);
        instantiatedByLabel.put(normalized, instantiated);
        boolean shouldCapture =
            singletonSupport
                ? instantiated
                : shouldCaptureLifecycleSnapshot(
                    runtimeActive, controlledLifecycleActive, instantiated, controlledState);
        if (!shouldCapture) {
          continue;
        }
        frc.robot.diag.snapshots.DeviceSnapshot snapshot =
            core.captureCreatedSnapshotForLabel(
                entry.label, frc.robot.diag.snapshots.SnapshotDetail.FULL);
        if (snapshot == null || snapshot.label == null || snapshot.label.isBlank()) {
          continue;
        }
        snapshotsByLabel.put(snapshot.label.trim().toLowerCase(), snapshot);
      }
    }
    deviceLifecycle.refresh(entries, snapshotsByLabel, instantiatedByLabel, inScopeByLabel, nowMs);
  }

  static boolean isLifecycleDeviceInstantiated(
      BringupUtil.DeviceEntry entry, frc.robot.devices.DeviceUnit device) {
    if (device == null) {
      return entry != null
          && isLifecycleSingletonEntry(entry)
          && BringupUtil.hasAppSingletonService(entry);
    }
    if (device.isCreated()) {
      return true;
    }
    return device.getLifecycleOwnership()
            == frc.robot.devices.DeviceLifecycleOwnership.APP_OWNED_SINGLETON_SERVICE
        && BringupUtil.hasAppSingletonService(device);
  }

  private void ensureSingletonLifecycleDeviceCreated(String label, boolean shouldInstantiate) {
    if (core == null || !shouldInstantiate || label == null || label.isBlank()) {
      return;
    }
    frc.robot.devices.DeviceUnit device = core.findDeviceByLabel(label);
    if (device == null || device.isCreated()) {
      return;
    }
    try {
      device.ensureCreated();
    } catch (RuntimeException ex) {
      // Leave lifecycle publication to report the device as unavailable.
    }
  }

  static boolean resolveLifecycleDeviceInScope(
      boolean runtimeActive,
      boolean controlledLifecycleActive,
      frc.robot.diag.lifecycle.runtime.DeviceRuntimeState controlledState) {
    if (controlledLifecycleActive) {
      return controlledState != null && controlledState.isActive();
    }
    return runtimeActive;
  }

  static boolean shouldCaptureLifecycleSnapshot(
      boolean runtimeActive,
      boolean controlledLifecycleActive,
      boolean instantiated,
      frc.robot.diag.lifecycle.runtime.DeviceRuntimeState controlledState) {
    if (!instantiated) {
      return false;
    }
    if (controlledLifecycleActive) {
      return controlledState != null && controlledState.isActive();
    }
    return runtimeActive;
  }

  static boolean shouldInstantiateLifecycleSingleton(
      boolean runtimeActive,
      boolean controlledLifecycleActive,
      frc.robot.diag.lifecycle.runtime.DeviceRuntimeState controlledState) {
    if (controlledLifecycleActive) {
      return controlledState != null && controlledState.isActive();
    }
    return runtimeActive;
  }

  static ActivationMemberSelection selectActivationMembers(
      ActivationMembershipMode membershipMode,
      List<String> requestedDeviceLabels,
      java.util.function.Predicate<String> runnableNow) {
    List<String> requested =
        requestedDeviceLabels == null ? List.of() : List.copyOf(requestedDeviceLabels);
    if (membershipMode == ActivationMembershipMode.FORCE) {
      return new ActivationMemberSelection(
          requested,
          requested,
          List.of(),
          true,
          TEXT_EMPTY,
          TEXT_EMPTY);
    }
    List<String> attempted = new ArrayList<>();
    List<String> skipped = new ArrayList<>();
    for (String label : requested) {
      if (runnableNow.test(label)) {
        attempted.add(label);
      } else {
        skipped.add(label);
      }
    }
    if (membershipMode == ActivationMembershipMode.STRICT && !skipped.isEmpty()) {
      return new ActivationMemberSelection(
          requested,
          List.of(),
          skipped,
          false,
          ERROR_REQUESTED_DEVICES_NOT_RUNNABLE,
          TEXT_UNAVAILABLE_MEMBERS_PREFIX + formatActivationMemberList(skipped));
    }
    if (membershipMode == ActivationMembershipMode.PARTIAL && attempted.isEmpty()) {
      return new ActivationMemberSelection(
          requested,
          List.of(),
          skipped,
          false,
          ERROR_NO_RUNNABLE_REQUESTED_DEVICES,
          TEXT_EXCLUDED_MEMBERS_PREFIX + formatActivationMemberList(skipped));
    }
    return new ActivationMemberSelection(
        requested,
        attempted,
        skipped,
        true,
        TEXT_EMPTY,
        TEXT_EMPTY);
  }

  private boolean isLifecycleDeviceEligibleForActivation(String label) {
    if (label == null || label.isBlank()) {
      return false;
    }
    DeviceLifecycleRegistry.DeviceLifecycleView lifecycle = deviceLifecycle.viewForLabel(label);
    return isLifecycleViewEligibleForActivation(lifecycle);
  }

  static boolean isLifecycleViewEligibleForActivation(
      DeviceLifecycleRegistry.DeviceLifecycleView lifecycle) {
    if (lifecycle == null) {
      return false;
    }
    if (lifecycle.testable) {
      return true;
    }
    String lifecycleState = lifecycle.lifecycleState != null ? lifecycle.lifecycleState : TEXT_EMPTY;
    String notTestableReason =
        lifecycle.notTestableReason != null ? lifecycle.notTestableReason : TEXT_EMPTY;
    if (TEXT_LIFECYCLE_REASON_NOT_IN_SCOPE.equals(notTestableReason)) {
      return TEXT_LIFECYCLE_STATE_DEFINED.equals(lifecycleState)
          || TEXT_LIFECYCLE_STATE_DEFINED_PRESENT.equals(lifecycleState)
          || TEXT_LIFECYCLE_STATE_DEFINED_STALE.equals(lifecycleState)
          || TEXT_LIFECYCLE_STATE_IN_SCOPE.equals(lifecycleState)
          || TEXT_LIFECYCLE_STATE_IN_SCOPE_PRESENT.equals(lifecycleState);
    }
    if (TEXT_LIFECYCLE_REASON_NO_PRESENCE.equals(notTestableReason)) {
      return false;
    }
    if (TEXT_LIFECYCLE_REASON_NOT_INSTANTIATED.equals(notTestableReason)) {
      return lifecycle.presenceScore > 0.0;
    }
    return lifecycle.presenceScore > 0.0;
  }

  private static String formatActivationMemberList(List<String> labels) {
    if (labels == null || labels.isEmpty()) {
      return TEXT_NONE;
    }
    List<String> parts = new ArrayList<>();
    int total = labels.size();
    int limit = Math.min(total, ACTIVATION_MEMBER_MESSAGE_LIMIT);
    for (int i = 0; i < limit; i++) {
      String label = labels.get(i);
      if (label != null && !label.isBlank()) {
        parts.add(label);
      }
    }
    if (total > limit) {
      parts.add("+" + (total - limit) + " more");
    }
    return String.join(", ", parts);
  }

  record ActivationMemberSelection(
      List<String> requestedDeviceLabels,
      List<String> attemptedDeviceLabels,
      List<String> skippedDeviceLabels,
      boolean allowActivation,
      String errorCode,
      String errorMessage) {
    ActivationMemberSelection {
      requestedDeviceLabels =
          requestedDeviceLabels == null ? List.of() : List.copyOf(requestedDeviceLabels);
      attemptedDeviceLabels =
          attemptedDeviceLabels == null ? List.of() : List.copyOf(attemptedDeviceLabels);
      skippedDeviceLabels =
          skippedDeviceLabels == null ? List.of() : List.copyOf(skippedDeviceLabels);
      errorCode = errorCode == null ? TEXT_EMPTY : errorCode;
      errorMessage = errorMessage == null ? TEXT_EMPTY : errorMessage;
    }
  }

  private frc.robot.diag.lifecycle.runtime.DeviceRuntimeState controlledLifecycleRuntimeStateForLabel(
      String label) {
    if (controlledBringupLifecycleRuntime == null || label == null || label.isBlank()) {
      return null;
    }
    try {
      return controlledBringupLifecycleRuntime.catalogBundle().deviceCatalog().runtimeState(label);
    } catch (IllegalArgumentException ex) {
      return null;
    }
  }

  private List<BringupUtil.DeviceEntry> currentLifecycleProfileDevices() {
    String profileName = currentLifecycleProfileName();
    if (profileName == null || profileName.isBlank()) {
      return Collections.emptyList();
    }
    return BringupUtil.getProfileDevicesSorted(profileName);
  }

  private String currentLifecycleProfileName() {
    return resolveLifecycleProfileName(
        BringupUtil.isProfileActive(),
        BringupUtil.getActiveRuntimeProfileLabel(),
        BringupUtil.getSelectedCanProfile(),
        BringupUtil.getDefaultCanProfile());
  }

  static String resolveLifecycleProfileName(
      boolean runtimeActive,
      String activeRuntimeProfileName,
      String selectedProfileName,
      String defaultProfileName) {
    if (runtimeActive) {
      String activeName = normalizeLifecycleProfileName(activeRuntimeProfileName);
      if (!activeName.isBlank()) {
        return activeName;
      }
    }
    String selectedName = normalizeLifecycleProfileName(selectedProfileName);
    if (!selectedName.isBlank()) {
      return selectedName;
    }
    String defaultName = normalizeLifecycleProfileName(defaultProfileName);
    if (!defaultName.isBlank()) {
      return defaultName;
    }
    return TEXT_EMPTY;
  }

  private static String normalizeLifecycleProfileName(String profileName) {
    if (profileName == null) {
      return TEXT_EMPTY;
    }
    String normalized = profileName.trim();
    if (normalized.isBlank() || TEXT_NONE.equals(normalized)) {
      return TEXT_EMPTY;
    }
    return normalized;
  }

  static boolean isLifecycleSingletonEntry(BringupUtil.DeviceEntry entry) {
    if (entry == null || entry.type == null) {
      return false;
    }
    String type = entry.type.trim();
    return TYPE_PDH.equalsIgnoreCase(type)
        || TYPE_PDP.equalsIgnoreCase(type)
        || TYPE_ROBORIO.equalsIgnoreCase(type)
        || TYPE_XBOX_CONTROLLER.equalsIgnoreCase(type);
  }

  private void replaceCore() {
    String selectedTestName =
        core != null ? safeText(core.getSelectedBringupTestName()) : TEXT_EMPTY;
    core = new BringupCore(sampledTelemetry, deviceLifecycle);
    core.setRunTestBindingLabel(runTestBindingLabel);
    restoreSelectedTestSelection(core, selectedTestName);
    if (diagnostics == null) {
      diagnostics = new DiagnosticsReporter(core, canHealth);
    } else {
      diagnostics.setCore(core);
    }
    initializeDeviceLifecycle(System.currentTimeMillis());
  }

  static void restoreSelectedTestSelection(BringupCore core, String selectedTestName) {
    if (core == null) {
      return;
    }
    String selectedName = selectedTestName != null ? selectedTestName.trim() : TEXT_EMPTY;
    if (!selectedName.isBlank()) {
      core.selectBringupTestByName(selectedName);
    }
  }

  private JsonArray toJsonArray(List<String> labels) {
    JsonArray array = new JsonArray();
    if (labels == null) {
      return array;
    }
    for (String label : labels) {
      if (label != null && !label.isBlank()) {
        array.add(label);
      }
    }
    return array;
  }

  private String formatLabelList(List<String> labels) {
    if (labels == null || labels.isEmpty()) {
      return TEXT_NONE;
    }
    return String.join(", ", labels);
  }

  private String safeText(String value) {
    return value != null ? value : TEXT_EMPTY;
  }
}
