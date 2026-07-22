package frc.robot;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj.Filesystem;
import edu.wpi.first.wpilibj.livewindow.LiveWindow;
import edu.wpi.first.wpilibj.shuffleboard.Shuffleboard;
import frc.robot.commands.local.RobotLocalCommandExecutor;
import frc.robot.commands.local.RobotLocalCommandHost;
import frc.robot.commands.local.RobotLocalCommandRequest;
import frc.robot.commands.local.RobotLocalCommandRegistry;
import frc.robot.commands.local.RobotLocalControllerGateway;
import frc.robot.commands.local.RobotLocalControllerValueProvider;
import frc.robot.commands.local.RobotLocalCommandSource;
import frc.robot.commands.local.RobotLocalDispatchMode;
import frc.robot.commands.local.RobotLocalDispatchResult;
import frc.robot.commands.local.RobotLocalExecutionResult;
import frc.robot.commands.local.RobotLocalHostUiValueProvider;
import frc.robot.commands.local.RobotLocalNoopValueProvider;
import frc.robot.commands.local.RobotLocalValueProvider;
import frc.robot.diag.probe.ActiveDevicePresenceProbe;
import frc.robot.diag.lifecycle.groups.ResolvedGroupStates;
import frc.robot.diag.snapshots.SampledSignalsAttachment;
import frc.robot.input.BindingsManager;
import frc.robot.input.InputAliasResolver;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.SnapshotDetail;
import frc.robot.status.StatusRuntime;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.ctre.diag.PdpStatusAttachment;
import frc.robot.manufacturers.rev.diag.PdhStatusAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
import frc.robot.telemetry.SampledSignalNames;
import frc.robot.telemetry.SampledSignalSummary;
import frc.robot.tests.BringupTestRegistry;
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
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * NAME
 *   BridgeUiCommandHandler - UI command handler for bringup controls.
 *
 * DESCRIPTION
 *   Owns UI protocol state and command execution for the bringup UI/CLI
 *   surfaces.
 */
public class BridgeUiCommandHandler {
  public static final class RestCommandResult {
    public final boolean ok;
    public final String message;
    public final String outText;
    public final String outJson;
    public final boolean running;

    private RestCommandResult(
        boolean ok,
        String message,
        String outText,
        String outJson,
        boolean running) {
      this.ok = ok;
      this.message = message;
      this.outText = outText;
      this.outJson = outJson;
      this.running = running;
    }

    public static RestCommandResult finished(
        boolean ok,
        String message,
        String outText,
        String outJson) {
      return new RestCommandResult(ok, message, outText, outJson, false);
    }
  }

  private static final long MIN_PRINT_INTERVAL_MS = 1000;
  private static final int UI_PROTOCOL_VERSION = 1;
  private static final int UI_LOG_MAX_LINES = 200;
  private static final int VERSION_TEXT_BUILDER_SIZE = 128;
  private static final String JSON_KEY_LABEL = "label";
  private static final String JSON_KEY_VENDOR = "vendor";
  private static final String JSON_KEY_TYPE = "type";
  private static final String JSON_KEY_ID = "id";
  private static final String JSON_KEY_NAME = "name";
  private static final String JSON_KEY_DEVICE = "device";
  private static final String JSON_KEY_SKIPPED_MEMBERS = "skippedMembers";
  private static final String JSON_KEY_ENABLED = "enabled";
  private static final String JSON_KEY_INSTANTIATED = "instantiated";
  private static final String JSON_KEY_PRESENCE_CONF = "presenceConfidence";
  private static final String JSON_KEY_LIFECYCLE_STATE = "lifecycleState";
  private static final String JSON_KEY_CONTROLLED_LIFECYCLE_ACTIVE =
      "controlledLifecycleActive";
  private static final String JSON_KEY_TESTABLE = "testable";
  private static final String JSON_KEY_OVERRIDE_ACTIVE = "overrideActive";
  private static final String JSON_KEY_OVERRIDE_ORIGINATED = "overrideOriginated";
  private static final String JSON_KEY_OVERRIDE_FAILURE = "overrideFailure";
  private static final String JSON_KEY_LAST_EVENT = "lastEvent";
  private static final String JSON_KEY_LAST_TRANSITION_TIME_MS =
      "lastTransitionTimeMs";
  private static final String JSON_KEY_NOT_TESTABLE_REASON = "notTestableReason";
  private static final String JSON_KEY_LAST_SEEN_MS = "lastSeenMs";
  private static final String JSON_KEY_ATTACHMENTS = "attachments";
  private static final String JSON_KEY_SCHEMA_VERSION = "schemaVersion";
  private static final String JSON_KEY_GENERATED_AT_MS = "generatedAtMs";
  private static final String JSON_KEY_BUILD = "build";
  private static final String JSON_KEY_PROFILE = "profile";
  private static final String JSON_KEY_RUNTIME_ACTIVE = "runtimeActive";
  private static final String JSON_KEY_DISCOVER_THRESHOLD = "discoverThreshold";
  private static final String JSON_KEY_LOST_PRESENCE_THRESHOLD = "lostPresenceThreshold";
  private static final String JSON_KEY_ESTOPPED = "estopped";
  private static final String JSON_KEY_MODE = "mode";
  private static final String JSON_KEY_GROUPS = "groups";
  private static final String JSON_KEY_CAN_BUS = "canBus";
  private static final String JSON_KEY_MEMBERS = "members";
  private static final String JSON_KEY_BINDINGS = "bindings";
  private static final String JSON_KEY_BINDING_ACTIVE = "bindingActive";
  private static final String JSON_KEY_LAST_BINDING_OUTPUT = "lastBindingOutput";
  private static final String JSON_KEY_PRIMARY_LABEL = "primaryLabel";
  private static final String JSON_KEY_MEMBER_COUNT = "memberCount";
  private static final String JSON_KEY_ENABLED_MEMBER_COUNT = "enabledMemberCount";
  private static final String JSON_KEY_HAS_MEMBERS = "hasMembers";
  private static final String JSON_KEY_ALL_ENABLED_MEMBERS_PRESENT =
      "allEnabledMembersPresent";
  private static final String JSON_KEY_LOCKED = "locked";
  private static final String JSON_KEY_INVALID = "invalid";
  private static final String JSON_KEY_SCOPE_ACTIVE = "scopeActive";
  private static final String JSON_KEY_RUNTIME_PRESENT = "runtimePresent";
  private static final String JSON_KEY_PRESENCE_CONFIDENCE = "presenceConfidence";
  private static final String JSON_KEY_ACTIVE = "active";
  private static final String JSON_KEY_REASON = "reason";
  private static final String TEXT_RUNTIME_STATE_HEADER = "=== Runtime State ===";
  private static final String TEXT_RUNTIME_STATE_GROUPS = "groups:";
  private static final String TEXT_RUNTIME_STATE_SELECTED_DEVICE = "selectedDevice:";
  private static final String TEXT_RUNTIME_STATE_DEVICES = "devices:";
  private static final String TEXT_RUNTIME_STATE_NONE = "(none)";
  private static final String TEXT_RUNTIME_STATE_ENABLED_PREFIX = " enabled=";
  private static final String TEXT_RUNTIME_STATE_MEMBERS_PREFIX = " members=";
  private static final String TEXT_RUNTIME_STATE_BINDINGS_PREFIX = " bindings=";
  private static final String TEXT_RUNTIME_STATE_VENDOR_PREFIX = " vendor=";
  private static final String TEXT_RUNTIME_STATE_TYPE_PREFIX = " type=";
  private static final String TEXT_RUNTIME_STATE_ID_PREFIX = " id=";
  private static final String TEXT_RUNTIME_STATE_INSTANTIATED_PREFIX = " instantiated=";
  private static final String TEXT_RUNTIME_STATE_LIFECYCLE_PREFIX = " lifecycleState=";
  private static final String TEXT_RUNTIME_STATE_TESTABLE_PREFIX = " testable=";
  private static final String TEXT_RUNTIME_STATE_PRESENCE_PREFIX = " presenceConfidence=";
  private static final String TEXT_RUNTIME_STATE_DEVICE_FIELD_PREFIX = "  device=";
  private static final String TEXT_RUNTIME_STATE_DEVICE_ENABLED_PREFIX = " enabled=";
  private static final String MESSAGE_RUNTIME_INACTIVE_ACTIVATE =
      "Runtime inactive. Click Runtime Activate.";
  private static final String MESSAGE_ACTIVE_PRESENCE_PROBE_UNAVAILABLE =
      "Active presence probe unavailable.";
  private static final String JSON_KEY_MOTOR_CURRENT_A = "motorCurrentA";
  private static final String JSON_KEY_CMD_DUTY = "cmdDuty";
  private static final String JSON_KEY_APPLIED_DUTY = "appliedDuty";
  private static final String JSON_KEY_APPLIED_V = "appliedV";
  private static final String JSON_KEY_TEMP_C = "tempC";
  private static final String JSON_KEY_VEL_RPM = "velRpm";
  private static final String JSON_KEY_POSITION_ROT = "positionRot";
  private static final String JSON_KEY_BUS_V = "busV";
  private static final String JSON_KEY_ACTIVE_SESSION_ID = "activeSessionId";
  private static final String JSON_KEY_ACTIVE_GROUP_LABEL = "activeGroupLabel";
  private static final String JSON_KEY_LAST_ACTIVATION_MODE = "lastActivationMode";
  private static final String JSON_KEY_LAST_ERROR = "lastError";
  private static final String JSON_KEY_FAULTS_RAW = "faultsRaw";
  private static final String JSON_KEY_STICKY_FAULTS_RAW = "stickyFaultsRaw";
  private static final String JSON_KEY_WARNINGS_RAW = "warningsRaw";
  private static final String JSON_KEY_STICKY_WARNINGS_RAW = "stickyWarningsRaw";
  private static final String JSON_KEY_IS_FOLLOWER = "isFollower";
  private static final String TEXT_CONTROLLED_LIFECYCLE_ACTIVE =
      "controlled-active";
  private static final String TEXT_CONTROLLED_LIFECYCLE_INSTANTIATED =
      "controlled-instantiated";
  private static final String TEXT_CONTROLLED_LIFECYCLE_FAILED =
      "controlled-failed";
  private static final String TEXT_CONTROLLED_LIFECYCLE_ACTIVE_EVENT =
      "controlled-lifecycle";
  private static final String TEXT_CONTROLLED_LIFECYCLE_FAILED_EVENT =
      "controlled-lifecycle-failed";
  private static final String TEXT_CONTROLLED_LIFECYCLE_TESTABLE_REASON =
      "Testable via active scope session.";
  private static final String TEXT_CONTROLLED_LIFECYCLE_INSTANTIATED_REASON =
      "Instantiated by scope activation but not currently active.";
  private static final String TEXT_CONTROLLED_LIFECYCLE_SCOPE_REQUIRED_REASON =
      "Testable only when included in the active scope membership.";
  private static final String JSON_KEY_CURRENT_INSTANT_A = "currentInstantA";
  private static final String JSON_KEY_CURRENT_AVG_A = "currentAvgA";
  private static final String JSON_KEY_CURRENT_PEAK_A = "currentPeakA";
  private static final String JSON_KEY_CURRENT_NONZERO_RATIO = "currentNonzeroRatio";
  private static final String JSON_KEY_CURRENT_SAMPLE_COUNT = "currentSampleCount";
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
  private static final String JSON_KEY_SAFETY_LATCH = "safetyLatch";
  private static final String JSON_KEY_BUILD_FIELDS = "fields";
  private static final String JSON_KEY_BUILD_LABEL = "label";
  private static final String JSON_KEY_BUILD_VALUE = "value";
  private static final String CMD_SHOW_VERSION = "showVersion";
  private static final String CMD_SHOW_TESTS = "showTests";
  private static final String CMD_SHOW_SOURCES = "showSources";
  private static final String CMD_UI_PING = "uiPing";
  private static final String CMD_UI_POLL_LOG = "uiPollLog";
  private static final String CMD_ACTIVE_ADD = "activeAdd";
  private static final String CMD_ACTIVE_NEXT = "activeNext";
  private static final String CMD_MANUAL_DEVICE_DUTY_SET = "manualDeviceDutySet";
  private static final String CMD_MANUAL_DEVICE_DUTY_CLEAR = "manualDeviceDutyClear";
  private static final String CMD_MANUAL_GROUP_DUTY_SET = "manualGroupDutySet";
  private static final String CMD_MANUAL_GROUP_DUTY_CLEAR = "manualGroupDutyClear";
  private static final String DUTY_WRITE_SOURCE_MANUAL_DEVICE = "manual-device";
  private static final String DUTY_WRITE_SOURCE_MANUAL_DEVICE_CLEAR =
      "manual-device-clear";
  private static final String DUTY_WRITE_SOURCE_MANUAL_DEVICE_SWITCH_CLEAR =
      "manual-device-switch-clear";
  private static final String DUTY_WRITE_SOURCE_MANUAL_GROUP_PREFIX = "manual-group:";
  private static final String DUTY_WRITE_SOURCE_MANUAL_GROUP_CLEAR_PREFIX =
      "manual-group-clear:";
  private static final String GROUP_ACTIVE = "active-group";
  private static final String PROFILE_DEVICE_TYPE_MOTOR = "motor";
  private static final String TEXT_GROUP_SKIPPED_MEMBERS_HEADER = "Skipped unsupported members:\n";
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
  private static final String CMD_RUNTIME_ACTIVATE = "runtimeActivate";
  private static final String CMD_RUNTIME_DEACTIVATE = "runtimeDeactivate";
  private static final String CMD_LIFECYCLE_ACTIVATE = "lifecycleActivate";
  private static final String CMD_LIFECYCLE_DEACTIVATE = "lifecycleDeactivate";
  private static final String CMD_LIFECYCLE_DEACTIVATE_ACTIVE =
      "lifecycleDeactivateActive";
  private static final String CMD_ACTIVATE_SELECTED_TEST_DEVICES =
      "activateSelectedTestDevices";
  private static final String CMD_DEACTIVATE_SELECTED_TEST_DEVICES =
      "deactivateSelectedTestDevices";
  private static final String CMD_SHOW_LIFECYCLE_STATE = "showLifecycleState";
  private static final String CMD_PROFILES_RELOAD = "profilesReload";
  private static final String TEXT_SAFETY_LATCH = "  safetyLatch=";
  private static final String TEXT_REASON_PREFIX = " reason=";
  private static final int INDEX_START = 0;
  private static final String JSON_KEY_OK = "ok";
  private static final String JSON_KEY_MESSAGE = "message";
  private static final String JSON_KEY_TRANSFER_CHECK = "transferCheck";
  private static final String JSON_KEY_CONTENT_VALIDATION = "contentValidation";
  private static final String JSON_KEY_APPLY = "apply";
  private static final String JSON_KEY_POST_APPLY = "postApplyCheck";
  private static final String JSON_KEY_OVERALL_OK = "overallOk";
  private static final String JSON_KEY_ACTIVE_PROFILE = "activeProfile";
  private static final String JSON_KEY_SELECTED_PROFILE = "selectedProfile";
  private static final String JSON_KEY_ACTIVE_RUNTIME_PROFILE = "activeRuntimeProfile";
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
  private static final String JSON_KEY_TESTS_REQUIRED_DEVICES = "requiredDevices";
  private static final String JSON_KEY_TESTS_RUNNABLE_NOW = "runnableNow";
  private static final String JSON_KEY_TESTS_BLOCKED_REASON = "blockedReason";
  private static final String JSON_KEY_TESTS_RUN = "run";
  private static final String JSON_KEY_RUN_ID = "runId";
  private static final String JSON_KEY_RUN_STATE = "state";
  private static final String JSON_KEY_RUN_TEST = "test";
  private static final String JSON_KEY_RUN_RESULT = "result";
  private static final String JSON_KEY_RUN_STATUS = "status";
  private static final String JSON_KEY_RUN_MESSAGE = "message";
  private static final String JSON_KEY_RUN_STARTED_AT_MS = "startedAtMs";
  private static final String JSON_KEY_RUN_FINISHED_AT_MS = "finishedAtMs";
  private static final String JSON_KEY_RUN_DETAILS = "details";
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
  private static final String TEXT_PROFILES_APPLY_MISSING_REGISTRY = "profilesApply requires registryJson.";
  private static final String TEXT_PROFILES_APPLY_MISSING_HASH = "profilesApply requires registryHash.";
  private static final String TEXT_PROFILES_APPLY_MISSING_BYTES = "profilesApply requires registryBytes.";
  private static final double SPEED_ZERO = 0.0;
  private static final double DUTY_MIN = -1.0;
  private static final double DUTY_MAX = 1.0;
  private static final String TEXT_PROFILES_APPLY_HASH_MISMATCH = "registryHash mismatch.";
  private static final String TEXT_PROFILES_APPLY_HASH_UNAVAILABLE = "registryHash unavailable.";
  private static final String TEXT_PROFILES_APPLY_BYTES_MISMATCH = "registryBytes mismatch.";
  private static final String TEXT_PROFILES_APPLY_HASH_DETAIL =
      " expectedHash=%s computedHash=%s expectedBytes=%d computedBytes=%d";
  private static final String TEXT_PROFILES_APPLY_DEVICES = " devices=";
  private static final String TEXT_PROFILES_APPLY_PROFILES = " profiles=";
  private static final String TEXT_PROFILES_APPLY_ACTIVE = " active=";
  private static final String TEXT_ACK_OK = "ok";
  private static final String TEXT_ACK_ERROR = "error";
  private static final String TEXT_BOOL_TRUE = "true";
  private static final String TEXT_BOOL_FALSE = "false";
  private static final String TEXT_SPACE = " ";
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
  private final BridgeUiIngressPolicy uiIngressPolicy;
  private final BridgeUiCommandDispatcher uiCommandDispatcher;
  private final BridgeUiCommandExecutor uiExecuteFacade;
  private final RobotLocalCommandHost robotLocalHost;
  private final RobotLocalCommandExecutor robotLocalExecutor;
  private final RobotLocalControllerValueProvider controllerValueProvider;
  private final RobotLocalControllerGateway controllerGateway;
  private final Runnable profileToggleAction;
  private final Runnable profileActivateAction;
  private final Runnable profileDeactivateAction;
  private Map<String, String> inputAliases = new HashMap<>();

  private boolean dashboardUpdatesEnabled = false;
  private long lastStartupPrintMs = 0L;
  private int lastTestsCount = 0;
  private long lastUiSeq = -1;
  private String uiSessionId = UUID.randomUUID().toString();
  private String activeUiClientId = null;
  private boolean stopLatchActive = false;
  private String stopLatchReason = "";
  private boolean lastXboxConnected = false;
  private final ConcurrentLinkedQueue<String> uiLogQueue = new ConcurrentLinkedQueue<>();
  private final AtomicInteger uiLogCount = new AtomicInteger(0);
  private boolean uiProtocolMonitorEnabled = false;
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
      Runnable profileToggleAction,
      Runnable profileActivateAction,
      Runnable profileDeactivateAction) {
    this.runtime = runtime;
    this.bindings = bindings;
    this.profileToggleAction = profileToggleAction;
    this.profileActivateAction = profileActivateAction;
    this.profileDeactivateAction = profileDeactivateAction;
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
      public void resetUiSessionRuntimeContext() {
        runtime.resetUiSessionRuntimeContext();
        BridgeUiCommandHandler.this.resetProfileRuntimeUiState();
      }

      @Override
      public long getLastUiSeq() {
        return lastUiSeq;
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
            runtime.clearProfileScopedBridgeRuntimeState();
            BridgeUiCommandHandler.this.resetProfileRuntimeUiState();
            runtime.stageSelectedProfileForBringup();
            runtime.initializeDeviceLifecycle(System.currentTimeMillis());
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
          public void deactivateActiveProfile() {
            runtime.deactivateActiveProfile(CMD_RUNTIME_DEACTIVATE);
          }

          @Override
          public boolean isProfileActive() {
            return runtime.isRuntimeReady();
          }

          @Override
          public boolean isRuntimeDeclaredActive() {
            return runtime.isRuntimeDeclaredActive();
          }

          @Override
          public boolean isRuntimeActivationAllowed() {
            return DriverStation.isEnabled() && DriverStation.isTeleop() && !DriverStation.isEStopped();
          }

          @Override
          public boolean isControlledLifecycleActive() {
            var lifecycleRuntime = runtime.getControlledBringupLifecycleRuntime();
            return lifecycleRuntime != null
                && lifecycleRuntime.activationManager().lifecycleState()
                    == frc.robot.diag.lifecycle.activation.LifecycleState.ACTIVE;
          }

          @Override
          public String getActiveCanProfileLabel() {
            return BringupUtil.getActiveCanProfileLabel();
          }

          @Override
          public String getSelectedCanProfileLabel() {
            return BringupUtil.getSelectedCanProfileLabel();
          }

          @Override
          public String getActiveRuntimeProfileLabel() {
            return BringupUtil.getActiveRuntimeProfileLabel();
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
          public void runProfileDeactivateAction() {
            if (BridgeUiCommandHandler.this.profileDeactivateAction != null) {
              BridgeUiCommandHandler.this.profileDeactivateAction.run();
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
            runtime.clearProfileScopedBridgeRuntimeState();
            BridgeUiCommandHandler.this.resetProfileRuntimeUiState();
            runtime.stageSelectedProfileForBringup();
            runtime.initializeDeviceLifecycle(System.currentTimeMillis());
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
      public String buildRuntimeStateText() {
        return BridgeUiCommandHandler.this.buildRuntimeStateText();
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

      @Override
      public boolean isRuntimeActive() {
        return runtime.isRuntimeReady();
      }

      @Override
      public boolean isControlledLifecycleActive() {
        return BridgeUiCommandHandler.this.isControlledLifecycleActive();
      }

      @Override
      public boolean isControlledLifecycleDeviceActive(String deviceName) {
        return BridgeUiCommandHandler.this.isControlledLifecycleDeviceActive(deviceName);
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
      public boolean isTestRunning() {
        return core() != null && core().isTestRunning();
      }

      @Override
      public boolean applyManualDeviceDuty(String deviceName, double duty) {
        return BridgeUiCommandHandler.this.applyManualDeviceDuty(deviceName, duty);
      }

      @Override
      public boolean clearManualDeviceDuty(String deviceName) {
        return BridgeUiCommandHandler.this.clearManualDeviceDuty(deviceName);
      }

      @Override
      public boolean applyManualGroupDuty(String groupName, double duty) {
        return BridgeUiCommandHandler.this.applyManualGroupDuty(groupName, duty);
      }

      @Override
      public boolean clearManualGroupDuty(String groupName) {
        return BridgeUiCommandHandler.this.clearManualGroupDuty(groupName);
      }

      @Override
      public String overrideInstantiateDevice(String deviceName) {
        return BridgeUiCommandHandler.this.overrideInstantiateDevice(deviceName);
      }

      @Override
      public String clearDeviceOverride(String deviceName) {
        return BridgeUiCommandHandler.this.clearDeviceOverride(deviceName);
      }
    });

    BridgeUiLifecycleCommands lifecycleCommands =
        new BridgeUiLifecycleCommands(new BridgeUiLifecycleCommands.Dependencies() {
          @Override
          public String parseUiArgString(JsonObject args, String key) {
            return BridgeUiCommandHandler.this.parseUiArgString(args, key);
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
          public boolean isRuntimeActivationAllowed() {
            return DriverStation.isEnabled() && DriverStation.isTeleop() && !DriverStation.isEStopped();
          }

          @Override
          public frc.robot.diag.lifecycle.activation.ActivationResult activateLifecycle(
              String label,
              frc.robot.diag.lifecycle.activation.ActivationMode mode,
              frc.robot.diag.lifecycle.activation.ActivationMembershipMode membershipMode) {
            return runtime.activateControlledBringupLifecycle(label, mode, membershipMode);
          }

          @Override
          public frc.robot.diag.lifecycle.activation.ActivationResult activateSelectedTestDevices(
              frc.robot.diag.lifecycle.activation.ActivationMode mode,
              frc.robot.diag.lifecycle.activation.ActivationMembershipMode membershipMode) {
            return runtime.activateSelectedTestDevices(mode, membershipMode);
          }

          @Override
          public frc.robot.diag.lifecycle.activation.DeactivateResult deactivateLifecycle(String label) {
            return runtime.deactivateControlledBringupLifecycle(label);
          }

          @Override
          public frc.robot.diag.lifecycle.activation.DeactivateResult deactivateSelectedTestDevices() {
            return runtime.deactivateSelectedTestDevices();
          }

          @Override
          public frc.robot.diag.lifecycle.activation.DeactivateResult deactivateActiveLifecycle() {
            return runtime.deactivateActiveControlledBringupLifecycle();
          }

          @Override
          public String buildLifecycleStateText() {
            return runtime.buildControlledBringupLifecycleText();
          }

          @Override
          public JsonObject buildLifecycleStateJson() {
            return runtime.buildControlledBringupLifecycleJson();
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
      public String buildSelectedTestSourceReportText() {
        return core().buildSelectedTestSourceReportText();
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
      public String stageSelectedProfileForBringup() {
        return runtime.stageSelectedProfileForBringup();
      }

      @Override
      public boolean isProfileActive() {
        return runtime.isRuntimeReady();
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

    });

    this.uiCommandDispatcher = new BridgeUiCommandDispatcher(List.of(
        sessionCommands,
        profileCommands,
        testCommands,
        groupCommands,
        lifecycleCommands,
        reportCommands,
        runtimeCommands));

    this.uiExecuteFacade = new BridgeUiCommandExecutor(uiIngressPolicy, uiCommandDispatcher);
    this.robotLocalHost =
        new RobotLocalCommandHost() {
          @Override
          public boolean ensureActiveProfile(String reason) {
            boolean wasReady = runtime.isSelectedProfileRuntimeReady();
            boolean ready = runtime.ensureSelectedProfileRuntime(reason);
            if (!wasReady && ready && profileActivateAction != null) {
              profileActivateAction.run();
            }
            return ready;
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
          public void runGenericCommand() {
            runtime.addAllDevicesCommand();
          }

          @Override
          public void clearAllFaults() {
            runtime.clearAllFaults();
          }

          @Override
          public void runCanSweep() {
            BringupPrinter.enqueue("Command: canSweep");
            String report = core().buildCanPingSweepReportText();
            runtime.requestTextReport(report, 6);
          }

          @Override
          public void toggleDashboard() {
            BridgeUiCommandHandler.this.toggleDashboardUpdates();
          }

          @Override
          public void toggleProfile() {
            BringupUtil.selectNextProfile();
            if (profileToggleAction != null) {
              profileToggleAction.run();
            }
          }

          @Override
          public void printState() {
            runtime.requestTextReport(core().buildStateReportText(), 4);
          }

          @Override
          public void printHealth() {
            runtime.requestTextReport(core().buildHealthReportText(), 4);
          }

          @Override
          public void printCANCoder() {
            runtime.requestTextReport(core().buildCANCoderReportText(), 4);
          }

          @Override
          public void printCanDiagnostics() {
            String report = diagnostics() != null ? diagnostics().buildCanDiagnosticsReportIfReady() : null;
            if (report == null) {
              long remainingMs = diagnostics() != null ? diagnostics().getCanDiagCooldownRemainingMs() : 0L;
              report =
                  remainingMs > 0
                      ? String.format("CAN diagnostics rate-limited, try again in %.1fs.", remainingMs / 1000.0)
                      : "CAN diagnostics not ready yet.";
            }
            runtime.requestTextReport(report, 4);
          }

          @Override
          public void printBindings() {
            BridgeUiCommandHandler.this.printBindings();
          }

          @Override
          public void printTestsInfo() {
            BridgeUiCommandHandler.this.printTestsInfo();
          }

          @Override
          public void printTestsOverview() {
            BridgeUiCommandHandler.this.printTestsOverview();
          }

          @Override
          public void printSelectedTestSource() {
            BridgeUiCommandHandler.this.printSelectedTestSource();
          }

          @Override
          public void printNextTest() {
            runtime.printNextTestReport();
          }

          @Override
          public void printInputs() {
            String report = String.format(
                "Inputs: leftY=%.2f rightY=%.2f (NEO/FLEX=%.2f, KRAKEN/FALCON=%.2f)",
                lastNeoSpeed,
                lastKrakenSpeed,
                lastNeoSpeed,
                lastKrakenSpeed);
            runtime.requestTextReport(report, 4);
          }

          @Override
          public void dumpReport() {
            if (diagnostics() == null) {
              runtime.requestTextReport("Diagnostics unavailable.", 4);
              return;
            }
            String json = diagnostics().buildReportJsonForDump();
            runtime.requestTextReport(ReportTextUtil.wrapLongLine(json, 120), 4);
            diagnostics().writeReportJsonToFile(json);
          }

          @Override
          public RobotLocalExecutionResult runActivePresenceProbe() {
            if (!isRuntimeEffectivelyActive()) {
              return RobotLocalExecutionResult.failed(MESSAGE_RUNTIME_INACTIVE_ACTIVATE);
            }
            ActiveDevicePresenceProbe.ProbeSessionResult session = runtime.runActivePresenceProbe();
            if (session == null) {
              return RobotLocalExecutionResult.failed(MESSAGE_ACTIVE_PRESENCE_PROBE_UNAVAILABLE);
            }
            return RobotLocalExecutionResult.complete(
                session.message,
                session.toText(),
                session.toJsonString());
          }

          @Override
          public void selectPreviousTest() {
            runtime.selectPreviousTest();
          }

          @Override
          public void selectNextTest() {
            runtime.selectNextTest();
          }

          @Override
          public Boolean toggleSelectedTestEnabled() {
            return runtime.toggleSelectedTestEnabled();
          }

          @Override
          public RobotLocalExecutionResult runSelectedTest() {
            BringupCore.TestRunSnapshot snapshot = runtime.runSelectedTest();
            String message =
                snapshot != null && snapshot.message != null && !snapshot.message.isBlank()
                    ? snapshot.message
                    : snapshot != null ? snapshot.state : "runTest";
            return RobotLocalExecutionResult.complete(
                message,
                message,
                snapshot != null ? GSON.toJson(snapshot) : "");
          }

          @Override
          public RobotLocalExecutionResult runAllTests() {
            runtime.runAllTests();
            return RobotLocalExecutionResult.complete("Command: runAllTests");
          }

          @Override
          public boolean isActiveTestRunning() {
            return core() != null && core().isTestRunning();
          }

          @Override
          public void updateReportsAndTests(boolean runHeld) {
            runtime.updateReportsAndTests(runHeld);
          }

          @Override
          public boolean clearStopLatch(String reason) {
            return clearStopLatchFromUi(reason);
          }

          @Override
          public void applyCommandStop(String reason, boolean latchSafety) {
            if (latchSafety) {
              setStopLatch(reason);
            }
            applySafetyStop(reason);
          }

          @Override
          public RobotLocalExecutionResult executeLegacyUiCommand(
              String commandName,
              JsonObject args,
              String clientId,
              double timestampSec,
              boolean isTcp) {
            BridgeUiIngressPolicy.Ingress ingress =
                uiIngressPolicy.parseIngress(commandName, args != null ? args.toString() : "", clientId);
            return fromBridgeUiResult(executeUiCommandSwitch(ingress, timestampSec, isTcp));
          }
        };
    this.robotLocalExecutor = new RobotLocalCommandExecutor(robotLocalHost);
    this.controllerValueProvider = new RobotLocalControllerValueProvider();
    this.controllerGateway = new RobotLocalControllerGateway(robotLocalExecutor, controllerValueProvider);
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
   *   Clears selected device state, cached speed reports, active-group
   *   cursor state, and any stop latch from the
   *   previous active profile.
   */
  public void resetProfileRuntimeUiState() {
    clearSelectedManualDutyWatches();
    bridgeSelected().device = TEXT_EMPTY;
    bridgeSelected().enabled = false;
    bridgeSelected().group = TEXT_EMPTY;
    bridgeSelected().groupEnabled = false;
    bridgeSelected().groupMembers.clear();
    lastNeoSpeed = SPEED_ZERO;
    lastKrakenSpeed = SPEED_ZERO;
    activeGroupCursor = INDEX_START;
    stopLatchActive = false;
    stopLatchReason = TEXT_EMPTY;
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

  /**
   * NAME
   *   submitControllerBindings - Submit controller-originated command edges.
   */
  public void submitControllerBindings(BindingsManager.BindingState bindingState) {
    controllerGateway.submitFromBindings(bindingState);
  }

  /**
   * NAME
   *   clearSelectedManualDutyWatches - Drop diagnostics watches for current manual selections.
   *
   * SIDE EFFECTS
   *   Removes tracked manual-duty labels from the robot-side overwrite
   *   diagnostics so future reports only cover the current popup session.
   */
  private void clearSelectedManualDutyWatches() {
    if (core() == null) {
      return;
    }
    if (bridgeSelected().device != null && !bridgeSelected().device.isBlank()) {
      core().clearManualDutyWatch(bridgeSelected().device);
    }
    for (String label : bridgeSelected().groupMembers) {
      if (label == null || label.isBlank()) {
        continue;
      }
      core().clearManualDutyWatch(label);
    }
  }

  /**
   * NAME
   *   manualGroupDutySource - Build a stable source tag for manual group applies.
   */
  private String manualGroupDutySource(String groupName) {
    String suffix = groupName != null ? groupName.trim() : TEXT_EMPTY;
    return DUTY_WRITE_SOURCE_MANUAL_GROUP_PREFIX + suffix;
  }

  /**
   * NAME
   *   manualGroupDutyClearSource - Build a stable source tag for manual group clears.
   */
  private String manualGroupDutyClearSource(String groupName) {
    String suffix = groupName != null ? groupName.trim() : TEXT_EMPTY;
    return DUTY_WRITE_SOURCE_MANUAL_GROUP_CLEAR_PREFIX + suffix;
  }

  /**
   * NAME
   *   stageManualDeviceSelection - Publish manual device ownership before output writes.
   *
   * PARAMETERS
   *   selected - Shared selected-device state.
   *   deviceLabel - Manual-duty target label.
   *
   * SIDE EFFECTS
   *   Clears group ownership and marks the requested device as the active manual
   *   owner. This lets the periodic binding loop see the manual owner
   *   immediately even if a slider update races with the next 20 ms cycle.
   */
  static void stageManualDeviceSelection(
      BridgeGroupManager.SelectedState selected,
      String deviceLabel) {
    if (selected == null) {
      return;
    }
    selected.group = TEXT_EMPTY;
    selected.groupEnabled = false;
    selected.groupMembers.clear();
    selected.device = deviceLabel != null ? deviceLabel.trim() : TEXT_EMPTY;
    selected.enabled = selected.device != null && !selected.device.isBlank();
  }

  /**
   * NAME
   *   stageManualGroupSelection - Publish manual group ownership before output writes.
   *
   * PARAMETERS
   *   selected - Shared selected-device state.
   *   group - Manual-duty target group.
   *
   * SIDE EFFECTS
   *   Clears device ownership and marks the requested group and its members as
   *   the active manual owner before any duty writes occur. This closes the
   *   transient gap where the binding loop could observe no manual owner and
   *   write zero output during a slider update.
   */
  static void stageManualGroupSelection(
      BridgeGroupManager.SelectedState selected,
      BridgeGroupManager.Group group) {
    if (selected == null) {
      return;
    }
    selected.enabled = false;
    selected.device = TEXT_EMPTY;
    selected.group = TEXT_EMPTY;
    selected.groupEnabled = false;
    selected.groupMembers.clear();
    if (group == null || group.name == null || group.name.isBlank()) {
      return;
    }
    selected.group = group.name;
    selected.groupEnabled = true;
    for (BridgeGroupManager.MemberState member : group.members.values()) {
      if (member == null || member.label == null || member.label.isBlank()) {
        continue;
      }
      selected.groupMembers.add(member.label.trim().toLowerCase(java.util.Locale.ROOT));
    }
  }

  /**
   * NAME
   *   stepRobotLocalCommands - Advance the shared robot-local executor one loop.
   */
  public void stepRobotLocalCommands() {
    robotLocalExecutor.step();
  }

  /**
   * NAME
   *   isRobotLocalCommandActive - Return whether the named command is active.
   */
  public boolean isRobotLocalCommandActive(String commandName) {
    return robotLocalExecutor.isActiveCommand(commandName);
  }

  public RestCommandResult executeRestCommand(String name, String argsJson, String clientId) {
    double commandTimestamp = System.currentTimeMillis() / 1000.0;
    BridgeUiIngressPolicy.Ingress ingress = uiIngressPolicy.parseIngress(name, argsJson, clientId);
    BridgeUiIngressPolicy.ValidationFailure failure = uiIngressPolicy.validateIngress(ingress, false);
    if (failure != null) {
      return new RestCommandResult(
          false,
          failure.message,
          failure.message,
          TEXT_EMPTY,
          false);
    }
    uiIngressPolicy.applyPreExecution(ingress, false);
    if (shouldBypassRobotLocalExecutor(ingress)) {
      BridgeUiCommandResult bypassResult = executeUiCommandSwitch(ingress, commandTimestamp, false);
      return new RestCommandResult(
          bypassResult.ok,
          bypassResult.message,
          bypassResult.outText,
          bypassResult.outJson,
          false);
    }
    RobotLocalDispatchResult dispatchResult =
        robotLocalExecutor.submit(
            new RobotLocalCommandRequest(
                name,
                RobotLocalCommandSource.HOST_UI,
                dispatchModeForUiCommand(name),
                ingress.args,
                uiValueProviderForCommand(name),
                clientId,
                commandTimestamp,
                false));
    BridgeUiCommandResult result = toBridgeUiResult(dispatchResult);
    boolean running =
        dispatchResult != null
            && dispatchResult.executionResult() != null
            && dispatchResult.executionResult().state()
                == frc.robot.commands.local.RobotLocalExecutionState.RUNNING;
    return new RestCommandResult(
        result.ok,
        result.message,
        result.outText,
        result.outJson,
        running);
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
   *   executeUnifiedUiCommand - Validate and submit a UI command through the unified executor.
   */
  private BridgeUiCommandResult executeUnifiedUiCommand(
      String name,
      String argsJson,
      double cmdTs,
      String clientId,
      boolean isTcp) {
    BridgeUiIngressPolicy.Ingress ingress = uiIngressPolicy.parseIngress(name, argsJson, clientId);
    BridgeUiIngressPolicy.ValidationFailure failure = uiIngressPolicy.validateIngress(ingress, isTcp);
    if (failure != null) {
      BridgeUiCommandResult result = new BridgeUiCommandResult();
      result.ok = false;
      result.message = failure.message;
      result.outText = failure.message;
      return result;
    }
    uiIngressPolicy.applyPreExecution(ingress, isTcp);
    if (shouldBypassRobotLocalExecutor(ingress)) {
      return executeUiCommandSwitch(ingress, cmdTs, isTcp);
    }
    RobotLocalDispatchResult dispatchResult =
        robotLocalExecutor.submit(
            new RobotLocalCommandRequest(
                name,
                RobotLocalCommandSource.HOST_UI,
                dispatchModeForUiCommand(name),
                ingress.args,
                uiValueProviderForCommand(name),
                clientId,
                cmdTs,
                isTcp));
    return toBridgeUiResult(dispatchResult);
  }

  /**
   * NAME
   *   uiValueProviderForCommand - Resolve the source-state provider for host UI commands.
   *
   * PARAMETERS
   *   name - Wire command name.
   *
   * RETURNS
   *   Host-UI hold provider for HOLD commands, otherwise the no-op provider.
   */
  private RobotLocalValueProvider uiValueProviderForCommand(String name) {
    frc.robot.commands.local.RobotLocalCommandDefinition definition =
        RobotLocalCommandRegistry.definition(name);
    if (definition != null
        && definition.invocationKind() == frc.robot.commands.local.RobotLocalInvocationKind.HOLD) {
      return RobotLocalHostUiValueProvider.INSTANCE;
    }
    return RobotLocalNoopValueProvider.INSTANCE;
  }

  /**
   * NAME
   *   shouldBypassRobotLocalExecutor - Route protocol/session commands around active-command gating.
   *
   * DESCRIPTION
   *   Session/protocol commands must remain available even when a long-running
   *   robot-local command is active. They do not represent the active robot
   *   actuation slot and therefore must dispatch directly to the UI command
   *   families instead of entering the single-active-command executor.
   */
  private boolean shouldBypassRobotLocalExecutor(BridgeUiIngressPolicy.Ingress ingress) {
    if (ingress == null || ingress.name == null || ingress.name.isBlank()) {
      return false;
    }
    switch (ingress.name) {
      case "uiPing":
      case "uiHandshake":
      case "uiDisconnect":
      case "uiMonitorEnable":
      case "uiMonitorDisable":
      case "uiPollLog":
      case "selectProfile":
      case "profileActivate":
      case "runtimeActivate":
      case "runtimeDeactivate":
      case "profilesReload":
      case "profilesApply":
      case "showProfiles":
      case "showProfile":
      case "showRuntimeState":
      case "showStatus":
      case "showState":
      case "showDevices":
      case "toggleTest":
      case "selectTestPrev":
      case "selectTestNext":
      case "printSelectedTestSource":
      case "printNextTest":
      case "printTestsInfo":
      case "printTestsOverview":
      case "selectTestByName":
      case CMD_ACTIVATE_SELECTED_TEST_DEVICES:
      case CMD_DEACTIVATE_SELECTED_TEST_DEVICES:
      case "showTests":
      case "groupReplaceMembers":
      case CMD_MANUAL_GROUP_DUTY_SET:
      case CMD_MANUAL_GROUP_DUTY_CLEAR:
      case "deviceOverrideInstantiate":
      case "deviceOverrideClear":
        return true;
      default:
        return false;
    }
  }

  private RobotLocalDispatchMode dispatchModeForUiCommand(String name) {
    if (RobotLocalCommandRegistry.COMMAND_STOP.equals(name)) {
      return RobotLocalDispatchMode.INTERRUPT;
    }
    return RobotLocalDispatchMode.IMMEDIATE;
  }

  private BridgeUiCommandResult toBridgeUiResult(RobotLocalDispatchResult dispatchResult) {
    if (dispatchResult == null) {
      BridgeUiCommandResult result = new BridgeUiCommandResult();
      result.ok = false;
      result.message = "No dispatch result.";
      result.outText = result.message;
      return result;
    }
    return toBridgeUiResult(dispatchResult.executionResult(), dispatchResult.message());
  }

  private BridgeUiCommandResult toBridgeUiResult(
      RobotLocalExecutionResult executionResult,
      String fallbackMessage) {
    BridgeUiCommandResult result = new BridgeUiCommandResult();
    if (executionResult == null) {
      result.ok = true;
      result.message = fallbackMessage != null ? fallbackMessage : "OK";
      result.outText = result.message;
      return result;
    }
    result.ok = executionResult.ok();
    result.message =
        executionResult.message() != null && !executionResult.message().isBlank()
            ? executionResult.message()
            : (fallbackMessage != null ? fallbackMessage : "OK");
    result.outText =
        executionResult.outText() != null && !executionResult.outText().isBlank()
            ? executionResult.outText()
            : result.message;
    result.outJson = executionResult.outJson() != null ? executionResult.outJson() : "";
    result.code = StatusRuntime.ackCode(result.ok);
    return result;
  }

  private RobotLocalExecutionResult fromBridgeUiResult(BridgeUiCommandResult result) {
    if (result == null) {
      return RobotLocalExecutionResult.failed("No UI result.");
    }
    if (result.ok) {
      return RobotLocalExecutionResult.complete(result.message, result.outText, result.outJson);
    }
    return RobotLocalExecutionResult.failed(result.message);
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
    if (isControlledLifecycleActive()) {
      result.ok = false;
      result.message =
          "Active group membership is locked while an active scope session is running. Deactivate scope first.";
      result.outText = result.message;
      setActiveResultJson(result, ensureActiveGroupDefined(), List.of(result.message));
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
    if (isControlledLifecycleActive()) {
      result.ok = false;
      result.message =
          "Active group membership is locked while an active scope session is running. Deactivate scope first.";
      result.outText = result.message;
      setActiveResultJson(result, ensureActiveGroupDefined(), List.of(result.message));
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
      if (primary != null && primary.label != null && !primary.label.isBlank()) {
        var device = core() != null ? core().findDeviceByLabel(primary.label) : null;
        if (device != null) {
          device.stop();
          device.deactivate();
        }
        bridgeGroups().removeDevice(GROUP_ACTIVE, primary.label);
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
   *   selectNextReadyActiveCandidate - Select next eligible device by active or selected profile
   *   order.
   */
  private ActiveNextCandidate selectNextReadyActiveCandidate(List<String> warnings) {
    List<BringupUtil.DeviceEntry> entries = activeGroupCandidateEntries();
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
      String profileType = BringupUtil.getConfiguredDeviceTypeByLabel(label);
      if (!PROFILE_DEVICE_TYPE_MOTOR.equalsIgnoreCase(profileType)) {
        continue;
      }
      if (!isDeviceEligibleForActiveGroup(label)) {
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
   *   activeGroupCandidateEntries - Return the profile-scoped device order used by active-group.
   */
  private List<BringupUtil.DeviceEntry> activeGroupCandidateEntries() {
    return runtime.isRuntimeReady()
        ? BringupUtil.getActiveDevices()
        : BringupUtil.getSelectedDevicesSorted();
  }

  /**
   * NAME
   *   isDeviceEligibleForActiveGroup - Check eligibility for active-group membership.
   */
  private boolean isDeviceEligibleForActiveGroup(String label) {
    if (label == null || label.isBlank()) {
      return false;
    }
    runtime.refreshDeviceLifecycle(System.currentTimeMillis());
    DeviceLifecycleRegistry.DeviceLifecycleView lifecycle =
        runtime.getDeviceLifecycle().viewForLabel(label);
    if (lifecycle == null) {
      return false;
    }
    if (runtime.isRuntimeReady()) {
      return lifecycle.testable;
    }
    return true;
  }

  /**
   * NAME
   *   isControlledLifecycleActive - Return whether one controlled lifecycle session is active.
   */
  private boolean isControlledLifecycleActive() {
    var lifecycleRuntime = runtime.getControlledBringupLifecycleRuntime();
    return lifecycleRuntime != null
        && lifecycleRuntime.activationManager().lifecycleState()
            == frc.robot.diag.lifecycle.activation.LifecycleState.ACTIVE;
  }

  /**
   * NAME
   *   isRuntimeEffectivelyActive - Return whether runtime-backed actions may use either legacy runtime or controlled lifecycle activation.
   */
  private boolean isRuntimeEffectivelyActive() {
    return runtime.isRuntimeReady() || isControlledLifecycleActive();
  }

  /**
   * NAME
   *   isControlledLifecycleDeviceActive - Return whether a device is active in the controlled session.
   */
  private boolean isControlledLifecycleDeviceActive(String label) {
    if (!isControlledLifecycleActive() || label == null || label.isBlank()) {
      return false;
    }
    var lifecycleRuntime = runtime.getControlledBringupLifecycleRuntime();
    frc.robot.diag.lifecycle.runtime.DeviceRuntimeState controlledState =
        controlledLifecycleRuntimeStateForLabel(lifecycleRuntime, label);
    return controlledState != null && controlledState.isActive();
  }

  /**
   * NAME
   *   isManualDutyEligible - Enforce lifecycle-scoped manual-duty eligibility.
   */
  private boolean isManualDutyEligible(String label) {
    if (label == null || label.isBlank()) {
      return false;
    }
    runtime.refreshDeviceLifecycle(System.currentTimeMillis());
    DeviceLifecycleRegistry.DeviceLifecycleView lifecycle =
        runtime.getDeviceLifecycle().viewForLabel(label);
    if (lifecycle == null || !lifecycle.testable) {
      return false;
    }
    if (isControlledLifecycleActive()) {
      return isControlledLifecycleDeviceActive(label);
    }
    return true;
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
   *   isTcpStartCommand - Check if a legacy transport stop-latch command starts activity.
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
      case CMD_MANUAL_DEVICE_DUTY_SET:
      case CMD_MANUAL_GROUP_DUTY_SET:
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
   *   isTcpStopCommand - Check if a legacy transport stop-latch command stops activity.
   */
  private boolean isTcpStopCommand(String name, JsonObject args) {
    if (name == null) {
      return false;
    }
    switch (name) {
      case "groupDisable":
      case "groupMemberDisable":
      case CMD_MANUAL_DEVICE_DUTY_CLEAR:
      case CMD_MANUAL_GROUP_DUTY_CLEAR:
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
   *   buildSafetyLatchJson - Build safety latch state for UI and CLI status.
   */
  private JsonObject buildSafetyLatchJson() {
    JsonObject latch = new JsonObject();
    latch.addProperty(JSON_KEY_ACTIVE, stopLatchActive);
    latch.addProperty(JSON_KEY_REASON, stopLatchReason != null ? stopLatchReason : TEXT_EMPTY);
    return latch;
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
   *   isTcp - Legacy transport flag; REST and NT pass false.
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
    if (registryJson == null || registryJson.isBlank()) {
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
      case CMD_SHOW_VERSION:
      case "showGroups":
      case "showGroup":
      case CMD_ACTIVE_ADD:
      case CMD_ACTIVE_NEXT:
      case "showDevices":
      case "showDevice":
      case "showBindings":
      case "showSelectedDevice":
      case "selectTestByName":
      case CMD_SHOW_TESTS:
      case CMD_SHOW_RUNTIME_STATE:
      case "showProfiles":
      case "showProfile":
      case "groupCreate":
      case "groupDelete":
      case "groupAddDevice":
      case "groupRemoveDevice":
      case "groupReplaceMembers":
      case "groupMemberEnable":
      case "groupMemberDisable":
      case "groupMemberToggle":
      case "groupBind":
      case "groupUnbind":
      case "groupEnable":
      case "groupDisable":
      case "selectedDeviceSet":
      case "selectedModeSet":
      case CMD_MANUAL_DEVICE_DUTY_SET:
      case CMD_MANUAL_DEVICE_DUTY_CLEAR:
      case CMD_MANUAL_GROUP_DUTY_SET:
      case CMD_MANUAL_GROUP_DUTY_CLEAR:
      case "deviceOverrideInstantiate":
      case "deviceOverrideClear":
      case CMD_PROFILE_ACTIVATE:
      case CMD_RUNTIME_ACTIVATE:
      case CMD_RUNTIME_DEACTIVATE:
      case CMD_LIFECYCLE_ACTIVATE:
      case CMD_LIFECYCLE_DEACTIVATE:
      case CMD_LIFECYCLE_DEACTIVATE_ACTIVE:
      case CMD_SHOW_LIFECYCLE_STATE:
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
   *   applyManualDeviceDuty - Apply direct manual duty to one selected device.
   *
   * PARAMETERS
   *   deviceName - Target device label.
   *   duty - Requested duty in [-1, 1].
   *
   * RETURNS
   *   True when the target device accepted the duty request.
   */
  private boolean applyManualDeviceDuty(String deviceName, double duty) {
    if (core() == null || deviceName == null || deviceName.isBlank()) {
      return false;
    }
    String target = deviceName.trim();
    if (!isManualDutyEligible(target)) {
      return false;
    }
    if (bridgeGroups().hasActiveBindingForDevice(target)) {
      return false;
    }
    String previous = bridgeSelected().device != null ? bridgeSelected().device.trim() : TEXT_EMPTY;
    double clamped = Math.max(DUTY_MIN, Math.min(DUTY_MAX, duty));
    stageManualDeviceSelection(bridgeSelected(), target);
    if (!previous.isBlank() && !previous.equals(target)) {
      core().clearManualDutyWatch(previous);
      core().setDutyByDeviceLabel(previous, SPEED_ZERO, DUTY_WRITE_SOURCE_MANUAL_DEVICE_SWITCH_CLEAR);
    }
    boolean ok = core().setDutyByDeviceLabel(target, clamped, DUTY_WRITE_SOURCE_MANUAL_DEVICE);
    if (!ok) {
      stageManualDeviceSelection(bridgeSelected(), TEXT_EMPTY);
      return false;
    }
    core().watchManualDutyLabel(target, clamped, DUTY_WRITE_SOURCE_MANUAL_DEVICE);
    return true;
  }

  /**
   * NAME
   *   clearManualDeviceDuty - Stop direct manual duty for the selected device.
   *
   * PARAMETERS
   *   deviceName - Optional explicit device label to stop.
   *
   * RETURNS
   *   True when the manual-duty state is cleared.
   */
  private boolean clearManualDeviceDuty(String deviceName) {
    if (core() == null) {
      return false;
    }
    String target = deviceName != null && !deviceName.isBlank()
        ? deviceName.trim()
        : bridgeSelected().device != null ? bridgeSelected().device.trim() : TEXT_EMPTY;
    if (!target.isBlank()) {
      core().clearManualDutyWatch(target);
      core().setDutyByDeviceLabel(target, SPEED_ZERO, DUTY_WRITE_SOURCE_MANUAL_DEVICE_CLEAR);
    }
    bridgeSelected().enabled = false;
    bridgeSelected().device = TEXT_EMPTY;
    bridgeSelected().groupEnabled = false;
    bridgeSelected().group = TEXT_EMPTY;
    bridgeSelected().groupMembers.clear();
    return true;
  }

  /**
   * NAME
   *   applyManualGroupDuty - Apply direct manual duty to every enabled motor member in one group.
   *
   * PARAMETERS
   *   groupName - Target runtime group name.
   *   duty - Requested duty in [-1, 1].
   *
   * RETURNS
   *   True when at least one enabled motor member accepted the duty request.
   */
  private boolean applyManualGroupDuty(String groupName, double duty) {
    if (core() == null || groupName == null || groupName.isBlank()) {
      return false;
    }
    BridgeGroupManager.Group group = bridgeGroups().getGroup(groupName);
    if (group == null || !group.enabled) {
      return false;
    }
    if (bridgeGroups().hasActiveBindingForGroup(groupName)) {
      return false;
    }
    double clamped = Math.max(DUTY_MIN, Math.min(DUTY_MAX, duty));
    boolean appliedAny = false;
    String source = manualGroupDutySource(groupName);
    clearSelectedManualDutyWatches();
    stageManualGroupSelection(bridgeSelected(), group);
    for (BridgeGroupManager.MemberState member : group.members.values()) {
      if (member == null || !member.enabled || member.label == null || member.label.isBlank()) {
        continue;
      }
      BringupUtil.DeviceEntry entry = findDeviceEntryByLabel(member.label);
      if (entry == null) {
        continue;
      }
      if (!isManualDutyEligible(member.label)) {
        continue;
      }
      if (core().setDutyByDeviceLabel(member.label, clamped, source)) {
        appliedAny = true;
        core().watchManualDutyLabel(member.label, clamped, source);
      }
    }
    if (!appliedAny) {
      stageManualGroupSelection(bridgeSelected(), null);
    }
    return appliedAny;
  }

  /**
   * NAME
   *   clearManualGroupDuty - Stop every enabled motor member in one group.
   *
   * PARAMETERS
   *   groupName - Target runtime group name.
   *
   * RETURNS
   *   True when the group existed and the clear path ran.
   */
  private boolean clearManualGroupDuty(String groupName) {
    if (core() == null || groupName == null || groupName.isBlank()) {
      return false;
    }
    BridgeGroupManager.Group group = bridgeGroups().getGroup(groupName);
    if (group == null || !group.enabled) {
      return false;
    }
    String clearSource = manualGroupDutyClearSource(groupName);
    for (BridgeGroupManager.MemberState member : group.members.values()) {
      if (member == null || !member.enabled || member.label == null || member.label.isBlank()) {
        continue;
      }
      BringupUtil.DeviceEntry entry = findDeviceEntryByLabel(member.label);
      if (entry == null) {
        continue;
      }
      core().clearManualDutyWatch(member.label);
      core().setDutyByDeviceLabel(member.label, SPEED_ZERO, clearSource);
    }
    bridgeSelected().enabled = false;
    bridgeSelected().device = TEXT_EMPTY;
    bridgeSelected().groupEnabled = false;
    bridgeSelected().group = TEXT_EMPTY;
    bridgeSelected().groupMembers.clear();
    return true;
  }

  /**
   * NAME
   *   overrideInstantiateDevice - Execute explicit lifecycle override instantiation.
   *
   * PARAMETERS
   *   deviceName - Target device label.
   *
   * RETURNS
   *   Empty string on success, or an operator-facing error message.
   */
  private String overrideInstantiateDevice(String deviceName) {
    if (core() == null || deviceName == null || deviceName.isBlank()) {
      return "Override instantiation requires a valid device.";
    }
    String target = deviceName.trim();
    DeviceLifecycleRegistry.DeviceLifecycleView lifecycle =
        runtime.getDeviceLifecycle().viewForLabel(target);
    if (lifecycle == null) {
      return "Override instantiation target not in current profile: " + target;
    }
    if (!runtime.getDeviceLifecycle().isInstantiationAllowed(target)) {
      return "Override instantiation not allowed: " + lifecycle.notTestableReason;
    }
    long nowMs = System.currentTimeMillis();
    runtime.getDeviceLifecycle().markOverrideInstantiationPending(target, nowMs);
    boolean ok = core().instantiateDeviceByLabel(target);
    if (!ok) {
      runtime.getDeviceLifecycle().markOverrideInstantiationFailed(target, nowMs);
      return "Override instantiation failed: " + target;
    }
    runtime.refreshDeviceLifecycle(nowMs);
    return TEXT_EMPTY;
  }

  /**
   * NAME
   *   clearDeviceOverride - Clear explicit lifecycle override failure state.
   *
   * PARAMETERS
   *   deviceName - Target device label.
   *
   * RETURNS
   *   Empty string on success, or an operator-facing error message.
   */
  private String clearDeviceOverride(String deviceName) {
    if (deviceName == null || deviceName.isBlank()) {
      return "Override clear requires a valid device.";
    }
    String target = deviceName.trim();
    DeviceLifecycleRegistry.DeviceLifecycleView lifecycle =
        runtime.getDeviceLifecycle().viewForLabel(target);
    if (lifecycle == null) {
      return "Override clear target not in current profile: " + target;
    }
    if (!lifecycle.overrideFailure) {
      return "Override clear not applicable: " + target;
    }
    runtime.getDeviceLifecycle().clearOverrideFailure(target, System.currentTimeMillis());
    runtime.refreshDeviceLifecycle(System.currentTimeMillis());
    return TEXT_EMPTY;
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
    sb.append("  selectedProfile=").append(BringupUtil.getSelectedCanProfileLabel()).append('\n');
    sb.append("  activeRuntimeProfile=")
        .append(formatProfileValue(BringupUtil.getActiveRuntimeProfileLabel())).append('\n');
    sb.append("  runtimeActive=").append(runtime.isRuntimeReady()).append('\n');
    sb.append("  enabled=").append(DriverStation.isEnabled()).append('\n');
    sb.append("  estopped=").append(DriverStation.isEStopped()).append('\n');
    sb.append("  mode=").append(DriverStation.isAutonomous() ? "auto"
        : DriverStation.isTeleop() ? "teleop"
        : DriverStation.isTest() ? "test" : "disabled").append('\n');
    sb.append("  groups=").append(bridgeGroups().getGroups().size()).append('\n');
    sb.append(TEXT_SAFETY_LATCH).append(stopLatchActive ? TEXT_ON : TEXT_OFF);
    if (stopLatchActive && stopLatchReason != null && !stopLatchReason.isBlank()) {
      sb.append(TEXT_REASON_PREFIX).append(stopLatchReason);
    }
    sb.append('\n');
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
    root.addProperty(JSON_KEY_SELECTED_PROFILE, BringupUtil.getSelectedCanProfileLabel());
    root.addProperty(JSON_KEY_ACTIVE_RUNTIME_PROFILE, BringupUtil.getActiveRuntimeProfileLabel());
    root.addProperty(JSON_KEY_RUNTIME_ACTIVE, runtime.isRuntimeReady());
    root.addProperty("enabled", DriverStation.isEnabled());
    root.addProperty("estopped", DriverStation.isEStopped());
    root.addProperty("mode", DriverStation.isAutonomous() ? "auto"
        : DriverStation.isTeleop() ? "teleop"
        : DriverStation.isTest() ? "test" : "disabled");
    root.addProperty("groupCount", bridgeGroups().getGroups().size());
    root.add(JSON_KEY_SAFETY_LATCH, buildSafetyLatchJson());
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
        .append(BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_REVISION, BuildInfo.BUILD_REVISION));
    sb.append(BuildInfo.TEXT_NEWLINE)
        .append(
            BuildInfo.formatBuildLine(
                BuildInfo.BUILD_LABEL_WORKSPACE_REVISION, BuildInfo.BUILD_WORKSPACE_REVISION));
    sb.append(BuildInfo.TEXT_NEWLINE)
        .append(
            BuildInfo.formatBuildLine(
                BuildInfo.BUILD_LABEL_CODE_REVISION, BuildInfo.BUILD_CODE_REVISION));
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
    fields.add(buildBuildField(BuildInfo.BUILD_LABEL_REVISION, BuildInfo.BUILD_REVISION));
    fields.add(
        buildBuildField(
            BuildInfo.BUILD_LABEL_WORKSPACE_REVISION, BuildInfo.BUILD_WORKSPACE_REVISION));
    fields.add(buildBuildField(BuildInfo.BUILD_LABEL_CODE_REVISION, BuildInfo.BUILD_CODE_REVISION));
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
      ResolvedGroupStates.ResolvedGroupState resolved = resolveGroupState(group);
      sb.append("  ")
          .append(resolved != null ? resolved.name : group.name)
          .append(" (")
          .append(group.enabled ? "enabled" : "disabled")
          .append(") members=")
          .append(resolved != null ? resolved.memberCount : group.members.size())
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
      ResolvedGroupStates.ResolvedGroupState resolved = resolveGroupState(group);
      JsonObject g = buildResolvedGroupJson(group, resolved);
      if (g == null) {
        continue;
      }
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
    ResolvedGroupStates.ResolvedGroupState resolved = resolveGroupState(group);
    StringBuilder sb = new StringBuilder(256);
    sb.append("Group ").append(resolved != null ? resolved.name : group.name)
        .append(" (").append(group.enabled ? "enabled" : "disabled").append(")\n");
    sb.append("Members:\n");
    if (resolved == null || !resolved.hasMembers) {
      sb.append("  (none)\n");
    } else {
      for (ResolvedGroupStates.ResolvedGroupMemberState member : resolved.members) {
        sb.append("  ").append(member.label)
            .append(" [").append(member.enabled ? "enabled" : "disabled").append("]\n");
      }
    }
    if (!group.lastSkippedMembers.isEmpty()) {
      sb.append(TEXT_GROUP_SKIPPED_MEMBERS_HEADER);
      for (String label : group.lastSkippedMembers) {
        if (label != null && !label.isBlank()) {
          sb.append("  ").append(label).append('\n');
        }
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
    ResolvedGroupStates.ResolvedGroupState resolved = resolveGroupState(group);
    JsonObject g = buildResolvedGroupJson(group, resolved);
    if (g == null) {
      return null;
    }
    if (!group.lastSkippedMembers.isEmpty()) {
      JsonArray skipped = new JsonArray();
      for (String label : group.lastSkippedMembers) {
        if (label != null && !label.isBlank()) {
          skipped.add(label);
        }
      }
      if (!skipped.isEmpty()) {
        g.add(JSON_KEY_SKIPPED_MEMBERS, skipped);
      }
    }
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
    g.add(JSON_KEY_BINDINGS, bindings);
    g.addProperty(JSON_KEY_BINDING_ACTIVE, group.bindingActive);
    g.addProperty(JSON_KEY_LAST_BINDING_OUTPUT, group.lastBindingOutput);
    return g;
  }

  private JsonObject buildResolvedGroupJson(
      BridgeGroupManager.Group group,
      ResolvedGroupStates.ResolvedGroupState resolved) {
    if (group == null || resolved == null) {
      return null;
    }
    JsonObject g = new JsonObject();
    g.addProperty(JSON_KEY_NAME, resolved.name);
    g.addProperty(JSON_KEY_ENABLED, group.enabled);
    g.addProperty(JSON_KEY_PRIMARY_LABEL, resolved.primaryLabel);
    g.addProperty(JSON_KEY_MEMBER_COUNT, resolved.memberCount);
    g.addProperty(JSON_KEY_ENABLED_MEMBER_COUNT, resolved.enabledMemberCount);
    g.addProperty(JSON_KEY_HAS_MEMBERS, resolved.hasMembers);
    g.addProperty(
        JSON_KEY_ALL_ENABLED_MEMBERS_PRESENT,
        resolved.allEnabledMembersPresent);
    JsonArray members = new JsonArray();
    for (ResolvedGroupStates.ResolvedGroupMemberState member : resolved.members) {
      JsonObject m = new JsonObject();
      m.addProperty(JSON_KEY_LABEL, member.label);
      m.addProperty(JSON_KEY_ENABLED, member.enabled);
      m.addProperty(JSON_KEY_LOCKED, member.locked);
      m.addProperty(JSON_KEY_INVALID, member.invalid);
      m.addProperty(JSON_KEY_SCOPE_ACTIVE, member.scopeActive);
      m.addProperty(JSON_KEY_RUNTIME_PRESENT, member.runtimePresent);
      m.addProperty(JSON_KEY_INSTANTIATED, member.instantiated);
      m.addProperty(JSON_KEY_TESTABLE, member.testable);
      members.add(m);
    }
    g.add(JSON_KEY_MEMBERS, members);
    return g;
  }

  private ResolvedGroupStates.ResolvedGroupState resolveGroupState(
      BridgeGroupManager.Group group) {
    var lifecycleRuntime = runtime.getControlledBringupLifecycleRuntime();
    boolean locked =
        lifecycleRuntime != null
            && lifecycleRuntime.activationManager().lifecycleState()
                == frc.robot.diag.lifecycle.activation.LifecycleState.ACTIVE;
    return ResolvedGroupStates.resolve(
        group,
        label -> runtime.getDeviceLifecycle().viewForLabel(label),
        label -> controlledLifecycleRuntimeStateForLabel(lifecycleRuntime, label),
        locked);
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
  public JsonObject buildDevicesJson() {
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
  public JsonObject buildRuntimeStateJson() {
    JsonObject root = new JsonObject();
    root.addProperty("schemaVersion", 1);
    long nowMs = System.currentTimeMillis();
    runtime.refreshDeviceLifecycle(nowMs);
    runtime.synchronizeControlledBringupLifecycleGroups();
    ensureActiveGroupDefined();
    var lifecycleRuntime = runtime.getControlledBringupLifecycleRuntime();
    boolean controlledLifecycleActive =
        lifecycleRuntime != null
            && lifecycleRuntime.activationManager().lifecycleState()
                == frc.robot.diag.lifecycle.activation.LifecycleState.ACTIVE;
    root.addProperty("generatedAtMs", nowMs);
    root.addProperty("build", BringupCore.getBuildMarker());
    String runtimeProfile = BringupUtil.getActiveCanProfileLabel();
    if (controlledLifecycleActive
        && lifecycleRuntime.catalogBundle().profileName() != null
        && !lifecycleRuntime.catalogBundle().profileName().isBlank()) {
      runtimeProfile = lifecycleRuntime.catalogBundle().profileName();
    }
    root.addProperty("profile", runtimeProfile);
    root.addProperty(JSON_KEY_SELECTED_PROFILE, BringupUtil.getSelectedCanProfileLabel());
    root.addProperty(JSON_KEY_ACTIVE_RUNTIME_PROFILE, BringupUtil.getActiveRuntimeProfileLabel());
    root.addProperty(JSON_KEY_RUNTIME_ACTIVE, runtime.isRuntimeReady());
    root.addProperty(JSON_KEY_CONTROLLED_LIFECYCLE_ACTIVE, controlledLifecycleActive);
    root.addProperty(
        JSON_KEY_DISCOVER_THRESHOLD,
        BringupUtil.getProfileDiscoverThreshold(
            BringupUtil.isProfileActive()
                ? BringupUtil.getActiveRuntimeProfileLabel()
                : BringupUtil.getSelectedCanProfileLabel()));
    root.addProperty(
        JSON_KEY_LOST_PRESENCE_THRESHOLD,
        BringupUtil.getProfileLostPresenceThreshold(
            BringupUtil.isProfileActive()
                ? BringupUtil.getActiveRuntimeProfileLabel()
                : BringupUtil.getSelectedCanProfileLabel()));
    root.addProperty("enabled", DriverStation.isEnabled());
    root.addProperty("estopped", DriverStation.isEStopped());
    root.addProperty("mode", DriverStation.isAutonomous() ? "auto"
        : DriverStation.isTeleop() ? "teleop"
        : DriverStation.isTest() ? "test" : "disabled");
    root.add(JSON_KEY_SAFETY_LATCH, buildSafetyLatchJson());
    root.add(
        JSON_KEY_CAN_BUS,
        diagnostics() != null ? diagnostics().buildBusHealthJson() : new JsonObject());
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
   *   buildRuntimeStateText - Build a human-readable runtime-state report.
   *
   * DESCRIPTION
   *   Renders the shared runtime-state JSON model into the default CLI text
   *   view so TCP/REST callers get the same contract with a text default.
   */
  private String buildRuntimeStateText() {
    JsonObject state = buildRuntimeStateJson();
    StringBuilder sb = new StringBuilder(1024);
    sb.append(TEXT_RUNTIME_STATE_HEADER).append('\n');
    appendRuntimeStateScalarLine(sb, JSON_KEY_SCHEMA_VERSION, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_GENERATED_AT_MS, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_BUILD, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_PROFILE, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_SELECTED_PROFILE, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_ACTIVE_RUNTIME_PROFILE, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_RUNTIME_ACTIVE, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_CONTROLLED_LIFECYCLE_ACTIVE, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_DISCOVER_THRESHOLD, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_LOST_PRESENCE_THRESHOLD, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_ENABLED, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_ESTOPPED, state);
    appendRuntimeStateScalarLine(sb, JSON_KEY_MODE, state);
    appendRuntimeStateSafetyLatch(sb, state.getAsJsonObject(JSON_KEY_SAFETY_LATCH));
    appendRuntimeStateGroups(sb, state.getAsJsonArray(JSON_KEY_GROUPS));
    appendRuntimeStateSelectedDevice(sb, state.getAsJsonObject("selectedDevice"));
    appendRuntimeStateDevices(sb, state.getAsJsonArray(JSON_KEY_DEVICES));
    return sb.toString();
  }

  /**
   * NAME
   *   appendRuntimeStateScalarLine - Append one top-level scalar runtime-state field.
   */
  private void appendRuntimeStateScalarLine(StringBuilder sb, String key, JsonObject state) {
    if (sb == null || key == null || state == null || !state.has(key)) {
      return;
    }
    sb.append(key).append('=').append(state.get(key).getAsString()).append('\n');
  }

  /**
   * NAME
   *   appendRuntimeStateSafetyLatch - Append safety-latch summary.
   */
  private void appendRuntimeStateSafetyLatch(StringBuilder sb, JsonObject safetyLatch) {
    if (sb == null || safetyLatch == null) {
      return;
    }
    sb.append(JSON_KEY_SAFETY_LATCH)
        .append('.')
        .append(JSON_KEY_ACTIVE)
        .append('=')
        .append(
            safetyLatch.has(JSON_KEY_ACTIVE)
                ? safetyLatch.get(JSON_KEY_ACTIVE).getAsString()
                : TEXT_RUNTIME_STATE_NONE)
        .append('\n');
    sb.append(JSON_KEY_SAFETY_LATCH)
        .append('.')
        .append(JSON_KEY_REASON)
        .append('=')
        .append(
            safetyLatch.has(JSON_KEY_REASON)
                ? safetyLatch.get(JSON_KEY_REASON).getAsString()
                : TEXT_RUNTIME_STATE_NONE)
        .append('\n');
  }

  /**
   * NAME
   *   appendRuntimeStateGroups - Append runtime-state group summary.
   */
  private void appendRuntimeStateGroups(StringBuilder sb, JsonArray groups) {
    sb.append(TEXT_RUNTIME_STATE_GROUPS).append('\n');
    if (groups == null || groups.size() == 0) {
      sb.append("  ").append(TEXT_RUNTIME_STATE_NONE).append('\n');
      return;
    }
    for (int i = 0; i < groups.size(); i++) {
      JsonObject group = groups.get(i).getAsJsonObject();
      JsonArray members = group.has(JSON_KEY_MEMBERS) ? group.getAsJsonArray(JSON_KEY_MEMBERS) : null;
      JsonArray bindings = group.has(JSON_KEY_BINDINGS) ? group.getAsJsonArray(JSON_KEY_BINDINGS) : null;
      sb.append("  ")
          .append(group.get(JSON_KEY_NAME).getAsString())
          .append(TEXT_RUNTIME_STATE_ENABLED_PREFIX)
          .append(group.get(JSON_KEY_ENABLED).getAsString())
          .append(TEXT_RUNTIME_STATE_MEMBERS_PREFIX)
          .append(members != null ? members.size() : 0)
          .append(TEXT_RUNTIME_STATE_BINDINGS_PREFIX)
          .append(bindings != null ? bindings.size() : 0)
          .append('\n');
    }
  }

  /**
   * NAME
   *   appendRuntimeStateSelectedDevice - Append selected-device runtime-state summary.
   */
  private void appendRuntimeStateSelectedDevice(StringBuilder sb, JsonObject selectedDevice) {
    sb.append(TEXT_RUNTIME_STATE_SELECTED_DEVICE).append('\n');
    if (selectedDevice == null) {
      sb.append("  ").append(TEXT_RUNTIME_STATE_NONE).append('\n');
      return;
    }
    String device =
        selectedDevice.has(JSON_KEY_DEVICE)
            ? selectedDevice.get(JSON_KEY_DEVICE).getAsString()
            : TEXT_RUNTIME_STATE_NONE;
    if (device.isBlank()) {
      device = TEXT_RUNTIME_STATE_NONE;
    }
    sb.append(TEXT_RUNTIME_STATE_DEVICE_FIELD_PREFIX)
        .append(device)
        .append(TEXT_RUNTIME_STATE_DEVICE_ENABLED_PREFIX)
        .append(
            selectedDevice.has(JSON_KEY_ENABLED)
                ? selectedDevice.get(JSON_KEY_ENABLED).getAsString()
                : TEXT_RUNTIME_STATE_NONE)
        .append('\n');
  }

  /**
   * NAME
   *   appendRuntimeStateDevices - Append runtime-state device summary.
   */
  private void appendRuntimeStateDevices(StringBuilder sb, JsonArray devices) {
    sb.append(TEXT_RUNTIME_STATE_DEVICES).append('\n');
    if (devices == null || devices.size() == 0) {
      sb.append("  ").append(TEXT_RUNTIME_STATE_NONE).append('\n');
      return;
    }
    for (int i = 0; i < devices.size(); i++) {
      JsonObject device = devices.get(i).getAsJsonObject();
      sb.append("  ")
          .append(device.get(JSON_KEY_LABEL).getAsString())
          .append(TEXT_RUNTIME_STATE_VENDOR_PREFIX)
          .append(device.get(JSON_KEY_VENDOR).getAsString())
          .append(TEXT_RUNTIME_STATE_TYPE_PREFIX)
          .append(device.get(JSON_KEY_TYPE).getAsString())
          .append(TEXT_RUNTIME_STATE_ID_PREFIX)
          .append(device.get(JSON_KEY_ID).getAsString())
          .append(TEXT_RUNTIME_STATE_INSTANTIATED_PREFIX)
          .append(device.get(JSON_KEY_INSTANTIATED).getAsString())
          .append(TEXT_RUNTIME_STATE_LIFECYCLE_PREFIX)
          .append(device.get(JSON_KEY_LIFECYCLE_STATE).getAsString())
          .append(TEXT_RUNTIME_STATE_TESTABLE_PREFIX)
          .append(device.get(JSON_KEY_TESTABLE).getAsString())
          .append(TEXT_RUNTIME_STATE_PRESENCE_PREFIX)
          .append(device.get(JSON_KEY_PRESENCE_CONFIDENCE).getAsString())
          .append('\n');
    }
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
      obj.addProperty(JSON_KEY_TESTS_RUNNABLE_NOW, row.runnableNow);
      obj.addProperty(
          JSON_KEY_TESTS_BLOCKED_REASON,
          row.blockedReason != null ? row.blockedReason : TEXT_EMPTY);
      JsonArray requiredDevices = new JsonArray();
      if (row.requiredDevices != null) {
        for (String label : row.requiredDevices) {
          if (label != null && !label.isBlank()) {
            requiredDevices.add(label);
          }
        }
      }
      obj.add(JSON_KEY_TESTS_REQUIRED_DEVICES, requiredDevices);
      rows.add(obj);
    }
    root.add(JSON_KEY_TESTS_ROWS, rows);
    return root;
  }

  /**
   * NAME
   *   buildTestsStateJson - Build the authoritative tests-state JSON payload.
   *
   * RETURNS
   *   JSON payload containing current selection, run state, and rows.
   */
  public JsonObject buildTestsStateJson() {
    return buildTestsOverviewJson(core().buildTestsOverview());
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
    obj.add(JSON_KEY_RUN_DETAILS, snapshot.details != null ? snapshot.details.deepCopy() : new JsonObject());
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
    var lifecycleRuntime = runtime.getControlledBringupLifecycleRuntime();
    boolean controlledLifecycleActive = isControlledLifecycleActive();
    String selectedLabel = bridgeSelected().device != null
        ? bridgeSelected().device.trim().toLowerCase()
        : TEXT_EMPTY;
    List<DeviceSnapshot> snapshots = core() != null
        ? core().captureSnapshots(SnapshotDetail.LIGHT)
        : new ArrayList<>();
    Map<String, DeviceSnapshot> byLabel = new HashMap<>();
    Map<Integer, DeviceSnapshot> byId = new HashMap<>();
    for (DeviceSnapshot snap : snapshots) {
      if (snap == null) {
        continue;
      }
      if (snap.label != null && !snap.label.isBlank()) {
        String labelKey = snap.label.trim().toLowerCase();
        DeviceSnapshot existing = byLabel.get(labelKey);
        byLabel.put(labelKey, choosePreferredSnapshot(existing, snap));
      }
      if (snap.canId >= 0) {
        DeviceSnapshot existing = byId.get(snap.canId);
        byId.put(snap.canId, choosePreferredSnapshot(existing, snap));
      }
    }
    if (!selectedLabel.isBlank() && core() != null) {
      DeviceSnapshot selectedSnapshot =
          core().captureSnapshotForLabel(bridgeSelected().device, SnapshotDetail.FULL);
      if (selectedSnapshot != null
          && selectedSnapshot.label != null
          && !selectedSnapshot.label.isBlank()) {
        String labelKey = selectedSnapshot.label.trim().toLowerCase();
        DeviceSnapshot existing = byLabel.get(labelKey);
        byLabel.put(labelKey, choosePreferredSnapshot(existing, selectedSnapshot));
        if (selectedSnapshot.canId >= 0) {
          DeviceSnapshot existingById = byId.get(selectedSnapshot.canId);
          byId.put(
              selectedSnapshot.canId,
              choosePreferredSnapshot(existingById, selectedSnapshot));
        }
      }
    }

    JsonArray array = new JsonArray();
    java.util.HashSet<String> emitted = new java.util.HashSet<>();
    List<BringupUtil.DeviceEntry> runtimeDevices = BringupUtil.isProfileActive()
        ? BringupUtil.getActiveDevicesSorted()
        : BringupUtil.getSelectedDevicesSorted();
    for (BringupUtil.DeviceEntry entry : runtimeDevices) {
      if (entry == null) {
        continue;
      }
      String entryKey = runtimeStateDeviceKey(entry);
      if (!emitted.add(entryKey)) {
        continue;
      }
      JsonObject obj = new JsonObject();
      obj.addProperty(JSON_KEY_LABEL, entry.label);
      obj.addProperty(JSON_KEY_VENDOR, entry.vendor);
      obj.addProperty(JSON_KEY_TYPE, entry.type);
      obj.addProperty(JSON_KEY_ID, entry.id);
      DeviceLifecycleRegistry.DeviceLifecycleView lifecycle =
          runtime.getDeviceLifecycle().viewForLabel(entry.label);
      frc.robot.diag.lifecycle.runtime.DeviceRuntimeState controlledState =
          controlledLifecycleRuntimeStateForLabel(lifecycleRuntime, entry.label);
      boolean controlledActive = controlledState != null && controlledState.isActive();

      DeviceSnapshot snap = null;
      if (entry.label != null) {
        snap = byLabel.get(entry.label.trim().toLowerCase());
      }
      if (snap == null && entry.id >= 0) {
        snap = byId.get(entry.id);
      }
      boolean controlledInstantiated =
          controlledState != null && controlledState.isInstantiated();
      obj.addProperty(
          JSON_KEY_INSTANTIATED,
          controlledInstantiated
              || (lifecycle != null ? lifecycle.lifecycleState.startsWith("instantiated") : snap != null));
      if (lifecycle != null) {
        obj.addProperty(JSON_KEY_PRESENCE_CONF, lifecycle.presenceScore);
        obj.addProperty(JSON_KEY_LIFECYCLE_STATE, lifecycle.lifecycleState);
        obj.addProperty(JSON_KEY_TESTABLE, lifecycle.testable);
        obj.addProperty(JSON_KEY_OVERRIDE_ACTIVE, lifecycle.overrideActive);
        obj.addProperty(JSON_KEY_OVERRIDE_ORIGINATED, lifecycle.overrideOriginated);
        obj.addProperty(JSON_KEY_OVERRIDE_FAILURE, lifecycle.overrideFailure);
        obj.addProperty(JSON_KEY_LAST_EVENT, lifecycle.lastEvent);
        obj.addProperty(JSON_KEY_LAST_TRANSITION_TIME_MS, lifecycle.lastTransitionTimeMs);
        obj.addProperty(JSON_KEY_NOT_TESTABLE_REASON, lifecycle.notTestableReason);
      }
      applyControlledLifecycleRuntimeFields(obj, controlledState, lifecycle, nowMs);
      if (controlledLifecycleActive && !controlledActive) {
        obj.addProperty(JSON_KEY_TESTABLE, false);
        obj.addProperty(
            JSON_KEY_NOT_TESTABLE_REASON,
            TEXT_CONTROLLED_LIFECYCLE_SCOPE_REQUIRED_REASON);
      }
      if (snap != null) {
        if (lifecycle == null) {
          obj.addProperty(JSON_KEY_PRESENCE_CONF, snap.present ? 1.0 : 0.0);
        }
        if (snap.present || (lifecycle != null && lifecycle.presenceScore > 0.0)) {
          obj.addProperty(JSON_KEY_LAST_SEEN_MS, nowMs);
        }
        if (snap.attachments != null && !snap.attachments.isEmpty()) {
          obj.add(JSON_KEY_ATTACHMENTS, GSON.toJsonTree(snap.attachments));
        }
        applySampledSignalFields(obj, snap.getAttachment(SampledSignalsAttachment.class));
        RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
        if (rev != null) {
          if (rev.busV != null) {
            obj.addProperty(JSON_KEY_BUS_V, rev.busV);
          }
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
          if (rev.positionRot != null) {
            obj.addProperty(JSON_KEY_POSITION_ROT, rev.positionRot);
          }
          if (rev.tempC != null) {
            obj.addProperty(JSON_KEY_TEMP_C, rev.tempC);
          }
          if (rev.lastError != null && !rev.lastError.isBlank()) {
            obj.addProperty(JSON_KEY_LAST_ERROR, rev.lastError);
          }
          obj.addProperty(JSON_KEY_FAULTS_RAW, rev.faultsRaw);
          obj.addProperty(JSON_KEY_STICKY_FAULTS_RAW, rev.stickyFaultsRaw);
          obj.addProperty(JSON_KEY_WARNINGS_RAW, rev.warningsRaw);
          obj.addProperty(JSON_KEY_STICKY_WARNINGS_RAW, rev.stickyWarningsRaw);
          obj.addProperty(JSON_KEY_IS_FOLLOWER, rev.follower);
        }
        CtreMotorAttachment ctre = snap.getAttachment(CtreMotorAttachment.class);
        if (ctre != null) {
          if (ctre.motorCurrentA != null) {
            obj.addProperty(JSON_KEY_MOTOR_CURRENT_A, ctre.motorCurrentA);
          }
          if (ctre.cmdDuty != null) {
            obj.addProperty(JSON_KEY_CMD_DUTY, ctre.cmdDuty);
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
          if (ctre.positionRot != null) {
            obj.addProperty(JSON_KEY_POSITION_ROT, ctre.positionRot);
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

  private frc.robot.diag.lifecycle.runtime.DeviceRuntimeState controlledLifecycleRuntimeStateForLabel(
      frc.robot.diag.lifecycle.integration.ControlledBringupLifecycleRuntime lifecycleRuntime,
      String label) {
    if (lifecycleRuntime == null || label == null || label.isBlank()) {
      return null;
    }
    try {
      return lifecycleRuntime.catalogBundle().deviceCatalog().runtimeState(label);
    } catch (IllegalArgumentException ex) {
      return null;
    }
  }

  private void applyControlledLifecycleRuntimeFields(
      JsonObject obj,
      frc.robot.diag.lifecycle.runtime.DeviceRuntimeState controlledState,
      DeviceLifecycleRegistry.DeviceLifecycleView lifecycle,
      long nowMs) {
    if (obj == null || controlledState == null) {
      return;
    }
    boolean controlledActive = controlledState.isActive();
    boolean controlledInstantiated = controlledState.isInstantiated();
    String controlledError = controlledState.lastError();
    boolean hasControlledLifecycle =
        controlledActive
            || controlledInstantiated
            || (controlledError != null && !controlledError.isBlank());
    if (!hasControlledLifecycle) {
      return;
    }

    obj.addProperty(JSON_KEY_INSTANTIATED, controlledInstantiated);
    obj.addProperty(
        JSON_KEY_LIFECYCLE_STATE,
        controlledActive
            ? TEXT_CONTROLLED_LIFECYCLE_ACTIVE
            : controlledInstantiated
                ? TEXT_CONTROLLED_LIFECYCLE_INSTANTIATED
                : TEXT_CONTROLLED_LIFECYCLE_FAILED);
    obj.addProperty(JSON_KEY_TESTABLE, controlledActive);
    obj.addProperty(JSON_KEY_OVERRIDE_ACTIVE, false);
    obj.addProperty(JSON_KEY_OVERRIDE_ORIGINATED, false);
    obj.addProperty(JSON_KEY_OVERRIDE_FAILURE, false);
    obj.addProperty(
        JSON_KEY_LAST_EVENT,
        controlledActive
            ? TEXT_CONTROLLED_LIFECYCLE_ACTIVE_EVENT
            : TEXT_CONTROLLED_LIFECYCLE_FAILED_EVENT);
    if (lifecycle == null) {
      obj.addProperty(JSON_KEY_LAST_TRANSITION_TIME_MS, nowMs);
    }
    obj.addProperty(
        JSON_KEY_NOT_TESTABLE_REASON,
        controlledActive
            ? TEXT_CONTROLLED_LIFECYCLE_TESTABLE_REASON
            : TEXT_CONTROLLED_LIFECYCLE_INSTANTIATED_REASON);
    obj.addProperty(JSON_KEY_ACTIVE_SESSION_ID, safeText(controlledState.activeSessionId()));
    obj.addProperty(JSON_KEY_ACTIVE_GROUP_LABEL, safeText(controlledState.activeGroupLabel()));
    obj.addProperty(
        JSON_KEY_LAST_ACTIVATION_MODE, safeText(controlledState.lastActivationMode()));
    obj.addProperty(JSON_KEY_LAST_ERROR, safeText(controlledError));
    if (controlledInstantiated) {
      obj.addProperty(JSON_KEY_LAST_SEEN_MS, nowMs);
    }
  }

  private String safeText(String value) {
    return value != null ? value : TEXT_EMPTY;
  }

  /**
   * NAME
   *   applySampledSignalFields - Flatten generic sampled telemetry into runtime-state fields.
   */
  private void applySampledSignalFields(JsonObject obj, SampledSignalsAttachment sampled) {
    if (obj == null || sampled == null || sampled.signals == null) {
      return;
    }
    SampledSignalSummary current = findSampledSignal(sampled, SampledSignalNames.CURRENT_ACTUAL);
    if (current == null) {
      return;
    }
    if (current.instantValue != null) {
      obj.addProperty(JSON_KEY_CURRENT_INSTANT_A, current.instantValue);
    }
    if (current.avgValue != null) {
      obj.addProperty(JSON_KEY_CURRENT_AVG_A, current.avgValue);
    }
    if (current.peakValue != null) {
      obj.addProperty(JSON_KEY_CURRENT_PEAK_A, current.peakValue);
    }
    if (current.nonzeroRatio != null) {
      obj.addProperty(JSON_KEY_CURRENT_NONZERO_RATIO, current.nonzeroRatio);
    }
    if (current.sampleCount != null) {
      obj.addProperty(JSON_KEY_CURRENT_SAMPLE_COUNT, current.sampleCount);
    }
  }

  /**
   * NAME
   *   findSampledSignal - Locate a sampled-signal summary by canonical name.
   */
  private SampledSignalSummary findSampledSignal(
      SampledSignalsAttachment sampled,
      String signalName) {
    if (sampled == null || sampled.signals == null || signalName == null || signalName.isBlank()) {
      return null;
    }
    for (SampledSignalSummary summary : sampled.signals) {
      if (summary == null || summary.signalName == null) {
        continue;
      }
      if (signalName.equals(summary.signalName)) {
        return summary;
      }
    }
    return null;
  }

  /**
   * NAME
   *   choosePreferredSnapshot - Prefer the richer/live snapshot when duplicates exist.
   */
  private DeviceSnapshot choosePreferredSnapshot(DeviceSnapshot first, DeviceSnapshot second) {
    if (first == null) {
      return second;
    }
    if (second == null) {
      return first;
    }
    int firstScore = snapshotScore(first);
    int secondScore = snapshotScore(second);
    return secondScore >= firstScore ? second : first;
  }

  /**
   * NAME
   *   snapshotScore - Rank snapshots so present snapshots with telemetry win.
   */
  private int snapshotScore(DeviceSnapshot snapshot) {
    if (snapshot == null) {
      return Integer.MIN_VALUE;
    }
    int score = 0;
    if (snapshot.present) {
      score += 100;
    }
    if (snapshot.attachments != null) {
      score += snapshot.attachments.size() * 10;
    }
    if (snapshot.note == null || snapshot.note.isBlank()) {
      score += 1;
    }
    return score;
  }

  /**
   * NAME
   *   runtimeStateDeviceKey - Build a stable dedupe key for runtime-state devices.
   */
  private String runtimeStateDeviceKey(BringupUtil.DeviceEntry entry) {
    if (entry == null) {
      return "";
    }
    String label = entry.label != null ? entry.label.trim().toLowerCase() : "";
    String vendor = entry.vendor != null ? entry.vendor.trim().toLowerCase() : "";
    String type = entry.type != null ? entry.type.trim().toLowerCase() : "";
    return label + "|" + vendor + "|" + type + "|" + entry.id;
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
    BringupUtil.DeviceEntry entry = findDeviceEntryByLabel(label, BringupUtil.getActiveDevicesSorted());
    if (entry != null) {
      return entry;
    }
    return findDeviceEntryByLabel(label, BringupUtil.getSelectedDevicesSorted());
  }

  /**
   * NAME
   *   findDeviceEntryByLabel - Lookup one device entry by label from one candidate list.
   */
  private BringupUtil.DeviceEntry findDeviceEntryByLabel(
      String label,
      List<BringupUtil.DeviceEntry> devices) {
    if (label == null || label.isBlank() || devices == null || devices.isEmpty()) {
      return null;
    }
    String needle = label.trim();
    for (BringupUtil.DeviceEntry entry : devices) {
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
    ReportTextUtil.appendLine(
        sb, BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_REVISION, BuildInfo.BUILD_REVISION));
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
    ReportTextUtil.appendLine(
        sb, BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_REVISION, BuildInfo.BUILD_REVISION));
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
    ReportTextUtil.appendLine(
        sb, BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_REVISION, BuildInfo.BUILD_REVISION));
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
   *   formatProfileValue - Render empty profile state values consistently.
   */
  private String formatProfileValue(String value) {
    if (value == null || value.isBlank()) {
      return TEXT_NONE;
    }
    return value;
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
    ReportTextUtil.appendLine(
        sb, BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_REVISION, BuildInfo.BUILD_REVISION));
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
      if (entry == null) {
        continue;
      }
      String vendor = entry.vendor != null ? entry.vendor.trim() : "";
      String type = entry.type != null ? entry.type.trim() : "";
      String addressLabel = BringupUtil.summaryAddressLabelForInterface(entry.deviceInterface);
      String key =
          (vendor.isEmpty() ? "UNKNOWN" : vendor)
              + " "
              + (type.isEmpty() ? "Device" : type)
              + " "
              + addressLabel;
      String deviceInterface = entry.deviceInterface != null ? entry.deviceInterface.trim() : "";
      if (deviceInterface.isBlank() || !BringupUtil.isEnabledDeviceAddress(entry.id)) {
        continue;
      }
      groups.computeIfAbsent(key, ignored -> new ArrayList<>()).add(entry.id);
    }
    for (Map.Entry<String, List<Integer>> entry : groups.entrySet()) {
      List<Integer> addresses = entry.getValue();
      if (addresses.isEmpty()) {
        continue;
      }
      StringBuilder line = new StringBuilder();
      for (int i = 0; i < addresses.size(); i++) {
        if (i > 0) {
          line.append(", ");
        }
        line.append(addresses.get(i));
      }
      ReportTextUtil.appendLine(sb, entry.getKey() + ": " + line);
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
   *   Enqueues a text report for the supported host/UI output path.
   */
  public String printTestsOverview() {
    BringupCore.TestsOverview overview = core().buildTestsOverview();
    String text = core().formatTestsOverview(overview);
    runtime.requestTextReport(text, 6);
    return text;
  }

  /**
   * NAME
   *   printSelectedTestSource - Emit the stored DSL source for the selected test.
   *
   * RETURNS
   *   Full selected-test source report text.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  public String printSelectedTestSource() {
    String text = core().buildSelectedTestSourceReportText();
    runtime.requestTextReport(text, 4);
    return text;
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
