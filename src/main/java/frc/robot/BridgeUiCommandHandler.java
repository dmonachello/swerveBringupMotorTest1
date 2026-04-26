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
import frc.robot.input.InputAliasResolver;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.status.StatusRuntime;
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
  private static final long TCP_PROFILE_APPLY_TIMEOUT_MS = 10000;
  private static final long TCP_RUNTIME_STATE_TIMEOUT_MS = 10000;
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
  private static final String JSON_KEY_CODE = "code";
  private static final String JSON_KEY_CODE_TEXT = "codeText";
  private static final String JSON_KEY_VERSION = "version";
  private static final String JSON_KEY_BUILD = "build";
  private static final String JSON_KEY_BUILD_FIELDS = "fields";
  private static final String JSON_KEY_BUILD_LABEL = "label";
  private static final String JSON_KEY_BUILD_VALUE = "value";
  private static final String CMD_SHOW_VERSION = "showVersion";
  private static final String CMD_SHOW_TESTS = "showTests";
  private static final String CMD_SHOW_SOURCES = "showSources";
  private static final String CMD_ACTIVE_ADD = "activeAdd";
  private static final String CMD_ACTIVE_NEXT = "activeNext";
  private static final String GROUP_ACTIVE = "active-group";
  private static final String JSON_KEY_WARNINGS = "warnings";
  private static final String JSON_KEY_GROUP = "group";
  private static final String WARNING_WRAPPED = "WARNING: device list wrapped to first entry.";
  private static final String WARNING_NO_ELIGIBLE_ADD = "WARNING: no eligible next device for active add.";
  private static final String WARNING_NO_ELIGIBLE_NEXT = "WARNING: no eligible next device for active next.";
  private static final String WARNING_DUPLICATE_PREFIX = "WARNING: device already in active-group: ";
  private static final String WARNING_SKIPPED_PREFIX = "WARNING: skipped not-ready device: ";
  private static final String WARNING_REJECT_TEST_RUNNING =
      "WARNING: command rejected while TEST_RUNNING.";
  private static final String MESSAGE_ACTIVE_ADDED_PREFIX = "Active group added device: ";
  private static final String MESSAGE_ACTIVE_NEXT_PREFIX = "Active group rotated to device: ";
  private static final String MESSAGE_ACTIVE_NOT_FOUND = "Active group not found.";
  private static final String MESSAGE_ACTIVE_ADD_FAILED_PREFIX =
      "Failed to add device to active-group: ";
  private static final String MESSAGE_PROFILE_INACTIVE_ADD =
      "Cannot add devices: profile is not active.";
  private static final String CMD_PROFILE_ACTIVATE = "profileActivate";
  private static final String CMD_PROFILES_RELOAD = "profilesReload";
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
  private static final String JSON_KEY_TESTS_RUN = "run";
  private static final String JSON_KEY_RUN_ID = "runId";
  private static final String JSON_KEY_RUN_STATE = "state";
  private static final String JSON_KEY_RUN_TEST = "test";
  private static final String JSON_KEY_RUN_RESULT = "result";
  private static final String JSON_KEY_RUN_STATUS = "status";
  private static final String JSON_KEY_RUN_MESSAGE = "message";
  private static final String JSON_KEY_RUN_STARTED_AT_MS = "startedAtMs";
  private static final String JSON_KEY_RUN_FINISHED_AT_MS = "finishedAtMs";
  private static final String JSON_KEY_SOURCES = "sources";
  private static final String JSON_KEY_SOURCES_NAME = "name";
  private static final String JSON_KEY_SOURCES_PATH = "path";
  private static final String JSON_KEY_SOURCES_EXISTS = "exists";
  private static final String CMD_PROFILES_APPLY = "profilesApply";
  private static final String CMD_SHOW_RUNTIME_STATE = "showRuntimeState";
  private static final String TEXT_SELECTED_DEVICE_PREFIX = "Selected device: ";
  private static final String TEXT_PAREN_OPEN = " (";
  private static final String TEXT_PAREN_CLOSE = ")";
  private static final String TEXT_NONE = "(none)";
  private static final String TEXT_ON = "on";
  private static final String TEXT_OFF = "off";
  private static final String TEXT_DEVICE_PREFIX = "Device ";
  private static final String TEXT_VENDOR_SEP = " ";
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
  private static final String TEXT_PROFILE_ACTIVATE_RESET_REASON = "profilesApplyActivate";
  private static final String TEXT_PROFILES_RELOAD_OK = "Profiles reloaded.";
  private static final String TEXT_PROFILES_RELOAD_FAILED = "Profiles reload failed: %s";
  private static final String TEXT_PROFILES_APPLY_OK = "Profiles applied.";
  private static final String TEXT_PROFILES_APPLY_FAILED = "Profiles apply failed.";
  private static final String TEXT_PROFILES_APPLY_NOT_SUPPORTED = "profilesApply only supported over TCP.";
  private static final String TEXT_PROFILES_APPLY_MISSING_REGISTRY = "profilesApply requires registryJson.";
  private static final String TEXT_PROFILES_APPLY_MISSING_HASH = "profilesApply requires registryHash.";
  private static final String TEXT_PROFILES_APPLY_MISSING_BYTES = "profilesApply requires registryBytes.";
  private static final double SPEED_ZERO = 0.0;
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

  private final BringupRuntime runtime;
  private final BindingsManager bindings;
  private final NetworkTable testsTable;
  private final NetworkTable uiTable;
  private final NetworkTable uiTcpTable;
  private final BridgeUiIngressPolicy uiIngressPolicy;
  private final BridgeUiCommandDispatcher uiCommandDispatcher;
  private final BridgeUiCommandExecutor uiExecuteFacade;
  private final BridgeUiOutputFacade uiOutputFacade;
  private final Runnable profileToggleAction;
  private final Runnable profileActivateAction;
  private Map<String, String> inputAliases = new HashMap<>();

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
  private int activeGroupCursor = INDEX_START;

  /**
   * NAME
   *   BridgeUiCommandHandler - Create a handler for UI commands.
   */
  public BridgeUiCommandHandler(
      BringupRuntime runtime,
      BindingsManager bindings,
      NetworkTable testsTable,
      NetworkTable uiTable,
      NetworkTable uiTcpTable,
      Runnable profileToggleAction,
      Runnable profileActivateAction) {
    this.runtime = runtime;
    this.bindings = bindings;
    this.testsTable = testsTable;
    this.uiTable = uiTable;
    this.uiTcpTable = uiTcpTable;
    this.uiIngressPolicy =
        new BridgeUiIngressPolicy(
            new BridgeUiIngressPolicy.Dependencies() {
              @Override
              public JsonObject parseUiArgs(String argsJson) {
                return BridgeUiCommandHandler.this.parseUiArgs(argsJson);
              }

              @Override
              public String getActiveUiClientId() {
                return activeUiClientId;
              }

              @Override
              public boolean stopLatchActive() {
                return stopLatchActive;
              }

              @Override
              public String stopLatchReason() {
                return stopLatchReason;
              }

              @Override
              public boolean isUiCommandAllowedWhenDisabled(String name) {
                return BridgeUiCommandHandler.this.isUiCommandAllowedWhenDisabled(name);
              }

              @Override
              public boolean isTcpStartCommand(String name, JsonObject args) {
                return BridgeUiCommandHandler.this.isTcpStartCommand(name, args);
              }

              @Override
              public boolean isTcpStopCommand(String name, JsonObject args) {
                return BridgeUiCommandHandler.this.isTcpStopCommand(name, args);
              }

              @Override
              public boolean isRobotEnabled() {
                return DriverStation.isEnabled();
              }

              @Override
              public boolean isRobotEStopped() {
                return DriverStation.isEStopped();
              }

              @Override
              public void setStopLatch(String reason) {
                BridgeUiCommandHandler.this.setStopLatch(reason);
              }

              @Override
              public void applySafetyStop(String reason) {
                BridgeUiCommandHandler.this.applySafetyStop(reason);
              }
            });
    BridgeUiSessionCommands sessionCommands = new BridgeUiSessionCommands(new BridgeUiSessionCommands.Dependencies() {
      @Override
      public String getActiveUiClientId() {
        return activeUiClientId;
      }

      @Override
      public void setActiveUiClientId(String clientId) {
        activeUiClientId = clientId;
      }

      @Override
      public boolean isUiProtocolMonitorEnabled() {
        return uiProtocolMonitorEnabled;
      }

      @Override
      public void setUiProtocolMonitorEnabled(boolean enabled) {
        uiProtocolMonitorEnabled = enabled;
      }

      @Override
      public NetworkTable getUiTcpTable() {
        return uiTcpTable;
      }

      @Override
      public ZoneId resolveRemoteCommandZone(JsonObject args) {
        return BridgeUiCommandHandler.this.resolveRemoteCommandZone(args);
      }

      @Override
      public void setRemoteCommandZone(ZoneId zone) {
        remoteCommandZone = zone;
      }

      @Override
      public String getUiSessionId() {
        return uiSessionId;
      }

      @Override
      public void setUiSessionId(String sessionId) {
        uiSessionId = sessionId;
      }

      @Override
      public long getLastUiSeq() {
        return lastUiSeq;
      }

      @Override
      public long getLastTcpSeq() {
        return lastTcpSeq;
      }

      @Override
      public int getUiProtocolVersion() {
        return UI_PROTOCOL_VERSION;
      }

      @Override
      public String drainUiLog() {
        return BridgeUiCommandHandler.this.drainUiLog();
      }
    });

    BridgeUiProfileCommands profileCommands =
        new BridgeUiProfileCommands(new BridgeUiProfileCommands.Dependencies() {
          @Override
          public String parseUiArgString(JsonObject args, String key) {
            return BridgeUiCommandHandler.this.parseUiArgString(args, key);
          }

          @Override
          public void selectCanProfile(String profileName) {
            BringupUtil.selectCanProfile(profileName);
          }

          @Override
          public void prepareActivationForSelectedProfile() {
            BringupUtil.prepareActivationForSelectedProfile();
          }

          @Override
          public void activateSelectedProfile() {
            runtime.activateSelectedProfile(TEXT_PROFILE_ACTIVATE_RESET_REASON);
          }

          @Override
          public boolean isProfileActive() {
            return BringupUtil.isProfileActive();
          }

          @Override
          public String getActiveCanProfileLabel() {
            return BringupUtil.getActiveCanProfileLabel();
          }

          @Override
          public String reloadProfilesFromJson() {
            return BringupUtil.reloadProfilesFromJson();
          }

          @Override
          public void runProfileActivateAction() {
            if (profileActivateAction != null) {
              profileActivateAction.run();
            }
          }

          @Override
          public void runProfileToggleAction() {
            if (profileToggleAction != null) {
              profileToggleAction.run();
            }
          }

          @Override
          public void selectNextProfile() {
            BringupUtil.selectNextProfile();
          }

          @Override
          public void applyProfilesApplyCommand(BridgeUiCommandResult result, JsonObject args, boolean isTcp) {
            BridgeUiCommandHandler.this.applyProfilesApplyCommand(result, args, isTcp);
          }

          @Override
          public Boolean parseUiArgBoolean(JsonObject args, String key) {
            return BridgeUiCommandHandler.this.parseUiArgBoolean(args, key);
          }

          @Override
          public void applyShowResult(
              BridgeUiCommandResult result,
              String text,
              JsonObject json,
              boolean wantsJson) {
            BridgeUiCommandHandler.this.applyShowResult(result, text, json, wantsJson);
          }

          @Override
          public String getDefaultCanProfile() {
            return BringupUtil.getDefaultCanProfile();
          }

          @Override
          public List<String> getProfileNames() {
            return BringupUtil.getProfileNames();
          }

          @Override
          public List<BringupUtil.DeviceEntry> getProfileDevicesSorted(String profileName) {
            return BringupUtil.getProfileDevicesSorted(profileName);
          }
        });

    BridgeUiTestCommands testCommands = new BridgeUiTestCommands(new BridgeUiTestCommands.Dependencies() {
      @Override
      public void toggleSelectedBringupTestEnabled() {
        runtime.toggleSelectedTestEnabled();
      }

      @Override
      public String printTestsOverview() {
        return BridgeUiCommandHandler.this.printTestsOverview();
      }

      @Override
      public void enqueuePrint(String text) {
        BringupPrinter.enqueue(text);
      }

      @Override
      public BringupCore.TestRunSnapshot runSelectedBringupTest() {
        return runtime.runSelectedTest();
      }

      @Override
      public void runAllBringupTests() {
        runtime.runAllTests();
      }

      @Override
      public void selectPrevBringupTest() {
        runtime.selectPreviousTest();
      }

      @Override
      public void selectNextBringupTest() {
        runtime.selectNextTest();
      }

      @Override
      public String getSelectedBringupTestName() {
        return core().getSelectedBringupTestName();
      }

      @Override
      public String buildNextTestReportText() {
        return core().buildNextTestReportText();
      }

      @Override
      public void requestTextReport(String text, int batchSize) {
        runtime.requestTextReport(text, batchSize);
      }

      @Override
      public String printTestsInfo() {
        return BridgeUiCommandHandler.this.printTestsInfo();
      }

      @Override
      public String parseUiArgName(JsonObject args) {
        return BridgeUiCommandHandler.this.parseUiArgName(args);
      }

      @Override
      public boolean selectBringupTestByName(String testName) {
        return runtime.selectTestByName(testName);
      }

      @Override
      public Boolean parseUiArgBoolean(JsonObject args, String key) {
        return BridgeUiCommandHandler.this.parseUiArgBoolean(args, key);
      }

      @Override
      public BringupCore.TestsOverview buildTestsOverview() {
        return core().buildTestsOverview();
      }

      @Override
      public String formatTestsOverview(BringupCore.TestsOverview overview) {
        return core().formatTestsOverview(overview);
      }

      @Override
      public JsonObject buildTestsOverviewJson(BringupCore.TestsOverview overview) {
        return BridgeUiCommandHandler.this.buildTestsOverviewJson(overview);
      }

      @Override
      public void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson) {
        BridgeUiCommandHandler.this.applyShowResult(result, text, json, wantsJson);
      }
    });

    BridgeUiGroupCommands groupCommands = new BridgeUiGroupCommands(new BridgeUiGroupCommands.Dependencies() {
      @Override
      public Boolean parseUiArgBoolean(JsonObject args, String key) {
        return BridgeUiCommandHandler.this.parseUiArgBoolean(args, key);
      }

      @Override
      public String parseUiArgString(JsonObject args, String key) {
        return BridgeUiCommandHandler.this.parseUiArgString(args, key);
      }

      @Override
      public Double parseUiArgDouble(JsonObject args, String key) {
        return BridgeUiCommandHandler.this.parseUiArgDouble(args, key);
      }

      @Override
      public void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson) {
        BridgeUiCommandHandler.this.applyShowResult(result, text, json, wantsJson);
      }

      @Override
      public String buildGroupsText() {
        return BridgeUiCommandHandler.this.buildGroupsText();
      }

      @Override
      public JsonObject buildGroupsJson() {
        return BridgeUiCommandHandler.this.buildGroupsJson();
      }

      @Override
      public String buildGroupText(BridgeGroupManager.Group group) {
        return BridgeUiCommandHandler.this.buildGroupText(group);
      }

      @Override
      public JsonObject buildGroupJson(BridgeGroupManager.Group group) {
        return BridgeUiCommandHandler.this.buildGroupJson(group);
      }

      @Override
      public void applyActiveAdd(BridgeUiCommandResult result) {
        BridgeUiCommandHandler.this.applyActiveAdd(result);
      }

      @Override
      public void applyActiveNext(BridgeUiCommandResult result) {
        BridgeUiCommandHandler.this.applyActiveNext(result);
      }

      @Override
      public String buildDevicesText() {
        return BridgeUiCommandHandler.this.buildDevicesText();
      }

      @Override
      public JsonObject buildDevicesJson() {
        return BridgeUiCommandHandler.this.buildDevicesJson();
      }

      @Override
      public BringupUtil.DeviceEntry findDeviceEntryByLabel(String label) {
        return BridgeUiCommandHandler.this.findDeviceEntryByLabel(label);
      }

      @Override
      public String buildDeviceText(BringupUtil.DeviceEntry entry) {
        return BridgeUiCommandHandler.this.buildDeviceText(entry);
      }

      @Override
      public JsonObject buildDeviceJson(BringupUtil.DeviceEntry entry) {
        return BridgeUiCommandHandler.this.buildDeviceJson(entry);
      }

      @Override
      public String buildBindingsText() {
        return BridgeUiCommandHandler.this.buildBindingsText();
      }

      @Override
      public JsonObject buildBindingsJson() {
        return BridgeUiCommandHandler.this.buildBindingsJson();
      }

      @Override
      public String buildSelectedDeviceText() {
        return BridgeUiCommandHandler.this.buildSelectedDeviceText();
      }

      @Override
      public JsonObject buildSelectedDeviceJson() {
        return BridgeUiCommandHandler.this.buildSelectedDeviceJson();
      }

      @Override
      public String buildStatusText() {
        return BridgeUiCommandHandler.this.buildStatusText();
      }

      @Override
      public JsonObject buildRuntimeStateJson() {
        return BridgeUiCommandHandler.this.buildRuntimeStateJson();
      }

      @Override
      public BridgeGroupManager getBridgeGroups() {
        return bridgeGroups();
      }

      @Override
      public boolean isValidBindingInput(String input) {
        return BridgeUiCommandHandler.this.isValidBindingInput(input);
      }

      @Override
      public boolean selectBringupTestByName(String name) {
        return runtime.selectTestByName(name);
      }

      @Override
      public void runSelectedBringupTest() {
        runtime.runSelectedTest();
      }

      @Override
      public BridgeGroupManager.SelectedState getBridgeSelected() {
        return bridgeSelected();
      }
    });

    BridgeUiReportCommands reportCommands = new BridgeUiReportCommands(new BridgeUiReportCommands.Dependencies() {
      @Override
      public String buildStateReportText() {
        return core().buildStateReportText();
      }

      @Override
      public String buildQuickSummary() {
        return diagnostics().buildQuickSummary();
      }

      @Override
      public String buildHealthReportText() {
        return core().buildHealthReportText();
      }

      @Override
      public String buildCANCoderReportText() {
        return core().buildCANCoderReportText();
      }

      @Override
      public double getLastNeoSpeed() {
        return lastNeoSpeed;
      }

      @Override
      public double getLastKrakenSpeed() {
        return lastKrakenSpeed;
      }

      @Override
      public String printBindings() {
        return BridgeUiCommandHandler.this.printBindings();
      }

      @Override
      public String printProfileDevices() {
        return BridgeUiCommandHandler.this.printProfileDevices();
      }

      @Override
      public String buildNetworkDiagnosticsReportIfReady() {
        return diagnostics().buildNetworkDiagnosticsReportIfReady();
      }

      @Override
      public String appendUiTcpStats(String report) {
        return BridgeUiCommandHandler.this.appendUiTcpStats(report);
      }

      @Override
      public String buildCanDiagnosticsReportIfReady() {
        return diagnostics().buildCanDiagnosticsReportIfReady();
      }

      @Override
      public long getCanDiagCooldownRemainingMs() {
        return diagnostics().getCanDiagCooldownRemainingMs();
      }

      @Override
      public String buildReportJsonForDump() {
        return diagnostics().buildReportJsonForDump();
      }

      @Override
      public boolean writeReportJsonToFile(String json) {
        return diagnostics().writeReportJsonToFile(json);
      }

      @Override
      public String getReportPath() {
        return diagnostics().getReportPath();
      }

      @Override
      public void requestTextReport(String text, int batchSize) {
        runtime.requestTextReport(text, batchSize);
      }

      @Override
      public Boolean parseUiArgBoolean(JsonObject args, String key) {
        return BridgeUiCommandHandler.this.parseUiArgBoolean(args, key);
      }

      @Override
      public void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson) {
        BridgeUiCommandHandler.this.applyShowResult(result, text, json, wantsJson);
      }

      @Override
      public String buildStatusText() {
        return BridgeUiCommandHandler.this.buildStatusText();
      }

      @Override
      public JsonObject buildStatusJson() {
        return BridgeUiCommandHandler.this.buildStatusJson();
      }

      @Override
      public String buildVersionText() {
        return BridgeUiCommandHandler.this.buildVersionText();
      }

      @Override
      public JsonObject buildVersionJson() {
        return BridgeUiCommandHandler.this.buildVersionJson();
      }

      @Override
      public String buildSourcesText() {
        return BridgeUiCommandHandler.this.buildSourcesText();
      }

      @Override
      public JsonObject buildSourcesJson() {
        return BridgeUiCommandHandler.this.buildSourcesJson();
      }

      @Override
      public boolean hasDiagnostics() {
        return diagnostics() != null;
      }
    });

    BridgeUiRuntimeCommands runtimeCommands = new BridgeUiRuntimeCommands(new BridgeUiRuntimeCommands.Dependencies() {
      @Override
      public void prepareActivationForSelectedProfile() {
        BringupUtil.prepareActivationForSelectedProfile();
      }

      @Override
      public void activateSelectedProfile() {
        runtime.activateSelectedProfile(TEXT_PROFILE_ACTIVATE_RESET_REASON);
      }

      @Override
      public boolean isProfileActive() {
        return BringupUtil.isProfileActive();
      }

      @Override
      public void runProfileActivateAction() {
        if (profileActivateAction != null) {
          profileActivateAction.run();
        }
      }

      @Override
      public void addNextMotorCommand() {
        runtime.addNextMotorCommand();
      }

      @Override
      public void addAllDevicesCommand() {
        runtime.addAllDevicesCommand();
      }

      @Override
      public void setDashboardUpdatesEnabled(boolean enabled) {
        dashboardUpdatesEnabled = enabled;
      }

      @Override
      public boolean isDashboardUpdatesEnabled() {
        return dashboardUpdatesEnabled;
      }

      @Override
      public void applyDashboardUpdateState() {
        BridgeUiCommandHandler.this.applyDashboardUpdateState();
      }

      @Override
      public void enqueuePrint(String text) {
        BringupPrinter.enqueue(text);
      }

      @Override
      public void clearAllFaults() {
        runtime.clearAllFaults();
      }

      @Override
      public boolean clearStopLatchFromUi(String reason) {
        return BridgeUiCommandHandler.this.clearStopLatchFromUi(reason);
      }

      @Override
      public String buildCanPingSweepReportText() {
        return core().buildCanPingSweepReportText();
      }

      @Override
      public void requestTextReport(String text, int batchSize) {
        runtime.requestTextReport(text, batchSize);
      }

      @Override
      public double getUiFixedSpeed() {
        return uiFixedSpeed;
      }

      @Override
      public void setUiFixedSpeed(double speed) {
        uiFixedSpeed = speed;
      }
    });

    this.uiCommandDispatcher = new BridgeUiCommandDispatcher(List.of(
        sessionCommands,
        profileCommands,
        testCommands,
        groupCommands,
        reportCommands,
        runtimeCommands));

    this.uiExecuteFacade = new BridgeUiCommandExecutor(uiIngressPolicy, uiCommandDispatcher);
    this.uiOutputFacade = new BridgeUiOutputFacade(uiTable, uiTcpTable, UI_PROTOCOL_VERSION);
    this.profileToggleAction = profileToggleAction;
    this.profileActivateAction = profileActivateAction;
  }

  /**
   * NAME
   *   core - Return the current runtime core.
   */
  private BringupCore core() {
    return runtime.getCore();
  }

  /**
   * NAME
   *   diagnostics - Return the current runtime diagnostics reporter.
   */
  private DiagnosticsReporter diagnostics() {
    return runtime.getDiagnostics();
  }

  /**
   * NAME
   *   bridgeGroups - Return current shared group state.
   */
  private BridgeGroupManager bridgeGroups() {
    return runtime.getBridgeGroups();
  }

  /**
   * NAME
   *   bridgeSelected - Return current selected-device state.
   */
  private BridgeGroupManager.SelectedState bridgeSelected() {
    return runtime.getBridgeSelected();
  }

  /**
   * NAME
   *   setInputAliases - Update input alias mapping for binding validation.
   *
   * PARAMETERS
   *   aliases - Alias map (alias -> canonical input key).
   */
  public void setInputAliases(Map<String, String> aliases) {
    inputAliases = aliases != null ? new HashMap<>(aliases) : new HashMap<>();
  }

  /**
   * NAME
   *   resetProfileRuntimeUiState - Clear profile-derived UI runtime state.
   *
   * SIDE EFFECTS
   *   Clears selected device state, fixed speed overrides, cached speed
   *   reports, active-group cursor state, and any stop latch from the
   *   previous active profile.
   */
  public void resetProfileRuntimeUiState() {
    bridgeSelected().device = TEXT_EMPTY;
    bridgeSelected().enabled = false;
    uiFixedSpeed = Double.NaN;
    lastNeoSpeed = SPEED_ZERO;
    lastKrakenSpeed = SPEED_ZERO;
    activeGroupCursor = INDEX_START;
    stopLatchActive = false;
    stopLatchReason = TEXT_EMPTY;
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
    BridgeUiCommandResult result = uiExecuteFacade.executeRaw(name, argsJson, cmdTs, clientId, false);
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
      return pending.future.get(tcpCommandTimeoutMs(command), TimeUnit.MILLISECONDS);
    } catch (TimeoutException ex) {
      pending.cancelled = true;
      tcpCommandTimeouts++;
      BridgeUiCommandResult result = new BridgeUiCommandResult();
      result.ok = false;
      result.message = "Robot loop timeout.";
      result.outText = result.message;
      return buildTcpResponse(command, result);
    } catch (Exception ex) {
      pending.cancelled = true;
      BridgeUiCommandResult result = new BridgeUiCommandResult();
      result.ok = false;
      result.message = "UI command failed: " + ex.getMessage();
      result.outText = result.message;
      return buildTcpResponse(command, result);
    }
  }

  /**
   * NAME
   *   tcpCommandTimeoutMs - Select TCP wait timeout for queued robot-loop commands.
   *
   * DESCRIPTION
   *   Most UI commands are expected to finish in one or two robot cycles. A
   *   profile apply is intentionally heavier because it validates, persists,
   *   activates, and instantiates a complete runtime configuration.
   *
   * PARAMETERS
   *   command - TCP command envelope.
   *
   * RETURNS
   *   Timeout in milliseconds for the caller waiting on the command result.
   */
  private long tcpCommandTimeoutMs(TcpUiServer.UiCommand command) {
    if (command != null && CMD_PROFILES_APPLY.equals(command.name)) {
      return TCP_PROFILE_APPLY_TIMEOUT_MS;
    }
    if (command != null && CMD_SHOW_RUNTIME_STATE.equals(command.name)) {
      return TCP_RUNTIME_STATE_TIMEOUT_MS;
    }
    return TCP_CMD_TIMEOUT_MS;
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
      BridgeUiCommandResult result = uiExecuteFacade.executeRaw(
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
  private TcpUiServer.UiResponse buildTcpResponse(TcpUiServer.UiCommand command, BridgeUiCommandResult result) {
    JsonObject state = buildUiStateJson();
    JsonObject ack = new JsonObject();
    ack.addProperty("type", "ack");
    ack.addProperty("seq", command.seq);
    ack.addProperty("name", command.name != null ? command.name : "");
    ack.addProperty("status", StatusRuntime.ackLabel(result.ok));
    ack.addProperty(JSON_KEY_CODE, result.code);
    ack.addProperty(JSON_KEY_CODE_TEXT, StatusRuntime.messageFor(result.code));
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
   *   executeUiCommandSwitch - Execute command switch for validated ingress.
   */
  private BridgeUiCommandResult executeUiCommandSwitch(
      BridgeUiIngressPolicy.Ingress ingress,
      double cmdTs,
      boolean isTcp) {
    BridgeUiCommandResult result = uiCommandDispatcher.dispatch(ingress, cmdTs, isTcp);

    if (result.outText == null || result.outText.isBlank()) {
      if (!result.ok) {
        result.outText = result.message;
      } else {
        result.outText = "";
      }
    }
    if (result.ok) {
      result.code = StatusRuntime.ackCode(true);
    } else {
      result.code = StatusRuntime.ackCode(false);
    }
    return result;
  }

  /**
   * NAME
   *   applyActiveAdd - Add the next ready device to active-group.
   *
   * SIDE EFFECTS
   *   Mutates runtime group membership and emits warning/status payloads.
   */
  private void applyActiveAdd(BridgeUiCommandResult result) {
    if (core() != null && core().isTestRunning()) {
      result.ok = false;
      result.message = WARNING_REJECT_TEST_RUNNING;
      result.outText = result.message;
      setActiveResultJson(result, null, List.of(WARNING_REJECT_TEST_RUNNING));
      return;
    }
    BridgeGroupManager.Group group = ensureActiveGroupDefined();
    if (group == null) {
      result.ok = false;
      result.message = MESSAGE_ACTIVE_NOT_FOUND;
      result.outText = result.message;
      return;
    }
    List<String> warnings = new ArrayList<>();
    ActiveNextCandidate candidate = selectNextReadyActiveCandidate(warnings);
    if (candidate == null) {
      result.ok = true;
      result.message = WARNING_NO_ELIGIBLE_ADD;
      warnings.add(WARNING_NO_ELIGIBLE_ADD);
      result.outText = result.message;
      setActiveResultJson(result, group, warnings);
      return;
    }
    if (candidate.wrapped) {
      warnings.add(WARNING_WRAPPED);
    }
    String deviceKey = candidate.device.trim().toLowerCase(java.util.Locale.ROOT);
    if (group.members.containsKey(deviceKey)) {
      String warning = WARNING_DUPLICATE_PREFIX + candidate.device;
      warnings.add(warning);
      result.ok = true;
      result.message = warning;
      result.outText = warning;
      setActiveResultJson(result, group, warnings);
      return;
    }
    boolean added = bridgeGroups().addDevice(GROUP_ACTIVE, candidate.device, false);
    if (!added) {
      String owner = bridgeGroups().getDeviceGroup(candidate.device);
      String detail = candidate.device;
      if (owner != null && !owner.isBlank()) {
        detail += " (already in group: " + owner + ")";
      }
      String failure = MESSAGE_ACTIVE_ADD_FAILED_PREFIX + detail;
      warnings.add(failure);
      result.ok = false;
      result.message = failure;
      result.outText = failure;
      setActiveResultJson(result, bridgeGroups().getGroup(GROUP_ACTIVE), warnings);
      return;
    }
    BridgeGroupManager.Group updated = bridgeGroups().getGroup(GROUP_ACTIVE);
    result.ok = true;
    result.message = MESSAGE_ACTIVE_ADDED_PREFIX + candidate.device;
    result.outText = result.message;
    setActiveResultJson(result, updated, warnings);
  }

  /**
   * NAME
   *   applyActiveNext - Rotate active-group to the next ready device.
   *
   * SIDE EFFECTS
   *   Stops/deactivates current primary device, updates membership, and emits
   *   warning/status payloads.
   */
  private void applyActiveNext(BridgeUiCommandResult result) {
    if (core() != null && core().isTestRunning()) {
      result.ok = false;
      result.message = WARNING_REJECT_TEST_RUNNING;
      result.outText = result.message;
      setActiveResultJson(result, null, List.of(WARNING_REJECT_TEST_RUNNING));
      return;
    }
    BridgeGroupManager.Group group = ensureActiveGroupDefined();
    if (group == null) {
      result.ok = false;
      result.message = MESSAGE_ACTIVE_NOT_FOUND;
      result.outText = result.message;
      return;
    }
    if (!group.members.isEmpty()) {
      BridgeGroupManager.MemberState primary = group.members.values().iterator().next();
      if (primary != null && primary.device != null && !primary.device.isBlank()) {
        var device = core() != null ? core().findDeviceByLabel(primary.device) : null;
        if (device != null) {
          device.stop();
          device.deactivate();
        }
        bridgeGroups().removeDevice(GROUP_ACTIVE, primary.device);
      }
    }
    List<String> warnings = new ArrayList<>();
    ActiveNextCandidate candidate = selectNextReadyActiveCandidate(warnings);
    if (candidate == null) {
      warnings.add(WARNING_NO_ELIGIBLE_NEXT);
      result.ok = true;
      result.message = WARNING_NO_ELIGIBLE_NEXT;
      result.outText = result.message;
      setActiveResultJson(result, bridgeGroups().getGroup(GROUP_ACTIVE), warnings);
      return;
    }
    if (candidate.wrapped) {
      warnings.add(WARNING_WRAPPED);
    }
    boolean added = bridgeGroups().addDevice(GROUP_ACTIVE, candidate.device, false);
    if (!added) {
      String owner = bridgeGroups().getDeviceGroup(candidate.device);
      String detail = candidate.device;
      if (owner != null && !owner.isBlank()) {
        detail += " (already in group: " + owner + ")";
      }
      String failure = MESSAGE_ACTIVE_ADD_FAILED_PREFIX + detail;
      warnings.add(failure);
      result.ok = false;
      result.message = failure;
      result.outText = failure;
      setActiveResultJson(result, bridgeGroups().getGroup(GROUP_ACTIVE), warnings);
      return;
    }
    BridgeGroupManager.Group updated = bridgeGroups().getGroup(GROUP_ACTIVE);
    result.ok = true;
    result.message = MESSAGE_ACTIVE_NEXT_PREFIX + candidate.device;
    result.outText = result.message;
    setActiveResultJson(result, updated, warnings);
  }

  /**
   * NAME
   *   ensureActiveGroupDefined - Ensure runtime active-group exists.
   */
  private BridgeGroupManager.Group ensureActiveGroupDefined() {
    BridgeGroupManager.Group group = bridgeGroups().getGroup(GROUP_ACTIVE);
    if (group != null) {
      return group;
    }
    bridgeGroups().createGroup(GROUP_ACTIVE);
    return bridgeGroups().getGroup(GROUP_ACTIVE);
  }

  /**
   * NAME
   *   selectNextReadyActiveCandidate - Select next ready device by active profile order.
   */
  private ActiveNextCandidate selectNextReadyActiveCandidate(List<String> warnings) {
    List<BringupUtil.DeviceEntry> entries = BringupUtil.getActiveDevices();
    if (entries == null || entries.isEmpty()) {
      return null;
    }
    int count = entries.size();
    boolean wrapped = false;
    for (int i = INDEX_START; i < count; i++) {
      int idx = (activeGroupCursor + i) % count;
      if (activeGroupCursor + i >= count) {
        wrapped = true;
      }
      BringupUtil.DeviceEntry entry = entries.get(idx);
      String label = entry != null && entry.label != null ? entry.label.trim() : TEXT_EMPTY;
      if (label.isBlank()) {
        continue;
      }
      if (!isDeviceTotallyReady(label)) {
        warnings.add(WARNING_SKIPPED_PREFIX + label);
        continue;
      }
      activeGroupCursor = (idx + 1) % count;
      return new ActiveNextCandidate(label, wrapped);
    }
    return null;
  }

  /**
   * NAME
   *   isDeviceTotallyReady - Check readiness for active-group operations.
   */
  private boolean isDeviceTotallyReady(String label) {
    if (core() == null || label == null || label.isBlank()) {
      return false;
    }
    var device = core().findDeviceByLabel(label);
    return device != null && device.isCreated();
  }

  /**
   * NAME
   *   setActiveResultJson - Publish active-group response JSON with warnings.
   */
  private void setActiveResultJson(
      BridgeUiCommandResult result,
      BridgeGroupManager.Group group,
      List<String> warnings) {
    JsonObject payload = new JsonObject();
    if (group != null) {
      payload.add(JSON_KEY_GROUP, buildGroupJson(group));
    }
    JsonArray warningArray = new JsonArray();
    if (warnings != null) {
      for (String warning : warnings) {
        if (warning != null && !warning.isBlank()) {
          warningArray.add(warning);
        }
      }
    }
    payload.add(JSON_KEY_WARNINGS, warningArray);
    result.outJson = payload.toString();
  }

  /**
   * NAME
   *   ActiveNextCandidate - Next-device selection result for active-group commands.
   */
  private static final class ActiveNextCandidate {
    private final String device;
    private final boolean wrapped;

    private ActiveNextCandidate(String device, boolean wrapped) {
      this.device = device;
      this.wrapped = wrapped;
    }
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
    if (core() == null) {
      return;
    }
    if (!DriverStation.isEnabled() || DriverStation.isEStopped()) {
      return;
    }
    core().safetyStop(reason);
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
  private void publishUiTcpMonitor(long seq, String name, String clientId, BridgeUiCommandResult result) {
    uiOutputFacade.publishUiTcpMonitor(
        seq,
        name,
        clientId,
        uiProtocolMonitorEnabled,
        result.ok,
        result.code,
        result.message);
  }

  /**
   * NAME
   *   publishUiAck - Publish UI command acknowledgements to NetworkTables.
   */
  private void publishUiAck(long seq, boolean ok, String message, String name, double cmdTs) {
    lastUiAckMs =
        uiOutputFacade.publishUiAck(seq, ok, message, name, cmdTs, uiSessionId, activeUiClientId);
  }

  /**
   * NAME
   *   publishUiOut - Publish UI command output to NetworkTables.
   *
   * DESCRIPTION
   *   Emits at least one output entry per command to release the UI.
   */
  private void publishUiOut(long seq, String name, String text, double cmdTs, String jsonText) {
    uiOutputFacade.publishUiOut(seq, name, text, cmdTs, jsonText);
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
  private void applyProfilesApplyCommand(BridgeUiCommandResult result, JsonObject args, boolean isTcp) {
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
    boolean activateRequested = activateProfile != null && !activateProfile.isBlank();
    if (transfer.ok && activateRequested) {
      report = runtime.applyAndActivateRegistry(
          registryJson,
          activateProfile,
          TEXT_PROFILE_ACTIVATE_RESET_REASON);
      if (profileActivateAction != null) {
        profileActivateAction.run();
      }
    } else if (transfer.ok) {
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
      case CMD_ACTIVE_ADD:
      case CMD_ACTIVE_NEXT:
      case "showDevices":
      case "showDevice":
      case "showBindings":
      case "showSelectedDevice":
      case CMD_SHOW_RUNTIME_STATE:
      case "showProfiles":
      case "showProfile":
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
      case CMD_PROFILES_RELOAD:
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
    String key = InputAliasResolver.resolve(input, inputAliases);
    return InputAliasResolver.isSupportedCanonical(key);
  }

  /**
   * NAME
   *   applyShowResult - Populate OUT text/JSON for show commands.
   */
  private void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson) {
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
    sb.append("  groups=").append(bridgeGroups().getGroups().size()).append('\n');
    sb.append("  selectedDevice=").append(
        bridgeSelected().device != null ? bridgeSelected().device : "(none)")
        .append(" (")
        .append(bridgeSelected().enabled ? "on" : "off")
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
    root.addProperty("groupCount", bridgeGroups().getGroups().size());
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
    List<BridgeGroupManager.Group> groups = bridgeGroups().getGroups();
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
    for (BridgeGroupManager.Group group : bridgeGroups().getGroups()) {
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
    List<BridgeGroupManager.Group> groups = bridgeGroups().getGroups();
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
    for (BridgeGroupManager.Group group : bridgeGroups().getGroups()) {
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
    String device = bridgeSelected().device != null ? bridgeSelected().device : TEXT_NONE;
    return TEXT_SELECTED_DEVICE_PREFIX + device + TEXT_PAREN_OPEN
        + (bridgeSelected().enabled ? TEXT_ON : TEXT_OFF) + TEXT_PAREN_CLOSE;
  }

  /**
   * NAME
   *   buildSelectedDeviceJson - Build JSON for selected-device state.
   */
  private JsonObject buildSelectedDeviceJson() {
    JsonObject obj = new JsonObject();
    obj.addProperty(JSON_KEY_DEVICE, bridgeSelected().device != null ? bridgeSelected().device : "");
    obj.addProperty(JSON_KEY_ENABLED, bridgeSelected().enabled);
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
    for (BridgeGroupManager.Group group : bridgeGroups().getGroups()) {
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
    root.add(JSON_KEY_TESTS_RUN, buildTestRunJson(overview.run));
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
   *   buildTestRunJson - Build JSON for the current test run lifecycle.
   */
  private JsonObject buildTestRunJson(BringupCore.TestRunSnapshot run) {
    JsonObject obj = new JsonObject();
    BringupCore.TestRunSnapshot snapshot = run != null ? run : BringupCore.TestRunSnapshot.idle();
    obj.addProperty(JSON_KEY_RUN_ID, snapshot.runId);
    obj.addProperty(JSON_KEY_RUN_STATE, snapshot.state != null ? snapshot.state : TEXT_EMPTY);
    obj.addProperty(JSON_KEY_RUN_TEST, snapshot.test != null ? snapshot.test : TEXT_EMPTY);
    obj.addProperty(JSON_KEY_RUN_RESULT, snapshot.result != null ? snapshot.result : TEXT_EMPTY);
    obj.addProperty(JSON_KEY_RUN_STATUS, snapshot.status != null ? snapshot.status : TEXT_EMPTY);
    obj.addProperty(JSON_KEY_RUN_MESSAGE, snapshot.message != null ? snapshot.message : TEXT_EMPTY);
    obj.addProperty(JSON_KEY_RUN_STARTED_AT_MS, snapshot.startedAtMs);
    obj.addProperty(JSON_KEY_RUN_FINISHED_AT_MS, snapshot.finishedAtMs);
    return obj;
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
    List<DeviceSnapshot> snapshots = core() != null ? core().captureSnapshots() : new ArrayList<>();
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
    runtime.requestTextReport(sb.toString(), 4);
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
    runtime.requestTextReport(report, 4);
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
    runtime.requestTextReport(sb.toString(), 4);
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
    runtime.requestTextReport(report, 4);
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
    runtime.requestTextReport(report, 4);
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
    BringupCore.TestsOverview overview = core().buildTestsOverview();
    String text = core().formatTestsOverview(overview);
    runtime.requestTextReport(text, 6);
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
    testsTable.getEntry("selectedIndex").setNumber(core().getSelectedBringupTestIndex());
    testsTable.getEntry("selectedName").setString(core().getSelectedBringupTestName());
    testsTable.getEntry("activeName").setString(core().getActiveBringupTestName());
    testsTable.getEntry("activeStatus").setString(core().getActiveBringupTestStatus());
    testsTable.getEntry("runAllActive").setBoolean(core().isRunAllActive());
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
    testsTable.getEntry("selectedIndex").setNumber(core().getSelectedBringupTestIndex());
    testsTable.getEntry("selectedName").setString(core().getSelectedBringupTestName());
    testsTable.getEntry("activeName").setString(core().getActiveBringupTestName());
    testsTable.getEntry("activeStatus").setString(core().getActiveBringupTestStatus());
    testsTable.getEntry("runAllActive").setBoolean(core().isRunAllActive());
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
