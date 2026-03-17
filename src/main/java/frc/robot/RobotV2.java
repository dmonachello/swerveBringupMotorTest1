package frc.robot;

//import edu.wpi.first.cameraserver.CameraServer;
import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import edu.wpi.first.wpilibj.livewindow.LiveWindow;
import edu.wpi.first.wpilibj.shuffleboard.Shuffleboard;
import edu.wpi.first.wpilibj.DriverStation;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;

import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import frc.robot.input.BindingsManager;
import frc.robot.input.ControllerManager;
import frc.robot.tests.BringupTestRegistry;
import java.time.Instant;

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
  // Samples roboRIO CAN controller health.
  private final CanBusHealth canHealth = new CanBusHealth();
  // Builds reports, JSON snapshots, and optional NT telemetry.
  private final NetworkTable diagTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("diag");
  private DiagnosticsReporter diagnostics;
  private final NetworkTable testsTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("tests");
  private final NetworkTable uiTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("ui");
  // Edge-detect state for buttons that should fire once per press.
  private final EdgeTrigger edge = new EdgeTrigger();
  // Disable dashboard chatter by default to reduce console lag.
  private boolean dashboardUpdatesEnabled = false;
  private static final long MIN_PRINT_INTERVAL_MS = 1000;
  private long lastStartupPrintMs = 0L;
  private int lastTestsCount = 0;
  private long lastUiSeq = -1;
  private double uiFixedSpeed = Double.NaN;
  private double lastNeoSpeed = 0.0;
  private double lastKrakenSpeed = 0.0;
  private static final Gson GSON = new Gson();

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
    applyDashboardUpdateState();
    // Print bindings and validate IDs once at startup.
    printStartupInfo();
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
    BringupCommandRouter.applyCommon(
        bind,
        core,
        diagnostics,
        this::printBindings,
        this::printTestsInfo,
        this::printTestsOverview,
        runHeld);

    // --- Profile switching ---
    if (bind.pressed("profileToggle")) {
      BringupUtil.toggleCanProfile();
      resetCoreForProfile("profileToggle");
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
    if (!Double.isNaN(uiFixedSpeed)) {
      neoSpeed = uiFixedSpeed;
      krakenSpeed = uiFixedSpeed;
    }
    lastNeoSpeed = neoSpeed;
    lastKrakenSpeed = krakenSpeed;

    handleUiCommands();

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

    publishTestsSelectionStatus();
  }

  /**
   * NAME
   *   handleUiCommands - Consume bringup/ui commands from NetworkTables.
   *
   * DESCRIPTION
   *   Applies UI-driven commands using the same core actions as controller
   *   bindings, then emits ack status back over NetworkTables.
   */
  private void handleUiCommands() {
    long seq = (long) uiTable.getEntry("cmd/seq").getInteger(-1);
    if (seq <= lastUiSeq) {
      return;
    }
    lastUiSeq = seq;
    String name = uiTable.getEntry("cmd/name").getString("");
    String argsJson = uiTable.getEntry("cmd/args/json").getString("");
    boolean ok = true;
    String message = "OK";

    if (name == null || name.isBlank()) {
      ok = false;
      message = "Missing command name.";
    } else {
      switch (name) {
        case "profileToggle":
          BringupUtil.toggleCanProfile();
          resetCoreForProfile("profileToggle");
          message = "Profile toggled.";
          break;
        case "addMotor":
          core.addNextMotorCommand();
          message = "Add motor.";
          break;
        case "addAll":
          core.addAllDevicesCommand();
          message = "Add all motors.";
          break;
        case "printState":
          core.requestStateReport();
          break;
        case "printHealth":
          core.requestHealthReport();
          break;
        case "printCANcoder":
          core.requestCANCoderReport();
          break;
        case "printInputs":
          core.requestTextReport(
              "Inputs: leftY=" + String.format("%.2f", lastNeoSpeed) +
              " rightY=" + String.format("%.2f", lastKrakenSpeed) +
              " (NEO/FLEX=" + String.format("%.2f", lastNeoSpeed) +
              ", KRAKEN/FALCON=" + String.format("%.2f", lastKrakenSpeed) + ")",
              4);
          break;
        case "toggleTest":
          core.toggleSelectedBringupTestEnabled();
          printTestsOverview();
          break;
        case "runTest":
          BringupPrinter.enqueue("Command: runTest (UI)");
          core.runSelectedBringupTest();
          break;
        case "runAllTests":
          BringupPrinter.enqueue("Command: runAllTests (UI)");
          core.runAllBringupTests();
          break;
        case "printNextTest":
          core.printNextTestReport();
          break;
        case "printBindings":
          printBindings();
          break;
        case "printTestsInfo":
          printTestsInfo();
          break;
        case "printTestsOverview":
          printTestsOverview();
          break;
        case "selectTestByName":
          String testName = parseUiArgName(argsJson);
          if (testName == null || testName.isBlank()) {
            ok = false;
            message = "selectTestByName requires args.name.";
          } else {
            boolean selected = core.selectBringupTestByName(testName);
            if (!selected) {
              ok = false;
              message = "Test not found: " + testName;
            } else {
              message = "Selected test: " + testName;
              printTestsOverview();
            }
          }
          break;
        case "toggleDashboard":
          dashboardUpdatesEnabled = !dashboardUpdatesEnabled;
          applyDashboardUpdateState();
          BringupPrinter.enqueue(
              "Dashboard/Shuffleboard updates: " + (dashboardUpdatesEnabled ? "ON" : "OFF"));
          break;
        case "clearFaults":
          core.clearAllFaults();
          BringupPrinter.enqueue("Cleared device faults (current + sticky).");
          break;
        case "canSweep":
          BringupPrinter.enqueue("Command: canSweep (UI)");
          core.runCanPingSweep();
          break;
        case "fixedSpeed25":
          uiFixedSpeed = toggleUiFixedSpeed(uiFixedSpeed, 0.25);
          message = uiFixedSpeedActiveMessage();
          break;
        case "fixedSpeed50":
          uiFixedSpeed = toggleUiFixedSpeed(uiFixedSpeed, 0.50);
          message = uiFixedSpeedActiveMessage();
          break;
        case "fixedSpeed75":
          uiFixedSpeed = toggleUiFixedSpeed(uiFixedSpeed, 0.75);
          message = uiFixedSpeedActiveMessage();
          break;
        case "fixedSpeed100":
          uiFixedSpeed = toggleUiFixedSpeed(uiFixedSpeed, 1.00);
          message = uiFixedSpeedActiveMessage();
          break;
        case "printNTdiag":
          if (diagnostics != null) {
            String report = diagnostics.buildNetworkDiagnosticsReportIfReady();
            if (report != null) {
              core.requestTextReport(report, 4);
            }
          } else {
            ok = false;
            message = "Diagnostics unavailable.";
          }
          break;
        case "printCANdiag":
          if (diagnostics != null) {
            String report = diagnostics.buildCanDiagnosticsReportIfReady();
            if (report != null) {
              core.requestTextReport(report, 4);
            }
          } else {
            ok = false;
            message = "Diagnostics unavailable.";
          }
          break;
        case "dumpReport":
          if (diagnostics != null) {
            String json = diagnostics.buildReportJsonForDump();
            String wrapped = ReportTextUtil.wrapLongLine(json, 120);
            core.requestTextReport(wrapped, 4);
            if (diagnostics.writeReportJsonToFile(json)) {
              core.requestTextReport("Wrote CAN report JSON to " + diagnostics.getReportPath(), 4);
            } else {
              core.requestTextReport("Failed to write CAN report JSON.", 4);
            }
          } else {
            ok = false;
            message = "Diagnostics unavailable.";
          }
          break;
        default:
          ok = false;
          message = "Unknown command: " + name;
          break;
      }
    }
    publishUiAck(seq, ok, message);
    publishUiOut(seq, name, message);
  }

  /**
   * NAME
   *   publishUiAck - Publish UI command acknowledgements to NetworkTables.
   */
  private void publishUiAck(long seq, boolean ok, String message) {
    uiTable.getEntry("ack/seq").setInteger(seq);
    uiTable.getEntry("ack/status").setString(ok ? "ok" : "error");
    uiTable.getEntry("ack/message").setString(message != null ? message : "");
  }

  /**
   * NAME
   *   publishUiOut - Publish UI command output to NetworkTables.
   *
   * DESCRIPTION
   *   Emits at least one output entry per command to release the UI.
   */
  private void publishUiOut(long seq, String name, String text) {
    uiTable.getEntry("out/seq").setInteger(seq);
    uiTable.getEntry("out/name").setString(name != null ? name : "");
    uiTable.getEntry("out/text").setString(text != null ? text : "");
  }

  /**
   * NAME
   *   parseUiArgName - Parse args JSON for a name field.
   */
  private String parseUiArgName(String argsJson) {
    if (argsJson == null || argsJson.isBlank()) {
      return null;
    }
    try {
      JsonObject obj = GSON.fromJson(argsJson, JsonObject.class);
      if (obj != null && obj.has("name")) {
        return obj.get("name").getAsString();
      }
    } catch (JsonParseException ex) {
      return null;
    }
    return null;
  }

  /**
   * NAME
   *   toggleUiFixedSpeed - Toggle a fixed-speed override.
   */
  private double toggleUiFixedSpeed(double current, double value) {
    if (Double.isNaN(current)) {
      return value;
    }
    if (Math.abs(current - value) < 1e-6) {
      return Double.NaN;
    }
    return value;
  }

  /**
   * NAME
   *   uiFixedSpeedActiveMessage - Build a status message for fixed speed state.
   */
  private String uiFixedSpeedActiveMessage() {
    if (Double.isNaN(uiFixedSpeed)) {
      return "Fixed speed: OFF.";
    }
    return "Fixed speed: " + String.format("%.2f", uiFixedSpeed);
  }

  /**
   * NAME
   *   resetCoreForProfile - Rebuild core and diagnostics after profile changes.
   */
  private void resetCoreForProfile(String reason) {
    core.resetState(reason);
    core = new BringupCore();
    if (diagnostics != null) {
      diagnostics.setCore(core);
      diagnostics.resetState();
    }
    validateCanIds();
    printProfileInfo();
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  // Print the control bindings and active CAN profile.
  /**
   * NAME
   *   printStartupInfo - Emit bindings and profile diagnostics.
   *
   * DESCRIPTION
   *   Builds a multi-line report of control bindings and active CAN IDs.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  private void printStartupInfo() {
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastStartupPrintMs < MIN_PRINT_INTERVAL_MS) {
      return;
    }
    lastStartupPrintMs = nowMs;
    StringBuilder sb = new StringBuilder(512);
    ReportTextUtil.appendLine(sb, "=== Swerve Bringup V2 ===");
    ReportTextUtil.appendLine(sb, "Build: " + BringupCore.getBuildMarker());
    ReportTextUtil.appendLine(sb, "Deadband: " + DEADBAND);
    ReportTextUtil.appendLine(sb, "Dashboard updates: " + (dashboardUpdatesEnabled ? "ON" : "OFF"));
    ReportTextUtil.appendLine(sb, "CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    appendDeviceSummary(sb);
    ReportTextUtil.appendLine(sb, "=========================");
    core.requestTextReport(sb.toString(), 4);
  }

  /**
   * NAME
   *   printBindings - Emit the command list on demand.
   *
   * DESCRIPTION
   *   Prints the current controller bindings and axis mappings.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  private void printBindings() {
    StringBuilder sb = new StringBuilder(384);
    ReportTextUtil.appendLine(sb, "=== Bringup Bindings ===");
    ReportTextUtil.appendLine(sb, "Build: " + BringupCore.getBuildMarker());
    for (String line : bindings.describeBindings()) {
      ReportTextUtil.appendLine(sb, "  " + line);
    }
    for (String line : bindings.describeAxes()) {
      ReportTextUtil.appendLine(sb, "  " + line);
    }
    ReportTextUtil.appendLine(sb, "========================");
    core.requestTextReport(sb.toString(), 4);
  }

  /**
   * NAME
   *   printProfileInfo - Emit CAN profile details after a switch.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  private void printProfileInfo() {
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastStartupPrintMs < MIN_PRINT_INTERVAL_MS) {
      return;
    }
    lastStartupPrintMs = nowMs;
    StringBuilder sb = new StringBuilder(256);
    ReportTextUtil.appendLine(sb, "=== Profile Updated ===");
    ReportTextUtil.appendLine(sb, "Build: " + BringupCore.getBuildMarker());
    ReportTextUtil.appendLine(sb, "CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    appendDeviceSummary(sb);
    ReportTextUtil.appendLine(sb, "========================");
    core.requestTextReport(sb.toString(), 4);
  }

  /**
   * NAME
   *   appendDeviceSummary - Append active devices grouped by vendor/type.
   *
   * PARAMETERS
   *   sb - Target StringBuilder.
   */
  private void appendDeviceSummary(StringBuilder sb) {
    List<BringupUtil.DeviceEntry> devices = BringupUtil.getActiveDevicesSorted();
    if (devices.isEmpty()) {
      ReportTextUtil.appendLine(sb, "Devices: (none)");
      return;
    }
    Map<String, List<Integer>> groups = new java.util.LinkedHashMap<>();
    for (BringupUtil.DeviceEntry entry : devices) {
      if (entry == null || !BringupUtil.isEnabledCanId(entry.id)) {
        continue;
      }
      String vendor = entry.vendor != null ? entry.vendor.trim() : "";
      String type = entry.type != null ? entry.type.trim() : "";
      String key = (vendor.isEmpty() ? "UNKNOWN" : vendor) + " " + (type.isEmpty() ? "Device" : type);
      groups.computeIfAbsent(key, ignored -> new ArrayList<>()).add(entry.id);
    }
    for (Map.Entry<String, List<Integer>> entry : groups.entrySet()) {
      List<Integer> ids = entry.getValue();
      if (ids.isEmpty()) {
        continue;
      }
      StringBuilder line = new StringBuilder();
      for (int i = 0; i < ids.size(); i++) {
        if (i > 0) {
          line.append(", ");
        }
        line.append(ids.get(i));
      }
      ReportTextUtil.appendLine(sb, entry.getKey() + " CAN IDs: " + line);
    }
  }

  /**
   * NAME
   *   printTestsInfo - Emit bringup test file diagnostics.
   *
   * DESCRIPTION
   *   Reports resolved test file path, metadata, and active test set info.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  private void printTestsInfo() {
    BringupTestRegistry.TestsInfo info = BringupTestRegistry.getTestsInfo();
    StringBuilder sb = new StringBuilder(256);
    ReportTextUtil.appendLine(sb, "=== Bringup Tests Info ===");
    ReportTextUtil.appendLine(
        sb,
        "Override path: " + (info.overridePath != null ? info.overridePath : "(none)"));
    ReportTextUtil.appendLine(
        sb,
        "Resolved path: " + (info.path != null ? info.path.toString() : "(none)"));
    ReportTextUtil.appendLine(sb, "Exists: " + info.exists);
    if (info.exists) {
      if (info.sizeBytes > 0) {
        ReportTextUtil.appendLine(sb, "Size: " + info.sizeBytes + " bytes");
      }
      if (info.lastModifiedMs > 0) {
        ReportTextUtil.appendLine(sb, "Last modified: " + Instant.ofEpochMilli(info.lastModifiedMs));
      }
      if (info.sha256 != null && !info.sha256.isBlank()) {
        ReportTextUtil.appendLine(sb, "SHA-256: " + info.sha256);
      }
      if (info.readError != null) {
        ReportTextUtil.appendLine(sb, "Read warning: " + info.readError);
      }
      if (info.usingTestSets) {
        String active = info.activeTestSetName != null ? info.activeTestSetName : "(none)";
        String def = info.defaultTestSetName != null ? info.defaultTestSetName : "(none)";
        ReportTextUtil.appendLine(
            sb,
            "Test sets: yes (active=" + active + ", default=" + def + ", count=" + info.testSetCount + ")");
      } else {
        ReportTextUtil.appendLine(sb, "Test sets: no");
      }
      if (info.testCount > 0) {
        ReportTextUtil.appendLine(sb, "Test count: " + info.testCount);
      }
    }
    ReportTextUtil.appendLine(sb, "==========================");
    core.requestTextReport(sb.toString(), 4);
  }

  /**
   * NAME
   *   printTestsOverview - Emit and publish a tests overview snapshot.
   *
   * SIDE EFFECTS
   *   Enqueues a text report and updates NetworkTables.
   */
  private void printTestsOverview() {
    BringupCore.TestsOverview overview = core.buildTestsOverview();
    String text = core.formatTestsOverview(overview);
    core.requestTextReport(text, 6);
    publishTestsOverview(overview);
  }

  /**
   * NAME
   *   publishTestsOverview - Publish test rows to NetworkTables.
   *
   * PARAMETERS
   *   overview - Snapshot of current test sets and rows.
   *
   * SIDE EFFECTS
   *   Writes NetworkTables entries under bringup/tests.
   */
  private void publishTestsOverview(BringupCore.TestsOverview overview) {
    if (overview == null) {
      return;
    }
    testsTable.getEntry("activeSet")
        .setString(overview.activeTestSet != null ? overview.activeTestSet : "");
    testsTable.getEntry("defaultSet")
        .setString(overview.defaultTestSet != null ? overview.defaultTestSet : "");
    testsTable.getEntry("usingTestSets").setBoolean(overview.usingTestSets);
    testsTable.getEntry("totalCount").setNumber(overview.totalCount);
    testsTable.getEntry("enabledCount").setNumber(overview.enabledCount);
    testsTable.getEntry("selectedIndex").setNumber(core.getSelectedBringupTestIndex());
    testsTable.getEntry("selectedName").setString(core.getSelectedBringupTestName());
    testsTable.getEntry("activeName").setString(core.getActiveBringupTestName());
    testsTable.getEntry("activeStatus").setString(core.getActiveBringupTestStatus());
    testsTable.getEntry("runAllActive").setBoolean(core.isRunAllActive());
    NetworkTable rowsTable = testsTable.getSubTable("rows");
    int count = overview.rows.size();
    for (int i = 0; i < count; i++) {
      BringupCore.TestRow row = overview.rows.get(i);
      NetworkTable rowTable = rowsTable.getSubTable(String.valueOf(i));
      rowTable.getEntry("index").setNumber(row.index);
      rowTable.getEntry("name").setString(row.name != null ? row.name : "");
      rowTable.getEntry("enabled").setBoolean(row.enabled);
      rowTable.getEntry("selected").setBoolean(row.selected);
      rowTable.getEntry("type").setString(row.type != null ? row.type : "");
      rowTable.getEntry("status").setString(row.status != null ? row.status : "");
      String motors =
          (row.motors == null || row.motors.isEmpty()) ? "" : String.join(", ", row.motors);
      rowTable.getEntry("motors").setString(motors);
    }
    for (int i = count; i < lastTestsCount; i++) {
      NetworkTable rowTable = rowsTable.getSubTable(String.valueOf(i));
      rowTable.getEntry("index").setNumber(-1);
      rowTable.getEntry("name").setString("");
      rowTable.getEntry("enabled").setBoolean(false);
      rowTable.getEntry("selected").setBoolean(false);
      rowTable.getEntry("type").setString("");
      rowTable.getEntry("status").setString("");
      rowTable.getEntry("motors").setString("");
    }
    lastTestsCount = count;
  }

  /**
   * NAME
   *   publishTestsSelectionStatus - Publish lightweight test selection/running status.
   *
   * SIDE EFFECTS
   *   Writes selected and active test info to NetworkTables.
   */
  private void publishTestsSelectionStatus() {
    testsTable.getEntry("selectedIndex").setNumber(core.getSelectedBringupTestIndex());
    testsTable.getEntry("selectedName").setString(core.getSelectedBringupTestName());
    testsTable.getEntry("activeName").setString(core.getActiveBringupTestName());
    testsTable.getEntry("activeStatus").setString(core.getActiveBringupTestStatus());
    testsTable.getEntry("runAllActive").setBoolean(core.isRunAllActive());
  }

  //@SuppressWarnings("removal")
  /**
   * NAME
   *   applyDashboardUpdateState - Enable/disable dashboard widgets.
   *
   * DESCRIPTION
   *   Toggles LiveWindow and Shuffleboard actuator widgets to reduce chatter.
   */
  private void applyDashboardUpdateState() {
    // WPILib deprecated setNetworkTablesFlushEnabled; no-op in newer versions.
    LiveWindow.setEnabled(dashboardUpdatesEnabled);
    if (dashboardUpdatesEnabled) {
      Shuffleboard.enableActuatorWidgets();
    } else {
      Shuffleboard.disableActuatorWidgets();
    }
  }

  /**
   * NAME
   *   validateCanIds - Check for duplicate or invalid CAN IDs.
   *
   * DESCRIPTION
   *   Builds labeled groups for clearer warning output from BringupUtil.
   */
  private void validateCanIds() {
    // Warn on duplicate CAN IDs in the active profile.
    BringupUtil.validateCanIds(BringupUtil.getActiveDevices());
  }

}
