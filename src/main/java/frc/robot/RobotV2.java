package frc.robot;

//import edu.wpi.first.cameraserver.CameraServer;
import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import edu.wpi.first.wpilibj.livewindow.LiveWindow;
import edu.wpi.first.wpilibj.shuffleboard.Shuffleboard;
import edu.wpi.first.wpilibj.DriverStation;
import java.util.ArrayList;

import edu.wpi.first.networktables.NetworkTableInstance;
import frc.robot.input.BindingsManager;
import frc.robot.input.ControllerManager;
import frc.robot.tests.BringupTestRegistry;

// Primary bringup robot program with CAN diagnostics, JSON reporting, and controller bindings.
// This class wires controller inputs to BringupCore and DiagnosticsReporter behaviors.
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
  private BringupCore core = new BringupCore();
  // Samples roboRIO CAN controller health.
  private final CanBusHealth canHealth = new CanBusHealth();
  // Builds reports, JSON snapshots, and optional NT telemetry.
  private final DiagnosticsReporter diagnostics =
      new DiagnosticsReporter(
          core,
          canHealth,
          NetworkTableInstance.getDefault().getTable("bringup").getSubTable("diag"));
  // Edge-detect state for buttons that should fire once per press.
  private final EdgeTrigger edge = new EdgeTrigger();
  // Disable dashboard chatter by default to reduce console lag.
  private boolean dashboardUpdatesEnabled = false;
  private static final long MIN_PRINT_INTERVAL_MS = 1000;
  private long lastStartupPrintMs = 0L;

  @Override
  public void robotInit() {
    // Load profile before anything instantiates devices.
    BringupUtil.applyProfileFromArgs();
    String testsOverride = BringupUtil.extractBringupTestsFromCommand();
    BringupTestRegistry.setOverrideTestsPath(testsOverride);
    core = new BringupCore();
    diagnostics.setCore(core);
    applyDashboardUpdateState();
    // Print bindings and validate IDs once at startup.
    printStartupInfo();
    validateCanIds();
    //CameraServer.startAutomaticCapture();
  }

  @Override
  public void teleopInit() {
    // Reset state whenever teleop is entered.
    core.resetState();
    diagnostics.resetState();
    edge.reset();
  }

  @Override
  public void disabledInit() {
    // Keep behavior symmetric in disabled and teleop to avoid stale state.
    core.resetState();
    diagnostics.resetState();
    edge.reset();
  }

  @Override
  public void robotPeriodic() {
    // Sample and publish CAN health every loop.
    diagnostics.update();
  }

  @Override
  public void teleopPeriodic() {

    // --- Device instantiation / local prints ---
    if (controller == null) {
      return;
    }
    BindingsManager.BindingState bind = bindings.sample(controller, controller2, edge);

    boolean runHeld = bind.held("runTest");
    BringupCommandRouter.applyCommon(
        bind,
        core,
        diagnostics,
        this::printStartupInfo,
        runHeld);

    // --- Profile switching ---
    if (bind.pressed("profileToggle")) {
      BringupUtil.toggleCanProfile();
      core.resetState();
      core = new BringupCore();
      diagnostics.setCore(core);
      diagnostics.resetState();
      validateCanIds();
      printStartupInfo();
    }

    // --- Diagnostics / reporting ---

    // Toggle dashboard updates to reduce periodic spam.
    if (bind.pressed("toggleDashboard")) {
      dashboardUpdatesEnabled = !dashboardUpdatesEnabled;
      applyDashboardUpdateState();
      BringupPrinter.enqueue(
          "Dashboard/Shuffleboard updates: " + (dashboardUpdatesEnabled ? "ON" : "OFF"));
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

    // D-pad Right: print current stick inputs.
    if (bind.pressed("printInputs")) {
      BringupPrinter.enqueue(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")");
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
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  // Print the control bindings and active CAN profile.
  private void printStartupInfo() {
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastStartupPrintMs < MIN_PRINT_INTERVAL_MS) {
      return;
    }
    lastStartupPrintMs = nowMs;
    StringBuilder sb = new StringBuilder(512);
    ReportTextUtil.appendLine(sb, "=== Swerve Bringup V2 ===");
    ReportTextUtil.appendLine(sb, "Bindings (from bringup_bindings.json):");
    for (String line : bindings.describeBindings()) {
      ReportTextUtil.appendLine(sb, "  " + line);
    }
    for (String line : bindings.describeAxes()) {
      ReportTextUtil.appendLine(sb, "  " + line);
    }
    ReportTextUtil.appendLine(sb, "Deadband: " + DEADBAND);
    ReportTextUtil.appendLine(sb, "Dashboard updates: " + (dashboardUpdatesEnabled ? "ON" : "OFF"));
    ReportTextUtil.appendLine(sb, "CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    ReportTextUtil.appendLine(sb, "NEO CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO_CAN_IDS));
    ReportTextUtil.appendLine(sb, "NEO 550 CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO550_CAN_IDS));
    ReportTextUtil.appendLine(sb, "FLEX CAN IDs: " + BringupUtil.joinIds(BringupUtil.FLEX_CAN_IDS));
    ReportTextUtil.appendLine(sb, "KRAKEN CAN IDs: " + BringupUtil.joinIds(BringupUtil.KRAKEN_CAN_IDS));
    ReportTextUtil.appendLine(sb, "FALCON CAN IDs: " + BringupUtil.joinIds(BringupUtil.FALCON_CAN_IDS));
    ReportTextUtil.appendLine(sb, "=========================");
    BringupPrinter.enqueueChunked(sb.toString(), 12);
  }

  //@SuppressWarnings("removal")
  private void applyDashboardUpdateState() {
    // WPILib deprecated setNetworkTablesFlushEnabled; no-op in newer versions.
    LiveWindow.setEnabled(dashboardUpdatesEnabled);
    if (dashboardUpdatesEnabled) {
      Shuffleboard.enableActuatorWidgets();
    } else {
      Shuffleboard.disableActuatorWidgets();
    }
  }

  private void validateCanIds() {
    // Build labeled groups for clearer warnings on duplicates/disabled IDs.
    ArrayList<String> labels = new ArrayList<>();
    ArrayList<int[]> groups = new ArrayList<>();

    labels.add("NEO");
    groups.add(BringupUtil.NEO_CAN_IDS);
    labels.add("NEO 550");
    groups.add(BringupUtil.NEO550_CAN_IDS);
    labels.add("FLEX");
    groups.add(BringupUtil.FLEX_CAN_IDS);
    labels.add("KRAKEN");
    groups.add(BringupUtil.KRAKEN_CAN_IDS);
    labels.add("FALCON");
    groups.add(BringupUtil.FALCON_CAN_IDS);
    labels.add("CANCoder");
    groups.add(BringupUtil.CANCODER_CAN_IDS);
    if (BringupUtil.isEnabledCanId(BringupUtil.PDH_CAN_ID)) {
      labels.add("PDH");
      groups.add(new int[] { BringupUtil.PDH_CAN_ID });
    }
    if (BringupUtil.isEnabledCanId(BringupUtil.PIGEON_CAN_ID)) {
      labels.add("Pigeon");
      groups.add(new int[] { BringupUtil.PIGEON_CAN_ID });
    }
    if (BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)) {
      labels.add("roboRIO");
      groups.add(new int[] { BringupUtil.ROBORIO_CAN_ID });
    }

    BringupUtil.validateCanIds(
        labels.toArray(new String[0]),
        groups.toArray(new int[0][]));
  }

}
