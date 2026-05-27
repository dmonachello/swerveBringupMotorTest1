package frc.robot.commands.local;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * NAME
 *   RobotLocalCommandRegistry - Canonical Java source of truth for local commands.
 *
 * DESCRIPTION
 *   Holds the command definition table used by bindings validation, generic
 *   lookup, executor dispatch, and generated host-UI artifacts.
 */
public final class RobotLocalCommandRegistry {
  private static final String JSON_KEY_NAME = "name";
  private static final String JSON_KEY_GROUP = "group";
  private static final String JSON_KEY_INVOCATION_KIND = "invocationKind";
  private static final String JSON_KEY_CONTROLLER_ALLOWED = "controllerAllowed";
  private static final String JSON_KEY_HOST_UI_ALLOWED = "hostUiAllowed";
  private static final String JSON_KEY_AUTO_STOP_ON_SOURCE_LOSS = "autoStopOnSourceLoss";
  private static final String JSON_KEY_SHOW_IN_HOST_UI = "showInHostUi";
  private static final String JSON_KEY_UI_SECTION = "uiSection";
  private static final String JSON_KEY_UI_LABEL = "uiLabel";
  private static final String JSON_KEY_UI_DESCRIPTION = "uiDescription";
  private static final String JSON_KEY_UI_ARGS_JSON = "uiArgsJson";
  private static final String JSON_KEY_COMMANDS = "commands";
  private static final String UI_SECTION_PROFILES = "Profiles";
  private static final String UI_SECTION_REPORTS = "Reports";
  private static final String UI_SECTION_TESTS = "Scriptable Tests";
  private static final String UI_SECTION_DIAGNOSTICS = "Diagnostics";
  private static final String UI_SECTION_SYSTEM = "System";
  private static final String UI_SECTION_SESSION = "Session";
  private static final String UI_SECTION_GROUPS = "Groups";
  private static final String UI_ARG_RESET_TRUE = "{\"reset\":true}";

  public static final String COMMAND_ADD_MOTOR = "addMotor";
  public static final String COMMAND_ADD_ALL = "addAll";
  public static final String COMMAND_GENERIC_CMD = "genericCmd";
  public static final String COMMAND_CLEAR_FAULTS = "clearFaults";
  public static final String COMMAND_CLEAR_STOP_LATCH = "clearStopLatch";
  public static final String COMMAND_CAN_SWEEP = "canSweep";
  public static final String COMMAND_TOGGLE_DASHBOARD = "toggleDashboard";
  public static final String COMMAND_PROFILE_TOGGLE = "profileToggle";
  public static final String COMMAND_STOP = "stopCommand";
  public static final String COMMAND_PRINT_STATE = "printState";
  public static final String COMMAND_PRINT_SUMMARY = "printSummary";
  public static final String COMMAND_PRINT_HEALTH = "printHealth";
  public static final String COMMAND_PRINT_CANCODER = "printCANcoder";
  public static final String COMMAND_PRINT_INPUTS = "printInputs";
  public static final String COMMAND_PRINT_BINDINGS = "printBindings";
  public static final String COMMAND_PRINT_PROFILE_DEVICES = "printProfileDevices";
  public static final String COMMAND_PRINT_NT_DIAG = "printNTdiag";
  public static final String COMMAND_PRINT_CAN_DIAG = "printCANdiag";
  public static final String COMMAND_DUMP_REPORT = "dumpReport";
  public static final String COMMAND_PRINT_TESTS_INFO = "printTestsInfo";
  public static final String COMMAND_PRINT_TESTS_OVERVIEW = "printTestsOverview";
  public static final String COMMAND_PRINT_NEXT_TEST = "printNextTest";
  public static final String COMMAND_SHOW_STATUS = "showStatus";
  public static final String COMMAND_SHOW_VERSION = "showVersion";
  public static final String COMMAND_SHOW_SOURCES = "showSources";
  public static final String COMMAND_SELECT_TEST_PREV = "selectTestPrev";
  public static final String COMMAND_SELECT_TEST_NEXT = "selectTestNext";
  public static final String COMMAND_TOGGLE_TEST = "toggleTest";
  public static final String COMMAND_RUN_TEST = "runTest";
  public static final String COMMAND_RUN_ALL_TESTS = "runAllTests";
  public static final String COMMAND_SELECT_TEST_BY_NAME = "selectTestByName";
  public static final String COMMAND_SHOW_TESTS = "showTests";
  public static final String COMMAND_SELECT_PROFILE = "selectProfile";
  public static final String COMMAND_PROFILE_ACTIVATE = "profileActivate";
  public static final String COMMAND_RUNTIME_ACTIVATE = "runtimeActivate";
  public static final String COMMAND_RUNTIME_DEACTIVATE = "runtimeDeactivate";
  public static final String COMMAND_PROFILES_RELOAD = "profilesReload";
  public static final String COMMAND_PROFILES_APPLY = "profilesApply";
  public static final String COMMAND_SHOW_PROFILES = "showProfiles";
  public static final String COMMAND_SHOW_PROFILE = "showProfile";
  public static final String COMMAND_UI_PING = "uiPing";
  public static final String COMMAND_UI_HANDSHAKE = "uiHandshake";
  public static final String COMMAND_UI_DISCONNECT = "uiDisconnect";
  public static final String COMMAND_UI_MONITOR_ENABLE = "uiMonitorEnable";
  public static final String COMMAND_UI_MONITOR_DISABLE = "uiMonitorDisable";
  public static final String COMMAND_UI_POLL_LOG = "uiPollLog";
  public static final String COMMAND_ACTIVE_ADD = "activeAdd";
  public static final String COMMAND_ACTIVE_NEXT = "activeNext";
  public static final String COMMAND_SHOW_GROUPS = "showGroups";
  public static final String COMMAND_SHOW_GROUP = "showGroup";
  public static final String COMMAND_SHOW_DEVICES = "showDevices";
  public static final String COMMAND_SHOW_DEVICE = "showDevice";
  public static final String COMMAND_SHOW_BINDINGS = "showBindings";
  public static final String COMMAND_SHOW_SELECTED_DEVICE = "showSelectedDevice";
  public static final String COMMAND_SHOW_RUNTIME_STATE = "showRuntimeState";
  public static final String COMMAND_GROUP_CREATE = "groupCreate";
  public static final String COMMAND_GROUP_DELETE = "groupDelete";
  public static final String COMMAND_GROUP_ADD_DEVICE = "groupAddDevice";
  public static final String COMMAND_GROUP_REMOVE_DEVICE = "groupRemoveDevice";
  public static final String COMMAND_GROUP_MEMBER_ENABLE = "groupMemberEnable";
  public static final String COMMAND_GROUP_MEMBER_DISABLE = "groupMemberDisable";
  public static final String COMMAND_GROUP_MEMBER_TOGGLE = "groupMemberToggle";
  public static final String COMMAND_GROUP_BIND = "groupBind";
  public static final String COMMAND_GROUP_UNBIND = "groupUnbind";
  public static final String COMMAND_GROUP_ENABLE = "groupEnable";
  public static final String COMMAND_GROUP_DISABLE = "groupDisable";
  public static final String COMMAND_GROUP_RUN_TEST = "groupRunTest";
  public static final String COMMAND_SELECTED_DEVICE_SET = "selectedDeviceSet";
  public static final String COMMAND_SELECTED_MODE_SET = "selectedModeSet";
  public static final String COMMAND_MANUAL_DEVICE_DUTY_SET = "manualDeviceDutySet";
  public static final String COMMAND_MANUAL_DEVICE_DUTY_CLEAR = "manualDeviceDutyClear";
  public static final String COMMAND_LEFT_DRIVE = "leftDrive";
  public static final String COMMAND_RIGHT_DRIVE = "rightDrive";

  private static final Map<String, RobotLocalCommandDefinition> DEFINITIONS = buildDefinitions();
  private static final Set<String> AXIS_COMMANDS =
      Set.of(COMMAND_LEFT_DRIVE, COMMAND_RIGHT_DRIVE);

  private RobotLocalCommandRegistry() {}

  public static Set<String> commandNames() {
    return DEFINITIONS.keySet();
  }

  public static Set<String> axisCommandNames() {
    return AXIS_COMMANDS;
  }

  public static boolean isKnownCommand(String commandName) {
    return commandName != null && DEFINITIONS.containsKey(commandName);
  }

  public static boolean isKnownAxisCommand(String commandName) {
    return commandName != null && AXIS_COMMANDS.contains(commandName);
  }

  public static RobotLocalCommandDefinition definition(String commandName) {
    return commandName != null ? DEFINITIONS.get(commandName) : null;
  }

  public static JsonObject buildInventoryJson() {
    JsonObject root = new JsonObject();
    JsonArray commands = new JsonArray();
    for (RobotLocalCommandDefinition definition : DEFINITIONS.values()) {
      JsonObject row = new JsonObject();
      row.addProperty(JSON_KEY_NAME, definition.wireName());
      row.addProperty(JSON_KEY_GROUP, definition.group().name());
      row.addProperty(JSON_KEY_INVOCATION_KIND, definition.invocationKind().name());
      row.addProperty(JSON_KEY_CONTROLLER_ALLOWED, definition.controllerAllowed());
      row.addProperty(JSON_KEY_HOST_UI_ALLOWED, definition.hostUiAllowed());
      row.addProperty(JSON_KEY_AUTO_STOP_ON_SOURCE_LOSS, definition.autoStopOnSourceLoss());
      row.addProperty(JSON_KEY_SHOW_IN_HOST_UI, definition.showInHostUi());
      row.addProperty(JSON_KEY_UI_SECTION, definition.uiSection());
      row.addProperty(JSON_KEY_UI_LABEL, definition.uiLabel());
      row.addProperty(JSON_KEY_UI_DESCRIPTION, definition.uiDescription());
      row.addProperty(JSON_KEY_UI_ARGS_JSON, definition.uiArgsJson());
      commands.add(row);
    }
    root.add(JSON_KEY_COMMANDS, commands);
    return root;
  }

  private static Map<String, RobotLocalCommandDefinition> buildDefinitions() {
    RobotLocalRuntimeCommandGroup runtimeGroup = new RobotLocalRuntimeCommandGroup();
    RobotLocalReportCommandGroup reportGroup = new RobotLocalReportCommandGroup();
    RobotLocalTestCommandGroup testGroup = new RobotLocalTestCommandGroup();
    RobotLocalLegacyUiCommandGroup legacyUiGroup = new RobotLocalLegacyUiCommandGroup();
    LinkedHashMap<String, RobotLocalCommandDefinition> rows = new LinkedHashMap<>();

    register(rows, runtimeDefinition(
        COMMAND_ADD_MOTOR,
        UI_SECTION_PROFILES,
        "Add Motor",
        "Instantiate the next configured motor on the robot.",
        true,
        true,
        runtimeGroup.addMotor()));
    register(rows, runtimeDefinition(
        COMMAND_ADD_ALL,
        UI_SECTION_PROFILES,
        "Add All Motors",
        "Instantiate all configured devices on the robot.",
        true,
        true,
        runtimeGroup.addAll()));
    register(rows, runtimeDefinition(
        COMMAND_GENERIC_CMD,
        "",
        "genericCmd",
        "Example controller/local command cloned from addAll.",
        false,
        false,
        runtimeGroup.genericCmd()));
    register(rows, runtimeDefinition(
        COMMAND_CLEAR_FAULTS,
        UI_SECTION_SYSTEM,
        "Clear Faults",
        "Clear sticky and current device faults.",
        true,
        false,
        runtimeGroup.clearFaults()));
    register(rows, new RobotLocalCommandDefinition(
        COMMAND_CLEAR_STOP_LATCH,
        RobotLocalCommandGroup.RUNTIME,
        RobotLocalInvocationKind.REMOTE,
        false,
        true,
        false,
        true,
        UI_SECTION_SYSTEM,
        "Clear Stop Latch",
        "Clear the active safety stop latch.",
        "",
        runtimeGroup.clearStopLatch()));
    register(rows, runtimeDefinition(
        COMMAND_CAN_SWEEP,
        UI_SECTION_DIAGNOSTICS,
        "CAN Sweep",
        "Run the vendor API CAN sweep report.",
        true,
        false,
        runtimeGroup.canSweep()));
    register(rows, runtimeDefinition(
        COMMAND_TOGGLE_DASHBOARD,
        UI_SECTION_SYSTEM,
        "Toggle Dashboard",
        "Toggle Shuffleboard/dashboard updates.",
        true,
        false,
        runtimeGroup.toggleDashboard()));
    register(rows, runtimeDefinition(
        COMMAND_PROFILE_TOGGLE,
        UI_SECTION_PROFILES,
        "Toggle Profile",
        "Select the next configured profile.",
        true,
        false,
        runtimeGroup.profileToggle()));
    register(rows, new RobotLocalCommandDefinition(
        COMMAND_STOP,
        RobotLocalCommandGroup.RUNTIME,
        RobotLocalInvocationKind.REMOTE,
        false,
        true,
        false,
        true,
        UI_SECTION_SYSTEM,
        "Stop Active Command",
        "Interrupt the active command and set the safety latch.",
        "",
        runtimeGroup.stop()));

    register(rows, reportDefinition(
        COMMAND_PRINT_STATE,
        "State",
        "Print current bringup state summary.",
        reportGroup.printState()));
    register(rows, reportDefinition(COMMAND_PRINT_HEALTH, "Health", "Print local device health snapshot.", reportGroup.printHealth()));
    register(rows, reportDefinition(COMMAND_PRINT_CANCODER, "CANcoder", "Print CANCoder telemetry report.", reportGroup.printCANcoder()));
    register(rows, reportDefinition(COMMAND_PRINT_INPUTS, "Inputs", "Print current controller input state.", reportGroup.printInputs()));
    register(rows, reportDefinition(COMMAND_PRINT_BINDINGS, "Bindings", "Print controller bindings and UI mappings.", reportGroup.printBindings()));
    register(rows, reportDefinition(COMMAND_PRINT_TESTS_INFO, "Tests Info", "Print current test selection details.", reportGroup.printTestsInfo()));
    register(rows, reportDefinition(COMMAND_PRINT_TESTS_OVERVIEW, "Tests Overview", "Print enabled/selected tests.", reportGroup.printTestsOverview()));
    register(rows, reportDefinition(COMMAND_PRINT_NEXT_TEST, "Print Next", "Print the selected test contract/report.", reportGroup.printNextTest()));
    register(rows, reportDefinition(COMMAND_PRINT_NT_DIAG, "NT Diagnostics", "Print NetworkTables diagnostics report.", reportGroup.printNtDiagnostics()));
    register(rows, reportDefinition(COMMAND_PRINT_CAN_DIAG, "CAN Bus", "Print CAN diagnostics report.", reportGroup.printCanDiagnostics()));
    register(rows, reportDefinition(COMMAND_DUMP_REPORT, "Dump", "Dump the JSON diagnostics report.", reportGroup.dumpReport()));
    register(rows, legacyReportDefinition(COMMAND_PRINT_SUMMARY, "Summary", "Print compact diagnostics summary.", legacyUiGroup));
    register(rows, legacyReportDefinition(COMMAND_PRINT_PROFILE_DEVICES, "Profile Devices", "Print active profile devices.", legacyUiGroup));
    register(rows, legacyReportDefinition(COMMAND_SHOW_STATUS, "Show Status", "Show runtime status payload.", legacyUiGroup));
    register(rows, legacyReportDefinition(COMMAND_SHOW_VERSION, "Show Version", "Show version/build metadata.", legacyUiGroup));
    register(rows, legacyReportDefinition(COMMAND_SHOW_SOURCES, "Show Sources", "Show active source file ownership.", legacyUiGroup));

    register(rows, testDefinition(COMMAND_SELECT_TEST_PREV, RobotLocalInvocationKind.BUTTON, "Test Prev", "Select previous test.", true, testGroup));
    register(rows, testDefinition(COMMAND_SELECT_TEST_NEXT, RobotLocalInvocationKind.BUTTON, "Test Next", "Select next test.", true, testGroup));
    register(rows, testDefinition(COMMAND_TOGGLE_TEST, RobotLocalInvocationKind.BUTTON, "Toggle Enabled", "Toggle selected test enabled state.", true, testGroup));
    register(rows, testDefinition(COMMAND_RUN_TEST, RobotLocalInvocationKind.HOLD, "Run Selected", "Run the selected test while active.", true, testGroup));
    register(rows, testDefinition(COMMAND_RUN_ALL_TESTS, RobotLocalInvocationKind.BUTTON, "Run All", "Run all enabled tests.", true, testGroup));
    register(rows, testDefinition(COMMAND_SELECT_TEST_BY_NAME, RobotLocalInvocationKind.REMOTE, "Select Test", "Select a test by name.", false, legacyUiGroup));
    register(rows, testDefinition(COMMAND_SHOW_TESTS, RobotLocalInvocationKind.REMOTE, "Show Tests", "Show tests payload.", false, legacyUiGroup));

    register(rows, profileDefinition(COMMAND_SELECT_PROFILE, "Select Profile", "Select a profile by name.", legacyUiGroup));
    register(rows, profileDefinition(COMMAND_PROFILE_ACTIVATE, "Activate Profile", "Activate the selected profile.", legacyUiGroup));
    register(rows, profileDefinition(COMMAND_RUNTIME_ACTIVATE, "Runtime Activate", "Activate the selected profile runtime.", legacyUiGroup));
    register(rows, profileDefinition(COMMAND_RUNTIME_DEACTIVATE, "Runtime Deactivate", "Deactivate the active runtime profile.", legacyUiGroup));
    register(rows, profileDefinition(COMMAND_PROFILES_RELOAD, "Reload Profiles", "Reload bringup_system.json on the robot.", legacyUiGroup));
    register(rows, profileDefinition(COMMAND_PROFILES_APPLY, "Apply Profiles", "Apply uploaded registry JSON on the robot.", legacyUiGroup));
    register(rows, profileDefinition(COMMAND_SHOW_PROFILES, "Show Profiles", "Show available profiles.", legacyUiGroup));
    register(rows, profileDefinition(COMMAND_SHOW_PROFILE, "Show Profile", "Show one profile and its devices.", legacyUiGroup));

    register(rows, sessionDefinition(COMMAND_UI_PING, "UI Ping", "Send UI keepalive ping.", "", false, legacyUiGroup));
    register(rows, sessionDefinition(COMMAND_UI_HANDSHAKE, "Reset UI Session", "Reset UI session handshake and sequence window.", UI_ARG_RESET_TRUE, true, legacyUiGroup));
    register(rows, sessionDefinition(COMMAND_UI_DISCONNECT, "Release UI Lock", "Release the active UI lock.", "", true, legacyUiGroup));
    register(rows, sessionDefinition(COMMAND_UI_MONITOR_ENABLE, "Protocol Monitor ON", "Enable UI protocol monitor publishing.", "", true, legacyUiGroup));
    register(rows, sessionDefinition(COMMAND_UI_MONITOR_DISABLE, "Protocol Monitor OFF", "Disable UI protocol monitor publishing.", "", true, legacyUiGroup));
    register(rows, sessionDefinition(COMMAND_UI_POLL_LOG, "Poll UI Log", "Drain pending UI protocol log lines.", "", false, legacyUiGroup));

    register(rows, groupDefinition(COMMAND_ACTIVE_ADD, "Active Add", "Add next ready device to active-group.", true, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_ACTIVE_NEXT, "Active Next", "Rotate active-group to next ready device.", true, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_SHOW_GROUPS, "Show Groups", "Show all groups.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_SHOW_GROUP, "Show Group", "Show one group.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_SHOW_DEVICES, "Show Devices", "Show devices list.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_SHOW_DEVICE, "Show Device", "Show one device.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_SHOW_BINDINGS, "Show Bindings", "Show runtime bindings.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_SHOW_SELECTED_DEVICE, "Show Selected Device", "Show selected device.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_SHOW_RUNTIME_STATE, "Show Runtime State", "Show runtime state payload.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_CREATE, "Group Create", "Create a group.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_DELETE, "Group Delete", "Delete a group.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_ADD_DEVICE, "Group Add Device", "Add a device to a group.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_REMOVE_DEVICE, "Group Remove Device", "Remove a device from a group.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_MEMBER_ENABLE, "Enable Member", "Enable a group member.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_MEMBER_DISABLE, "Disable Member", "Disable a group member.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_MEMBER_TOGGLE, "Toggle Member", "Toggle a group member.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_BIND, "Group Bind", "Bind a controller input to a group.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_UNBIND, "Group Unbind", "Remove group bindings.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_ENABLE, "Enable Group", "Enable a group.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_DISABLE, "Disable Group", "Disable a group.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_GROUP_RUN_TEST, "Run Group Test", "Run the group test operation.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_SELECTED_DEVICE_SET, "Selected Device", "Set selected device.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_SELECTED_MODE_SET, "Selected Mode", "Toggle selected-device mode.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_MANUAL_DEVICE_DUTY_SET, "Manual Device Duty Set", "Apply manual duty to one device.", false, legacyUiGroup));
    register(rows, groupDefinition(COMMAND_MANUAL_DEVICE_DUTY_CLEAR, "Manual Device Duty Clear", "Clear manual duty for one device.", false, legacyUiGroup));

    register(rows, axisDefinition(COMMAND_LEFT_DRIVE));
    register(rows, axisDefinition(COMMAND_RIGHT_DRIVE));

    return Collections.unmodifiableMap(new LinkedHashMap<>(rows));
  }

  private static RobotLocalCommandDefinition runtimeDefinition(
      String wireName,
      String uiSection,
      String label,
      String description,
      boolean showInUi,
      boolean hostUiAllowed,
      RobotLocalCommand command) {
    return new RobotLocalCommandDefinition(
        wireName,
        RobotLocalCommandGroup.RUNTIME,
        RobotLocalInvocationKind.BUTTON,
        true,
        hostUiAllowed,
        false,
        showInUi,
        showInUi ? uiSection : "",
        label,
        description,
        "",
        command);
  }

  private static RobotLocalCommandDefinition reportDefinition(
      String wireName,
      String label,
      String description,
      RobotLocalCommand command) {
    return new RobotLocalCommandDefinition(
        wireName,
        RobotLocalCommandGroup.REPORT,
        RobotLocalInvocationKind.BUTTON,
        true,
        true,
        false,
        true,
        UI_SECTION_REPORTS,
        label,
        description,
        "",
        command);
  }

  private static RobotLocalCommandDefinition legacyReportDefinition(
      String wireName,
      String label,
      String description,
      RobotLocalCommand command) {
    return new RobotLocalCommandDefinition(
        wireName,
        RobotLocalCommandGroup.REPORT,
        RobotLocalInvocationKind.BUTTON,
        true,
        true,
        false,
        true,
        UI_SECTION_REPORTS,
        label,
        description,
        "",
        command);
  }

  private static RobotLocalCommandDefinition testDefinition(
      String wireName,
      RobotLocalInvocationKind invocationKind,
      String label,
      String description,
      boolean showInUi,
      RobotLocalCommand command) {
    return new RobotLocalCommandDefinition(
        wireName,
        RobotLocalCommandGroup.TEST,
        invocationKind,
        true,
        true,
        COMMAND_RUN_TEST.equals(wireName),
        showInUi,
        UI_SECTION_TESTS,
        label,
        description,
        "",
        command);
  }

  private static RobotLocalCommandDefinition profileDefinition(
      String wireName,
      String label,
      String description,
      RobotLocalCommand command) {
    return new RobotLocalCommandDefinition(
        wireName,
        RobotLocalCommandGroup.PROFILE,
        RobotLocalInvocationKind.REMOTE,
        false,
        true,
        false,
        false,
        UI_SECTION_PROFILES,
        label,
        description,
        "",
        command);
  }

  private static RobotLocalCommandDefinition sessionDefinition(
      String wireName,
      String label,
      String description,
      String argsJson,
      boolean showInUi,
      RobotLocalCommand command) {
    return new RobotLocalCommandDefinition(
        wireName,
        RobotLocalCommandGroup.SESSION,
        RobotLocalInvocationKind.REMOTE,
        false,
        true,
        false,
        showInUi,
        UI_SECTION_SESSION,
        label,
        description,
        argsJson,
        command);
  }

  private static RobotLocalCommandDefinition groupDefinition(
      String wireName,
      String label,
      String description,
      boolean showInUi,
      RobotLocalCommand command) {
    return new RobotLocalCommandDefinition(
        wireName,
        RobotLocalCommandGroup.GROUP,
        RobotLocalInvocationKind.REMOTE,
        false,
        true,
        false,
        showInUi,
        UI_SECTION_GROUPS,
        label,
        description,
        "",
        command);
  }

  private static RobotLocalCommandDefinition axisDefinition(String wireName) {
    return new RobotLocalCommandDefinition(
        wireName,
        RobotLocalCommandGroup.RUNTIME,
        RobotLocalInvocationKind.AXIS_VALUE,
        true,
        false,
        false,
        false,
        "",
        wireName,
        "Axis-valued controller input used by active commands.",
        "",
        new RobotLocalLegacyUiCommandGroup());
  }

  private static void register(
      Map<String, RobotLocalCommandDefinition> rows,
      RobotLocalCommandDefinition definition) {
    rows.put(definition.wireName(), definition);
  }
}
