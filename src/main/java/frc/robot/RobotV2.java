package frc.robot;

import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import edu.wpi.first.wpilibj.livewindow.LiveWindow;
import edu.wpi.first.wpilibj.shuffleboard.Shuffleboard;
import java.util.ArrayList;

import edu.wpi.first.networktables.NetworkTableInstance;

// Primary bringup robot program with CAN diagnostics, JSON reporting, and controller bindings.
// This class wires controller inputs to BringupCore and DiagnosticsReporter behaviors.
public class RobotV2 extends TimedRobot {

  // ---------------- CAN ID DEFINITIONS ----------------
  private static final double DEADBAND = BringupUtil.DEADBAND;
  // ---------------------------------------------------

  // Driver Station controller input.
  private final XboxController controller = new XboxController(0);
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
    applyDashboardUpdateState();
    // Print bindings and validate IDs once at startup.
    printStartupInfo();
    validateCanIds();
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
    core.handleAdd(controller.getAButton());
    core.handleAddAll(controller.getStartButton());
    core.handlePrint(controller.getBButton());
    boolean healthNow = controller.getPOV() == 270;
    core.handleHealth(healthNow);
    boolean leftBumper = controller.getLeftBumperButton();
    boolean rightBumper = controller.getRightBumperButton();
    boolean nonMotorTest = leftBumper && rightBumper;
    core.handleCANCoder(nonMotorTest ? false : rightBumper);
    if (edge.pressed("nonMotorTest", nonMotorTest)) {
      core.runNextNonMotorTest();
    }

    // --- Profile switching ---
    if (edge.pressed("profileToggle", controller.getBackButton())) {
      BringupUtil.toggleCanProfile();
      core.resetState();
      core = new BringupCore();
      diagnostics.setCore(core);
      diagnostics.resetState();
      validateCanIds();
      printStartupInfo();
    }

    // --- Diagnostics / reporting ---
    // D-pad Down: print NetworkTables diagnostics.
    if (edge.pressed("ntDiag", controller.getPOV() == 180)) {
      diagnostics.printNetworkDiagnostics();
    }

    if (edge.pressed("bindings", leftBumper && !rightBumper)) {
      printStartupInfo();
    }

    // D-pad Up: print CAN diagnostics report (local + optional PC tool data).
    if (edge.pressed("canDiag", controller.getPOV() == 0)) {
      diagnostics.printCanDiagnosticsReport();
    }

    // Toggle dashboard updates to reduce periodic spam.
    if (edge.pressed("dashboardToggle", controller.getYButton())) {
      dashboardUpdatesEnabled = !dashboardUpdatesEnabled;
      applyDashboardUpdateState();
      BringupPrinter.enqueue(
          "Dashboard/Shuffleboard updates: " + (dashboardUpdatesEnabled ? "ON" : "OFF"));
    }

    // --- Analog input to motor outputs ---
    double neoSpeed = BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
    double krakenSpeed = BringupUtil.deadband(-controller.getRightY(), DEADBAND);

    // D-pad Right: print current stick inputs.
    if (edge.pressed("speedPrint", controller.getPOV() == 90)) {
      BringupPrinter.enqueue(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")");
    }

    // Left Stick: short, timed nudge for all motors.
    if (edge.pressed("nudge", controller.getLeftStickButton())) {
      core.triggerNudge(0.2, 0.5);
      BringupPrinter.enqueue("Nudge: 0.2 for 0.5s (all motors)");
    }

    // X: dump JSON snapshot to console + file for offline analysis.
    if (edge.pressed("reportDump", controller.getXButton())) {
      diagnostics.dumpReportJsonToConsoleAndFile();
    }

    // Right Stick: clear faults (current + sticky) on all devices.
    if (edge.pressed("clearFaults", controller.getRightStickButton())) {
      core.clearAllFaults();
      BringupPrinter.enqueue("Cleared device faults (current + sticky).");
    }

    // Apply speeds after any nudge overrides.
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
    ReportTextUtil.appendLine(sb, "A: add motor (alternates SPARK/CTRE)");
    ReportTextUtil.appendLine(sb, "Start: add all configured devices");
    ReportTextUtil.appendLine(sb, "B: print state");
    ReportTextUtil.appendLine(sb, "D-pad Left: print health status");
    ReportTextUtil.appendLine(sb, "Right Bumper: print CANCoder absolute positions");
    ReportTextUtil.appendLine(sb, "Left+Right Bumper: run non-motor test");
    ReportTextUtil.appendLine(sb, "Back: toggle CAN profile");
    ReportTextUtil.appendLine(sb, "D-pad Down: print NetworkTables diagnostics");
    ReportTextUtil.appendLine(sb, "Left Bumper: reprint bindings");
    ReportTextUtil.appendLine(sb, "D-pad Up: print CAN diagnostics report");
    ReportTextUtil.appendLine(sb, "D-pad Right: print speed inputs");
    ReportTextUtil.appendLine(sb, "Left Stick: nudge motors (0.2 for 0.5s)");
    ReportTextUtil.appendLine(sb, "Right Stick: clear device faults");
    ReportTextUtil.appendLine(sb, "X: dump CAN report JSON");
    ReportTextUtil.appendLine(sb, "Y: toggle dashboard/shuffleboard updates");
    ReportTextUtil.appendLine(sb, "Left Y: NEO/FLEX speed, Right Y: KRAKEN/FALCON speed");
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
    // WPILib deprecated setNetworkTablesFlushEnabled; we keep it for our version.
    setNetworkTablesFlushEnabled(dashboardUpdatesEnabled);
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
