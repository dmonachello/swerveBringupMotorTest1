package frc.robot;

import edu.wpi.first.networktables.NetworkTable;
import frc.robot.diag.probe.ActiveDevicePresenceProbe;
import frc.robot.telemetry.SampledTelemetrySampler;
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
  private static final String TEXT_EMPTY = "";

  private final CanBusHealth canHealth;
  private final NetworkTable diagTable;
  private final String runTestBindingLabel;
  private final BridgeGroupManager bridgeGroups = new BridgeGroupManager();
  private final BridgeGroupManager.SelectedState bridgeSelected =
      new BridgeGroupManager.SelectedState();
  private final SampledTelemetrySampler sampledTelemetry = new SampledTelemetrySampler();
  private final DeviceLifecycleRegistry deviceLifecycle = new DeviceLifecycleRegistry();

  private BringupCore core;
  private DiagnosticsReporter diagnostics;

  /**
   * NAME
   *   BringupRuntime - Construct runtime state around diagnostics dependencies.
   *
   * PARAMETERS
   *   canHealth - CAN health sampler.
   *   diagTable - Diagnostics NetworkTables root.
   *   runTestBindingLabel - Human-readable hold-to-run binding label.
   */
  public BringupRuntime(
      CanBusHealth canHealth,
      NetworkTable diagTable,
      String runTestBindingLabel) {
    this.canHealth = canHealth;
    this.diagTable = diagTable;
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
    refreshDeviceLifecycle(nowMs);
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
   *   getLatestTestRunSnapshot - Return the latest bringup test lifecycle snapshot.
   *
   * RETURNS
   *   Latest test-run state for REST/UI completion payloads.
   */
  public BringupCore.TestRunSnapshot getLatestTestRunSnapshot() {
    return core != null ? core.getLatestTestRunSnapshot() : BringupCore.TestRunSnapshot.idle();
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
    bridgeSelected.device = TEXT_EMPTY;
    bridgeSelected.enabled = false;
    if (diagnostics != null) {
      diagnostics.resetState();
    }
    BringupUtil.validateCanIds(BringupUtil.getActiveDevices());
  }

  /**
   * NAME
   *   prepareForRegistryApply - Tear down runtime-owned state before config replacement.
   *
   * PARAMETERS
   *   reason - Reset reason label.
   *
   * SIDE EFFECTS
   *   Stops actuation/tests, clears the declared active profile, resets
   *   sampled telemetry, diagnostics, lifecycle state, selected device state,
   *   and runtime groups so the next config becomes the sole source of truth.
   */
  public void prepareForRegistryApply(String reason) {
    if (core != null) {
      core.resetState(reason);
    }
    BringupUtil.deactivateActiveProfile();
    sampledTelemetry.clearAll();
    replaceCore();
    bridgeGroups.clear();
    bridgeSelected.device = TEXT_EMPTY;
    bridgeSelected.enabled = false;
    deviceLifecycle.resetForProfile(TEXT_EMPTY, Collections.emptyList(), System.currentTimeMillis());
    if (diagnostics != null) {
      diagnostics.resetState();
    }
    BringupUtil.validateCanIds(BringupUtil.getSelectedDevicesSorted());
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
    resetForProfile(reason);
    if (core != null) {
      core.reloadActiveProfileRuntime(reason);
    }
  }

  /**
   * NAME
   *   stageSelectedProfileForBringup - Load selected-profile device configs for incremental bringup.
   *
   * RETURNS
   *   Empty string on success, or an error message when staging fails.
   */
  public String stageSelectedProfileForBringup() {
    return BringupUtil.stageSelectedProfileForBringup();
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
    prepareForRegistryApply(reason);
    BringupUtil.RegistryApplyReport report =
        BringupUtil.applyRegistryJson(rawJson, activateProfile);
    if (report.overallOk && activateProfile != null && !activateProfile.isBlank()) {
      resetAndInstantiateForProfile(reason);
    }
    return report;
  }

  /**
   * NAME
   *   applyRegistry - Replace the canonical config while leaving runtime inactive.
   *
   * PARAMETERS
   *   rawJson - Full registry payload.
   *   reason - Reset reason label.
   *
   * RETURNS
   *   Registry apply report.
   */
  public BringupUtil.RegistryApplyReport applyRegistry(String rawJson, String reason) {
    prepareForRegistryApply(reason);
    return BringupUtil.applyRegistryJson(rawJson, TEXT_EMPTY);
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
   *   initializeDeviceLifecycle - Rebuild lifecycle registry from profile-defined devices.
   *
   * PARAMETERS
   *   nowMs - Event timestamp.
   */
  public void initializeDeviceLifecycle(long nowMs) {
    List<BringupUtil.DeviceEntry> entries = currentProfileDevices();
    deviceLifecycle.resetForProfile(currentProfileName(), entries, nowMs);
    refreshDeviceLifecycle(nowMs);
  }

  /**
   * NAME
   *   refreshDeviceLifecycle - Refresh lifecycle states from current core snapshots.
   *
   * PARAMETERS
   *   nowMs - Event timestamp.
   */
  public void refreshDeviceLifecycle(long nowMs) {
    List<BringupUtil.DeviceEntry> entries = currentProfileDevices();
    java.util.Map<String, frc.robot.diag.snapshots.DeviceSnapshot> snapshotsByLabel =
        new java.util.LinkedHashMap<>();
    java.util.Map<String, Boolean> instantiatedByLabel = new java.util.LinkedHashMap<>();
    java.util.Map<String, Boolean> inScopeByLabel = new java.util.LinkedHashMap<>();
    boolean runtimeActive = BringupUtil.isProfileActive();
    for (BringupUtil.DeviceEntry entry : entries) {
      if (entry == null || entry.label == null || entry.label.isBlank()) {
        continue;
      }
      inScopeByLabel.put(entry.label.trim().toLowerCase(), runtimeActive);
    }
    if (core != null) {
      for (BringupUtil.DeviceEntry entry : entries) {
        if (entry == null || entry.label == null || entry.label.isBlank()) {
          continue;
        }
        frc.robot.devices.DeviceUnit device = core.findDeviceByLabel(entry.label);
        String normalized = entry.label.trim().toLowerCase();
        boolean instantiated = device != null && device.isCreated();
        instantiatedByLabel.put(normalized, instantiated);
        if (!runtimeActive || !instantiated) {
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

  private List<BringupUtil.DeviceEntry> currentProfileDevices() {
    return BringupUtil.isProfileActive()
        ? BringupUtil.getActiveDevicesSorted()
        : BringupUtil.getSelectedDevicesSorted();
  }

  private String currentProfileName() {
    return BringupUtil.isProfileActive()
        ? BringupUtil.getActiveRuntimeProfileLabel()
        : BringupUtil.getSelectedCanProfileLabel();
  }

  private void replaceCore() {
    core = new BringupCore(sampledTelemetry, diagTable, deviceLifecycle);
    core.setRunTestBindingLabel(runTestBindingLabel);
    if (diagnostics == null) {
      diagnostics = new DiagnosticsReporter(core, canHealth, diagTable);
    } else {
      diagnostics.setCore(core);
    }
    initializeDeviceLifecycle(System.currentTimeMillis());
  }
}
