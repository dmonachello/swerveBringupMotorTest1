package frc.robot;

//import edu.wpi.first.cameraserver.CameraServer;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import frc.robot.commands.local.RobotLocalAxisCommandId;
import frc.robot.commands.local.RobotLocalCommandRegistry;
import frc.robot.input.BindingsManager;
import frc.robot.input.ControllerManager;
import frc.robot.input.InputAliasResolver;
import frc.robot.manufacturers.microsoft.XboxControllerDevice;
import frc.robot.rest.BringupRestServer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * NAME
 *   RobotV2 - Primary bringup robot program.
 *
 * DESCRIPTION
 *   Wires controller inputs to BringupCore behaviors and coordinates
 *   diagnostics reporting, JSON snapshots, and CAN health sampling.
 *
 * SIDE EFFECTS
 *   Drives motors/sensors through vendor APIs and serves diagnostics over the
 *   supported REST/UI paths.
 */
public class RobotV2 extends TimedRobot {

  // ---------------- CAN ID DEFINITIONS ----------------
  private static final double DEADBAND = BringupUtil.DEADBAND;
  private static final double SPEED_ZERO = 0.0;
  private static final double ACTUATION_REQUEST_EPSILON = 1e-6;
  private static final String BINDING_LEFT_DRIVE =
      RobotLocalAxisCommandId.LEFT_DRIVE.wireName();
  private static final String BINDING_RIGHT_DRIVE =
      RobotLocalAxisCommandId.RIGHT_DRIVE.wireName();
  private static final String COMMAND_RUN_TEST =
      RobotLocalCommandRegistry.COMMAND_RUN_TEST;
  private static final String MESSAGE_NON_TEST_DIRECT_ACTUATION_BLOCKED =
      "Actuation blocked: no active test.";
  private static final String REASON_PROFILE_ACTIVATE = "profileActivate";
  private static final String REASON_RUNTIME_DEACTIVATE = "runtimeDeactivate";
  private static final String REASON_DISABLED_RUNTIME_DEACTIVATE = "disabledInit";
  private static final String MESSAGE_DISABLED_RUNTIME_STABLE =
      "Disabled: runtime deactivated, outputs stopped, hardware released. Runtime Activate required before motion resumes.";
  private static final String TEXT_EMPTY = "";
  private static final int POV_UP = 0;
  private static final int POV_RIGHT = 90;
  private static final int POV_DOWN = 180;
  private static final int POV_LEFT = 270;
  private static final int MAX_CONTROLLER_COUNT = 6;
  private static final String DEFAULT_CONTROLLER_PREFIX = "controller";
  private static final String ACTIVE_GROUP_NAME = "active-group";
  private static final double BINDING_VALUE_ANALOG = 0.0;
  // ---------------------------------------------------

  // Driver Station controller input.
  private final ControllerManager controllers = new ControllerManager();
  private final java.util.Map<String, XboxController> controllerMap = controllers.getXboxControllers();
  private final XboxController controller0 = controllerMap.get("controller0");
  private final XboxController controller1 = controllerMap.get("controller1");
  private final BindingsManager bindings = new BindingsManager();
  // Shared runtime state used by Xbox, CLI, and UI commands.
  private BringupRuntime runtime;
  // Samples roboRIO CAN controller health.
  private final CanBusHealth canHealth = new CanBusHealth();
  private BridgeUiCommandHandler uiHandler;
  // Edge-detect state for buttons that should fire once per press.
  private final EdgeTrigger edge = new EdgeTrigger();
  private static final int UI_REST_PORT = 5805;
  private BringupRestServer uiRestServer;
  private final BringupPrinter.LineListener bringupLineListener = new BringupLineListener();
  private final BringupRestServer.RestCallbacks restCallbacks = new RestCallbacksImpl();
  private boolean warnedNonTestActuationBlocked = false;
  private final Runnable profileToggleAction = new ProfileToggleAction();
  private final Runnable profileActivateAction = new ProfileActivateAction();
  private final Runnable profileDeactivateAction = new ProfileDeactivateAction();
  private final Runnable bindingsPrinter = new BindingsPrinter();
  private final Runnable testsInfoPrinter = new TestsInfoPrinter();
  private final Runnable testsOverviewPrinter = new TestsOverviewPrinter();
  private final BringupCommandRouter.AddAllHandler addAllHandler = new AddAllHandlerImpl();
  private final BringupCommandRouter.GenericCmdHandler genericCmdHandler =
      new GenericCmdHandlerImpl();
  private final BringupCommandRouter.AddMotorHandler addMotorHandler = new AddMotorHandlerImpl();
  private Map<String, String> inputAliases = new HashMap<>();
  private String inputAliasProfile = TEXT_EMPTY;
  private static final String DEFAULT_GROUP_NAME = "defaultGroup";
  private static final String MESSAGE_SELECTED_PROFILE_STAGE_FAILED_PREFIX =
      "Failed to stage selected profile for incremental bringup: ";
  /**
   * NAME
   *   robotInit - One-time robot initialization.
   *
   * DESCRIPTION
   *   Loads config/profile selection, constructs core subsystems, and prints
   *   startup diagnostics without activating bringup runtime.
   */
  @Override
  public void robotInit() {
    System.out.println(BuildInfo.buildBootRevisionLine());
    System.out.println(BuildInfo.buildBootWorkspaceRevisionLine());
    System.out.println(BuildInfo.buildBootCodeRevisionLine());
    // Load profile before anything instantiates devices.
    BringupUtil.applyProfileFromArgs();
    runtime = new BringupRuntime(
        canHealth,
        bindings.describeBinding(COMMAND_RUN_TEST));
    uiHandler = new BridgeUiCommandHandler(
        runtime,
        bindings,
        profileToggleAction,
        profileActivateAction,
        profileDeactivateAction);
    BringupPrinter.setLineListener(bringupLineListener);
    try {
      uiRestServer = new BringupRestServer(UI_REST_PORT, restCallbacks);
      uiRestServer.start();
    } catch (java.io.IOException ex) {
      BringupPrinter.enqueue("REST UI server failed to start: " + ex.getMessage());
      uiRestServer = null;
    }
    uiHandler.applyDashboardUpdateState();
    refreshInputAliases();
    // Print bindings and validate IDs once at startup.
    uiHandler.printStartupInfo();
    validateCanIds();
    //CameraServer.startAutomaticCapture();
  }

  /**
   * NAME
   *   teleopInit - Teleop mode entry hook.
   *
   * DESCRIPTION
   *   Stops outputs and resets diagnostic counters for a fresh teleop run.
   */
  @Override
  public void teleopInit() {
    core().safetyStop("teleopInit");
    if (diagnostics() != null) {
      diagnostics().resetState();
    }
    edge.reset();
  }

  /**
   * NAME
   *   disabledInit - Disabled mode entry hook.
   *
   * DESCRIPTION
   *   Performs a full runtime deactivation so leaving Disabled always requires
   *   an explicit Runtime Activate before bringup motion can resume.
   */
  @Override
  public void disabledInit() {
    if (BringupUtil.isProfileActive() || runtime.isControlledLifecycleActive()) {
      runtime.deactivateActiveProfile(REASON_DISABLED_RUNTIME_DEACTIVATE);
      handleProfileDeactivate();
    } else {
      core().safetyStop(REASON_DISABLED_RUNTIME_DEACTIVATE);
      if (diagnostics() != null) {
        diagnostics().resetState();
      }
    }
    BringupPrinter.enqueue(MESSAGE_DISABLED_RUNTIME_STABLE);
    edge.reset();
  }

  /**
   * NAME
   *   robotPeriodic - Periodic loop for all modes.
   *
   * DESCRIPTION
   *   Samples CAN health and records loop timing metrics each cycle.
   */
  @Override
  public void robotPeriodic() {
    if (runtime != null) {
      runtime.sampleTelemetry(System.currentTimeMillis());
    }
    // Sample and publish CAN health every loop.
    if (diagnostics() != null) {
      diagnostics().update();
    }
    if (uiHandler != null) {
      boolean xboxConnected = controller0 != null && DriverStation.isJoystickConnected(0);
      uiHandler.updateSafety(xboxConnected);
    }
    frc.robot.diag.app.AppStatusTracker.recordLoop();
  }

  /**
   * NAME
   *   teleopPeriodic - Teleop periodic loop.
   *
   * DESCRIPTION
   *   Reads controller inputs, applies bringup commands, and updates motor
   *   outputs within the 20ms loop budget while allowing local bindings to
   *   suppress overlapping global bindings.
   */
  @Override
  public void teleopPeriodic() {

    // --- Device instantiation / local prints ---
    if (controller0 == null) {
      return;
    }
    Map<String, String> aliases = refreshInputAliases();
    Set<String> localOverrides =
        InputAliasResolver.resolveAll(bridgeGroups().getActiveBindingInputs(), aliases);
    BindingsManager.BindingState bind =
        bindings.sample(controllerMap, edge, localOverrides, aliases);

    boolean driverLeftOverridden = localOverrides.contains(InputAliasResolver.KEY_DRIVER_LEFT_Y);
    boolean driverRightOverridden = localOverrides.contains(InputAliasResolver.KEY_DRIVER_RIGHT_Y);

    final double neoSpeed = !driverLeftOverridden && bind.hasAxis(BINDING_LEFT_DRIVE)
        ? bind.axis(BINDING_LEFT_DRIVE)
        : SPEED_ZERO;
    final double krakenSpeed = !driverRightOverridden && bind.hasAxis(BINDING_RIGHT_DRIVE)
        ? bind.axis(BINDING_RIGHT_DRIVE)
        : SPEED_ZERO;

    if (uiHandler != null) {
      uiHandler.setLastSpeeds(neoSpeed, krakenSpeed);
      uiHandler.submitControllerBindings(bind);
      uiHandler.stepRobotLocalCommands();
    }

    // Feed test inputs (used by joystick-mode tests).
    core().setTestInputs(XboxControllerDevice.buildControllerInputs(controllerMap));
    runtime.updateReportsAndTests(
        uiHandler != null && uiHandler.isRobotLocalCommandActive(COMMAND_RUN_TEST));

    boolean actuationRequested = isActuationRequested(neoSpeed, krakenSpeed);
    // Apply direct joystick outputs only while a test is actively running.
    // Group bindings are evaluated independently below when host/runtime policy
    // allows the active scope to exist.
    if (core().isTestRunning()) {
      core().setSpeeds(neoSpeed, krakenSpeed);
      warnedNonTestActuationBlocked = false;
    } else if (actuationRequested && !warnedNonTestActuationBlocked) {
      BringupPrinter.enqueue(MESSAGE_NON_TEST_DIRECT_ACTUATION_BLOCKED);
      warnedNonTestActuationBlocked = true;
    } else if (!actuationRequested) {
      warnedNonTestActuationBlocked = false;
    }

    BridgeGroupManager.InputSnapshot inputs = new BridgeGroupManager.InputSnapshot();
    for (int controllerIndex = 0; controllerIndex < MAX_CONTROLLER_COUNT; controllerIndex++) {
      XboxController controller = controllerMap.get(DEFAULT_CONTROLLER_PREFIX + controllerIndex);
      if (controller == null || !DriverStation.isJoystickConnected(controllerIndex)) {
        continue;
      }
      BridgeGroupManager.ControllerState state = inputs.controllers[controllerIndex];
      state.leftY = BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
      state.rightY = BringupUtil.deadband(-controller.getRightY(), DEADBAND);
      state.leftX = BringupUtil.deadband(controller.getLeftX(), DEADBAND);
      state.rightX = BringupUtil.deadband(controller.getRightX(), DEADBAND);
      state.leftTrigger = controller.getLeftTriggerAxis();
      state.rightTrigger = controller.getRightTriggerAxis();
      state.a = controller.getAButton();
      state.b = controller.getBButton();
      state.x = controller.getXButton();
      state.y = controller.getYButton();
      state.lb = controller.getLeftBumperButton();
      state.rb = controller.getRightBumperButton();
      state.back = controller.getBackButton();
      state.start = controller.getStartButton();
      state.ls = controller.getLeftStickButton();
      state.rs = controller.getRightStickButton();
      int pov = controller.getPOV();
      state.dpadUp = pov == POV_UP;
      state.dpadRight = pov == POV_RIGHT;
      state.dpadDown = pov == POV_DOWN;
      state.dpadLeft = pov == POV_LEFT;
    }
    bridgeGroups().applyBindings(inputs, core(), bridgeSelected());

  }

  private static boolean isActuationRequested(double neoSpeed, double krakenSpeed) {
    return Math.abs(neoSpeed) > ACTUATION_REQUEST_EPSILON
        || Math.abs(krakenSpeed) > ACTUATION_REQUEST_EPSILON;
  }

  /**
   * NAME
   *   toggleDashboardUpdates - Apply the local dashboard toggle command.
   */
  private void toggleDashboardUpdates() {
    if (uiHandler != null) {
      uiHandler.toggleDashboardUpdates();
    }
  }

  /**
   * NAME
   *   printCurrentInputs - Emit the current local stick-input report.
   *
   * PARAMETERS
   *   neoSpeed - Current left-drive value after binding resolution.
   *   krakenSpeed - Current right-drive value after binding resolution.
   */
  private void printCurrentInputs(double neoSpeed, double krakenSpeed) {
    runtime.requestTextReport(
        "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
        " rightY=" + String.format("%.2f", krakenSpeed) +
        " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
        ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")",
        4);
  }

  private void resetCoreForProfile(String reason) {
    runtime.resetAndInstantiateForProfile(reason);
    if (uiHandler != null) {
      uiHandler.resetProfileRuntimeUiState();
      uiHandler.printProfileInfo();
    }
    refreshInputAliases();
    syncDefaultGroup();
    ensureActiveGroupDefined();
  }

  /**
   * NAME
   *   activateSelectedProfileForAllSurfaces - Activate selected profile through shared runtime.
   *
   * PARAMETERS
   *   reason - Reset reason label.
   *
   * SIDE EFFECTS
   *   Activates the selected profile, fully rebuilds runtime state, refreshes
   *   aliases/groups, and instantiates the active profile devices.
   */
  private void activateSelectedProfileForAllSurfaces(String reason) {
    runtime.activateSelectedProfile(reason);
    if (BringupUtil.isProfileActive()) {
      handleProfileActivate();
    }
  }

  private void ensureActiveGroupDefined() {
    if (bridgeGroups().getGroup(ACTIVE_GROUP_NAME) == null) {
      bridgeGroups().createGroup(ACTIVE_GROUP_NAME);
    }
  }

  /**
   * NAME
   *   stageSelectedProfileForIncrementalBringup - Prepare selected-profile device configs without activation.
   *
   * RETURNS
   *   True on success.
   */
  private boolean stageSelectedProfileForIncrementalBringup() {
    String error = runtime.stageSelectedProfileForBringup();
    if (error != null && !error.isBlank()) {
      BringupPrinter.enqueue(MESSAGE_SELECTED_PROFILE_STAGE_FAILED_PREFIX + error);
      return false;
    }
    validateCanIds();
    return true;
  }

  /**
   * NAME
   *   refreshInputAliases - Update alias map when the active profile changes.
   *
   * RETURNS
   *   Current merged alias map.
   */
  private Map<String, String> refreshInputAliases() {
    String profile = BringupUtil.isProfileActive()
        ? BringupUtil.getActiveCanProfile()
        : BringupUtil.getSelectedCanProfile();
    if (profile == null) {
      profile = TEXT_EMPTY;
    }
    if (!profile.equals(inputAliasProfile)) {
      inputAliasProfile = profile;
      Map<String, String> merged = new HashMap<>();
      merged.putAll(bindings.getInputAliases());
      Map<String, String> profileAliases = BringupUtil.getProfileInputAliases(profile);
      if (profileAliases != null && !profileAliases.isEmpty()) {
        merged.putAll(profileAliases);
      }
      inputAliases = merged;
      bridgeGroups().setInputAliases(inputAliases);
      if (uiHandler != null) {
        uiHandler.setInputAliases(inputAliases);
      }
    }
    return inputAliases;
  }

  /**
   * NAME
   *   syncDefaultGroup - Keep the default group aligned to active profile devices.
   */
  private void syncDefaultGroup() {
    List<BringupUtil.DeviceEntry> devices = BringupUtil.getActiveDevices();
    List<String> labels = new ArrayList<>();
    if (devices != null) {
      for (BringupUtil.DeviceEntry entry : devices) {
        if (entry == null) {
          continue;
        }
        String label = entry.label != null ? entry.label.trim() : TEXT_EMPTY;
        if (!label.isBlank()) {
          labels.add(label);
        }
      }
    }
    bridgeGroups().syncGroupMembers(DEFAULT_GROUP_NAME, labels);
  }

  /**
   * NAME
   *   syncRuntimeBridgeConfig - Rebuild runtime groups from active bridgeConfig.
   *
   * SIDE EFFECTS
   *   Clears runtime group/selected-device state and loads the active profile's
   *   bridgeConfig groups, bindings, and selected-device settings. Falls back
   *   to the legacy default group only when the profile defines no groups.
   */
  private void syncRuntimeBridgeConfig() {
    synchronizeRuntimeBridgeConfig(
        bridgeGroups(),
        bridgeSelected(),
        BringupUtil.getProfileBridgeConfig(BringupUtil.getActiveCanProfile()),
        BringupUtil.getActiveDevices());
  }

  static void synchronizeRuntimeBridgeConfig(
      BridgeGroupManager bridgeGroups,
      BridgeGroupManager.SelectedState bridgeSelected,
      BringupUtil.BridgeProfileRuntimeConfig config,
      List<BringupUtil.DeviceEntry> fallbackDevices) {
    BringupRuntime.synchronizeBridgeRuntimeConfig(
        bridgeGroups,
        bridgeSelected,
        config,
        fallbackDevices);
    if (bridgeSelected != null) {
      bridgeSelected.group = TEXT_EMPTY;
      bridgeSelected.groupEnabled = false;
      bridgeSelected.groupMembers.clear();
    }
  }

  /**
   * NAME
   *   handleBringupLine - Adapter for BringupPrinter output.
   */
  private void handleBringupLine(String text) {
    if (uiHandler != null) {
      uiHandler.onBringupLine(text);
    }
    if (uiRestServer != null) {
      uiRestServer.onBringupLine(text);
    }
  }

  /**
   * NAME
   *   handleProfileToggle - Adapter for UI profile toggle actions.
   */
  private void handleProfileToggle() {
    if (uiHandler != null) {
      uiHandler.printProfileInfo();
    }
  }

  /**
   * NAME
   *   handleProfileActivate - Refresh state after shared runtime activation.
   */
  private void handleProfileActivate() {
    if (uiHandler != null) {
      uiHandler.resetProfileRuntimeUiState();
      uiHandler.printProfileInfo();
    }
    refreshInputAliases();
  }

  /**
   * NAME
   *   handleProfileDeactivate - Refresh state after shared runtime deactivation.
   */
  private void handleProfileDeactivate() {
    if (uiHandler != null) {
      uiHandler.resetProfileRuntimeUiState();
      uiHandler.printProfileInfo();
    }
    refreshInputAliases();
    ensureActiveGroupDefined();
  }

  /**
   * NAME
   *   AddAllHandlerImpl - Activate profile before add-all.
   */
  private final class AddAllHandlerImpl implements BringupCommandRouter.AddAllHandler {
    @Override
    public void handleAddAll(boolean addAllNow) {
      if (addAllNow && !BringupUtil.isProfileActive()) {
        if (!stageSelectedProfileForIncrementalBringup()) {
          return;
        }
      }
      if (core() != null) {
        runtime.addAllDevices(addAllNow);
      }
    }
  }

  /**
   * NAME
   *   AddMotorHandlerImpl - Activate profile before add-next.
   */
  private final class AddMotorHandlerImpl implements BringupCommandRouter.AddMotorHandler {
    @Override
    public void handleAddMotor(boolean addMotorNow) {
      if (addMotorNow && !BringupUtil.isProfileActive()) {
        if (!stageSelectedProfileForIncrementalBringup()) {
          return;
        }
      }
      if (core() != null) {
        runtime.addMotor(addMotorNow);
      }
    }
  }

  /**
   * NAME
   *   GenericCmdHandlerImpl - Example command handler cloned from add-all.
   */
  private final class GenericCmdHandlerImpl implements BringupCommandRouter.GenericCmdHandler {
    @Override
    public void handleGenericCmd(boolean genericCmdNow) {
      if (genericCmdNow && !BringupUtil.isProfileActive()) {
        if (!stageSelectedProfileForIncrementalBringup()) {
          return;
        }
      }
      if (core() != null) {
        runtime.addAllDevices(genericCmdNow);
      }
    }
  }

  /**
   * NAME
   *   BringupLineListener - Delegate for BringupPrinter output.
   */
  private final class BringupLineListener implements BringupPrinter.LineListener {
    @Override
    public void onLine(String text) {
      handleBringupLine(text);
    }
  }

  /**
   * NAME
   *   RestCallbacksImpl - REST JSON supplier adapter.
   *
   * DESCRIPTION
   *   Reuses the existing robot-side scene/model builders for the first REST
   *   read commands so the new transport does not fork the payload contract.
   */
  private final class RestCallbacksImpl implements BringupRestServer.RestCallbacks {
    @Override
    public com.google.gson.JsonObject buildDevicesJson() {
      return uiHandler != null ? uiHandler.buildDevicesJson() : new com.google.gson.JsonObject();
    }

    @Override
    public com.google.gson.JsonObject buildRuntimeStateJson() {
      return uiHandler != null ? uiHandler.buildRuntimeStateJson() : new com.google.gson.JsonObject();
    }

    @Override
    public com.google.gson.JsonObject buildTestsStateJson() {
      return uiHandler != null ? uiHandler.buildTestsStateJson() : new com.google.gson.JsonObject();
    }

    @Override
    public com.google.gson.JsonObject buildCurrentConfigJson() {
      return BringupUtil.buildCurrentProfilesJson();
    }

    @Override
    public BridgeUiCommandHandler.RestCommandResult executeCommand(
        String name,
        String argsJson,
        String clientId) {
      return uiHandler != null ? uiHandler.executeRestCommand(name, argsJson, clientId) : null;
    }

    @Override
    public boolean isCommandActive(String name) {
      return uiHandler != null && uiHandler.isRobotLocalCommandActive(name);
    }
  }

  /**
   * NAME
   *   ProfileToggleAction - Delegate for profile toggle actions.
   */
  private final class ProfileToggleAction implements Runnable {
    @Override
    public void run() {
      handleProfileToggle();
    }
  }

  private final class ProfileActivateAction implements Runnable {
    @Override
    public void run() {
      handleProfileActivate();
    }
  }

  private final class ProfileDeactivateAction implements Runnable {
    @Override
    public void run() {
      handleProfileDeactivate();
    }
  }

  /**
   * NAME
   *   BindingsPrinter - Delegate for bindings printing.
   */
  private final class BindingsPrinter implements Runnable {
    @Override
    public void run() {
      if (uiHandler != null) {
        uiHandler.printBindings();
      }
    }
  }

  /**
   * NAME
   *   TestsInfoPrinter - Delegate for tests info printing.
   */
  private final class TestsInfoPrinter implements Runnable {
    @Override
    public void run() {
      if (uiHandler != null) {
        uiHandler.printTestsInfo();
      }
    }
  }

  /**
   * NAME
   *   TestsOverviewPrinter - Delegate for tests overview printing.
   */
  private final class TestsOverviewPrinter implements Runnable {
    @Override
    public void run() {
      if (uiHandler != null) {
        uiHandler.printTestsOverview();
      }
    }
  }

  private void validateCanIds() {
    // Warn on duplicate CAN IDs in the active profile, or the selected profile when inactive.
    List<BringupUtil.DeviceEntry> devices = BringupUtil.isProfileActive()
        ? BringupUtil.getActiveDevices()
        : BringupUtil.getSelectedDevicesSorted();
    BringupUtil.validateCanIds(devices);
  }

  private BringupCore core() {
    return runtime.getCore();
  }

  private DiagnosticsReporter diagnostics() {
    return runtime.getDiagnostics();
  }

  private BridgeGroupManager bridgeGroups() {
    return runtime.getBridgeGroups();
  }

  private BridgeGroupManager.SelectedState bridgeSelected() {
    return runtime.getBridgeSelected();
  }

}
