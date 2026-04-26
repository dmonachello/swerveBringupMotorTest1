package frc.robot;

//import edu.wpi.first.cameraserver.CameraServer;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import frc.robot.input.BindingsManager;
import frc.robot.input.ControllerManager;
import frc.robot.input.InputAliasResolver;
import frc.robot.ui.TcpUiServer;
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
 *   Drives motors/sensors through vendor APIs and publishes NetworkTables
 *   telemetry for diagnostics.
 */
public class RobotV2 extends TimedRobot {

  // ---------------- CAN ID DEFINITIONS ----------------
  private static final double DEADBAND = BringupUtil.DEADBAND;
  private static final double SPEED_ZERO = 0.0;
  private static final double SPEED_FIXED_25 = 0.25;
  private static final double SPEED_FIXED_50 = 0.50;
  private static final double SPEED_FIXED_75 = 0.75;
  private static final double SPEED_FIXED_100 = 1.00;
  private static final double ACTUATION_REQUEST_EPSILON = 1e-6;
  private static final String BINDING_LEFT_DRIVE = "leftDrive";
  private static final String BINDING_RIGHT_DRIVE = "rightDrive";
  private static final String COMMAND_RUN_TEST = "runTest";
  private static final String COMMAND_PROFILE_TOGGLE = "profileToggle";
  private static final String COMMAND_TOGGLE_DASHBOARD = "toggleDashboard";
  private static final String COMMAND_FIXED_SPEED_25 = "fixedSpeed25";
  private static final String COMMAND_FIXED_SPEED_50 = "fixedSpeed50";
  private static final String COMMAND_FIXED_SPEED_75 = "fixedSpeed75";
  private static final String COMMAND_FIXED_SPEED_100 = "fixedSpeed100";
  private static final String COMMAND_PRINT_INPUTS = "printInputs";
  private static final String MESSAGE_NON_TEST_ACTUATION_BLOCKED =
      "Actuation blocked: no active test.";
  private static final String TEXT_EMPTY = "";
  private static final int POV_UP = 0;
  private static final int POV_RIGHT = 90;
  private static final int POV_DOWN = 180;
  private static final int POV_LEFT = 270;
  private static final String ACTIVE_GROUP_NAME = "active-group";
  // ---------------------------------------------------

  // Driver Station controller input.
  private final ControllerManager controllers = new ControllerManager();
  private final java.util.Map<String, XboxController> controllerMap = controllers.getXboxControllers();
  private final XboxController controller0 = controllerMap.get("controller0");
  // Optional second controller for fixed-speed test buttons.
  private final XboxController controller1 = controllerMap.get("controller1");
  private final BindingsManager bindings = new BindingsManager();
  // Shared runtime state used by Xbox, CLI, and UI commands.
  private BringupRuntime runtime;
  // Samples roboRIO CAN controller health.
  private final CanBusHealth canHealth = new CanBusHealth();
  // Builds reports, JSON snapshots, and optional NT telemetry.
  private final NetworkTable diagTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("diag");
  private final NetworkTable testsTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("tests");
  private final NetworkTable uiTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("ui");
  private final NetworkTable uiTcpTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("ui_tcp");
  private BridgeUiCommandHandler uiHandler;
  // Edge-detect state for buttons that should fire once per press.
  private final EdgeTrigger edge = new EdgeTrigger();
  private static final int UI_TCP_PORT = 5809;
  private TcpUiServer uiTcpServer;
  private final TcpUiServer.CommandHandler uiCommandHandler = new UiCommandHandler();
  private final TcpUiServer.ConnectionListener uiConnectionListener = new UiConnectionListener();
  private final BringupPrinter.LineListener bringupLineListener = new BringupLineListener();
  private boolean warnedNonTestActuationBlocked = false;
  private final Runnable profileToggleAction = new ProfileToggleAction();
  private final Runnable profileActivateAction = new ProfileActivateAction();
  private final Runnable bindingsPrinter = new BindingsPrinter();
  private final Runnable testsInfoPrinter = new TestsInfoPrinter();
  private final Runnable testsOverviewPrinter = new TestsOverviewPrinter();
  private final BringupCommandRouter.AddAllHandler addAllHandler = new AddAllHandlerImpl();
  private final BringupCommandRouter.AddMotorHandler addMotorHandler = new AddMotorHandlerImpl();
  private Map<String, String> inputAliases = new HashMap<>();
  private String inputAliasProfile = TEXT_EMPTY;
  private static final String DEFAULT_GROUP_NAME = "defaultGroup";

  /**
   * NAME
   *   robotInit - One-time robot initialization.
   *
   * DESCRIPTION
   *   Loads the active profile, constructs core subsystems, and prints startup
   *   diagnostics.
   */
  @Override
  public void robotInit() {
    // Load profile before anything instantiates devices.
    BringupUtil.applyProfileFromArgs();
    runtime = new BringupRuntime(
        canHealth,
        diagTable,
        bindings.describeBinding(COMMAND_RUN_TEST));
    uiHandler = new BridgeUiCommandHandler(
        runtime,
        bindings,
        testsTable,
        uiTable,
        uiTcpTable,
        profileToggleAction,
        profileActivateAction);
    BringupPrinter.setLineListener(bringupLineListener);
    uiTcpServer = new TcpUiServer(
        UI_TCP_PORT,
        uiCommandHandler,
        uiConnectionListener);
    uiTcpServer.start();
    uiHandler.applyDashboardUpdateState();
    ensureActiveGroupDefined();
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
   *   Resets bringup state and diagnostic counters for a fresh teleop run.
   */
  @Override
  public void teleopInit() {
    // Reset state whenever teleop is entered.
    core().resetState("teleopInit");
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
   *   Disables tests and clears state to avoid stale outputs while disabled.
   */
  @Override
  public void disabledInit() {
    // Keep behavior symmetric in disabled and teleop to avoid stale state.
    core().disableAllBringupTests(true);
    core().resetState("disabledInit");
    if (diagnostics() != null) {
      diagnostics().resetState();
    }
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
    // Sample and publish CAN health every loop.
    if (diagnostics() != null) {
      diagnostics().update();
    }
    if (uiHandler != null) {
      uiHandler.processTcpCommands();
      boolean xboxConnected = controller0 != null && DriverStation.isJoystickConnected(0);
      uiHandler.updateSafety(xboxConnected);
      uiHandler.publishUiRobotState();
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

    boolean runHeld = bind.held(COMMAND_RUN_TEST);
    BringupCommandRouter.CommonResult commonResult = BringupCommandRouter.applyCommon(
        bind,
        runtime,
        bindingsPrinter,
        testsInfoPrinter,
        testsOverviewPrinter,
        runHeld,
        addAllHandler,
        addMotorHandler);

    // --- Profile switching ---
    if (bind.pressed(COMMAND_PROFILE_TOGGLE)) {
      BringupUtil.selectNextProfile();
      if (uiHandler != null) {
        uiHandler.printProfileInfo();
      }
    }

    // --- Diagnostics / reporting ---

    // Toggle dashboard updates to reduce periodic spam.
    if (bind.pressed(COMMAND_TOGGLE_DASHBOARD)) {
      if (uiHandler != null) {
        uiHandler.toggleDashboardUpdates();
      }
    }

    // --- Analog input to motor outputs ---
    boolean driverLeftOverridden = localOverrides.contains(InputAliasResolver.KEY_DRIVER_LEFT_Y);
    boolean driverRightOverridden = localOverrides.contains(InputAliasResolver.KEY_DRIVER_RIGHT_Y);

    double neoSpeed = SPEED_ZERO;
    if (!driverLeftOverridden) {
      neoSpeed = bind.hasAxis(BINDING_LEFT_DRIVE)
          ? bind.axis(BINDING_LEFT_DRIVE)
          : BringupUtil.deadband(-controller0.getLeftY(), DEADBAND);
    }
    double krakenSpeed = SPEED_ZERO;
    if (!driverRightOverridden) {
      krakenSpeed = bind.hasAxis(BINDING_RIGHT_DRIVE)
          ? bind.axis(BINDING_RIGHT_DRIVE)
          : BringupUtil.deadband(-controller0.getRightY(), DEADBAND);
    }

    boolean controller2Connected = controller1 != null && DriverStation.isJoystickConnected(1);
    if (controller2Connected) {
      double fixedSpeed = Double.NaN;
      if (bind.held(COMMAND_FIXED_SPEED_25)) {
        fixedSpeed = SPEED_FIXED_25;
      } else if (bind.held(COMMAND_FIXED_SPEED_50)) {
        fixedSpeed = SPEED_FIXED_50;
      } else if (bind.held(COMMAND_FIXED_SPEED_75)) {
        fixedSpeed = SPEED_FIXED_75;
      } else if (bind.held(COMMAND_FIXED_SPEED_100)) {
        fixedSpeed = SPEED_FIXED_100;
      }
      if (!Double.isNaN(fixedSpeed)) {
        neoSpeed = fixedSpeed;
        krakenSpeed = fixedSpeed;
      }
    }
    double uiFixedSpeed = uiHandler != null ? uiHandler.getUiFixedSpeed() : Double.NaN;
    if (!Double.isNaN(uiFixedSpeed)) {
      neoSpeed = uiFixedSpeed;
      krakenSpeed = uiFixedSpeed;
    }
    if (uiHandler != null) {
      uiHandler.setLastSpeeds(neoSpeed, krakenSpeed);
      uiHandler.handleUiCommands();
    }

    if (uiHandler != null && commonResult != null) {
      if (Boolean.FALSE.equals(commonResult.toggledTestEnabled)) {
        uiHandler.setStopLatchFromXbox("xboxDisableTest");
      }
      if (commonResult.runTestPressed || commonResult.runAllPressed) {
        uiHandler.clearStopLatchFromXbox("xboxRun");
      }
    }

    // D-pad Right: print current stick inputs.
    if (bind.pressed(COMMAND_PRINT_INPUTS)) {
      runtime.requestTextReport(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")",
          4);
    }

    if (controller2Connected) {
      if (bind.pressed(COMMAND_FIXED_SPEED_25)) {
        BringupPrinter.enqueue("Fixed speed: 0.25 (Controller 2 A)");
      }
      if (bind.pressed(COMMAND_FIXED_SPEED_50)) {
        BringupPrinter.enqueue("Fixed speed: 0.50 (Controller 2 B)");
      }
      if (bind.pressed(COMMAND_FIXED_SPEED_75)) {
        BringupPrinter.enqueue("Fixed speed: 0.75 (Controller 2 X)");
      }
      if (bind.pressed(COMMAND_FIXED_SPEED_100)) {
        BringupPrinter.enqueue("Fixed speed: 1.00 (Controller 2 Y)");
      }
    }

    // core update and diagnostics handled by BringupCommandRouter

    // Feed test inputs (used by joystick-mode tests).
    core().setTestInputs(buildAxisInputs(controllerMap, neoSpeed, krakenSpeed));

    boolean actuationRequested = isActuationRequested(neoSpeed, krakenSpeed);
    // Apply outputs only while a test is actively running.
    if (core().isTestRunning()) {
      core().setSpeeds(neoSpeed, krakenSpeed);
      warnedNonTestActuationBlocked = false;
    } else if (actuationRequested && !warnedNonTestActuationBlocked) {
      BringupPrinter.enqueue(MESSAGE_NON_TEST_ACTUATION_BLOCKED);
      warnedNonTestActuationBlocked = true;
    } else if (!actuationRequested) {
      warnedNonTestActuationBlocked = false;
    }

    BridgeGroupManager.InputSnapshot inputs = new BridgeGroupManager.InputSnapshot();
    inputs.driverLeftY = BringupUtil.deadband(-controller0.getLeftY(), DEADBAND);
    inputs.driverRightY = BringupUtil.deadband(-controller0.getRightY(), DEADBAND);
    inputs.driverLeftX = BringupUtil.deadband(controller0.getLeftX(), DEADBAND);
    inputs.driverRightX = BringupUtil.deadband(controller0.getRightX(), DEADBAND);
    inputs.driverLeftTrigger = controller0.getLeftTriggerAxis();
    inputs.driverRightTrigger = controller0.getRightTriggerAxis();
    inputs.driverA = controller0.getAButton();
    inputs.driverB = controller0.getBButton();
    inputs.driverX = controller0.getXButton();
    inputs.driverY = controller0.getYButton();
    inputs.driverLb = controller0.getLeftBumperButton();
    inputs.driverRb = controller0.getRightBumperButton();
    inputs.driverBack = controller0.getBackButton();
    inputs.driverStart = controller0.getStartButton();
    inputs.driverLs = controller0.getLeftStickButton();
    inputs.driverRs = controller0.getRightStickButton();
    int driverPov = controller0.getPOV();
    inputs.driverDpadUp = driverPov == POV_UP;
    inputs.driverDpadRight = driverPov == POV_RIGHT;
    inputs.driverDpadDown = driverPov == POV_DOWN;
    inputs.driverDpadLeft = driverPov == POV_LEFT;
    if (controller2Connected) {
      inputs.operatorLeftY = BringupUtil.deadband(-controller1.getLeftY(), DEADBAND);
      inputs.operatorRightY = BringupUtil.deadband(-controller1.getRightY(), DEADBAND);
      inputs.operatorLeftX = BringupUtil.deadband(controller1.getLeftX(), DEADBAND);
      inputs.operatorRightX = BringupUtil.deadband(controller1.getRightX(), DEADBAND);
      inputs.operatorLeftTrigger = controller1.getLeftTriggerAxis();
      inputs.operatorRightTrigger = controller1.getRightTriggerAxis();
      inputs.operatorA = controller1.getAButton();
      inputs.operatorB = controller1.getBButton();
      inputs.operatorX = controller1.getXButton();
      inputs.operatorY = controller1.getYButton();
      inputs.operatorLb = controller1.getLeftBumperButton();
      inputs.operatorRb = controller1.getRightBumperButton();
      inputs.operatorBack = controller1.getBackButton();
      inputs.operatorStart = controller1.getStartButton();
      inputs.operatorLs = controller1.getLeftStickButton();
      inputs.operatorRs = controller1.getRightStickButton();
      int operatorPov = controller1.getPOV();
      inputs.operatorDpadUp = operatorPov == POV_UP;
      inputs.operatorDpadRight = operatorPov == POV_RIGHT;
      inputs.operatorDpadDown = operatorPov == POV_DOWN;
      inputs.operatorDpadLeft = operatorPov == POV_LEFT;
    }
    if (core().isTestRunning()) {
      bridgeGroups().applyBindings(inputs, core(), bridgeSelected());
    }

    if (uiHandler != null) {
      uiHandler.publishTestsSelectionStatus();
    }
  }

  private static boolean isActuationRequested(double neoSpeed, double krakenSpeed) {
    return Math.abs(neoSpeed) > ACTUATION_REQUEST_EPSILON
        || Math.abs(krakenSpeed) > ACTUATION_REQUEST_EPSILON;
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
      if (uiHandler != null) {
        uiHandler.resetProfileRuntimeUiState();
        uiHandler.printProfileInfo();
      }
      refreshInputAliases();
      syncDefaultGroup();
      ensureActiveGroupDefined();
    }
  }

  private void ensureActiveGroupDefined() {
    if (bridgeGroups().getGroup(ACTIVE_GROUP_NAME) == null) {
      bridgeGroups().createGroup(ACTIVE_GROUP_NAME);
    }
  }

  /**
   * NAME
   *   refreshInputAliases - Update alias map when the active profile changes.
   *
   * RETURNS
   *   Current merged alias map.
   */
  private Map<String, String> refreshInputAliases() {
    String profile = BringupUtil.getActiveCanProfile();
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
   *   handleUiTcpCommand - Adapter for TCP UI command handling.
   */
  private TcpUiServer.UiResponse handleUiTcpCommand(TcpUiServer.UiCommand command) {
    if (uiHandler == null) {
      return null;
    }
    return uiHandler.handleTcpUiCommand(command);
  }

  /**
   * NAME
   *   handleUiTcpConnect - Adapter for TCP UI connect events.
   */
  private void handleUiTcpConnect(java.net.Socket socket) {
    if (uiHandler != null) {
      uiHandler.onTcpConnect(socket);
    }
  }

  /**
   * NAME
   *   handleUiTcpDisconnect - Adapter for TCP UI disconnect events.
   */
  private void handleUiTcpDisconnect() {
    if (uiHandler != null) {
      uiHandler.onTcpDisconnect();
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
    syncDefaultGroup();
    ensureActiveGroupDefined();
  }

  private Map<String, Map<String, Double>> buildAxisInputs(
      Map<String, XboxController> controllers,
      double leftDrive,
      double rightDrive) {
    Map<String, Map<String, Double>> axisInputs = new HashMap<>();
    if (controllers == null) {
      return axisInputs;
    }
    for (Map.Entry<String, XboxController> entry : controllers.entrySet()) {
      String name = entry.getKey();
      XboxController controller = entry.getValue();
      if (name == null || controller == null) {
        continue;
      }
      Map<String, Double> values = new HashMap<>();
      values.put("leftX", controller.getLeftX());
      values.put("leftY", controller.getLeftY());
      values.put("rightX", controller.getRightX());
      values.put("rightY", controller.getRightY());
      values.put("leftTrigger", controller.getLeftTriggerAxis());
      values.put("rightTrigger", controller.getRightTriggerAxis());
      if ("controller0".equals(name)) {
        values.put("leftY", leftDrive);
        values.put("rightY", rightDrive);
      }
      axisInputs.put(name, values);
    }
    return axisInputs;
  }

  /**
   * NAME
   *   AddAllHandlerImpl - Activate profile before add-all.
   */
  private final class AddAllHandlerImpl implements BringupCommandRouter.AddAllHandler {
    @Override
    public void handleAddAll(boolean addAllNow) {
      if (addAllNow && !BringupUtil.isProfileActive()) {
        activateSelectedProfileForAllSurfaces("profileActivate");
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
        activateSelectedProfileForAllSurfaces("profileActivate");
      }
      if (core() != null) {
        runtime.addMotor(addMotorNow);
      }
    }
  }

  /**
   * NAME
   *   UiCommandHandler - Delegate for TCP UI command handling.
   */
  private final class UiCommandHandler implements TcpUiServer.CommandHandler {
    @Override
    public TcpUiServer.UiResponse handle(TcpUiServer.UiCommand command) {
      return handleUiTcpCommand(command);
    }
  }

  /**
   * NAME
   *   UiConnectionListener - Delegate for TCP UI connect/disconnect.
   */
  private final class UiConnectionListener implements TcpUiServer.ConnectionListener {
    @Override
    public void onConnect(java.net.Socket socket) {
      handleUiTcpConnect(socket);
    }

    @Override
    public void onDisconnect() {
      handleUiTcpDisconnect();
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
    // Warn on duplicate CAN IDs in the active profile.
    BringupUtil.validateCanIds(BringupUtil.getActiveDevices());
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
