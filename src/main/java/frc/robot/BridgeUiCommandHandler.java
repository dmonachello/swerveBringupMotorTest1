package frc.robot;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj.Filesystem;
import edu.wpi.first.wpilibj.livewindow.LiveWindow;
import edu.wpi.first.wpilibj.shuffleboard.Shuffleboard;
import frc.robot.input.BindingsManager;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.BringupHealthFormat;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.ctre.diag.PdpStatusAttachment;
import frc.robot.manufacturers.rev.diag.PdhStatusAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
import frc.robot.tests.BringupTestRegistry;
import frc.robot.ui.TcpUiServer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.DateTimeException;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
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
  private static final long TCP_LEASE_TIMEOUT_MS = 750;
  private static final long TCP_TIMEOUT_STOP_COOLDOWN_MS = 5000;
  private static final long TCP_KEEPALIVE_INTERVAL_MS = 1000;
  private static final long TCP_KEEPALIVE_MISSES = 5;
  private static final int UI_LOG_MAX_LINES = 200;
  private static final int VERSION_TEXT_BUILDER_SIZE = 128;
  private static final String JSON_KEY_LABEL = "label";
  private static final String JSON_KEY_VENDOR = "vendor";
  private static final String JSON_KEY_TYPE = "type";
  private static final String JSON_KEY_ID = "id";
  private static final String JSON_KEY_DEVICE = "device";
  private static final String JSON_KEY_ENABLED = "enabled";
  private static final String JSON_KEY_PRESENCE_CONF = "presenceConfidence";
  private static final String JSON_KEY_LAST_SEEN_MS = "lastSeenMs";
  private static final String JSON_KEY_MOTOR_CURRENT_A = "motorCurrentA";
  private static final String JSON_KEY_CMD_DUTY = "cmdDuty";
  private static final String JSON_KEY_APPLIED_DUTY = "appliedDuty";
  private static final String JSON_KEY_APPLIED_V = "appliedV";
  private static final String JSON_KEY_TEMP_C = "tempC";
  private static final String JSON_KEY_VEL_RPM = "velRpm";
  private static final String JSON_KEY_BUS_V = "busV";
  private static final String JSON_KEY_TOTAL_CURRENT_A = "totalCurrentA";
  private static final String JSON_KEY_SWITCHABLE_ENABLED = "switchableEnabled";
  private static final String JSON_KEY_BROWNOUT = "brownout";
  private static final String JSON_KEY_CAN_WARNING = "canWarning";
  private static final String JSON_KEY_HARDWARE_FAULT = "hardwareFault";
  private static final String JSON_KEY_STICKY_BROWNOUT = "stickyBrownout";
  private static final String JSON_KEY_STICKY_CAN_WARNING = "stickyCanWarning";
  private static final String JSON_KEY_STICKY_CAN_BUS_OFF = "stickyCanBusOff";
  private static final String JSON_KEY_STICKY_HAS_RESET = "stickyHasReset";
  private static final String JSON_KEY_CHANNEL_CURRENT_A = "channelCurrentA";
  private static final String JSON_KEY_CHANNEL_FAULT = "channelFault";
  private static final String JSON_KEY_CHANNEL_STICKY_FAULT = "channelStickyFault";
  private static final String JSON_KEY_JSON = "json";
  private static final String JSON_KEY_VERSION = "version";
  private static final String JSON_KEY_BUILD = "build";
  private static final String JSON_KEY_BUILD_FIELDS = "fields";
  private static final String JSON_KEY_BUILD_LABEL = "label";
  private static final String JSON_KEY_BUILD_VALUE = "value";
  private static final String CMD_SHOW_VERSION = "showVersion";
  private static final String CMD_SHOW_TESTS = "showTests";
  private static final String CMD_SHOW_SOURCES = "showSources";
  private static final String CMD_PROFILE_ACTIVATE = "profileActivate";
  private static final int INDEX_START = 0;
  private static final String JSON_KEY_OK = "ok";
  private static final String JSON_KEY_MESSAGE = "message";
  private static final String JSON_KEY_TRANSFER_CHECK = "transferCheck";
  private static final String JSON_KEY_CONTENT_VALIDATION = "contentValidation";
  private static final String JSON_KEY_APPLY = "apply";
  private static final String JSON_KEY_POST_APPLY = "postApplyCheck";
  private static final String JSON_KEY_OVERALL_OK = "overallOk";
  private static final String JSON_KEY_ACTIVE_PROFILE = "activeProfile";
  private static final String JSON_KEY_ACTIVATED = "activated";
  private static final String JSON_KEY_EXPECTED_HASH = "expectedHash";
  private static final String JSON_KEY_COMPUTED_HASH = "computedHash";
  private static final String JSON_KEY_EXPECTED_BYTES = "expectedBytes";
  private static final String JSON_KEY_COMPUTED_BYTES = "computedBytes";
  private static final String ARG_REGISTRY_JSON = "registryJson";
  private static final String ARG_REGISTRY_HASH = "registryHash";
  private static final String ARG_REGISTRY_BYTES = "registryBytes";
  private static final String ARG_ACTIVATE_PROFILE = "activateProfile";
  private static final String JSON_KEY_TESTS_ACTIVE_SET = "activeSet";
  private static final String JSON_KEY_TESTS_DEFAULT_SET = "defaultSet";
  private static final String JSON_KEY_TESTS_USING_SETS = "usingTestSets";
  private static final String JSON_KEY_TESTS_TOTAL_COUNT = "totalCount";
  private static final String JSON_KEY_TESTS_ENABLED_COUNT = "enabledCount";
  private static final String JSON_KEY_TESTS_ROWS = "rows";
  private static final String JSON_KEY_TESTS_INDEX = "index";
  private static final String JSON_KEY_TESTS_NAME = "name";
  private static final String JSON_KEY_TESTS_ENABLED = "enabled";
  private static final String JSON_KEY_TESTS_SELECTED = "selected";
  private static final String JSON_KEY_TESTS_TYPE = "type";
  private static final String JSON_KEY_TESTS_STATUS = "status";
  private static final String JSON_KEY_TESTS_MOTORS = "motors";
  private static final String JSON_KEY_SOURCES = "sources";
  private static final String JSON_KEY_SOURCES_NAME = "name";
  private static final String JSON_KEY_SOURCES_PATH = "path";
  private static final String JSON_KEY_SOURCES_EXISTS = "exists";
  private static final String CMD_PROFILES_APPLY = "profilesApply";
  private static final String TEXT_SELECTED_DEVICE_PREFIX = "Selected device: ";
  private static final String TEXT_PAREN_OPEN = " (";
  private static final String TEXT_PAREN_CLOSE = ")";
  private static final String TEXT_NONE = "(none)";
  private static final String TEXT_ON = "on";
  private static final String TEXT_OFF = "off";
  private static final String TEXT_DEVICE_PREFIX = "Device ";
  private static final String TEXT_VENDOR_SEP = " ";
  private static final String TEXT_TYPE_SEP = " ";
  private static final String TEXT_ID_PREFIX = " id=";
  private static final String TEXT_LABEL_PREFIX = "label=";
  private static final String TEXT_VENDOR_PREFIX = " vendor=";
  private static final String TEXT_TYPE_PREFIX = " type=";
  private static final String TEXT_DEVICE_NOT_FOUND = "Device: (not found)";
  private static final String TEXT_DEVICES_NONE = "Devices: (none)";
  private static final String TEXT_DEVICES_HEADER = "Devices:\n";
  private static final String TEXT_DEVICE_LIST_PREFIX = "  ";
  private static final String TEXT_EMPTY = "";
  private static final String TEXT_BUILD_HEADER = "Build:";
  private static final String TEXT_TESTS_INFO_PROFILE = "Profile: ";
  private static final String TEXT_TESTS_INFO_SOURCE = "Source: ";
  private static final String TEXT_SOURCES_HEADER = "=== Sources ===";
  private static final String TEXT_SOURCES_FOOTER = "===============";
  private static final String TEXT_SOURCES_ENTRY = "  %s: %s (exists=%s)";
  private static final String TEXT_REMOTE_CMD_DETAIL_FMT = "Remote command: %s (seq=%d, client=%s)";
  private static final String TEXT_REMOTE_CMD_TIME_FMT = "[%s] ";
  private static final String TEXT_TIME_PATTERN = "yyyy-MM-dd HH:mm:ss.SSS";
  private static final DateTimeFormatter TEXT_TIME_FORMATTER =
      DateTimeFormatter.ofPattern(TEXT_TIME_PATTERN);
  private static final ZoneId TEXT_TIME_ZONE = ZoneId.systemDefault();
  private static final String ARG_TIMEZONE_ID = "timezoneId";
  private static final String ARG_TIMEZONE_OFFSET_MIN = "timezoneOffsetMin";
  private static final int SECONDS_PER_MINUTE = 60;
  private static final String ARG_PROFILE_NAME = "name";
  private static final String TEXT_PROFILE_ACTIVATE_OK = "Profile activated: %s";
  private static final String TEXT_PROFILE_ACTIVATE_FAIL = "Profile activation failed.";
  private static final String TEXT_PROFILES_APPLY_OK = "Profiles applied.";
  private static final String TEXT_PROFILES_APPLY_FAILED = "Profiles apply failed.";
  private static final String TEXT_PROFILES_APPLY_NOT_SUPPORTED = "profilesApply only supported over TCP.";
  private static final String TEXT_PROFILES_APPLY_MISSING_REGISTRY = "profilesApply requires registryJson.";
  private static final String TEXT_PROFILES_APPLY_MISSING_HASH = "profilesApply requires registryHash.";
  private static final String TEXT_PROFILES_APPLY_MISSING_BYTES = "profilesApply requires registryBytes.";
  private static final String TEXT_PROFILES_APPLY_HASH_MISMATCH = "registryHash mismatch.";
  private static final String TEXT_PROFILES_APPLY_HASH_UNAVAILABLE = "registryHash unavailable.";
  private static final String TEXT_PROFILES_APPLY_BYTES_MISMATCH = "registryBytes mismatch.";
  private static final String TEXT_PROFILES_APPLY_HASH_DETAIL =
      " expectedHash=%s computedHash=%s expectedBytes=%d computedBytes=%d";
  private static final String TEXT_PROFILES_APPLY_DEVICES = " devices=";
  private static final String TEXT_PROFILES_APPLY_PROFILES = " profiles=";
  private static final String TEXT_PROFILES_APPLY_ACTIVE = " active=";
  private static final String JSON_KEY_DEVICES = "devices";
  private static final Gson GSON = new Gson();
  private static final double DEADBAND = BringupUtil.DEADBAND;
  private static final String FILE_BINDINGS = "bringup_bindings.json";
  private static final String FILE_CAN_MAPPINGS = "can_mappings.json";
  private static final String SOURCE_NAME_PROFILES = "profiles";
  private static final String SOURCE_NAME_BINDINGS = "bindings";
  private static final String SOURCE_NAME_CAN_MAPPINGS = "canMappings";
  private static final String SOURCE_NAME_TESTS = "tests";
  private static final String DEV_PATH_SRC = "src";
  private static final String DEV_PATH_MAIN = "main";
  private static final String DEV_PATH_DEPLOY = "deploy";

  private BringupCore core;
  private DiagnosticsReporter diagnostics;
  private final BindingsManager bindings;
  private final BridgeGroupManager bridgeGroups;
  private final BridgeGroupManager.SelectedState bridgeSelected;
  private final NetworkTable testsTable;
  private final NetworkTable uiTable;
  private final NetworkTable uiTcpTable;
  private final Runnable profileToggleAction;
  private final Runnable profileActivateAction;

  private boolean dashboardUpdatesEnabled = false;
  private long lastStartupPrintMs = 0L;
  private int lastTestsCount = 0;
  private long lastUiSeq = -1;
  private long lastUiAckMs = 0L;
  private String uiSessionId = UUID.randomUUID().toString();
  private String activeUiClientId = null;
  private long lastTcpSeq = -1;
  private long lastTcpCommandMs = 0L;
  private boolean tcpConnected = false;
  private long lastTcpKeepaliveMs = 0L;
  private java.net.Socket tcpSocket;
  private long lastTcpTimeoutStopMs = 0L;
  private boolean stopLatchActive = false;
  private String stopLatchReason = "";
  private boolean lastXboxConnected = false;
  private final Map<String, Long> lastTcpSeqByClient = new HashMap<>();
  private final Map<String, LastTcpResponse> lastTcpResponseByClient = new HashMap<>();
  private long tcpCommandsProcessed = 0L;
  private long tcpCommandTimeouts = 0L;
  private long tcpDuplicateAcked = 0L;
  private long tcpDuplicateDropped = 0L;
  private final ConcurrentLinkedQueue<TcpPendingCommand> tcpCommandQueue = new ConcurrentLinkedQueue<>();
  private final ConcurrentLinkedQueue<String> uiLogQueue = new ConcurrentLinkedQueue<>();
  private final AtomicInteger uiLogCount = new AtomicInteger(0);
  private boolean uiProtocolMonitorEnabled = false;
  private double uiFixedSpeed = Double.NaN;
  private double lastNeoSpeed = 0.0;
  private double lastKrakenSpeed = 0.0;
  private ZoneId remoteCommandZone = null;

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
      Runnable profileToggleAction,
      Runnable profileActivateAction) {
    this.core = core;
    this.diagnostics = diagnostics;
    this.bindings = bindings;
    this.bridgeGroups = bridgeGroups;
    this.bridgeSelected = bridgeSelected;
    this.testsTable = testsTable;
    this.uiTable = uiTable;
    this.uiTcpTable = uiTcpTable;
    this.profileToggleAction = profileToggleAction;
    this.profileActivateAction = profileActivateAction;
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
    UiCommandResult result = processUiCommand(name, argsJson, cmdTs, clientId, false);
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
      tcpCommandTimeouts++;
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
    tcpConnected = true;
    tcpSocket = socket;
    lastTcpKeepaliveMs = System.currentTimeMillis();
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
    tcpConnected = false;
    tcpSocket = null;
    lastTcpKeepaliveMs = 0L;
    setStopLatch("tcpDisconnect");
    applySafetyStop("tcpDisconnect");
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
      String cmdName = command.name != null ? command.name : "";
      String cmdClient = command.clientId != null ? command.clientId : "";
      if (!cmdClient.isBlank()) {
        Long lastSeq = lastTcpSeqByClient.get(cmdClient);
        if (lastSeq != null && command.seq <= lastSeq) {
          LastTcpResponse lastResponse = lastTcpResponseByClient.get(cmdClient);
          if (lastResponse != null && lastResponse.seq == command.seq) {
            tcpDuplicateAcked++;
            pending.future.complete(lastResponse.response);
          } else {
            tcpDuplicateDropped++;
          }
          continue;
        }
        lastTcpSeqByClient.put(cmdClient, command.seq);
      }
      if (!"uiPing".equals(cmdName) && !"uiPollLog".equals(cmdName)) {
        String cmdInfo = formatRemoteCommandTimestamp()
            + String.format(TEXT_REMOTE_CMD_DETAIL_FMT, cmdName, command.seq, cmdClient);
        BringupPrinter.enqueue(cmdInfo);
      }
      lastTcpSeq = command.seq;
      lastTcpCommandMs = System.currentTimeMillis();
      lastTcpKeepaliveMs = lastTcpCommandMs;
      UiCommandResult result = processUiCommand(
          cmdName,
          command.argsJson,
          command.ts,
          cmdClient,
          true);
      TcpUiServer.UiResponse response = buildTcpResponse(command, result);
      if (!cmdClient.isBlank()) {
        lastTcpResponseByClient.put(cmdClient, new LastTcpResponse(command.seq, response));
      }
      tcpCommandsProcessed++;
      pending.future.complete(response);
    }
  }

  /**
   * NAME
   *   LastTcpResponse - Cache of last response per TCP client.
   */
  private static final class LastTcpResponse {
    private final long seq;
    private final TcpUiServer.UiResponse response;

    private LastTcpResponse(long seq, TcpUiServer.UiResponse response) {
      this.seq = seq;
      this.response = response;
    }
  }

  /**
   * NAME
   *   formatRemoteCommandTimestamp - Build the timestamp prefix for remote command logs.
   *
   * RETURNS
   *   Prefix including brackets and trailing space for log lines.
   */
  private String formatRemoteCommandTimestamp() {
    ZoneId zone = remoteCommandZone != null ? remoteCommandZone : TEXT_TIME_ZONE;
    String timestamp = LocalDateTime.ofInstant(
        Instant.ofEpochMilli(System.currentTimeMillis()),
        zone).format(TEXT_TIME_FORMATTER);
    return String.format(TEXT_REMOTE_CMD_TIME_FMT, timestamp);
  }

  /**
   * NAME
   *   resolveRemoteCommandZone - Resolve a ZoneId from uiHandshake args.
   *
   * PARAMETERS
   *   args - Parsed uiHandshake args JSON.
   *
   * RETURNS
   *   ZoneId when provided, otherwise null.
   */
  private ZoneId resolveRemoteCommandZone(JsonObject args) {
    if (args == null) {
      return null;
    }
    String zoneId = parseUiArgString(args, ARG_TIMEZONE_ID);
    if (zoneId != null && !zoneId.isBlank()) {
      try {
        return ZoneId.of(zoneId);
      } catch (DateTimeException ex) {
        // Fall through to offset parsing.
      }
    }
    Long offsetMin = parseUiArgLong(args, ARG_TIMEZONE_OFFSET_MIN);
    if (offsetMin != null) {
      try {
        long seconds = offsetMin * SECONDS_PER_MINUTE;
        return ZoneOffset.ofTotalSeconds(Math.toIntExact(seconds));
      } catch (DateTimeException | ArithmeticException ex) {
        return null;
      }
    }
    return null;
  }

  /**
   * NAME
   *   updateSafety - Update safety latch and timeouts from robot loop.
   *
   * PARAMETERS
   *   xboxConnected - Whether the controller0 Xbox controller is connected.
   *
   * SIDE EFFECTS
   *   May latch safety state and stop outputs on disconnect or timeout events.
   */
  public void updateSafety(boolean xboxConnected) {
    boolean connected = xboxConnected;
    if (lastXboxConnected && !connected) {
      setStopLatch("xboxDisconnected");
      applySafetyStop("xboxDisconnected");
    }
    lastXboxConnected = connected;
    checkTcpKeepalive();
    checkTcpTimeout();
  }

  /**
   * NAME
   *   setStopLatchFromXbox - Latch safety stop from the Xbox client.
   */
  public void setStopLatchFromXbox(String reason) {
    setStopLatch(reason);
    applySafetyStop(reason);
  }

  /**
   * NAME
   *   clearStopLatchFromXbox - Clear the stop latch from the Xbox client.
   *
   * RETURNS
   *   True if the latch was cleared.
   */
  public boolean clearStopLatchFromXbox(String reason) {
    if (!stopLatchActive) {
      return false;
    }
    stopLatchActive = false;
    stopLatchReason = "";
    String label = reason != null && !reason.isBlank() ? reason : "xboxClear";
    BringupPrinter.enqueue("Safety: stop latch cleared (" + label + ").");
    return true;
  }

  /**
   * NAME
   *   clearStopLatchFromUi - Clear the stop latch from the UI client.
   *
   * RETURNS
   *   True if the latch was cleared.
   */
  public boolean clearStopLatchFromUi(String reason) {
    if (!stopLatchActive) {
      return false;
    }
    stopLatchActive = false;
    stopLatchReason = "";
    String label = reason != null && !reason.isBlank() ? reason : "uiClear";
    BringupPrinter.enqueue("Safety: stop latch cleared (" + label + ").");
    return true;
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
  private UiCommandResult processUiCommand(
      String name,
      String argsJson,
      double cmdTs,
      String clientId,
      boolean isTcp) {
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
    boolean isPing = "uiPing".equals(name);
    boolean isSelectProfile = "selectProfile".equals(name);
    boolean allowWhenDisabled = isUiCommandAllowedWhenDisabled(name);
    boolean isEnabled = DriverStation.isEnabled();
    boolean isEStopped = DriverStation.isEStopped();

    if (!hasClient) {
      result.ok = false;
      result.message = "Missing clientId.";
    } else if (locked && !activeUiClientId.equals(client)) {
      result.ok = false;
      result.message = "UI locked by another client. Disconnect or reboot to switch.";
    } else if (!locked && !isHandshake && !isDisconnect && !isPing) {
      result.ok = false;
      result.message = "UI handshake required before commands.";
    } else if (isTcp && isTcpStartCommand(name, args) && stopLatchActive) {
      result.ok = false;
      result.message = "Stop latch active"
          + (stopLatchReason.isBlank() ? "." : " (" + stopLatchReason + ").")
          + " Clear from Xbox or UI to resume.";
    } else if (!isHandshake && !isDisconnect && !allowWhenDisabled && !isEnabled) {
      result.ok = false;
      result.message = isEStopped ? "Robot disabled (E-Stop)." : "Robot disabled.";
    }

    if (!result.ok) {
      result.outText = result.message;
      return result;
    }

    if (isTcp && isTcpStopCommand(name, args)) {
      setStopLatch("tcpStop");
      applySafetyStop("tcpStop");
    }

    switch (name) {
      case "uiPing":
        result.message = "OK";
        result.outText = "";
        break;
      case "selectProfile": {
        String profileName = parseUiArgString(args, ARG_PROFILE_NAME);
        if (profileName == null || profileName.isBlank()) {
          result.ok = false;
          result.message = "selectProfile requires args.name.";
          break;
        }
        BringupUtil.selectCanProfile(profileName.trim());
        result.message = "Selected profile: " + BringupUtil.getActiveCanProfileLabel();
        result.outText = result.message;
        break;
      }
      case CMD_PROFILE_ACTIVATE: {
        String profileName = parseUiArgString(args, ARG_PROFILE_NAME);
        if (profileName != null && !profileName.isBlank()) {
          BringupUtil.selectCanProfile(profileName.trim());
        }
        BringupUtil.prepareActivationForSelectedProfile();
        BringupUtil.activateSelectedProfile();
        if (BringupUtil.isProfileActive() && profileActivateAction != null) {
          profileActivateAction.run();
        }
        if (BringupUtil.isProfileActive()) {
          result.message = String.format(
              TEXT_PROFILE_ACTIVATE_OK,
              BringupUtil.getActiveCanProfileLabel());
          result.outText = result.message;
        } else {
          result.ok = false;
          result.message = TEXT_PROFILE_ACTIVATE_FAIL;
          result.outText = result.message;
        }
        break;
      }
      case "uiHandshake":
        if (!locked) {
          activeUiClientId = client;
        }
        boolean reset = args != null && args.has("reset") && args.get("reset").getAsBoolean();
        ZoneId tzOverride = resolveRemoteCommandZone(args);
        if (tzOverride != null) {
          remoteCommandZone = tzOverride;
        }
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
        BringupUtil.selectNextProfile();
        if (profileToggleAction != null) {
          profileToggleAction.run();
        }
        result.message = "Profile selected.";
        break;
      case "addMotor":
        if (!BringupUtil.isProfileActive()) {
          BringupUtil.prepareActivationForSelectedProfile();
          BringupUtil.activateSelectedProfile();
          if (BringupUtil.isProfileActive() && profileActivateAction != null) {
            profileActivateAction.run();
          }
        }
        core.addNextMotorCommand();
        result.message = "Add motor.";
        break;
      case "addAll":
        if (!BringupUtil.isProfileActive()) {
          BringupUtil.prepareActivationForSelectedProfile();
          BringupUtil.activateSelectedProfile();
          if (BringupUtil.isProfileActive() && profileActivateAction != null) {
            profileActivateAction.run();
          }
        }
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
      case "selectTestPrev":
        core.selectPrevBringupTest();
        result.outText = "Selected test: " + core.getSelectedBringupTestName();
        break;
      case "selectTestNext":
        core.selectNextBringupTest();
        result.outText = "Selected test: " + core.getSelectedBringupTestName();
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
      case "clearStopLatch":
        if (clearStopLatchFromUi("uiClear")) {
          result.message = "Stop latch cleared.";
        } else {
          result.message = "Stop latch not active.";
        }
        result.outText = result.message;
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
            report = appendUiTcpStats(report);
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
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
        applyShowResult(result, buildStatusText(), buildStatusJson(), wantsJson);
        break;
      }
      case CMD_SHOW_VERSION: {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
        applyShowResult(result, buildVersionText(), buildVersionJson(), wantsJson);
        break;
      }
      case CMD_SHOW_TESTS: {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
        BringupCore.TestsOverview overview = core.buildTestsOverview();
        applyShowResult(result, core.formatTestsOverview(overview), buildTestsOverviewJson(overview), wantsJson);
        break;
      }
      case CMD_SHOW_SOURCES: {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
        applyShowResult(result, buildSourcesText(), buildSourcesJson(), wantsJson);
        break;
      }
      case "showGroups": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
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
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
        applyShowResult(result, buildGroupText(group), buildGroupJson(group), wantsJson);
        break;
      }
      case "showDevices": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
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
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
        applyShowResult(result, buildDeviceText(entry), buildDeviceJson(entry), wantsJson);
        break;
      }
      case "showBindings": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
        applyShowResult(result, buildBindingsText(), buildBindingsJson(), wantsJson);
        break;
      }
      case "showSelectedDevice": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
        applyShowResult(result, buildSelectedDeviceText(), buildSelectedDeviceJson(), wantsJson);
        break;
      }
      case "showRuntimeState": {
        boolean wantsJson = Boolean.TRUE.equals(parseUiArgBoolean(args, JSON_KEY_JSON));
        String text = buildStatusText() + "\n" + buildGroupsText();
        applyShowResult(result, text, buildRuntimeStateJson(), wantsJson);
        break;
      }
      case CMD_PROFILES_APPLY: {
        applyProfilesApplyCommand(result, args, isTcp);
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
   *   checkTcpTimeout - Apply safety stop when TCP commands stall.
   */
  private void checkTcpTimeout() {
    if (!tcpConnected || activeUiClientId == null || activeUiClientId.isBlank()) {
      return;
    }
    if (lastTcpKeepaliveMs > 0) {
      return;
    }
    if (lastTcpCommandMs <= 0) {
      return;
    }
    long now = System.currentTimeMillis();
    if ((now - lastTcpCommandMs) <= TCP_LEASE_TIMEOUT_MS) {
      return;
    }
    setStopLatch("tcpTimeout");
    if ((now - lastTcpTimeoutStopMs) >= TCP_TIMEOUT_STOP_COOLDOWN_MS) {
      lastTcpTimeoutStopMs = now;
      applySafetyStop("tcpTimeout");
    }
  }

  /**
   * NAME
   *   checkTcpKeepalive - Enforce keepalive liveness for TCP clients.
   */
  private void checkTcpKeepalive() {
    if (!tcpConnected) {
      return;
    }
    if (lastTcpKeepaliveMs <= 0) {
      return;
    }
    long now = System.currentTimeMillis();
    long timeoutMs = TCP_KEEPALIVE_INTERVAL_MS * TCP_KEEPALIVE_MISSES;
    if ((now - lastTcpKeepaliveMs) <= timeoutMs) {
      return;
    }
    forceTcpDisconnect("tcpKeepaliveTimeout");
  }

  private void forceTcpDisconnect(String reason) {
    if (tcpSocket != null) {
      try {
        tcpSocket.close();
      } catch (Exception ignored) {
      }
    }
    tcpSocket = null;
    tcpConnected = false;
    activeUiClientId = null;
    lastTcpKeepaliveMs = 0L;
    setStopLatch(reason);
    applySafetyStop(reason);
    if (uiProtocolMonitorEnabled) {
      uiTcpTable.getEntry("connected").setBoolean(false);
    }
  }

  /**
   * NAME
   *   setStopLatch - Enable the safety stop latch.
   */
  private void setStopLatch(String reason) {
    if (stopLatchActive) {
      return;
    }
    stopLatchActive = true;
    stopLatchReason = reason != null ? reason : "";
    String label = stopLatchReason.isBlank() ? "stopLatch" : stopLatchReason;
    BringupPrinter.enqueue("Safety: stop latch set (" + label + ").");
  }

  /**
   * NAME
   *   applySafetyStop - Stop outputs on safety events.
   */
  private void applySafetyStop(String reason) {
    if (core == null) {
      return;
    }
    if (!DriverStation.isEnabled() || DriverStation.isEStopped()) {
      return;
    }
    core.safetyStop(reason);
  }

  /**
   * NAME
   *   isTcpStartCommand - Check if a TCP command starts or enables activity.
   */
  private boolean isTcpStartCommand(String name, JsonObject args) {
    if (name == null) {
      return false;
    }
    switch (name) {
      case "runTest":
      case "runAllTests":
      case "groupRunTest":
      case "groupEnable":
      case "groupMemberEnable":
        return true;
      case "selectedModeSet": {
        Boolean enabled = parseUiArgBoolean(args, "enabled");
        return Boolean.TRUE.equals(enabled);
      }
      default:
        return false;
    }
  }

  /**
   * NAME
   *   isTcpStopCommand - Check if a TCP command disables or stops activity.
   */
  private boolean isTcpStopCommand(String name, JsonObject args) {
    if (name == null) {
      return false;
    }
    switch (name) {
      case "groupDisable":
      case "groupMemberDisable":
        return true;
      case "selectedModeSet": {
        Boolean enabled = parseUiArgBoolean(args, "enabled");
        return Boolean.FALSE.equals(enabled);
      }
      default:
        return false;
    }
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
   *   parseUiArgStringRaw - Parse args JSON for a raw string field.
   *
   * PARAMETERS
   *   args - Parsed args object.
   *   key - Field name.
   *
   * RETURNS
   *   Raw string or null when missing/empty.
   */
  private String parseUiArgStringRaw(JsonObject args, String key) {
    if (args == null || key == null || !args.has(key)) {
      return null;
    }
    String value = args.get(key).getAsString();
    if (value == null || value.isEmpty()) {
      return null;
    }
    return value;
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
   *   parseUiArgLong - Parse args JSON for a long field.
   *
   * PARAMETERS
   *   args - Parsed args object.
   *   key - Field name.
   *
   * RETURNS
   *   Long value or null when missing/invalid.
   */
  private Long parseUiArgLong(JsonObject args, String key) {
    if (args == null || key == null || !args.has(key)) {
      return null;
    }
    try {
      return args.get(key).getAsLong();
    } catch (Exception ex) {
      return null;
    }
  }

  /**
   * NAME
   *   applyProfilesApplyCommand - Execute profilesApply registry push.
   *
   * PARAMETERS
   *   result - Mutable command result container.
   *   args - Parsed args JSON.
   *   isTcp - True when invoked over TCP.
   */
  private void applyProfilesApplyCommand(UiCommandResult result, JsonObject args, boolean isTcp) {
    if (result == null) {
      return;
    }
    BringupUtil.RegistryStageResult transfer = new BringupUtil.RegistryStageResult();
    BringupUtil.RegistryApplyReport report = new BringupUtil.RegistryApplyReport();
    String registryJson = parseUiArgStringRaw(args, ARG_REGISTRY_JSON);
    String registryHash = parseUiArgString(args, ARG_REGISTRY_HASH);
    Long registryBytes = parseUiArgLong(args, ARG_REGISTRY_BYTES);
    String activateProfile = parseUiArgString(args, ARG_ACTIVATE_PROFILE);
    transfer.expectedHash = registryHash != null ? registryHash : TEXT_EMPTY;
    transfer.expectedBytes = registryBytes != null ? registryBytes : BringupUtil.REGISTRY_BYTES_UNKNOWN;
    if (!isTcp) {
      transfer.message = TEXT_PROFILES_APPLY_NOT_SUPPORTED;
    } else if (registryJson == null || registryJson.isBlank()) {
      transfer.message = TEXT_PROFILES_APPLY_MISSING_REGISTRY;
    } else if (registryHash == null || registryHash.isBlank()) {
      transfer.message = TEXT_PROFILES_APPLY_MISSING_HASH;
    } else if (registryBytes == null) {
      transfer.message = TEXT_PROFILES_APPLY_MISSING_BYTES;
    } else {
      String computedHash = TEXT_EMPTY;
      long computedBytes = BringupUtil.REGISTRY_BYTES_UNKNOWN;
      try {
        computedHash = BringupUtil.computeRawRegistryHash(registryJson);
      } catch (RuntimeException ex) {
        computedHash = TEXT_EMPTY;
      }
      computedBytes = registryJson.getBytes(StandardCharsets.UTF_8).length;
      transfer.computedHash = computedHash;
      transfer.computedBytes = computedBytes;
      if (computedHash.isBlank()) {
        transfer.message = TEXT_PROFILES_APPLY_HASH_UNAVAILABLE;
      } else if (!computedHash.equals(registryHash)) {
        transfer.message = TEXT_PROFILES_APPLY_HASH_MISMATCH;
      } else {
        if (registryBytes != computedBytes) {
          transfer.message = TEXT_PROFILES_APPLY_BYTES_MISMATCH;
        } else {
          transfer.ok = true;
        }
      }
    }
    if (transfer.ok) {
      report = BringupUtil.applyRegistryJson(registryJson, activateProfile);
    }
    boolean overallOk = transfer.ok && report.overallOk;
    result.ok = overallOk;
    String failureMessage = selectProfilesApplyFailureMessage(transfer, report);
    if (overallOk) {
      result.message = TEXT_PROFILES_APPLY_OK;
    } else if (failureMessage.isBlank()) {
      result.message = TEXT_PROFILES_APPLY_FAILED;
    } else {
      result.message = failureMessage;
    }
    result.outText = buildProfilesApplyText(overallOk, transfer, report);
    result.outJson = buildProfilesApplyJson(overallOk, transfer, report);
    if (overallOk && report.activated && profileActivateAction != null) {
      profileActivateAction.run();
    }
  }

  /**
   * NAME
   *   buildProfilesApplyText - Build human-readable profilesApply output.
   */
  private String buildProfilesApplyText(
      boolean overallOk,
      BringupUtil.RegistryStageResult transfer,
      BringupUtil.RegistryApplyReport report) {
    if (overallOk) {
      String active = report.activeProfile != null && !report.activeProfile.isBlank()
          ? report.activeProfile
          : BringupUtil.getActiveCanProfile();
      StringBuilder builder = new StringBuilder();
      builder.append(TEXT_PROFILES_APPLY_OK)
          .append(TEXT_PROFILES_APPLY_DEVICES)
          .append(BringupUtil.getRegistryDeviceCount())
          .append(TEXT_PROFILES_APPLY_PROFILES)
          .append(BringupUtil.getProfileCount())
          .append(TEXT_PROFILES_APPLY_ACTIVE)
          .append(active);
      return builder.toString();
    }
    String message = selectProfilesApplyFailureMessage(transfer, report);
    if (message.isBlank()) {
      return TEXT_PROFILES_APPLY_FAILED;
    }
    if (transfer != null && (TEXT_PROFILES_APPLY_HASH_MISMATCH.equals(message)
        || TEXT_PROFILES_APPLY_BYTES_MISMATCH.equals(message))) {
      return TEXT_PROFILES_APPLY_FAILED + TEXT_VENDOR_SEP + message
          + String.format(
              TEXT_PROFILES_APPLY_HASH_DETAIL,
              BringupHealthFormat.safeText(transfer.expectedHash),
              BringupHealthFormat.safeText(transfer.computedHash),
              transfer.expectedBytes,
              transfer.computedBytes);
    }
    return TEXT_PROFILES_APPLY_FAILED + TEXT_VENDOR_SEP + message;
  }

  /**
   * NAME
   *   selectProfilesApplyFailureMessage - Choose the first failing stage message.
   */
  private String selectProfilesApplyFailureMessage(
      BringupUtil.RegistryStageResult transfer,
      BringupUtil.RegistryApplyReport report) {
    if (transfer != null && !transfer.ok && transfer.message != null && !transfer.message.isBlank()) {
      return transfer.message;
    }
    if (report != null) {
      if (!report.contentValidation.ok && !report.contentValidation.message.isBlank()) {
        return report.contentValidation.message;
      }
      if (!report.apply.ok && !report.apply.message.isBlank()) {
        return report.apply.message;
      }
      if (!report.postApplyCheck.ok && !report.postApplyCheck.message.isBlank()) {
        return report.postApplyCheck.message;
      }
    }
    return TEXT_EMPTY;
  }

  /**
   * NAME
   *   buildProfilesApplyJson - Build JSON output for profilesApply.
   */
  private String buildProfilesApplyJson(
      boolean overallOk,
      BringupUtil.RegistryStageResult transfer,
      BringupUtil.RegistryApplyReport report) {
    JsonObject payload = new JsonObject();
    payload.add(JSON_KEY_TRANSFER_CHECK, buildStageJson(transfer));
    payload.add(JSON_KEY_CONTENT_VALIDATION, buildStageJson(report.contentValidation));
    payload.add(JSON_KEY_APPLY, buildStageJson(report.apply));
    payload.add(JSON_KEY_POST_APPLY, buildStageJson(report.postApplyCheck));
    payload.addProperty(JSON_KEY_OVERALL_OK, overallOk);
    String active = report.activeProfile != null ? report.activeProfile : TEXT_EMPTY;
    if (active.isBlank()) {
      active = BringupUtil.getActiveCanProfile();
    }
    payload.addProperty(JSON_KEY_ACTIVE_PROFILE, active);
    payload.addProperty(JSON_KEY_ACTIVATED, report.activated);
    return payload.toString();
  }

  /**
   * NAME
   *   buildStageJson - Build a stage result JSON object.
   */
  private JsonObject buildStageJson(BringupUtil.RegistryStageResult stage) {
    JsonObject obj = new JsonObject();
    boolean ok = stage != null && stage.ok;
    String message = stage != null && stage.message != null ? stage.message : TEXT_EMPTY;
    obj.addProperty(JSON_KEY_OK, ok);
    obj.addProperty(JSON_KEY_MESSAGE, message);
    if (stage != null) {
      if (stage.expectedHash != null && !stage.expectedHash.isBlank()) {
        obj.addProperty(JSON_KEY_EXPECTED_HASH, stage.expectedHash);
      }
      if (stage.computedHash != null && !stage.computedHash.isBlank()) {
        obj.addProperty(JSON_KEY_COMPUTED_HASH, stage.computedHash);
      }
      if (stage.expectedBytes != BringupUtil.REGISTRY_BYTES_UNKNOWN) {
        obj.addProperty(JSON_KEY_EXPECTED_BYTES, stage.expectedBytes);
      }
      if (stage.computedBytes != BringupUtil.REGISTRY_BYTES_UNKNOWN) {
        obj.addProperty(JSON_KEY_COMPUTED_BYTES, stage.computedBytes);
      }
    }
    return obj;
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
      case "uiPing":
      case "selectProfile":
      case "selectTestPrev":
      case "selectTestNext":
      case "printProfileDevices":
      case "printSummary":
      case "clearStopLatch":
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
      case CMD_PROFILE_ACTIVATE:
      case CMD_PROFILES_APPLY:
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
   *   buildVersionText - Build the show version text output.
   */
  private String buildVersionText() {
    StringBuilder sb = new StringBuilder(VERSION_TEXT_BUILDER_SIZE);
    sb.append(AppVersion.VERSION_PREFIX).append(AppVersion.ROBOT_APP_VERSION);
    appendBuildLines(sb);
    return sb.toString();
  }

  /**
   * NAME
   *   buildVersionJson - Build the show version JSON payload.
   */
  private JsonObject buildVersionJson() {
    JsonObject root = new JsonObject();
    root.addProperty(JSON_KEY_VERSION, AppVersion.ROBOT_APP_VERSION);
    root.add(JSON_KEY_BUILD, buildBuildInfoJson());
    return root;
  }

  /**
   * NAME
   *   appendBuildLines - Append build-info lines to a StringBuilder.
   *
   * PARAMETERS
   *   sb - Target builder for build-info text.
   */
  private void appendBuildLines(StringBuilder sb) {
    sb.append(BuildInfo.TEXT_NEWLINE).append(TEXT_BUILD_HEADER);
    sb.append(BuildInfo.TEXT_NEWLINE)
        .append(BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_GIT, BuildInfo.BUILD_GIT_DESCRIBE));
    sb.append(BuildInfo.TEXT_NEWLINE)
        .append(BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_SHA, BuildInfo.BUILD_GIT_SHA));
    sb.append(BuildInfo.TEXT_NEWLINE)
        .append(BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_BRANCH, BuildInfo.BUILD_GIT_BRANCH));
    sb.append(BuildInfo.TEXT_NEWLINE)
        .append(BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_DIRTY, BuildInfo.BUILD_GIT_DIRTY));
    sb.append(BuildInfo.TEXT_NEWLINE)
        .append(BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_TIME, BuildInfo.BUILD_TIMESTAMP));
  }

  /**
   * NAME
   *   buildBuildInfoJson - Build JSON for build-info output.
   */
  private JsonObject buildBuildInfoJson() {
    JsonObject root = new JsonObject();
    JsonArray fields = new JsonArray();
    fields.add(buildBuildField(BuildInfo.BUILD_LABEL_GIT, BuildInfo.BUILD_GIT_DESCRIBE));
    fields.add(buildBuildField(BuildInfo.BUILD_LABEL_SHA, BuildInfo.BUILD_GIT_SHA));
    fields.add(buildBuildField(BuildInfo.BUILD_LABEL_BRANCH, BuildInfo.BUILD_GIT_BRANCH));
    fields.add(buildBuildField(BuildInfo.BUILD_LABEL_DIRTY, BuildInfo.BUILD_GIT_DIRTY));
    fields.add(buildBuildField(BuildInfo.BUILD_LABEL_TIME, BuildInfo.BUILD_TIMESTAMP));
    root.add(JSON_KEY_BUILD_FIELDS, fields);
    return root;
  }

  /**
   * NAME
   *   buildBuildField - Build a JSON field entry for build-info.
   *
   * PARAMETERS
   *   label - Build-info label.
   *   value - Build-info value.
   */
  private JsonObject buildBuildField(String label, String value) {
    JsonObject entry = new JsonObject();
    entry.addProperty(JSON_KEY_BUILD_LABEL, label);
    entry.addProperty(JSON_KEY_BUILD_VALUE, value);
    return entry;
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
    List<BringupUtil.DeviceEntry> devices = BringupUtil.isProfileActive()
        ? BringupUtil.getActiveDevicesSorted()
        : BringupUtil.getSelectedDevicesSorted();
    if (devices.isEmpty()) {
      return TEXT_DEVICES_NONE;
    }
    StringBuilder sb = new StringBuilder(256);
    sb.append(TEXT_DEVICES_HEADER);
    for (BringupUtil.DeviceEntry entry : devices) {
      if (entry == null) {
        continue;
      }
      sb.append(TEXT_DEVICE_LIST_PREFIX)
          .append(TEXT_LABEL_PREFIX).append(entry.label)
          .append(TEXT_VENDOR_PREFIX).append(entry.vendor)
          .append(TEXT_TYPE_PREFIX).append(entry.type)
          .append(TEXT_ID_PREFIX).append(entry.id)
          .append("\n");
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
    List<BringupUtil.DeviceEntry> devices = BringupUtil.isProfileActive()
        ? BringupUtil.getActiveDevicesSorted()
        : BringupUtil.getSelectedDevicesSorted();
    for (BringupUtil.DeviceEntry entry : devices) {
      if (entry == null) {
        continue;
      }
      JsonObject obj = new JsonObject();
      obj.addProperty(JSON_KEY_LABEL, entry.label);
      obj.addProperty(JSON_KEY_VENDOR, entry.vendor);
      obj.addProperty(JSON_KEY_TYPE, entry.type);
      obj.addProperty(JSON_KEY_ID, entry.id);
      array.add(obj);
    }
    root.add(JSON_KEY_DEVICES, array);
    return root;
  }

  /**
   * NAME
   *   buildDeviceText - Build text for a single device.
   */
  private String buildDeviceText(BringupUtil.DeviceEntry entry) {
    if (entry == null) {
      return TEXT_DEVICE_NOT_FOUND;
    }
    return TEXT_DEVICE_PREFIX + TEXT_LABEL_PREFIX + entry.label
        + TEXT_VENDOR_PREFIX + entry.vendor
        + TEXT_TYPE_PREFIX + entry.type
        + TEXT_ID_PREFIX + entry.id;
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
    obj.addProperty(JSON_KEY_LABEL, entry.label);
    obj.addProperty(JSON_KEY_VENDOR, entry.vendor);
    obj.addProperty(JSON_KEY_TYPE, entry.type);
    obj.addProperty(JSON_KEY_ID, entry.id);
    return obj;
  }

  /**
   * NAME
   *   buildSelectedDeviceText - Build text for selected-device state.
   */
  private String buildSelectedDeviceText() {
    String device = bridgeSelected.device != null ? bridgeSelected.device : TEXT_NONE;
    return TEXT_SELECTED_DEVICE_PREFIX + device + TEXT_PAREN_OPEN
        + (bridgeSelected.enabled ? TEXT_ON : TEXT_OFF) + TEXT_PAREN_CLOSE;
  }

  /**
   * NAME
   *   buildSelectedDeviceJson - Build JSON for selected-device state.
   */
  private JsonObject buildSelectedDeviceJson() {
    JsonObject obj = new JsonObject();
    obj.addProperty(JSON_KEY_DEVICE, bridgeSelected.device != null ? bridgeSelected.device : "");
    obj.addProperty(JSON_KEY_ENABLED, bridgeSelected.enabled);
    return obj;
  }

  /**
   * NAME
   *   buildRuntimeStateJson - Build runtime-state JSON blob.
   */
  private JsonObject buildRuntimeStateJson() {
    JsonObject root = new JsonObject();
    root.addProperty("schemaVersion", 1);
    long nowMs = System.currentTimeMillis();
    root.addProperty("generatedAtMs", nowMs);
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
    root.add("devices", buildRuntimeStateDevices(nowMs));
    return root;
  }

  /**
   * NAME
   *   buildTestsOverviewJson - Build JSON for bringup tests overview.
   *
   * PARAMETERS
   *   overview - Snapshot of current bringup tests.
   *
   * RETURNS
   *   JSON payload describing bringup tests overview.
   */
  private JsonObject buildTestsOverviewJson(BringupCore.TestsOverview overview) {
    JsonObject root = new JsonObject();
    if (overview == null) {
      return root;
    }
    root.addProperty(
        JSON_KEY_TESTS_ACTIVE_SET,
        overview.activeTestSet != null ? overview.activeTestSet : TEXT_EMPTY);
    root.addProperty(
        JSON_KEY_TESTS_DEFAULT_SET,
        overview.defaultTestSet != null ? overview.defaultTestSet : TEXT_EMPTY);
    root.addProperty(JSON_KEY_TESTS_USING_SETS, overview.usingTestSets);
    root.addProperty(JSON_KEY_TESTS_TOTAL_COUNT, overview.totalCount);
    root.addProperty(JSON_KEY_TESTS_ENABLED_COUNT, overview.enabledCount);
    JsonArray rows = new JsonArray();
    int count = overview.rows.size();
    for (int i = INDEX_START; i < count; i++) {
      BringupCore.TestRow row = overview.rows.get(i);
      if (row == null) {
        continue;
      }
      JsonObject obj = new JsonObject();
      obj.addProperty(JSON_KEY_TESTS_INDEX, row.index);
      obj.addProperty(JSON_KEY_TESTS_NAME, row.name != null ? row.name : TEXT_EMPTY);
      obj.addProperty(JSON_KEY_TESTS_ENABLED, row.enabled);
      obj.addProperty(JSON_KEY_TESTS_SELECTED, row.selected);
      obj.addProperty(JSON_KEY_TESTS_TYPE, row.type != null ? row.type : TEXT_EMPTY);
      obj.addProperty(JSON_KEY_TESTS_STATUS, row.status != null ? row.status : TEXT_EMPTY);
      JsonArray motors = new JsonArray();
      if (row.motors != null) {
        for (String motor : row.motors) {
          if (motor != null && !motor.isBlank()) {
            motors.add(motor);
          }
        }
      }
      obj.add(JSON_KEY_TESTS_MOTORS, motors);
      rows.add(obj);
    }
    root.add(JSON_KEY_TESTS_ROWS, rows);
    return root;
  }

  /**
   * NAME
   *   buildSourcesText - Build text describing robot config sources.
   *
   * RETURNS
   *   Multiline text describing the resolved file paths.
   */
  private String buildSourcesText() {
    StringBuilder sb = new StringBuilder(256);
    ReportTextUtil.appendLine(sb, TEXT_SOURCES_HEADER);
    appendSourceLine(sb, SOURCE_NAME_PROFILES, BringupUtil.getProfilePath());
    appendSourceLine(sb, SOURCE_NAME_BINDINGS, resolveDeployPathForFile(FILE_BINDINGS));
    appendSourceLine(sb, SOURCE_NAME_CAN_MAPPINGS, resolveDeployPathForFile(FILE_CAN_MAPPINGS));
    BringupTestRegistry.TestsInfo info = BringupTestRegistry.getTestsInfo();
    appendSourceLine(sb, SOURCE_NAME_TESTS, info != null ? info.path : null);
    ReportTextUtil.appendLine(sb, TEXT_SOURCES_FOOTER);
    return sb.toString();
  }

  /**
   * NAME
   *   buildSourcesJson - Build JSON describing robot config sources.
   *
   * RETURNS
   *   JSON payload listing resolved file paths.
   */
  private JsonObject buildSourcesJson() {
    JsonObject root = new JsonObject();
    JsonArray sources = new JsonArray();
    addSourceJson(sources, SOURCE_NAME_PROFILES, BringupUtil.getProfilePath());
    addSourceJson(sources, SOURCE_NAME_BINDINGS, resolveDeployPathForFile(FILE_BINDINGS));
    addSourceJson(sources, SOURCE_NAME_CAN_MAPPINGS, resolveDeployPathForFile(FILE_CAN_MAPPINGS));
    BringupTestRegistry.TestsInfo info = BringupTestRegistry.getTestsInfo();
    addSourceJson(sources, SOURCE_NAME_TESTS, info != null ? info.path : null);
    root.add(JSON_KEY_SOURCES, sources);
    return root;
  }

  /**
   * NAME
   *   appendSourceLine - Append a single source line to the text buffer.
   *
   * PARAMETERS
   *   sb - StringBuilder to append to.
   *   name - Source name.
   *   path - Resolved file path, if available.
   */
  private void appendSourceLine(StringBuilder sb, String name, Path path) {
    String pathText = path != null ? path.toString() : TEXT_NONE;
    boolean exists = path != null && java.nio.file.Files.exists(path);
    ReportTextUtil.appendLine(sb, String.format(TEXT_SOURCES_ENTRY, name, pathText, exists));
  }

  /**
   * NAME
   *   addSourceJson - Append a single source entry to the JSON list.
   *
   * PARAMETERS
   *   sources - JSON array to append to.
   *   name - Source name.
   *   path - Resolved file path, if available.
   */
  private void addSourceJson(JsonArray sources, String name, Path path) {
    JsonObject entry = new JsonObject();
    entry.addProperty(JSON_KEY_SOURCES_NAME, name);
    entry.addProperty(JSON_KEY_SOURCES_PATH, path != null ? path.toString() : "");
    entry.addProperty(JSON_KEY_SOURCES_EXISTS, path != null && java.nio.file.Files.exists(path));
    sources.add(entry);
  }

  /**
   * NAME
   *   resolveDeployPathForFile - Resolve a deploy path with dev fallback.
   *
   * PARAMETERS
   *   fileName - File name to resolve.
   *
   * RETURNS
   *   Path to the file, or a best-effort local path when deploy not found.
   */
  private Path resolveDeployPathForFile(String fileName) {
    try {
      Path deployPath = Filesystem.getDeployDirectory().toPath().resolve(fileName);
      if (java.nio.file.Files.exists(deployPath)) {
        return deployPath;
      }
    } catch (Exception ex) {
      // Fall through to local dev path.
    }
    Path devPath = Path.of(DEV_PATH_SRC, DEV_PATH_MAIN, DEV_PATH_DEPLOY, fileName);
    if (java.nio.file.Files.exists(devPath)) {
      return devPath;
    }
    return Path.of(fileName);
  }

  /**
   * NAME
   *   buildRuntimeStateDevices - Build device entries with live telemetry.
   */
  private JsonArray buildRuntimeStateDevices(long nowMs) {
    List<DeviceSnapshot> snapshots = core != null ? core.captureSnapshots() : new ArrayList<>();
    Map<String, DeviceSnapshot> byLabel = new HashMap<>();
    Map<Integer, DeviceSnapshot> byId = new HashMap<>();
    for (DeviceSnapshot snap : snapshots) {
      if (snap == null) {
        continue;
      }
      if (snap.label != null && !snap.label.isBlank()) {
        byLabel.put(snap.label.trim().toLowerCase(), snap);
      }
      if (snap.canId >= 0) {
        byId.put(snap.canId, snap);
      }
    }

    JsonArray array = new JsonArray();
    for (BringupUtil.DeviceEntry entry : BringupUtil.getActiveDevicesSorted()) {
      if (entry == null) {
        continue;
      }
      JsonObject obj = new JsonObject();
      obj.addProperty(JSON_KEY_LABEL, entry.label);
      obj.addProperty(JSON_KEY_VENDOR, entry.vendor);
      obj.addProperty(JSON_KEY_TYPE, entry.type);
      obj.addProperty(JSON_KEY_ID, entry.id);

      DeviceSnapshot snap = null;
      if (entry.label != null) {
        snap = byLabel.get(entry.label.trim().toLowerCase());
      }
      if (snap == null && entry.id >= 0) {
        snap = byId.get(entry.id);
      }
      if (snap != null) {
        obj.addProperty(JSON_KEY_PRESENCE_CONF, snap.present ? 1.0 : 0.0);
        if (snap.present) {
          obj.addProperty(JSON_KEY_LAST_SEEN_MS, nowMs);
        }
        RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
        if (rev != null) {
          if (rev.motorCurrentA != null) {
            obj.addProperty(JSON_KEY_MOTOR_CURRENT_A, rev.motorCurrentA);
          }
          if (rev.cmdDuty != null) {
            obj.addProperty(JSON_KEY_CMD_DUTY, rev.cmdDuty);
          }
          if (rev.appliedDuty != null) {
            obj.addProperty(JSON_KEY_APPLIED_DUTY, rev.appliedDuty);
          }
          if (rev.appliedV != null) {
            obj.addProperty(JSON_KEY_APPLIED_V, rev.appliedV);
          }
          if (rev.velRpm != null) {
            obj.addProperty(JSON_KEY_VEL_RPM, rev.velRpm);
          }
          if (rev.tempC != null) {
            obj.addProperty(JSON_KEY_TEMP_C, rev.tempC);
          }
        }
        CtreMotorAttachment ctre = snap.getAttachment(CtreMotorAttachment.class);
        if (ctre != null) {
          if (ctre.motorCurrentA != null) {
            obj.addProperty(JSON_KEY_MOTOR_CURRENT_A, ctre.motorCurrentA);
          }
          if (ctre.appliedDuty != null) {
            obj.addProperty(JSON_KEY_APPLIED_DUTY, ctre.appliedDuty);
          }
          if (ctre.appliedV != null) {
            obj.addProperty(JSON_KEY_APPLIED_V, ctre.appliedV);
          }
          if (ctre.velRpm != null) {
            obj.addProperty(JSON_KEY_VEL_RPM, ctre.velRpm);
          }
          if (ctre.tempC != null) {
            obj.addProperty(JSON_KEY_TEMP_C, ctre.tempC);
          }
        }
        PdhStatusAttachment pdh = snap.getAttachment(PdhStatusAttachment.class);
        if (pdh != null) {
          applyPdhFields(obj, pdh);
        }
        PdpStatusAttachment pdp = snap.getAttachment(PdpStatusAttachment.class);
        if (pdp != null) {
          applyPdpFields(obj, pdp);
        }
      }
      array.add(obj);
    }
    return array;
  }

  /**
   * NAME
   *   applyPdhFields - Add PDH telemetry to a runtime-state JSON entry.
   */
  private void applyPdhFields(JsonObject obj, PdhStatusAttachment pdh) {
    obj.addProperty(JSON_KEY_BUS_V, pdh.voltage);
    obj.addProperty(JSON_KEY_TOTAL_CURRENT_A, pdh.totalCurrent);
    obj.addProperty(JSON_KEY_SWITCHABLE_ENABLED, pdh.switchableEnabled);
    obj.addProperty(JSON_KEY_TEMP_C, pdh.temperature);
    obj.addProperty(JSON_KEY_BROWNOUT, pdh.brownout);
    obj.addProperty(JSON_KEY_CAN_WARNING, pdh.canWarning);
    obj.addProperty(JSON_KEY_HARDWARE_FAULT, pdh.hardwareFault);
    obj.addProperty(JSON_KEY_STICKY_BROWNOUT, pdh.stickyBrownout);
    obj.addProperty(JSON_KEY_STICKY_CAN_WARNING, pdh.stickyCanWarning);
    obj.addProperty(JSON_KEY_STICKY_CAN_BUS_OFF, pdh.stickyCanBusOff);
    obj.addProperty(JSON_KEY_STICKY_HAS_RESET, pdh.stickyHasReset);
    if (pdh.channelCurrentA != null) {
      obj.add(JSON_KEY_CHANNEL_CURRENT_A, buildDoubleArray(pdh.channelCurrentA));
    }
    if (pdh.channelFault != null) {
      obj.add(JSON_KEY_CHANNEL_FAULT, buildBooleanArray(pdh.channelFault));
    }
    if (pdh.channelStickyFault != null) {
      obj.add(JSON_KEY_CHANNEL_STICKY_FAULT, buildBooleanArray(pdh.channelStickyFault));
    }
  }

  /**
   * NAME
   *   applyPdpFields - Add PDP telemetry to a runtime-state JSON entry.
   */
  private void applyPdpFields(JsonObject obj, PdpStatusAttachment pdp) {
    obj.addProperty(JSON_KEY_BUS_V, pdp.voltage);
    obj.addProperty(JSON_KEY_TOTAL_CURRENT_A, pdp.totalCurrent);
    obj.addProperty(JSON_KEY_SWITCHABLE_ENABLED, pdp.switchableEnabled);
    obj.addProperty(JSON_KEY_TEMP_C, pdp.temperature);
    obj.addProperty(JSON_KEY_BROWNOUT, pdp.brownout);
    obj.addProperty(JSON_KEY_CAN_WARNING, pdp.canWarning);
    obj.addProperty(JSON_KEY_HARDWARE_FAULT, pdp.hardwareFault);
    obj.addProperty(JSON_KEY_STICKY_BROWNOUT, pdp.stickyBrownout);
    obj.addProperty(JSON_KEY_STICKY_CAN_WARNING, pdp.stickyCanWarning);
    obj.addProperty(JSON_KEY_STICKY_CAN_BUS_OFF, pdp.stickyCanBusOff);
    obj.addProperty(JSON_KEY_STICKY_HAS_RESET, pdp.stickyHasReset);
    if (pdp.channelCurrentA != null) {
      obj.add(JSON_KEY_CHANNEL_CURRENT_A, buildDoubleArray(pdp.channelCurrentA));
    }
    if (pdp.channelFault != null) {
      obj.add(JSON_KEY_CHANNEL_FAULT, buildBooleanArray(pdp.channelFault));
    }
    if (pdp.channelStickyFault != null) {
      obj.add(JSON_KEY_CHANNEL_STICKY_FAULT, buildBooleanArray(pdp.channelStickyFault));
    }
  }

  /**
   * NAME
   *   buildDoubleArray - Convert a double array to JsonArray.
   */
  private JsonArray buildDoubleArray(double[] values) {
    JsonArray array = new JsonArray();
    if (values == null) {
      return array;
    }
    for (int idx = INDEX_START; idx < values.length; idx++) {
      array.add(values[idx]);
    }
    return array;
  }

  /**
   * NAME
   *   buildBooleanArray - Convert a boolean array to JsonArray.
   */
  private JsonArray buildBooleanArray(boolean[] values) {
    JsonArray array = new JsonArray();
    if (values == null) {
      return array;
    }
    for (int idx = INDEX_START; idx < values.length; idx++) {
      array.add(values[idx]);
    }
    return array;
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
    ReportTextUtil.appendLine(sb, AppVersion.VERSION_PREFIX + AppVersion.ROBOT_APP_VERSION);
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
   *   appendUiTcpStats - Append UI/TCP stats to an existing report.
   *
   * PARAMETERS
   *   report - Base report text.
   *
   * RETURNS
   *   Report with a UI/TCP stats block appended.
   */
  private String appendUiTcpStats(String report) {
    StringBuilder sb = new StringBuilder(256);
    sb.append(report == null ? "" : report.trim());
    if (sb.length() > 0) {
      sb.append('\n');
    }
    sb.append("UI/TCP stats (since boot):\n");
    sb.append("  commandsProcessed=").append(tcpCommandsProcessed)
        .append(" timeouts=").append(tcpCommandTimeouts)
        .append(" dupAcked=").append(tcpDuplicateAcked)
        .append(" dupDropped=").append(tcpDuplicateDropped);
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
    List<BringupUtil.DeviceEntry> devices = BringupUtil.isProfileActive()
        ? BringupUtil.getActiveDevicesSorted()
        : BringupUtil.getSelectedDevicesSorted();
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
   *   printTestsInfo - Emit bringup tests diagnostics.
   *
   * DESCRIPTION
   *   Reports resolved registry path, metadata, and active test set info.
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
        "Resolved path: " + (info.path != null ? info.path.toString() : "(none)"));
    ReportTextUtil.appendLine(
        sb,
        TEXT_TESTS_INFO_PROFILE + (info.profileName != null ? info.profileName : "(none)"));
    ReportTextUtil.appendLine(
        sb,
        TEXT_TESTS_INFO_SOURCE + (info.source != null ? info.source : "(none)"));
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
