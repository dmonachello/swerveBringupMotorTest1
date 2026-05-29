package frc.robot;

import edu.wpi.first.networktables.NetworkTable;

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
   *   updateDiagnostics - Update diagnostics publishers.
   */
  public void updateDiagnostics() {
    if (diagnostics != null) {
      diagnostics.update();
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
    replaceCore();
    bridgeGroups.clear();
    bridgeSelected.device = TEXT_EMPTY;
    bridgeSelected.enabled = false;
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
    String selectedProfile = BringupUtil.getSelectedCanProfile();
    String activeProfile = BringupUtil.getActiveRuntimeProfileLabel();
    if (
        BringupUtil.isProfileActive()
            && selectedProfile != null
            && !selectedProfile.isBlank()
            && selectedProfile.equals(activeProfile)
    ) {
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
    replaceCore();
    bridgeGroups.clear();
    bridgeSelected.device = TEXT_EMPTY;
    bridgeSelected.enabled = false;
    if (diagnostics != null) {
      diagnostics.resetState();
    }
    BringupUtil.validateCanIds(BringupUtil.getSelectedDevicesSorted());
  }

  private void replaceCore() {
    core = new BringupCore();
    core.setRunTestBindingLabel(runTestBindingLabel);
    if (diagnostics == null) {
      diagnostics = new DiagnosticsReporter(core, canHealth, diagTable);
    } else {
      diagnostics.setCore(core);
    }
  }
}
