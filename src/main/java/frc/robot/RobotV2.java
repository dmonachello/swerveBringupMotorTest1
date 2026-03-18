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
import java.util.UUID;

import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import frc.robot.input.BindingsManager;
import frc.robot.input.ControllerManager;
import frc.robot.tests.BringupTestRegistry;
import frc.robot.ui.TcpUiServer;
import java.time.Instant;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

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
  private long lastUiAckMs = 0L;
  private static final int UI_PROTOCOL_VERSION = 1;
  private String uiSessionId = UUID.randomUUID().toString();
  private String activeUiClientId = null;
  private long lastTcpSeq = -1;
  private static final long TCP_CMD_TIMEOUT_MS = 1000;
  private final ConcurrentLinkedQueue<TcpPendingCommand> tcpCommandQueue = new ConcurrentLinkedQueue<>();
  private static final int UI_TCP_PORT = 5809;
  private TcpUiServer uiTcpServer;
  private boolean uiProtocolMonitorEnabled = false;
  private final NetworkTable uiTcpTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("ui_tcp");
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
    uiTcpServer = new TcpUiServer(
        UI_TCP_PORT,
        this::handleTcpUiCommand,
        new TcpUiServer.ConnectionListener() {
          @Override
          public void onConnect(java.net.Socket socket) {
            onTcpConnect(socket);
          }

          @Override
          public void onDisconnect() {
            onTcpDisconnect();
          }
        });
    uiTcpServer.start();
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
    processTcpCommands();
    publishUiRobotState();
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
    double cmdTs = uiTable.getEntry("cmd/ts").getDouble(0.0);
    String clientId = uiTable.getEntry("cmd/clientId").getString("");
    UiCommandResult result = processUiCommand(name, argsJson, cmdTs, clientId);
    publishUiAck(seq, result.ok, result.message, name, cmdTs);
    publishUiOut(seq, name, result.outText, cmdTs, result.outJson);
  }

  /**
   * NAME
   *   handleTcpUiCommand - Handle a TCP UI command and build responses.
   */
  private TcpUiServer.UiResponse handleTcpUiCommand(TcpUiServer.UiCommand command) {
    if (command == null) {
      return null;
    }
    TcpPendingCommand pending = new TcpPendingCommand(command);
    tcpCommandQueue.add(pending);
    try {
      return pending.future.get(TCP_CMD_TIMEOUT_MS, TimeUnit.MILLISECONDS);
    } catch (TimeoutException ex) {
      pending.cancelled = true;
      UiCommandResult result = new UiCommandResult();
      result.ok = false;
      result.message = "Robot loop timeout.";
      result.outText = result.message;
      return buildTcpResponse(command, result);
    } catch (Exception ex) {
      pending.cancelled = true;
      UiCommandResult result = new UiCommandResult();
      result.ok = false;
      result.message = "UI command failed: " + ex.getMessage();
      result.outText = result.message;
      return buildTcpResponse(command, result);
    }
  }

  /**
   * NAME
   *   onTcpConnect - Handle TCP UI client connect events.
   */
  private void onTcpConnect(java.net.Socket socket) {
    if (uiProtocolMonitorEnabled) {
      uiTcpTable.getEntry("connected").setBoolean(true);
      if (socket != null && socket.getRemoteSocketAddress() != null) {
        uiTcpTable.getEntry("remote").setString(socket.getRemoteSocketAddress().toString());
      }
    }
  }

  /**
   * NAME
   *   onTcpDisconnect - Handle TCP UI client disconnect events.
   */
  private void onTcpDisconnect() {
    activeUiClientId = null;
    if (uiProtocolMonitorEnabled) {
      uiTcpTable.getEntry("connected").setBoolean(false);
    }
  }

  /**
   * NAME
   *   processTcpCommands - Drain queued TCP commands on the main loop.
   */
  private void processTcpCommands() {
    TcpPendingCommand pending;
    while ((pending = tcpCommandQueue.poll()) != null) {
      TcpUiServer.UiCommand command = pending.command;
      if (command == null || pending.cancelled) {
        continue;
      }
      lastTcpSeq = command.seq;
      UiCommandResult result = processUiCommand(
          command.name,
          command.argsJson,
          command.ts,
          command.clientId);
      TcpUiServer.UiResponse response = buildTcpResponse(command, result);
      pending.future.complete(response);
    }
  }

  /**
   * NAME
   *   buildTcpResponse - Build ACK/OUT payloads for TCP responses.
   */
  private TcpUiServer.UiResponse buildTcpResponse(TcpUiServer.UiCommand command, UiCommandResult result) {
    JsonObject state = buildUiStateJson();
    JsonObject ack = new JsonObject();
    ack.addProperty("type", "ack");
    ack.addProperty("seq", command.seq);
    ack.addProperty("name", command.name != null ? command.name : "");
    ack.addProperty("status", result.ok ? "ok" : "error");
    ack.addProperty("message", result.message != null ? result.message : "");
    ack.addProperty("ts", command.ts);
    ack.addProperty("sessionId", uiSessionId);
    ack.add("state", state);

    JsonObject out = new JsonObject();
    out.addProperty("type", "out");
    out.addProperty("seq", command.seq);
    out.addProperty("name", command.name != null ? command.name : "");
    out.addProperty("text", result.outText != null ? result.outText : "");
    out.addProperty("ts", command.ts);
    out.addProperty("sessionId", uiSessionId);
    if (result.outJson != null && !result.outJson.isBlank()) {
      out.addProperty("json", result.outJson);
    }
    out.add("state", state);

    if (uiProtocolMonitorEnabled) {
      publishUiTcpMonitor(command.seq, command.name, command.clientId, result);
    }

    return new TcpUiServer.UiResponse(ack.toString(), out.toString());
  }

  /**
   * NAME
   *   TcpPendingCommand - Pending TCP command for the main loop.
   */
  private static final class TcpPendingCommand {
    private final TcpUiServer.UiCommand command;
    private final CompletableFuture<TcpUiServer.UiResponse> future;
    private volatile boolean cancelled;

    private TcpPendingCommand(TcpUiServer.UiCommand command) {
      this.command = command;
      this.future = new CompletableFuture<>();
      this.cancelled = false;
    }
  }

  /**
   * NAME
   *   UiCommandResult - Result bundle for UI command handling.
   */
  private static final class UiCommandResult {
    private boolean ok = true;
    private String message = "OK";
    private String outText = "OK";
    private String outJson = "";
  }

  /**
   * NAME
   *   processUiCommand - Execute a UI command and return the result.
   */
  private UiCommandResult processUiCommand(String name, String argsJson, double cmdTs, String clientId) {
    UiCommandResult result = new UiCommandResult();
    if (name == null || name.isBlank()) {
      result.ok = false;
      result.message = "Missing command name.";
      result.outText = result.message;
      return result;
    }
    JsonObject args = parseUiArgs(argsJson);
    String client = clientId != null ? clientId.trim() : "";
    boolean hasClient = !client.isEmpty();
    boolean locked = activeUiClientId != null && !activeUiClientId.isBlank();
    boolean isHandshake = "uiHandshake".equals(name);
    boolean isDisconnect = "uiDisconnect".equals(name);
    boolean isEnabled = DriverStation.isEnabled();
    boolean isEStopped = DriverStation.isEStopped();

    if (!hasClient) {
      result.ok = false;
      result.message = "Missing clientId.";
    } else if (locked && !activeUiClientId.equals(client)) {
      result.ok = false;
      result.message = "UI locked by another client. Disconnect or reboot to switch.";
    } else if (!locked && !isHandshake && !isDisconnect) {
      result.ok = false;
      result.message = "UI handshake required before commands.";
    } else if (!isHandshake && !isDisconnect && !isEnabled) {
      result.ok = false;
      result.message = isEStopped ? "Robot disabled (E-Stop)." : "Robot disabled.";
    }

    if (!result.ok) {
      result.outText = result.message;
      return result;
    }

    switch (name) {
      case "uiHandshake":
        if (!locked) {
          activeUiClientId = client;
        }
        boolean reset = args != null && args.has("reset") && args.get("reset").getAsBoolean();
        if (reset) {
          uiSessionId = UUID.randomUUID().toString();
        }
        long baseSeq = Math.max(lastUiSeq, lastTcpSeq);
        JsonObject payload = new JsonObject();
        payload.addProperty("sessionId", uiSessionId);
        payload.addProperty("lastAckSeq", baseSeq);
        payload.addProperty("minNextSeq", baseSeq + 1);
        payload.addProperty("protocolVersion", UI_PROTOCOL_VERSION);
        result.outJson = payload.toString();
        result.message = reset ? "UI session reset." : "UI handshake OK.";
        break;
      case "uiDisconnect":
        if (locked && activeUiClientId.equals(client)) {
          activeUiClientId = null;
          result.message = "UI lock released.";
          if (uiProtocolMonitorEnabled) {
            uiTcpTable.getEntry("connected").setBoolean(false);
          }
        } else if (!locked) {
          result.message = "No active UI lock.";
        } else {
          result.ok = false;
          result.message = "UI lock held by another client.";
        }
        break;
      case "uiMonitorEnable":
        uiProtocolMonitorEnabled = true;
        result.message = "Protocol monitor enabled.";
        break;
      case "uiMonitorDisable":
        uiProtocolMonitorEnabled = false;
        uiTcpTable.getEntry("enabled").setBoolean(false);
        uiTcpTable.getEntry("connected").setBoolean(false);
        result.message = "Protocol monitor disabled.";
        break;
      case "profileToggle":
        BringupUtil.toggleCanProfile();
        resetCoreForProfile("profileToggle");
        result.message = "Profile toggled.";
        break;
      case "addMotor":
        core.addNextMotorCommand();
        result.message = "Add motor.";
        break;
      case "addAll":
        core.addAllDevicesCommand();
        result.message = "Add all motors.";
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
        String testName = parseUiArgName(args);
        if (testName == null || testName.isBlank()) {
          result.ok = false;
          result.message = "selectTestByName requires args.name.";
        } else {
          boolean selected = core.selectBringupTestByName(testName);
          if (!selected) {
            result.ok = false;
            result.message = "Test not found: " + testName;
          } else {
            result.message = "Selected test: " + testName;
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
        result.message = uiFixedSpeedActiveMessage();
        break;
      case "fixedSpeed50":
        uiFixedSpeed = toggleUiFixedSpeed(uiFixedSpeed, 0.50);
        result.message = uiFixedSpeedActiveMessage();
        break;
      case "fixedSpeed75":
        uiFixedSpeed = toggleUiFixedSpeed(uiFixedSpeed, 0.75);
        result.message = uiFixedSpeedActiveMessage();
        break;
      case "fixedSpeed100":
        uiFixedSpeed = toggleUiFixedSpeed(uiFixedSpeed, 1.00);
        result.message = uiFixedSpeedActiveMessage();
        break;
      case "printNTdiag":
        if (diagnostics != null) {
          String report = diagnostics.buildNetworkDiagnosticsReportIfReady();
          if (report != null) {
            core.requestTextReport(report, 4);
          }
        } else {
          result.ok = false;
          result.message = "Diagnostics unavailable.";
        }
        break;
      case "printCANdiag":
        if (diagnostics != null) {
          String report = diagnostics.buildCanDiagnosticsReportIfReady();
          if (report != null) {
            core.requestTextReport(report, 4);
          }
        } else {
          result.ok = false;
          result.message = "Diagnostics unavailable.";
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
          result.ok = false;
          result.message = "Diagnostics unavailable.";
        }
        break;
      default:
        result.ok = false;
        result.message = "Unknown command: " + name;
        break;
    }

    result.outText = result.message;
    return result;
  }

  /**
   * NAME
   *   buildUiStateJson - Build a small state payload for UI responses.
   */
  private JsonObject buildUiStateJson() {
    JsonObject state = new JsonObject();
    state.addProperty("enabled", DriverStation.isEnabled());
    state.addProperty("estopped", DriverStation.isEStopped());
    state.addProperty("mode", DriverStation.isAutonomous() ? "auto"
        : DriverStation.isTeleop() ? "teleop"
        : DriverStation.isTest() ? "test" : "disabled");
    return state;
  }

  /**
   * NAME
   *   publishUiTcpMonitor - Publish TCP protocol monitor entries to NT.
   */
  private void publishUiTcpMonitor(long seq, String name, String clientId, UiCommandResult result) {
    uiTcpTable.getEntry("enabled").setBoolean(uiProtocolMonitorEnabled);
    uiTcpTable.getEntry("connected").setBoolean(true);
    uiTcpTable.getEntry("lastSeq").setInteger(seq);
    uiTcpTable.getEntry("lastName").setString(name != null ? name : "");
    uiTcpTable.getEntry("lastStatus").setString(result.ok ? "ok" : "error");
    uiTcpTable.getEntry("lastMessage").setString(result.message != null ? result.message : "");
    uiTcpTable.getEntry("activeClientId").setString(clientId != null ? clientId : "");
  }

  /**
   * NAME
   *   publishUiAck - Publish UI command acknowledgements to NetworkTables.
   */
  private void publishUiAck(long seq, boolean ok, String message, String name, double cmdTs) {
    uiTable.getEntry("ack/seq").setInteger(seq);
    uiTable.getEntry("ack/status").setString(ok ? "ok" : "error");
    uiTable.getEntry("ack/message").setString(message != null ? message : "");
    uiTable.getEntry("ack/name").setString(name != null ? name : "");
    uiTable.getEntry("ack/ts").setDouble(cmdTs);
    publishUiState(seq);
  }

  /**
   * NAME
   *   publishUiOut - Publish UI command output to NetworkTables.
   *
   * DESCRIPTION
   *   Emits at least one output entry per command to release the UI.
   */
  private void publishUiOut(long seq, String name, String text, double cmdTs, String jsonText) {
    uiTable.getEntry("out/seq").setInteger(seq);
    uiTable.getEntry("out/name").setString(name != null ? name : "");
    uiTable.getEntry("out/text").setString(text != null ? text : "");
    uiTable.getEntry("out/ts").setDouble(cmdTs);
    uiTable.getEntry("out/json").setString(jsonText != null ? jsonText : "");
  }

  /**
   * NAME
   *   publishUiState - Publish UI command state/heartbeat.
   *
   * PARAMETERS
   *   seq - Most recent processed command sequence.
   */
  private void publishUiState(long seq) {
    lastUiAckMs = System.currentTimeMillis();
    uiTable.getEntry("state/lastAckSeq").setInteger(seq);
    uiTable.getEntry("state/lastAckMs").setDouble(lastUiAckMs);
    uiTable.getEntry("state/sessionId").setString(uiSessionId);
    uiTable.getEntry("state/protocolVersion").setInteger(UI_PROTOCOL_VERSION);
    uiTable.getEntry("state/activeClientId").setString(
        activeUiClientId != null ? activeUiClientId : "");
  }

  /**
   * NAME
   *   publishUiRobotState - Publish driver station state for UI feedback.
   */
  private void publishUiRobotState() {
    boolean enabled = DriverStation.isEnabled();
    boolean estopped = DriverStation.isEStopped();
    String mode = "disabled";
    if (DriverStation.isAutonomous()) {
      mode = "auto";
    } else if (DriverStation.isTeleop()) {
      mode = "teleop";
    } else if (DriverStation.isTest()) {
      mode = "test";
    }
    uiTable.getEntry("state/enabled").setBoolean(enabled);
    uiTable.getEntry("state/estopped").setBoolean(estopped);
    uiTable.getEntry("state/mode").setString(mode);
    uiTable.getEntry("state/lastAckMs").setDouble(System.currentTimeMillis());
  }

  /**
   * NAME
   *   parseUiArgName - Parse args JSON for a name field.
   */
  private String parseUiArgName(JsonObject args) {
    if (args == null || !args.has("name")) {
      return null;
    }
    return args.get("name").getAsString();
  }

  /**
   * NAME
   *   parseUiArgs - Parse args JSON for UI commands.
   */
  private JsonObject parseUiArgs(String argsJson) {
    if (argsJson == null || argsJson.isBlank()) {
      return null;
    }
    try {
      return GSON.fromJson(argsJson, JsonObject.class);
    } catch (JsonParseException ex) {
      return null;
    }
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
