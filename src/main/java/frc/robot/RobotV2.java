package frc.robot;

//import edu.wpi.first.cameraserver.CameraServer;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import frc.robot.input.BindingsManager;
import frc.robot.input.ControllerManager;
import frc.robot.tests.BringupTestRegistry;
import frc.robot.ui.TcpUiServer;

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
  // ---------------------------------------------------

  // Driver Station controller input.
  private final ControllerManager controllers = new ControllerManager();
  private final XboxController controller = controllers.getXbox(0);
  // Optional second controller for fixed-speed test buttons.
  private final XboxController controller2 = controllers.getXbox(1);
  private final BindingsManager bindings = new BindingsManager();
  // Local bringup behaviors for device creation and health.
  private BringupCore core;
  // Runtime groups and bindings for bridge CLI/GUI.
  private final BridgeGroupManager bridgeGroups = new BridgeGroupManager();
  private final BridgeGroupManager.SelectedState bridgeSelected = new BridgeGroupManager.SelectedState();
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
  private DiagnosticsReporter diagnostics;
  private BridgeUiCommandHandler uiHandler;
  // Edge-detect state for buttons that should fire once per press.
  private final EdgeTrigger edge = new EdgeTrigger();
  private static final int UI_TCP_PORT = 5809;
  private TcpUiServer uiTcpServer;
  private final TcpUiServer.CommandHandler uiCommandHandler = new UiCommandHandler();
  private final TcpUiServer.ConnectionListener uiConnectionListener = new UiConnectionListener();
  private final BringupPrinter.LineListener bringupLineListener = new BringupLineListener();
  private final Runnable profileToggleAction = new ProfileToggleAction();
  private final Runnable profileActivateAction = new ProfileActivateAction();
  private final Runnable bindingsPrinter = new BindingsPrinter();
  private final Runnable testsInfoPrinter = new TestsInfoPrinter();
  private final Runnable testsOverviewPrinter = new TestsOverviewPrinter();
  private final BringupCommandRouter.AddAllHandler addAllHandler = new AddAllHandlerImpl();
  private final BringupCommandRouter.AddMotorHandler addMotorHandler = new AddMotorHandlerImpl();

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
    String testsOverride = BringupUtil.extractBringupTestsFromCommand();
    BringupTestRegistry.setOverrideTestsPath(testsOverride);
    core = new BringupCore();
    diagnostics = new DiagnosticsReporter(core, canHealth, diagTable);
    uiHandler = new BridgeUiCommandHandler(
        core,
        diagnostics,
        bindings,
        bridgeGroups,
        bridgeSelected,
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
    core.resetState("teleopInit");
    if (diagnostics != null) {
      diagnostics.resetState();
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
    core.disableAllBringupTests(true);
    core.resetState("disabledInit");
    if (diagnostics != null) {
      diagnostics.resetState();
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
    if (diagnostics != null) {
      diagnostics.update();
    }
    if (uiHandler != null) {
      uiHandler.processTcpCommands();
      boolean xboxConnected = controller != null && DriverStation.isJoystickConnected(0);
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
   *   outputs within the 20ms loop budget.
   */
  @Override
  public void teleopPeriodic() {

    // --- Device instantiation / local prints ---
    if (controller == null) {
      return;
    }
    BindingsManager.BindingState bind = bindings.sample(controller, controller2, edge);

    boolean runHeld = bind.held("runTest");
    BringupCommandRouter.CommonResult commonResult = BringupCommandRouter.applyCommon(
        bind,
        core,
        diagnostics,
        bindingsPrinter,
        testsInfoPrinter,
        testsOverviewPrinter,
        runHeld,
        addAllHandler,
        addMotorHandler);

    // --- Profile switching ---
    if (bind.pressed("profileToggle")) {
      BringupUtil.selectNextProfile();
      if (uiHandler != null) {
        uiHandler.printProfileInfo();
      }
    }

    // --- Diagnostics / reporting ---

    // Toggle dashboard updates to reduce periodic spam.
    if (bind.pressed("toggleDashboard")) {
      if (uiHandler != null) {
        uiHandler.toggleDashboardUpdates();
      }
    }

    // --- Analog input to motor outputs ---
    double neoSpeed = bind.hasAxis("leftDrive")
        ? bind.axis("leftDrive")
        : BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
    double krakenSpeed = bind.hasAxis("rightDrive")
        ? bind.axis("rightDrive")
        : BringupUtil.deadband(-controller.getRightY(), DEADBAND);

    boolean controller2Connected = controller2 != null && DriverStation.isJoystickConnected(1);
    if (controller2Connected) {
      double fixedSpeed = Double.NaN;
      if (bind.held("fixedSpeed25")) {
        fixedSpeed = 0.25;
      } else if (bind.held("fixedSpeed50")) {
        fixedSpeed = 0.50;
      } else if (bind.held("fixedSpeed75")) {
        fixedSpeed = 0.75;
      } else if (bind.held("fixedSpeed100")) {
        fixedSpeed = 1.00;
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
    if (bind.pressed("printInputs")) {
      core.requestTextReport(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")",
          4);
    }

    if (controller2Connected) {
      if (bind.pressed("fixedSpeed25")) {
        BringupPrinter.enqueue("Fixed speed: 0.25 (Controller 2 A)");
      }
      if (bind.pressed("fixedSpeed50")) {
        BringupPrinter.enqueue("Fixed speed: 0.50 (Controller 2 B)");
      }
      if (bind.pressed("fixedSpeed75")) {
        BringupPrinter.enqueue("Fixed speed: 0.75 (Controller 2 X)");
      }
      if (bind.pressed("fixedSpeed100")) {
        BringupPrinter.enqueue("Fixed speed: 1.00 (Controller 2 Y)");
      }
    }

    // core update and diagnostics handled by BringupCommandRouter

    // Feed test inputs (used by joystick-mode tests).
    core.setTestInputs(neoSpeed, krakenSpeed);

    // Apply speeds after inputs are processed.
    core.setSpeeds(neoSpeed, krakenSpeed);

    BridgeGroupManager.InputSnapshot inputs = new BridgeGroupManager.InputSnapshot();
    inputs.driverLeftY = BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
    inputs.driverRightY = BringupUtil.deadband(-controller.getRightY(), DEADBAND);
    inputs.driverA = controller.getAButton();
    inputs.driverB = controller.getBButton();
    inputs.driverX = controller.getXButton();
    inputs.driverY = controller.getYButton();
    inputs.driverLb = controller.getLeftBumperButton();
    inputs.driverRb = controller.getRightBumperButton();
    if (controller2Connected) {
      inputs.operatorLeftY = BringupUtil.deadband(-controller2.getLeftY(), DEADBAND);
      inputs.operatorRightY = BringupUtil.deadband(-controller2.getRightY(), DEADBAND);
      inputs.operatorA = controller2.getAButton();
      inputs.operatorB = controller2.getBButton();
      inputs.operatorX = controller2.getXButton();
      inputs.operatorY = controller2.getYButton();
      inputs.operatorLb = controller2.getLeftBumperButton();
      inputs.operatorRb = controller2.getRightBumperButton();
    }
    bridgeGroups.applyBindings(inputs, core, bridgeSelected);

    if (uiHandler != null) {
      uiHandler.publishTestsSelectionStatus();
    }
  }

  private void resetCoreForProfile(String reason) {
    core.resetState(reason);
    core = new BringupCore();
    if (diagnostics != null) {
      diagnostics.setCore(core);
      diagnostics.resetState();
    }
    validateCanIds();
    if (uiHandler != null) {
      uiHandler.setCore(core);
      uiHandler.setDiagnostics(diagnostics);
      uiHandler.printProfileInfo();
    }
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
   *   handleProfileActivate - Adapter for profile activation.
   */
  private void handleProfileActivate() {
    resetCoreForProfile("profileActivate");
  }

  /**
   * NAME
   *   AddAllHandlerImpl - Activate profile before add-all.
   */
  private final class AddAllHandlerImpl implements BringupCommandRouter.AddAllHandler {
    @Override
    public void handleAddAll(boolean addAllNow) {
      if (addAllNow && !BringupUtil.isProfileActive()) {
        BringupUtil.prepareActivationForSelectedProfile();
        BringupUtil.activateSelectedProfile();
        if (BringupUtil.isProfileActive()) {
          resetCoreForProfile("profileActivate");
        }
      }
      if (core != null) {
        core.handleAddAll(addAllNow);
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
        BringupUtil.prepareActivationForSelectedProfile();
        BringupUtil.activateSelectedProfile();
        if (BringupUtil.isProfileActive()) {
          resetCoreForProfile("profileActivate");
        }
      }
      if (core != null) {
        core.handleAdd(addMotorNow);
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

}
