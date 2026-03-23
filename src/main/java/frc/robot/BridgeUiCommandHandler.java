package frc.robot;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj.livewindow.LiveWindow;
import edu.wpi.first.wpilibj.shuffleboard.Shuffleboard;
import frc.robot.input.BindingsManager;
import frc.robot.tests.BringupTestRegistry;
import frc.robot.ui.TcpUiServer;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * NAME
 *   BridgeUiCommandHandler - UI/TCP command handler for bringup controls.
 *
 * DESCRIPTION
 *   Owns UI protocol state, command execution, and NetworkTables publishing
 *   for the bringup UI/CLI surfaces.
 */
public class BridgeUiCommandHandler {

  private static final long MIN_PRINT_INTERVAL_MS = 1000;
  private static final int UI_PROTOCOL_VERSION = 1;
  private static final long TCP_CMD_TIMEOUT_MS = 1000;
  private static final int UI_LOG_MAX_LINES = 200;
  private static final Gson GSON = new Gson();
  private static final double DEADBAND = BringupUtil.DEADBAND;

  private BringupCore core;
  private DiagnosticsReporter diagnostics;
  private final BindingsManager bindings;
  private final BridgeGroupManager bridgeGroups;
  private final BridgeGroupManager.SelectedState bridgeSelected;
  private final NetworkTable testsTable;
  private final NetworkTable uiTable;
  private final NetworkTable uiTcpTable;
  private final Runnable profileToggleAction;

  private boolean dashboardUpdatesEnabled = false;
  private long lastStartupPrintMs = 0L;
  private int lastTestsCount = 0;
  private long lastUiSeq = -1;
  private long lastUiAckMs = 0L;
  private String uiSessionId = UUID.randomUUID().toString();
  private String activeUiClientId = null;
  private long lastTcpSeq = -1;
  private final ConcurrentLinkedQueue<TcpPendingCommand> tcpCommandQueue = new ConcurrentLinkedQueue<>();
  private final ConcurrentLinkedQueue<String> uiLogQueue = new ConcurrentLinkedQueue<>();
  private final AtomicInteger uiLogCount = new AtomicInteger(0);
  private boolean uiProtocolMonitorEnabled = false;
  private double uiFixedSpeed = Double.NaN;
  private double lastNeoSpeed = 0.0;
  private double lastKrakenSpeed = 0.0;

  /**
   * NAME
   *   BridgeUiCommandHandler - Create a handler for UI commands.
   */
  public BridgeUiCommandHandler(
      BringupCore core,
      DiagnosticsReporter diagnostics,
      BindingsManager bindings,
      BridgeGroupManager bridgeGroups,
      BridgeGroupManager.SelectedState bridgeSelected,
      NetworkTable testsTable,
      NetworkTable uiTable,
      NetworkTable uiTcpTable,
      Runnable profileToggleAction) {
    this.core = core;
    this.diagnostics = diagnostics;
    this.bindings = bindings;
    this.bridgeGroups = bridgeGroups;
    this.bridgeSelected = bridgeSelected;
    this.testsTable = testsTable;
    this.uiTable = uiTable;
    this.uiTcpTable = uiTcpTable;
    this.profileToggleAction = profileToggleAction;
  }

  /**
   * NAME
   *   setCore - Update the active bringup core reference.
   */
  public void setCore(BringupCore core) {
    this.core = core;
  }

  /**
   * NAME
   *   setDiagnostics - Update diagnostics reporter reference.
   */
  public void setDiagnostics(DiagnosticsReporter diagnostics) {
    this.diagnostics = diagnostics;
  }

  /**
   * NAME
   *   getUiFixedSpeed - Return fixed-speed override value.
   */
  public double getUiFixedSpeed() {
    return uiFixedSpeed;
  }

  /**
   * NAME
   *   setLastSpeeds - Store last motor command values for UI reporting.
   */
  public void setLastSpeeds(double neoSpeed, double krakenSpeed) {
    this.lastNeoSpeed = neoSpeed;
    this.lastKrakenSpeed = krakenSpeed;
  }

  /**
   * NAME
   *   toggleDashboardUpdates - Toggle dashboard widget updates.
   */
  public void toggleDashboardUpdates() {
    dashboardUpdatesEnabled = !dashboardUpdatesEnabled;
    applyDashboardUpdateState();
    BringupPrinter.enqueue(
        "Dashboard/Shuffleboard updates: " + (dashboardUpdatesEnabled ? "ON" : "OFF"));
  }

  public void handleUiCommands() {
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
  public TcpUiServer.UiResponse handleTcpUiCommand(TcpUiServer.UiCommand command) {
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
  public void onTcpConnect(java.net.Socket socket) {
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
  public void onTcpDisconnect() {
    activeUiClientId = null;
    if (uiProtocolMonitorEnabled) {
      uiTcpTable.getEntry("connected").setBoolean(false);
    }
  }

  /**
   * NAME
   *   processTcpCommands - Drain queued TCP commands on the main loop.
   */
  public void processTcpCommands() {
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
    boolean allowWhenDisabled = isUiCommandAllowedWhenDisabled(name);
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
    } else if (!isHandshake && !isDisconnect && !allowWhenDisabled && !isEnabled) {
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
      case "uiPollLog":
        result.outText = drainUiLog();
        break;
      case "profileToggle":
        BringupUtil.toggleCanProfile();
        profileToggleAction.run();
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
        String stateReport = core.buildStateReportText();
        core.requestTextReport(stateReport, 4);
        result.outText = stateReport;
        break;
      case "printSummary":
        if (diagnostics != null) {
          String summary = diagnostics.buildQuickSummary();
          core.requestTextReport(summary, 4);
          result.outText = summary;
        } else {
          result.ok = false;
          result.message = "Diagnostics unavailable.";
        }
        break;
      case "printHealth":
        String healthReport = core.buildHealthReportText();
        core.requestTextReport(healthReport, 4);
        result.outText = healthReport;
        break;
      case "printCANcoder":
        String canCoderReport = core.buildCANCoderReportText();
        core.requestTextReport(canCoderReport, 4);
        result.outText = canCoderReport;
        break;
      case "printInputs":
        String inputsReport =
            "Inputs: leftY=" + String.format("%.2f", lastNeoSpeed) +
            " rightY=" + String.format("%.2f", lastKrakenSpeed) +
            " (NEO/FLEX=" + String.format("%.2f", lastNeoSpeed) +
            ", KRAKEN/FALCON=" + String.format("%.2f", lastKrakenSpeed) + ")";
        core.requestTextReport(inputsReport, 4);
        result.outText = inputsReport;
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
        String nextTestReport = core.buildNextTestReportText();
        core.requestTextReport(nextTestReport, 4);
        result.outText = nextTestReport;
        break;
      case "printBindings":
        result.outText = printBindings();
        break;
      case "printProfileDevices":
        result.outText = printProfileDevices();
        break;
      case "printTestsInfo":
        result.outText = printTestsInfo();
        break;
      case "printTestsOverview":
        result.outText = printTestsOverview();
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
        String sweepReport = core.buildCanPingSweepReportText();
        core.requestTextReport(sweepReport, 6);
        result.outText = sweepReport;
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
            result.outText = report;
          } else {
            String message = "Network diagnostics rate-limited; try again shortly.";
            core.requestTextReport(message, 4);
            result.outText = message;
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
            result.outText = report;
          } else {
            long remainingMs = diagnostics.getCanDiagCooldownRemainingMs();
            String message;
            if (remainingMs > 0) {
              double remainingSec = remainingMs / 1000.0;
              message = String.format("CAN diagnostics rate-limited, try again in %.1fs.", remainingSec);
            } else {
              message = "CAN diagnostics not ready yet.";
            }
            core.requestTextReport(message, 4);
            result.outText = message;
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
          StringBuilder dumpOut = new StringBuilder(wrapped);
          if (diagnostics.writeReportJsonToFile(json)) {
            core.requestTextReport("Wrote CAN report JSON to " + diagnostics.getReportPath(), 4);
            dumpOut.append('\n')
                .append("Wrote CAN report JSON to ")
                .append(diagnostics.getReportPath());
          } else {
            core.requestTextReport("Failed to write CAN report JSON.", 4);
            dumpOut.append('\n').append("Failed to write CAN report JSON.");
          }
          result.outText = dumpOut.toString();
        } else {
          result.ok = false;
          result.message = "Diagnostics unavailable.";
        }
        break;
      case "showStatus": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, "json"));
        applyShowResult(result, buildStatusText(), buildStatusJson(), wantsJson);
        break;
      }
      case "showGroups": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, "json"));
        applyShowResult(result, buildGroupsText(), buildGroupsJson(), wantsJson);
        break;
      }
      case "showGroup": {
        String groupName = parseUiArgString(args, "name");
        if (groupName == null) {
          result.ok = false;
          result.message = "showGroup requires args.name.";
          break;
        }
        BridgeGroupManager.Group group = bridgeGroups.getGroup(groupName);
        if (group == null) {
          result.ok = false;
          result.message = "Group not found: " + groupName;
          break;
        }
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, "json"));
        applyShowResult(result, buildGroupText(group), buildGroupJson(group), wantsJson);
        break;
      }
      case "showDevices": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, "json"));
        applyShowResult(result, buildDevicesText(), buildDevicesJson(), wantsJson);
        break;
      }
      case "showDevice": {
        String deviceName = parseUiArgString(args, "name");
        if (deviceName == null) {
          result.ok = false;
          result.message = "showDevice requires args.name.";
          break;
        }
        BringupUtil.DeviceEntry entry = findDeviceEntryByLabel(deviceName);
        if (entry == null) {
          result.ok = false;
          result.message = "Device not found: " + deviceName;
          break;
        }
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, "json"));
        applyShowResult(result, buildDeviceText(entry), buildDeviceJson(entry), wantsJson);
        break;
      }
      case "showBindings": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, "json"));
        applyShowResult(result, buildBindingsText(), buildBindingsJson(), wantsJson);
        break;
      }
      case "showSelectedDevice": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, "json"));
        applyShowResult(result, buildSelectedDeviceText(), buildSelectedDeviceJson(), wantsJson);
        break;
      }
      case "showRuntimeState": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, "json"));
        String text = buildStatusText() + "\n" + buildGroupsText();
        applyShowResult(result, text, buildRuntimeStateJson(), wantsJson);
        break;
      }
      case "groupCreate": {
        String groupName = parseUiArgString(args, "name");
        if (groupName == null) {
          result.ok = false;
          result.message = "groupCreate requires args.name.";
          break;
        }
        if (bridgeGroups.getGroup(groupName) != null) {
          result.ok = false;
          result.message = "Group already exists: " + groupName;
          break;
        }
        boolean created = bridgeGroups.createGroup(groupName);
        if (!created) {
          result.ok = false;
          result.message = "Failed to create group: " + groupName;
        } else {
          result.message = "Group created: " + groupName;
          result.outText = result.message;
        }
        break;
      }
      case "groupDelete": {
        String groupName = parseUiArgString(args, "name");
        Boolean confirm = parseUiArgBoolean(args, "confirm");
        if (groupName == null) {
          result.ok = false;
          result.message = "groupDelete requires args.name.";
          break;
        }
        if (!Boolean.TRUE.equals(confirm)) {
          result.ok = false;
          result.message = "groupDelete requires confirm=true.";
          break;
        }
        boolean removed = bridgeGroups.deleteGroup(groupName);
        if (!removed) {
          result.ok = false;
          result.message = "Group not found: " + groupName;
        } else {
          result.message = "Group deleted: " + groupName;
          result.outText = result.message;
        }
        break;
      }
      case "groupAddDevice": {
        String groupName = parseUiArgString(args, "group");
        String deviceName = parseUiArgString(args, "device");
        String policy = parseUiArgString(args, "conflictPolicy");
        Boolean forceMove = parseUiArgBoolean(args, "forceMove");
        if (groupName == null || deviceName == null) {
          result.ok = false;
          result.message = "groupAddDevice requires args.group and args.device.";
          break;
        }
        if (bridgeGroups.getGroup(groupName) == null) {
          result.ok = false;
          result.message = "Group not found: " + groupName;
          break;
        }
        if (findDeviceEntryByLabel(deviceName) == null) {
          result.ok = false;
          result.message = "Unknown device: " + deviceName;
          break;
        }
        String existing = bridgeGroups.getDeviceGroup(deviceName);
        boolean sameGroup = existing != null && existing.equalsIgnoreCase(groupName);
        boolean wantsMove = Boolean.TRUE.equals(forceMove)
            || (policy != null && policy.equalsIgnoreCase("move"));
        if (!sameGroup && existing != null && !existing.isBlank() && !wantsMove) {
          result.ok = false;
          result.message = "Device already in group " + existing + ".";
          JsonObject conflict = new JsonObject();
          conflict.addProperty("conflict", true);
          conflict.addProperty("device", deviceName);
          conflict.addProperty("currentGroup", existing);
          conflict.addProperty("requestedGroup", groupName);
          conflict.addProperty("policy", policy != null ? policy : "error");
          result.outJson = conflict.toString();
          break;
        }
        boolean added = bridgeGroups.addDevice(groupName, deviceName, wantsMove);
        if (!added) {
          result.ok = false;
          result.message = "Failed to add device to group.";
          break;
        }
        JsonObject info = new JsonObject();
        info.addProperty("device", deviceName);
        info.addProperty("group", groupName);
        if (!sameGroup && existing != null && !existing.isBlank()) {
          info.addProperty("moved", true);
          info.addProperty("previousGroup", existing);
        } else {
          info.addProperty("moved", false);
        }
        result.outJson = info.toString();
        result.message = "Device added: " + deviceName + " -> " + groupName;
        result.outText = result.message;
        break;
      }
      case "groupRemoveDevice": {
        String groupName = parseUiArgString(args, "group");
        String deviceName = parseUiArgString(args, "device");
        if (groupName == null || deviceName == null) {
          result.ok = false;
          result.message = "groupRemoveDevice requires args.group and args.device.";
          break;
        }
        BridgeGroupManager.Group group = bridgeGroups.getGroup(groupName);
        if (group == null) {
          result.ok = false;
          result.message = "Group not found: " + groupName;
          break;
        }
        String current = bridgeGroups.getDeviceGroup(deviceName);
        if (current == null || !current.equalsIgnoreCase(groupName)) {
          result.ok = false;
          result.message = "Device not in group: " + deviceName;
          break;
        }
        bridgeGroups.removeDevice(groupName, deviceName);
        result.message = "Device removed: " + deviceName + " from " + groupName;
        result.outText = result.message;
        break;
      }
      case "groupMemberEnable":
      case "groupMemberDisable":
      case "groupMemberToggle": {
        String groupName = parseUiArgString(args, "group");
        String deviceName = parseUiArgString(args, "device");
        if (groupName == null || deviceName == null) {
          result.ok = false;
          result.message = name + " requires args.group and args.device.";
          break;
        }
        BridgeGroupManager.Group group = bridgeGroups.getGroup(groupName);
        if (group == null) {
          result.ok = false;
          result.message = "Group not found: " + groupName;
          break;
        }
        String current = bridgeGroups.getDeviceGroup(deviceName);
        if (current == null || !current.equalsIgnoreCase(groupName)) {
          result.ok = false;
          result.message = "Device not in group: " + deviceName;
          break;
        }
        boolean ok;
        if ("groupMemberEnable".equals(name)) {
          ok = bridgeGroups.setMemberEnabled(groupName, deviceName, true);
        } else if ("groupMemberDisable".equals(name)) {
          ok = bridgeGroups.setMemberEnabled(groupName, deviceName, false);
        } else {
          ok = bridgeGroups.toggleMember(groupName, deviceName);
        }
        if (!ok) {
          result.ok = false;
          result.message = "Failed to update member: " + deviceName;
          break;
        }
        result.message = "Member updated: " + deviceName;
        result.outText = result.message;
        break;
      }
      case "groupBind": {
        String groupName = parseUiArgString(args, "group");
        String input = parseUiArgString(args, "input");
        String kindRaw = parseUiArgString(args, "kind");
        Double value = parseUiArgDouble(args, "value");
        if (groupName == null || input == null || kindRaw == null) {
          result.ok = false;
          result.message = "groupBind requires args.group, args.input, args.kind.";
          break;
        }
        BridgeGroupManager.Group group = bridgeGroups.getGroup(groupName);
        if (group == null) {
          result.ok = false;
          result.message = "Group not found: " + groupName;
          break;
        }
        if (!isValidBindingInput(input)) {
          result.ok = false;
          result.message = "Unknown input: " + input;
          break;
        }
        BridgeGroupManager.BindingKind kind = BridgeGroupManager.BindingKind.parse(kindRaw);
        if (kind == null) {
          result.ok = false;
          result.message = "Unknown binding kind: " + kindRaw;
          break;
        }
        if (kind != BridgeGroupManager.BindingKind.ANALOG && value == null) {
          result.ok = false;
          result.message = "Binding value required for " + kind.label() + ".";
          break;
        }
        double bindValue = value != null ? value : 0.0;
        boolean ok = bridgeGroups.addBinding(groupName, input, kind, bindValue);
        if (!ok) {
          result.ok = false;
          result.message = "Failed to add binding.";
          break;
        }
        result.message = "Binding added.";
        result.outText = result.message;
        break;
      }
      case "groupUnbind": {
        String groupName = parseUiArgString(args, "group");
        if (groupName == null) {
          result.ok = false;
          result.message = "groupUnbind requires args.group.";
          break;
        }
        boolean ok = bridgeGroups.clearBindings(groupName);
        if (!ok) {
          result.ok = false;
          result.message = "Group not found: " + groupName;
          break;
        }
        result.message = "Bindings cleared for " + groupName;
        result.outText = result.message;
        break;
      }
      case "groupEnable":
      case "groupDisable": {
        String groupName = parseUiArgString(args, "group");
        if (groupName == null) {
          result.ok = false;
          result.message = name + " requires args.group.";
          break;
        }
        boolean enabled = "groupEnable".equals(name);
        boolean ok = bridgeGroups.setGroupEnabled(groupName, enabled);
        if (!ok) {
          result.ok = false;
          result.message = "Group not found: " + groupName;
          break;
        }
        result.message = "Group " + groupName + " " + (enabled ? "enabled" : "disabled") + ".";
        result.outText = result.message;
        break;
      }
      case "groupRunTest": {
        String groupName = parseUiArgString(args, "group");
        if (groupName == null) {
          result.ok = false;
          result.message = "groupRunTest requires args.group.";
          break;
        }
        if (bridgeGroups.getGroup(groupName) == null) {
          result.ok = false;
          result.message = "Group not found: " + groupName;
          break;
        }
        String groupTestName = parseUiArgString(args, "name");
        if (groupTestName != null && !groupTestName.isBlank()) {
          boolean selected = core.selectBringupTestByName(groupTestName);
          if (!selected) {
            result.ok = false;
            result.message = "Test not found: " + groupTestName;
            break;
          }
        }
        core.runSelectedBringupTest();
        result.message = "Test started.";
        result.outText = result.message;
        break;
      }
      case "selectedDeviceSet": {
        String deviceName = parseUiArgString(args, "name");
        if (deviceName == null) {
          result.ok = false;
          result.message = "selectedDeviceSet requires args.name.";
          break;
        }
        if (findDeviceEntryByLabel(deviceName) == null) {
          result.ok = false;
          result.message = "Unknown device: " + deviceName;
          break;
        }
        bridgeSelected.device = deviceName;
        result.message = "Selected device: " + deviceName;
        result.outText = result.message;
        break;
      }
      case "selectedModeSet": {
        Boolean enabled = parseUiArgBoolean(args, "enabled");
        if (enabled == null) {
          result.ok = false;
          result.message = "selectedModeSet requires args.enabled.";
          break;
        }
        if (enabled && (bridgeSelected.device == null || bridgeSelected.device.isBlank())) {
          result.ok = false;
          result.message = "No selected device set.";
          break;
        }
        bridgeSelected.enabled = enabled;
        result.message = "Selected mode " + (enabled ? "on" : "off") + ".";
        result.outText = result.message;
        break;
      }
      default:
        result.ok = false;
        result.message = "Unknown command: " + name;
        break;
    }

    if (result.outText == null || result.outText.isBlank()) {
      if (!result.ok) {
        result.outText = result.message;
      } else {
        result.outText = "";
      }
    }
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
  public void publishUiRobotState() {
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
   *   parseUiArgString - Parse args JSON for a string field.
   *
   * PARAMETERS
   *   args - Parsed args object.
   *   key - Field name.
   *
   * RETURNS
   *   Trimmed string or null when missing/blank.
   */
  private String parseUiArgString(JsonObject args, String key) {
    if (args == null || key == null || !args.has(key)) {
      return null;
    }
    String value = args.get(key).getAsString();
    if (value == null || value.isBlank()) {
      return null;
    }
    return value.trim();
  }

  /**
   * NAME
   *   parseUiArgBoolean - Parse args JSON for a boolean field.
   *
   * PARAMETERS
   *   args - Parsed args object.
   *   key - Field name.
   *
   * RETURNS
   *   Boolean value or null when missing.
   */
  private Boolean parseUiArgBoolean(JsonObject args, String key) {
    if (args == null || key == null || !args.has(key)) {
      return null;
    }
    return args.get(key).getAsBoolean();
  }

  /**
   * NAME
   *   parseUiArgDouble - Parse args JSON for a numeric field.
   *
   * PARAMETERS
   *   args - Parsed args object.
   *   key - Field name.
   *
   * RETURNS
   *   Double value or null when missing/invalid.
   */
  private Double parseUiArgDouble(JsonObject args, String key) {
    if (args == null || key == null || !args.has(key)) {
      return null;
    }
    try {
      return args.get(key).getAsDouble();
    } catch (Exception ex) {
      return null;
    }
  }

  /**
   * NAME
   *   isUiCommandAllowedWhenDisabled - Check if command is allowed while disabled.
   */
  private boolean isUiCommandAllowedWhenDisabled(String name) {
    if (name == null || name.isBlank()) {
      return false;
    }
    switch (name) {
      case "printProfileDevices":
      case "printSummary":
      case "uiPollLog":
      case "showStatus":
      case "showGroups":
      case "showGroup":
      case "showDevices":
      case "showDevice":
      case "showBindings":
      case "showSelectedDevice":
      case "showRuntimeState":
      case "groupCreate":
      case "groupDelete":
      case "groupAddDevice":
      case "groupRemoveDevice":
      case "groupMemberEnable":
      case "groupMemberDisable":
      case "groupMemberToggle":
      case "groupBind":
      case "groupUnbind":
      case "groupEnable":
      case "groupDisable":
      case "selectedDeviceSet":
      case "selectedModeSet":
        return true;
      default:
        return false;
    }
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
   *   isValidBindingInput - Validate allowed binding inputs.
   */
  private boolean isValidBindingInput(String input) {
    if (input == null || input.isBlank()) {
      return false;
    }
    String key = input.trim().toLowerCase();
    switch (key) {
      case "driver.left.y":
      case "driver.right.y":
      case "driver.a":
      case "driver.b":
      case "driver.x":
      case "driver.y":
      case "driver.lb":
      case "driver.rb":
      case "operator.left.y":
      case "operator.right.y":
      case "operator.a":
      case "operator.b":
      case "operator.x":
      case "operator.y":
      case "operator.lb":
      case "operator.rb":
      case "ui.slider1":
      case "ui.slider2":
      case "ui.button1":
      case "ui.button2":
        return true;
      default:
        return false;
    }
  }

  /**
   * NAME
   *   applyShowResult - Populate OUT text/JSON for show commands.
   */
  private void applyShowResult(UiCommandResult result, String text, JsonObject json, boolean wantsJson) {
    if (result == null) {
      return;
    }
    if (wantsJson) {
      result.outText = "";
      result.outJson = json != null ? json.toString() : "";
      if (json == null) {
        result.ok = false;
        result.message = "No JSON available.";
        result.outText = result.message;
      }
    } else {
      result.outText = text != null ? text : "";
    }
  }

  /**
   * NAME
   *   buildStatusText - Build the show status text output.
   */
  private String buildStatusText() {
    StringBuilder sb = new StringBuilder(256);
    sb.append("Bridge status:\n");
    sb.append("  build=").append(BringupCore.getBuildMarker()).append('\n');
    sb.append("  profile=").append(BringupUtil.getActiveCanProfileLabel()).append('\n');
    sb.append("  enabled=").append(DriverStation.isEnabled()).append('\n');
    sb.append("  estopped=").append(DriverStation.isEStopped()).append('\n');
    sb.append("  mode=").append(DriverStation.isAutonomous() ? "auto"
        : DriverStation.isTeleop() ? "teleop"
        : DriverStation.isTest() ? "test" : "disabled").append('\n');
    sb.append("  groups=").append(bridgeGroups.getGroups().size()).append('\n');
    sb.append("  selectedDevice=").append(
        bridgeSelected.device != null ? bridgeSelected.device : "(none)")
        .append(" (")
        .append(bridgeSelected.enabled ? "on" : "off")
        .append(")\n");
    return sb.toString();
  }

  /**
   * NAME
   *   buildStatusJson - Build the show status JSON payload.
   */
  private JsonObject buildStatusJson() {
    JsonObject root = new JsonObject();
    root.addProperty("build", BringupCore.getBuildMarker());
    root.addProperty("profile", BringupUtil.getActiveCanProfileLabel());
    root.addProperty("enabled", DriverStation.isEnabled());
    root.addProperty("estopped", DriverStation.isEStopped());
    root.addProperty("mode", DriverStation.isAutonomous() ? "auto"
        : DriverStation.isTeleop() ? "teleop"
        : DriverStation.isTest() ? "test" : "disabled");
    root.addProperty("groupCount", bridgeGroups.getGroups().size());
    root.add("selectedDevice", buildSelectedDeviceJson());
    return root;
  }

  /**
   * NAME
   *   buildGroupsText - Build the show groups text output.
   */
  private String buildGroupsText() {
    List<BridgeGroupManager.Group> groups = bridgeGroups.getGroups();
    if (groups.isEmpty()) {
      return "Groups: (none)";
    }
    StringBuilder sb = new StringBuilder(256);
    sb.append("Groups:\n");
    for (BridgeGroupManager.Group group : groups) {
      sb.append("  ")
          .append(group.name)
          .append(" (")
          .append(group.enabled ? "enabled" : "disabled")
          .append(") members=")
          .append(group.members.size())
          .append(" bindings=")
          .append(group.bindings.size())
          .append('\n');
    }
    return sb.toString();
  }

  /**
   * NAME
   *   buildGroupsJson - Build the show groups JSON payload.
   */
  private JsonObject buildGroupsJson() {
    JsonObject root = new JsonObject();
    JsonArray array = new JsonArray();
    for (BridgeGroupManager.Group group : bridgeGroups.getGroups()) {
      JsonObject g = new JsonObject();
      g.addProperty("name", group.name);
      g.addProperty("enabled", group.enabled);
      g.addProperty("memberCount", group.members.size());
      g.addProperty("bindingCount", group.bindings.size());
      array.add(g);
    }
    root.add("groups", array);
    return root;
  }

  /**
   * NAME
   *   buildGroupText - Build detailed group text output.
   */
  private String buildGroupText(BridgeGroupManager.Group group) {
    if (group == null) {
      return "Group: (not found)";
    }
    StringBuilder sb = new StringBuilder(256);
    sb.append("Group ").append(group.name)
        .append(" (").append(group.enabled ? "enabled" : "disabled").append(")\n");
    sb.append("Members:\n");
    if (group.members.isEmpty()) {
      sb.append("  (none)\n");
    } else {
      for (BridgeGroupManager.MemberState member : group.members.values()) {
        sb.append("  ").append(member.device)
            .append(" [").append(member.enabled ? "enabled" : "disabled").append("]\n");
      }
    }
    sb.append("Bindings:\n");
    if (group.bindings.isEmpty()) {
      sb.append("  (none)\n");
    } else {
      for (BridgeGroupManager.Binding binding : group.bindings) {
        sb.append("  ").append(binding.input)
            .append(" ").append(binding.kind.label());
        if (binding.kind != BridgeGroupManager.BindingKind.ANALOG) {
          sb.append(" ").append(binding.value);
        }
        sb.append('\n');
      }
    }
    return sb.toString();
  }

  /**
   * NAME
   *   buildGroupJson - Build detailed group JSON payload.
   */
  private JsonObject buildGroupJson(BridgeGroupManager.Group group) {
    if (group == null) {
      return null;
    }
    JsonObject g = new JsonObject();
    g.addProperty("name", group.name);
    g.addProperty("enabled", group.enabled);
    JsonArray members = new JsonArray();
    for (BridgeGroupManager.MemberState member : group.members.values()) {
      JsonObject m = new JsonObject();
      m.addProperty("device", member.device);
      m.addProperty("enabled", member.enabled);
      members.add(m);
    }
    g.add("members", members);
    JsonArray bindings = new JsonArray();
    for (BridgeGroupManager.Binding binding : group.bindings) {
      JsonObject b = new JsonObject();
      b.addProperty("input", binding.input);
      b.addProperty("kind", binding.kind.label());
      if (binding.kind != BridgeGroupManager.BindingKind.ANALOG) {
        b.addProperty("value", binding.value);
      }
      bindings.add(b);
    }
    g.add("bindings", bindings);
    return g;
  }

  /**
   * NAME
   *   buildBindingsText - Build a summary of all bindings.
   */
  private String buildBindingsText() {
    List<BridgeGroupManager.Group> groups = bridgeGroups.getGroups();
    if (groups.isEmpty()) {
      return "Bindings: (no groups)";
    }
    StringBuilder sb = new StringBuilder(256);
    sb.append("Bindings:\n");
    for (BridgeGroupManager.Group group : groups) {
      sb.append("  ").append(group.name).append('\n');
      if (group.bindings.isEmpty()) {
        sb.append("    (none)\n");
        continue;
      }
      for (BridgeGroupManager.Binding binding : group.bindings) {
        sb.append("    ").append(binding.input)
            .append(" ").append(binding.kind.label());
        if (binding.kind != BridgeGroupManager.BindingKind.ANALOG) {
          sb.append(" ").append(binding.value);
        }
        sb.append('\n');
      }
    }
    return sb.toString();
  }

  /**
   * NAME
   *   buildBindingsJson - Build JSON for all bindings.
   */
  private JsonObject buildBindingsJson() {
    JsonObject root = new JsonObject();
    JsonArray groups = new JsonArray();
    for (BridgeGroupManager.Group group : bridgeGroups.getGroups()) {
      JsonObject g = new JsonObject();
      g.addProperty("name", group.name);
      JsonArray bindings = new JsonArray();
      for (BridgeGroupManager.Binding binding : group.bindings) {
        JsonObject b = new JsonObject();
        b.addProperty("input", binding.input);
        b.addProperty("kind", binding.kind.label());
        if (binding.kind != BridgeGroupManager.BindingKind.ANALOG) {
          b.addProperty("value", binding.value);
        }
        bindings.add(b);
      }
      g.add("bindings", bindings);
      groups.add(g);
    }
    root.add("groups", groups);
    return root;
  }

  /**
   * NAME
   *   buildDevicesText - Build text list of active profile devices.
   */
  private String buildDevicesText() {
    List<BringupUtil.DeviceEntry> devices = BringupUtil.getActiveDevicesSorted();
    if (devices.isEmpty()) {
      return "Devices: (none)";
    }
    StringBuilder sb = new StringBuilder(256);
    sb.append("Devices:\n");
    for (BringupUtil.DeviceEntry entry : devices) {
      if (entry == null) {
        continue;
      }
      sb.append("  ").append(entry.label)
          .append(" (").append(entry.vendor).append(" ")
          .append(entry.type).append(" id=").append(entry.id).append(")\n");
    }
    return sb.toString();
  }

  /**
   * NAME
   *   buildDevicesJson - Build JSON list of active devices.
   */
  private JsonObject buildDevicesJson() {
    JsonObject root = new JsonObject();
    JsonArray array = new JsonArray();
    for (BringupUtil.DeviceEntry entry : BringupUtil.getActiveDevicesSorted()) {
      if (entry == null) {
        continue;
      }
      JsonObject obj = new JsonObject();
      obj.addProperty("label", entry.label);
      obj.addProperty("vendor", entry.vendor);
      obj.addProperty("type", entry.type);
      obj.addProperty("id", entry.id);
      array.add(obj);
    }
    root.add("devices", array);
    return root;
  }

  /**
   * NAME
   *   buildDeviceText - Build text for a single device.
   */
  private String buildDeviceText(BringupUtil.DeviceEntry entry) {
    if (entry == null) {
      return "Device: (not found)";
    }
    return "Device " + entry.label + " (" + entry.vendor + " " + entry.type + " id=" + entry.id + ")";
  }

  /**
   * NAME
   *   buildDeviceJson - Build JSON for a single device.
   */
  private JsonObject buildDeviceJson(BringupUtil.DeviceEntry entry) {
    if (entry == null) {
      return null;
    }
    JsonObject obj = new JsonObject();
    obj.addProperty("label", entry.label);
    obj.addProperty("vendor", entry.vendor);
    obj.addProperty("type", entry.type);
    obj.addProperty("id", entry.id);
    return obj;
  }

  /**
   * NAME
   *   buildSelectedDeviceText - Build text for selected-device state.
   */
  private String buildSelectedDeviceText() {
    String device = bridgeSelected.device != null ? bridgeSelected.device : "(none)";
    return "Selected device: " + device + " (" + (bridgeSelected.enabled ? "on" : "off") + ")";
  }

  /**
   * NAME
   *   buildSelectedDeviceJson - Build JSON for selected-device state.
   */
  private JsonObject buildSelectedDeviceJson() {
    JsonObject obj = new JsonObject();
    obj.addProperty("device", bridgeSelected.device != null ? bridgeSelected.device : "");
    obj.addProperty("enabled", bridgeSelected.enabled);
    return obj;
  }

  /**
   * NAME
   *   buildRuntimeStateJson - Build runtime-state JSON blob.
   */
  private JsonObject buildRuntimeStateJson() {
    JsonObject root = new JsonObject();
    root.addProperty("schemaVersion", 1);
    root.addProperty("generatedAtMs", System.currentTimeMillis());
    root.addProperty("build", BringupCore.getBuildMarker());
    root.addProperty("profile", BringupUtil.getActiveCanProfileLabel());
    root.addProperty("enabled", DriverStation.isEnabled());
    root.addProperty("estopped", DriverStation.isEStopped());
    root.addProperty("mode", DriverStation.isAutonomous() ? "auto"
        : DriverStation.isTeleop() ? "teleop"
        : DriverStation.isTest() ? "test" : "disabled");
    JsonArray groups = new JsonArray();
    for (BridgeGroupManager.Group group : bridgeGroups.getGroups()) {
      JsonObject g = buildGroupJson(group);
      if (g != null) {
        groups.add(g);
      }
    }
    root.add("groups", groups);
    root.add("selectedDevice", buildSelectedDeviceJson());
    root.add("devices", buildDevicesJson().get("devices"));
    return root;
  }

  /**
   * NAME
   *   findDeviceEntryByLabel - Lookup a device entry by label.
   */
  private BringupUtil.DeviceEntry findDeviceEntryByLabel(String label) {
    if (label == null || label.isBlank()) {
      return null;
    }
    String needle = label.trim();
    for (BringupUtil.DeviceEntry entry : BringupUtil.getActiveDevicesSorted()) {
      if (entry == null) {
        continue;
      }
      if (needle.equalsIgnoreCase(entry.label)) {
        return entry;
      }
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

  public void printStartupInfo() {
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
   * RETURNS
   *   Full bindings report text.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  public String printBindings() {
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
    String report = sb.toString();
    core.requestTextReport(report, 4);
    return report;
  }

  /**
   * NAME
   *   printProfileInfo - Emit CAN profile details after a switch.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  public void printProfileInfo() {
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
   *   onBringupLine - Mirror queued console output into the UI log.
   *
   * PARAMETERS
   *   text - Console output chunk to store for UI polling.
   *
   * SIDE EFFECTS
   *   Appends to the UI log queue, trimming old entries.
   */
  public void onBringupLine(String text) {
    if (text == null || text.isBlank()) {
      return;
    }
    String[] lines = text.split("\\R");
    for (String line : lines) {
      if (line == null || line.isBlank()) {
        continue;
      }
      uiLogQueue.add(line);
      int count = uiLogCount.incrementAndGet();
      while (count > UI_LOG_MAX_LINES) {
        String dropped = uiLogQueue.poll();
        if (dropped == null) {
          count = uiLogCount.get();
          break;
        }
        count = uiLogCount.decrementAndGet();
      }
    }
  }

  /**
   * NAME
   *   drainUiLog - Drain buffered UI log lines into a single payload.
   *
   * RETURNS
   *   Newline-joined UI log text, or an empty string if none.
   */
  private String drainUiLog() {
    if (uiLogQueue.isEmpty()) {
      return "";
    }
    StringBuilder sb = new StringBuilder(256);
    String line;
    boolean first = true;
    while ((line = uiLogQueue.poll()) != null) {
      uiLogCount.decrementAndGet();
      if (!first) {
        sb.append('\n');
      }
      sb.append(line);
      first = false;
    }
    return sb.toString();
  }

  /**
   * NAME
   *   printProfileDevices - Emit active profile devices on demand.
   *
   * DESCRIPTION
   *   Prints the active CAN profile label and configured device list.
   *
   * RETURNS
   *   Full profile device report text.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  public String printProfileDevices() {
    StringBuilder sb = new StringBuilder(256);
    ReportTextUtil.appendLine(sb, "=== Active Profile Devices ===");
    ReportTextUtil.appendLine(sb, "Build: " + BringupCore.getBuildMarker());
    ReportTextUtil.appendLine(sb, "CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    appendDeviceSummary(sb);
    ReportTextUtil.appendLine(sb, "===============================");
    String report = sb.toString();
    core.requestTextReport(report, 4);
    return report;
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
   * RETURNS
   *   Full tests info report text.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  public String printTestsInfo() {
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
    String report = sb.toString();
    core.requestTextReport(report, 4);
    return report;
  }

  /**
   * NAME
   *   printTestsOverview - Emit and publish a tests overview snapshot.
   *
   * RETURNS
   *   Full tests overview report text.
   *
   * SIDE EFFECTS
   *   Enqueues a text report and updates NetworkTables.
   */
  public String printTestsOverview() {
    BringupCore.TestsOverview overview = core.buildTestsOverview();
    String text = core.formatTestsOverview(overview);
    core.requestTextReport(text, 6);
    publishTestsOverview(overview);
    return text;
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
  public void publishTestsOverview(BringupCore.TestsOverview overview) {
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
  public void publishTestsSelectionStatus() {
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
  public void applyDashboardUpdateState() {
    // WPILib deprecated setNetworkTablesFlushEnabled; no-op in newer versions.
    LiveWindow.setEnabled(dashboardUpdatesEnabled);
    if (dashboardUpdatesEnabled) {
      Shuffleboard.enableActuatorWidgets();
    } else {
      Shuffleboard.disableActuatorWidgets();
    }
  }

}
