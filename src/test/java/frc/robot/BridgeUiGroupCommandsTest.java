package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class BridgeUiGroupCommandsTest {

  private static final String EMPTY = "";
  private static final String CMD_SHOW_GROUP = "showGroup";
  private static final String CMD_GROUP_CREATE = "groupCreate";
  private static final String CMD_GROUP_DELETE = "groupDelete";
  private static final String CMD_GROUP_ADD_DEVICE = "groupAddDevice";
  private static final String CMD_GROUP_REMOVE_DEVICE = "groupRemoveDevice";
  private static final String CMD_GROUP_REPLACE_MEMBERS = "groupReplaceMembers";
  private static final String CMD_SHOW_DEVICE = "showDevice";
  private static final String CMD_SHOW_GROUPS = "showGroups";
  private static final String CMD_SHOW_RUNTIME_STATE = "showRuntimeState";
  private static final String CMD_MANUAL_DEVICE_DUTY_SET = "manualDeviceDutySet";
  private static final String CMD_MANUAL_DEVICE_DUTY_CLEAR = "manualDeviceDutyClear";
  private static final String CMD_MANUAL_GROUP_DUTY_SET = "manualGroupDutySet";
  private static final String CMD_MANUAL_GROUP_DUTY_CLEAR = "manualGroupDutyClear";
  private static final String KEY_GROUP = "group";
  private static final String KEY_DEVICE = "device";

  private static final String KEY_NAME = "name";
  private static final String KEY_CONFIRM = "confirm";
  private static final String KEY_JSON = "json";
  private static final String KEY_DUTY = "duty";

  private static final String MSG_SHOW_GROUP_REQUIRES = "showGroup requires args.name.";
  private static final String MSG_GROUP_NOT_FOUND_PREFIX = "Group not found: ";
  private static final String MSG_GROUP_CREATED_PREFIX = "Group created: ";
  private static final String MSG_GROUP_EXISTS_PREFIX = "Group already exists: ";
  private static final String MSG_GROUP_DELETE_CONFIRM = "groupDelete requires confirm=true.";
  private static final String MSG_GROUP_REPLACE_REQUIRES_GROUP =
      "groupReplaceMembers requires args.group.";
  private static final String MSG_SHOW_DEVICE_REQUIRES = "showDevice requires args.name.";
  private static final String MSG_DEVICE_NOT_FOUND_PREFIX = "Device not found: ";
  private static final String MSG_MANUAL_DUTY_SCOPE_BLOCKED =
      "Manual duty blocked: device is outside the active scope membership.";
  private static final String MSG_MANUAL_GROUP_DUTY_SCOPE_BLOCKED =
      "Manual duty blocked: group contains device(s) outside the active scope membership.";
  private static final String MSG_ACTIVE_GROUP_LOCKED =
      "Active group membership is locked while an active scope session is running. Deactivate scope first.";

  private static final String GROUP_ALPHA = "alpha";
  private static final String GROUP_ACTIVE = "active-group";
  private static final String GROUP_MOTORS = "motors";
  private static final String DEVICE_MOTOR_1 = "motor1";
  private static final int DUTY_TEST_ID = 3;
  private static final int DUTY_TEST_MFG = 5;
  private static final int DUTY_TEST_DEVICE_TYPE = 2;
  private static final String DUTY_TEST_VENDOR = "REV";
  private static final String DUTY_TEST_TYPE = "neo";
  private static final String DUTY_TEST_MOTOR = "NEO";
  private static final double DUTY_HALF = 0.5;

  @Test
  void showGroupRequiresName() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_SHOW_GROUP, new JsonObject()), 0.0, false);

    assertFalse(result.ok);
    assertEquals(MSG_SHOW_GROUP_REQUIRES, result.message);
  }

  @Test
  void showGroupReturnsNotFoundWhenMissing() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_NAME, GROUP_ALPHA);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_SHOW_GROUP, args), 0.0, false);

    assertFalse(result.ok);
    assertEquals(MSG_GROUP_NOT_FOUND_PREFIX + GROUP_ALPHA, result.message);
  }

  @Test
  void groupCreateCreatesMissingGroup() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_NAME, GROUP_ALPHA);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_GROUP_CREATE, args), 0.0, false);

    assertTrue(result.ok);
    assertEquals(MSG_GROUP_CREATED_PREFIX + GROUP_ALPHA, result.message);
    assertNotNull(deps.bridgeGroups.getGroup(GROUP_ALPHA));
  }

  @Test
  void groupCreateRejectsDuplicateGroup() {
    TestDeps deps = new TestDeps();
    deps.bridgeGroups.createGroup(GROUP_ALPHA);
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_NAME, GROUP_ALPHA);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_GROUP_CREATE, args), 0.0, false);

    assertFalse(result.ok);
    assertEquals(MSG_GROUP_EXISTS_PREFIX + GROUP_ALPHA, result.message);
  }

  @Test
  void groupDeleteRequiresConfirmTrue() {
    TestDeps deps = new TestDeps();
    deps.bridgeGroups.createGroup(GROUP_ALPHA);
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_NAME, GROUP_ALPHA);
    args.addProperty(KEY_CONFIRM, false);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_GROUP_DELETE, args), 0.0, false);

    assertFalse(result.ok);
    assertEquals(MSG_GROUP_DELETE_CONFIRM, result.message);
  }

  @Test
  void showDeviceRequiresName() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_SHOW_DEVICE, new JsonObject()), 0.0, false);

    assertFalse(result.ok);
    assertEquals(MSG_SHOW_DEVICE_REQUIRES, result.message);
  }

  @Test
  void showDeviceReturnsNotFoundWhenMissing() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_NAME, DEVICE_MOTOR_1);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_SHOW_DEVICE, args), 0.0, false);

    assertFalse(result.ok);
    assertEquals(MSG_DEVICE_NOT_FOUND_PREFIX + DEVICE_MOTOR_1, result.message);
  }

  @Test
  void showGroupsRoutesThroughApplyShowResult() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_JSON, true);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_SHOW_GROUPS, args), 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.applyShowCalled);
    assertTrue(deps.lastWantsJson);
    assertEquals(deps.expectedGroupsText, deps.lastShowText);
  }

  @Test
  void showRuntimeStateUsesRuntimeStateTextByDefault() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_SHOW_RUNTIME_STATE, new JsonObject()), 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.applyShowCalled);
    assertFalse(deps.lastWantsJson);
    assertEquals("runtimeStateText", deps.lastShowText);
    assertEquals("runtimeStateText", result.outText);
  }

  @Test
  void manualDeviceDutySetActivatesSelectedDevice() {
    TestDeps deps = new TestDeps();
    deps.deviceByLabel.put(
        DEVICE_MOTOR_1,
        new BringupUtil.DeviceEntry(
            DUTY_TEST_ID,
            DUTY_TEST_MFG,
            DUTY_TEST_DEVICE_TYPE,
            "CAN",
            DUTY_TEST_VENDOR,
            DUTY_TEST_TYPE,
            DEVICE_MOTOR_1,
            DUTY_TEST_MOTOR,
            null,
            null,
            null));
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_NAME, DEVICE_MOTOR_1);
    args.addProperty(KEY_DUTY, DUTY_HALF);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_DEVICE_DUTY_SET, args), 0.0, true);

    assertTrue(result.ok);
    assertEquals(DEVICE_MOTOR_1, deps.selected.device);
    assertTrue(deps.selected.enabled);
  }

  @Test
  void manualDeviceDutySetAllowsRightClickTestWhenRuntimeInactive() {
    TestDeps deps = new TestDeps();
    deps.runtimeActive = false;
    deps.deviceByLabel.put(
        DEVICE_MOTOR_1,
        new BringupUtil.DeviceEntry(
            DUTY_TEST_ID,
            DUTY_TEST_MFG,
            DUTY_TEST_DEVICE_TYPE,
            "CAN",
            DUTY_TEST_VENDOR,
            DUTY_TEST_TYPE,
            DEVICE_MOTOR_1,
            DUTY_TEST_MOTOR,
            null,
            null,
            null));
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_NAME, DEVICE_MOTOR_1);
    args.addProperty(KEY_DUTY, DUTY_HALF);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_DEVICE_DUTY_SET, args), 0.0, true);

    assertTrue(result.ok);
    assertEquals(DEVICE_MOTOR_1, deps.selected.device);
    assertTrue(deps.selected.enabled);
  }

  @Test
  void manualDeviceDutySetBlocksDeviceOutsideControlledLifecycleScope() {
    TestDeps deps = new TestDeps();
    deps.controlledLifecycleActive = true;
    deps.controlledLifecycleDeviceActiveByLabel.put(DEVICE_MOTOR_1, false);
    deps.deviceByLabel.put(
        DEVICE_MOTOR_1,
        new BringupUtil.DeviceEntry(
            DUTY_TEST_ID,
            DUTY_TEST_MFG,
            DUTY_TEST_DEVICE_TYPE,
            "CAN",
            DUTY_TEST_VENDOR,
            DUTY_TEST_TYPE,
            DEVICE_MOTOR_1,
            DUTY_TEST_MOTOR,
            null,
            null,
            null));
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_NAME, DEVICE_MOTOR_1);
    args.addProperty(KEY_DUTY, DUTY_HALF);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_DEVICE_DUTY_SET, args), 0.0, true);

    assertFalse(result.ok);
    assertEquals(MSG_MANUAL_DUTY_SCOPE_BLOCKED, result.message);
  }

  @Test
  void manualDeviceDutyClearDisablesSelectedDevice() {
    TestDeps deps = new TestDeps();
    deps.deviceByLabel.put(
        DEVICE_MOTOR_1,
        new BringupUtil.DeviceEntry(
            DUTY_TEST_ID,
            DUTY_TEST_MFG,
            DUTY_TEST_DEVICE_TYPE,
            "CAN",
            DUTY_TEST_VENDOR,
            DUTY_TEST_TYPE,
            DEVICE_MOTOR_1,
            DUTY_TEST_MOTOR,
            null,
            null,
            null));
    deps.selected.device = DEVICE_MOTOR_1;
    deps.selected.enabled = true;
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_NAME, DEVICE_MOTOR_1);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_DEVICE_DUTY_CLEAR, args), 0.0, true);

    assertTrue(result.ok);
    assertEquals(EMPTY, deps.selected.device);
    assertFalse(deps.selected.enabled);
  }

  @Test
  void manualDeviceDutyClearRejectsUnknownDevice() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_NAME, DEVICE_MOTOR_1);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_DEVICE_DUTY_CLEAR, args), 0.0, true);

    assertFalse(result.ok);
    assertEquals("Unknown device: " + DEVICE_MOTOR_1, result.message);
  }

  @Test
  void manualGroupDutySetUsesGroupDependencyPath() {
    TestDeps deps = new TestDeps();
    deps.bridgeGroups.createGroup(GROUP_MOTORS);
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("group", GROUP_MOTORS);
    args.addProperty(KEY_DUTY, DUTY_HALF);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_GROUP_DUTY_SET, args), 0.0, true);

    assertTrue(result.ok);
    assertEquals(GROUP_MOTORS, deps.lastManualGroupName);
    assertEquals(DUTY_HALF, deps.lastManualGroupDuty);
  }

  @Test
  void manualGroupDutySetAllowsRightClickTestWhenRuntimeInactive() {
    TestDeps deps = new TestDeps();
    deps.runtimeActive = false;
    deps.bridgeGroups.createGroup(GROUP_MOTORS);
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("group", GROUP_MOTORS);
    args.addProperty(KEY_DUTY, DUTY_HALF);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_GROUP_DUTY_SET, args), 0.0, true);

    assertTrue(result.ok);
    assertEquals(GROUP_MOTORS, deps.lastManualGroupName);
    assertEquals(DUTY_HALF, deps.lastManualGroupDuty);
  }

  @Test
  void manualGroupDutySetBlocksGroupOutsideControlledLifecycleScope() {
    TestDeps deps = new TestDeps();
    deps.controlledLifecycleActive = true;
    deps.bridgeGroups.createGroup(GROUP_MOTORS);
    deps.bridgeGroups.addDevice(GROUP_MOTORS, DEVICE_MOTOR_1, false);
    deps.controlledLifecycleDeviceActiveByLabel.put(DEVICE_MOTOR_1, false);
    deps.deviceByLabel.put(
        DEVICE_MOTOR_1,
        new BringupUtil.DeviceEntry(
            DUTY_TEST_ID,
            DUTY_TEST_MFG,
            DUTY_TEST_DEVICE_TYPE,
            "CAN",
            DUTY_TEST_VENDOR,
            DUTY_TEST_TYPE,
            DEVICE_MOTOR_1,
            DUTY_TEST_MOTOR,
            null,
            null,
            null));
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("group", GROUP_MOTORS);
    args.addProperty(KEY_DUTY, DUTY_HALF);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_GROUP_DUTY_SET, args), 0.0, true);

    assertFalse(result.ok);
    assertEquals(MSG_MANUAL_GROUP_DUTY_SCOPE_BLOCKED, result.message);
  }

  @Test
  void manualGroupDutyClearUsesGroupDependencyPath() {
    TestDeps deps = new TestDeps();
    deps.bridgeGroups.createGroup(GROUP_MOTORS);
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("group", GROUP_MOTORS);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_GROUP_DUTY_CLEAR, args), 0.0, true);

    assertTrue(result.ok);
    assertEquals(GROUP_MOTORS, deps.lastManualGroupCleared);
  }

  @Test
  void groupAddDeviceBlocksActiveGroupEditWhileControlledLifecycleActive() {
    TestDeps deps = new TestDeps();
    deps.controlledLifecycleActive = true;
    deps.bridgeGroups.createGroup(GROUP_ACTIVE);
    deps.deviceByLabel.put(
        DEVICE_MOTOR_1,
        new BringupUtil.DeviceEntry(
            DUTY_TEST_ID,
            DUTY_TEST_MFG,
            DUTY_TEST_DEVICE_TYPE,
            "CAN",
            DUTY_TEST_VENDOR,
            DUTY_TEST_TYPE,
            DEVICE_MOTOR_1,
            DUTY_TEST_MOTOR,
            null,
            null,
            null));
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_GROUP, GROUP_ACTIVE);
    args.addProperty(KEY_DEVICE, DEVICE_MOTOR_1);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_GROUP_ADD_DEVICE, args), 0.0, false);

    assertFalse(result.ok);
    assertEquals(MSG_ACTIVE_GROUP_LOCKED, result.message);
  }

  @Test
  void manualGroupDutyClearRequiresGroup() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_GROUP_DUTY_CLEAR, new JsonObject()), 0.0, true);

    assertFalse(result.ok);
    assertEquals("manualGroupDutyClear requires args.group.", result.message);
  }

  @Test
  void manualGroupDutyClearRejectsUnknownGroup() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_GROUP, GROUP_MOTORS);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_MANUAL_GROUP_DUTY_CLEAR, args), 0.0, true);

    assertFalse(result.ok);
    assertEquals(MSG_GROUP_NOT_FOUND_PREFIX + GROUP_MOTORS, result.message);
  }

  @Test
  void groupAddDeviceAllowsMembershipAlongsideExistingGroup() {
    TestDeps deps = new TestDeps();
    deps.bridgeGroups.createGroup(GROUP_MOTORS);
    deps.bridgeGroups.createGroup(GROUP_ACTIVE);
    deps.bridgeGroups.addDevice(GROUP_MOTORS, DEVICE_MOTOR_1, false);
    deps.deviceByLabel.put(
        DEVICE_MOTOR_1,
        new BringupUtil.DeviceEntry(
            DUTY_TEST_ID,
            DUTY_TEST_MFG,
            DUTY_TEST_DEVICE_TYPE,
            "CAN",
            DUTY_TEST_VENDOR,
            DUTY_TEST_TYPE,
            DEVICE_MOTOR_1,
            DUTY_TEST_MOTOR,
            null,
            null,
            null));
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_GROUP, GROUP_ACTIVE);
    args.addProperty(KEY_DEVICE, DEVICE_MOTOR_1);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_GROUP_ADD_DEVICE, args), 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.bridgeGroups.hasDevice(GROUP_MOTORS, DEVICE_MOTOR_1));
    assertTrue(deps.bridgeGroups.hasDevice(GROUP_ACTIVE, DEVICE_MOTOR_1));
  }

  @Test
  void groupRemoveDeviceRemovesOnlyTargetGroupMembership() {
    TestDeps deps = new TestDeps();
    deps.bridgeGroups.createGroup(GROUP_MOTORS);
    deps.bridgeGroups.createGroup(GROUP_ACTIVE);
    deps.bridgeGroups.addDevice(GROUP_MOTORS, DEVICE_MOTOR_1, false);
    deps.bridgeGroups.addDevice(GROUP_ACTIVE, DEVICE_MOTOR_1, false);
    deps.deviceByLabel.put(
        DEVICE_MOTOR_1,
        new BringupUtil.DeviceEntry(
            DUTY_TEST_ID,
            DUTY_TEST_MFG,
            DUTY_TEST_DEVICE_TYPE,
            "CAN",
            DUTY_TEST_VENDOR,
            DUTY_TEST_TYPE,
            DEVICE_MOTOR_1,
            DUTY_TEST_MOTOR,
            null,
            null,
            null));
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_GROUP, GROUP_ACTIVE);
    args.addProperty(KEY_DEVICE, DEVICE_MOTOR_1);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_GROUP_REMOVE_DEVICE, args), 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.bridgeGroups.hasDevice(GROUP_MOTORS, DEVICE_MOTOR_1));
    assertFalse(deps.bridgeGroups.hasDevice(GROUP_ACTIVE, DEVICE_MOTOR_1));
  }

  @Test
  void groupReplaceMembersRebuildsActiveGroupMembership() {
    TestDeps deps = new TestDeps();
    deps.bridgeGroups.createGroup(GROUP_ACTIVE);
    deps.bridgeGroups.addDevice(GROUP_ACTIVE, DEVICE_MOTOR_1, false);
    deps.deviceByLabel.put(
        DEVICE_MOTOR_1,
        new BringupUtil.DeviceEntry(
            DUTY_TEST_ID,
            DUTY_TEST_MFG,
            DUTY_TEST_DEVICE_TYPE,
            "CAN",
            DUTY_TEST_VENDOR,
            DUTY_TEST_TYPE,
            DEVICE_MOTOR_1,
            DUTY_TEST_MOTOR,
            null,
            null,
            null));
    deps.deviceByLabel.put(
        "lmtSw0",
        new BringupUtil.DeviceEntry(
            0,
            1,
            10,
            "DIO",
            "NI",
            "limitSwitch",
            "lmtSw0",
            "limitSwitch",
            null,
            null,
            null));
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_GROUP, GROUP_ACTIVE);
    JsonArray members = new JsonArray();
    JsonObject member = new JsonObject();
    member.addProperty("label", "lmtSw0");
    member.addProperty("enabled", true);
    members.add(member);
    args.add("members", members);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_GROUP_REPLACE_MEMBERS, args), 0.0, false);

    assertTrue(result.ok);
    assertFalse(deps.bridgeGroups.hasDevice(GROUP_ACTIVE, DEVICE_MOTOR_1));
    assertTrue(deps.bridgeGroups.hasDevice(GROUP_ACTIVE, "lmtSw0"));
  }

  @Test
  void groupReplaceMembersBlocksLockedActiveGroupEdit() {
    TestDeps deps = new TestDeps();
    deps.controlledLifecycleActive = true;
    deps.bridgeGroups.createGroup(GROUP_ACTIVE);
    deps.deviceByLabel.put(
        DEVICE_MOTOR_1,
        new BringupUtil.DeviceEntry(
            DUTY_TEST_ID,
            DUTY_TEST_MFG,
            DUTY_TEST_DEVICE_TYPE,
            "CAN",
            DUTY_TEST_VENDOR,
            DUTY_TEST_TYPE,
            DEVICE_MOTOR_1,
            DUTY_TEST_MOTOR,
            null,
            null,
            null));
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_GROUP, GROUP_ACTIVE);
    JsonArray members = new JsonArray();
    JsonObject member = new JsonObject();
    member.addProperty("label", DEVICE_MOTOR_1);
    members.add(member);
    args.add("members", members);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_GROUP_REPLACE_MEMBERS, args), 0.0, false);

    assertFalse(result.ok);
    assertEquals(MSG_ACTIVE_GROUP_LOCKED, result.message);
  }

  @Test
  void groupReplaceMembersRequiresGroup() {
    TestDeps deps = new TestDeps();
    BridgeUiGroupCommands commands = new BridgeUiGroupCommands(deps);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_GROUP_REPLACE_MEMBERS, new JsonObject()), 0.0, false);

    assertFalse(result.ok);
    assertEquals(MSG_GROUP_REPLACE_REQUIRES_GROUP, result.message);
  }

  private static BridgeUiIngressPolicy.Ingress ingress(String name, JsonObject args) {
    return new BridgeUiIngressPolicy.Ingress(
        name,
        args,
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);
  }

  private static final class TestDeps implements BridgeUiGroupCommands.Dependencies {
    private final BridgeGroupManager bridgeGroups = new BridgeGroupManager();
    private final BridgeGroupManager.SelectedState selected = new BridgeGroupManager.SelectedState();
    private final Map<String, BringupUtil.DeviceEntry> deviceByLabel = new HashMap<>();

    private boolean applyShowCalled;
    private boolean lastWantsJson;
    private String lastShowText = EMPTY;
    private final String expectedGroupsText = "groupsText";
    private String lastManualGroupName = EMPTY;
    private double lastManualGroupDuty = 0.0;
    private String lastManualGroupCleared = EMPTY;
    private boolean runtimeActive = true;
    private boolean controlledLifecycleActive;
    private final Map<String, Boolean> controlledLifecycleDeviceActiveByLabel = new HashMap<>();

    @Override
    public Boolean parseUiArgBoolean(JsonObject args, String key) {
      return args != null && args.has(key) ? args.get(key).getAsBoolean() : null;
    }

    @Override
    public String parseUiArgString(JsonObject args, String key) {
      if (args == null || !args.has(key)) {
        return null;
      }
      String value = args.get(key).getAsString();
      return value == null || value.isBlank() ? null : value;
    }

    @Override
    public Double parseUiArgDouble(JsonObject args, String key) {
      return args != null && args.has(key) ? args.get(key).getAsDouble() : null;
    }

    @Override
    public void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson) {
      applyShowCalled = true;
      lastWantsJson = wantsJson;
      lastShowText = text;
      if (wantsJson) {
        result.outJson = json.toString();
      } else {
        result.outText = text;
      }
    }

    @Override
    public String buildGroupsText() {
      return expectedGroupsText;
    }

    @Override
    public JsonObject buildGroupsJson() {
      JsonObject json = new JsonObject();
      json.addProperty("groups", 0);
      return json;
    }

    @Override
    public String buildGroupText(BridgeGroupManager.Group group) {
      return group.name;
    }

    @Override
    public JsonObject buildGroupJson(BridgeGroupManager.Group group) {
      JsonObject json = new JsonObject();
      json.addProperty("name", group.name);
      return json;
    }

    @Override
    public void applyActiveAdd(BridgeUiCommandResult result) {}

    @Override
    public void applyActiveNext(BridgeUiCommandResult result) {}

    @Override
    public String buildDevicesText() {
      return "devicesText";
    }

    @Override
    public JsonObject buildDevicesJson() {
      return new JsonObject();
    }

    @Override
    public BringupUtil.DeviceEntry findDeviceEntryByLabel(String label) {
      return deviceByLabel.get(label);
    }

    @Override
    public String buildDeviceText(BringupUtil.DeviceEntry entry) {
      return entry.label;
    }

    @Override
    public JsonObject buildDeviceJson(BringupUtil.DeviceEntry entry) {
      JsonObject json = new JsonObject();
      json.addProperty("label", entry.label);
      return json;
    }

    @Override
    public String buildBindingsText() {
      return "bindingsText";
    }

    @Override
    public JsonObject buildBindingsJson() {
      return new JsonObject();
    }

    @Override
    public String buildSelectedDeviceText() {
      return "selectedText";
    }

    @Override
    public JsonObject buildSelectedDeviceJson() {
      return new JsonObject();
    }

    @Override
    public String buildRuntimeStateText() {
      return "runtimeStateText";
    }

    @Override
    public String buildStatusText() {
      return "statusText";
    }

    @Override
    public JsonObject buildRuntimeStateJson() {
      return new JsonObject();
    }

    @Override
    public BridgeGroupManager getBridgeGroups() {
      return bridgeGroups;
    }

    @Override
    public boolean isValidBindingInput(String input) {
      return true;
    }

    @Override
    public boolean selectBringupTestByName(String name) {
      return true;
    }

    @Override
    public void runSelectedBringupTest() {}

    @Override
    public BridgeGroupManager.SelectedState getBridgeSelected() {
      return selected;
    }

    @Override
    public boolean isRuntimeActive() {
      return runtimeActive;
    }

    @Override
    public boolean isControlledLifecycleActive() {
      return controlledLifecycleActive;
    }

    @Override
    public boolean isControlledLifecycleDeviceActive(String deviceName) {
      return Boolean.TRUE.equals(controlledLifecycleDeviceActiveByLabel.get(deviceName));
    }

    @Override
    public boolean isRobotEnabled() {
      return true;
    }

    @Override
    public boolean isRobotEStopped() {
      return false;
    }

    @Override
    public boolean applyManualDeviceDuty(String deviceName, double duty) {
      selected.device = deviceName;
      selected.enabled = true;
      return duty >= -1.0 && duty <= 1.0;
    }

    @Override
    public boolean clearManualDeviceDuty(String deviceName) {
      selected.device = "";
      selected.enabled = false;
      return true;
    }

    @Override
    public boolean applyManualGroupDuty(String groupName, double duty) {
      if (groupName == null || groupName.isBlank() || duty < -1.0 || duty > 1.0) {
        return false;
      }
      lastManualGroupName = groupName;
      lastManualGroupDuty = duty;
      return true;
    }

    @Override
    public boolean clearManualGroupDuty(String groupName) {
      if (groupName == null || groupName.isBlank()) {
        return false;
      }
      lastManualGroupCleared = groupName;
      return true;
    }

    @Override
    public String overrideInstantiateDevice(String deviceName) {
      return EMPTY;
    }

    @Override
    public String clearDeviceOverride(String deviceName) {
      return EMPTY;
    }
  }
}
