package frc.robot;

import com.google.gson.JsonObject;
import java.util.Set;

/**
 * NAME
 *   BridgeUiGroupCommands - Group/selection command family executor.
 */
final class BridgeUiGroupCommands implements BridgeUiCommandDispatcher.CommandFamily {

  private static final String CMD_SHOW_GROUPS = "showGroups";
  private static final String CMD_SHOW_GROUP = "showGroup";
  private static final String CMD_ACTIVE_ADD = "activeAdd";
  private static final String CMD_ACTIVE_NEXT = "activeNext";
  private static final String CMD_SHOW_DEVICES = "showDevices";
  private static final String CMD_SHOW_DEVICE = "showDevice";
  private static final String CMD_SHOW_BINDINGS = "showBindings";
  private static final String CMD_SHOW_SELECTED_DEVICE = "showSelectedDevice";
  private static final String CMD_SHOW_RUNTIME_STATE = "showRuntimeState";
  private static final String CMD_GROUP_CREATE = "groupCreate";
  private static final String CMD_GROUP_DELETE = "groupDelete";
  private static final String CMD_GROUP_ADD_DEVICE = "groupAddDevice";
  private static final String CMD_GROUP_REMOVE_DEVICE = "groupRemoveDevice";
  private static final String CMD_GROUP_MEMBER_ENABLE = "groupMemberEnable";
  private static final String CMD_GROUP_MEMBER_DISABLE = "groupMemberDisable";
  private static final String CMD_GROUP_MEMBER_TOGGLE = "groupMemberToggle";
  private static final String CMD_GROUP_BIND = "groupBind";
  private static final String CMD_GROUP_UNBIND = "groupUnbind";
  private static final String CMD_GROUP_ENABLE = "groupEnable";
  private static final String CMD_GROUP_DISABLE = "groupDisable";
  private static final String CMD_GROUP_RUN_TEST = "groupRunTest";
  private static final String CMD_SELECTED_DEVICE_SET = "selectedDeviceSet";
  private static final String CMD_SELECTED_MODE_SET = "selectedModeSet";
  private static final String CMD_MANUAL_DEVICE_DUTY_SET = "manualDeviceDutySet";
  private static final String CMD_MANUAL_DEVICE_DUTY_CLEAR = "manualDeviceDutyClear";

  private static final String JSON_KEY_JSON = "json";

  private static final Set<String> COMMANDS = Set.of(
      CMD_SHOW_GROUPS,
      CMD_SHOW_GROUP,
      CMD_ACTIVE_ADD,
      CMD_ACTIVE_NEXT,
      CMD_SHOW_DEVICES,
      CMD_SHOW_DEVICE,
      CMD_SHOW_BINDINGS,
      CMD_SHOW_SELECTED_DEVICE,
      CMD_SHOW_RUNTIME_STATE,
      CMD_GROUP_CREATE,
      CMD_GROUP_DELETE,
      CMD_GROUP_ADD_DEVICE,
      CMD_GROUP_REMOVE_DEVICE,
      CMD_GROUP_MEMBER_ENABLE,
      CMD_GROUP_MEMBER_DISABLE,
      CMD_GROUP_MEMBER_TOGGLE,
      CMD_GROUP_BIND,
      CMD_GROUP_UNBIND,
      CMD_GROUP_ENABLE,
      CMD_GROUP_DISABLE,
      CMD_GROUP_RUN_TEST,
      CMD_SELECTED_DEVICE_SET,
      CMD_SELECTED_MODE_SET,
      CMD_MANUAL_DEVICE_DUTY_SET,
      CMD_MANUAL_DEVICE_DUTY_CLEAR);

  /**
   * NAME
   *   Dependencies - Narrow dependency contract for group commands.
   */
  interface Dependencies {
    Boolean parseUiArgBoolean(JsonObject args, String key);

    String parseUiArgString(JsonObject args, String key);

    Double parseUiArgDouble(JsonObject args, String key);

    void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson);

    String buildGroupsText();

    JsonObject buildGroupsJson();

    String buildGroupText(BridgeGroupManager.Group group);

    JsonObject buildGroupJson(BridgeGroupManager.Group group);

    void applyActiveAdd(BridgeUiCommandResult result);

    void applyActiveNext(BridgeUiCommandResult result);

    String buildDevicesText();

    JsonObject buildDevicesJson();

    BringupUtil.DeviceEntry findDeviceEntryByLabel(String label);

    String buildDeviceText(BringupUtil.DeviceEntry entry);

    JsonObject buildDeviceJson(BringupUtil.DeviceEntry entry);

    String buildBindingsText();

    JsonObject buildBindingsJson();

    String buildSelectedDeviceText();

    JsonObject buildSelectedDeviceJson();

    String buildStatusText();

    JsonObject buildRuntimeStateJson();

    BridgeGroupManager getBridgeGroups();

    boolean isValidBindingInput(String input);

    boolean selectBringupTestByName(String name);

    void runSelectedBringupTest();

    BridgeGroupManager.SelectedState getBridgeSelected();

    boolean applyManualDeviceDuty(String deviceName, double duty);

    boolean clearManualDeviceDuty(String deviceName);
  }

  private final Dependencies dependencies;

  BridgeUiGroupCommands(Dependencies dependencies) {
    this.dependencies = dependencies;
  }

  @Override
  public boolean handles(String commandName) {
    return COMMANDS.contains(commandName);
  }

  @Override
  public BridgeUiCommandResult execute(
      BridgeUiIngressPolicy.Ingress ingress,
      double cmdTs,
      boolean isTcp) {
    BridgeUiCommandResult result = new BridgeUiCommandResult();
    String name = ingress.name;
    JsonObject args = ingress.args;
    BridgeGroupManager bridgeGroups = dependencies.getBridgeGroups();

    switch (name) {
      case CMD_SHOW_GROUPS: {
        boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, JSON_KEY_JSON));
        dependencies.applyShowResult(result, dependencies.buildGroupsText(), dependencies.buildGroupsJson(), wantsJson);
        break;
      }
      case CMD_SHOW_GROUP: {
        String groupName = dependencies.parseUiArgString(args, "name");
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
        boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, JSON_KEY_JSON));
        dependencies.applyShowResult(result, dependencies.buildGroupText(group), dependencies.buildGroupJson(group), wantsJson);
        break;
      }
      case CMD_ACTIVE_ADD:
        dependencies.applyActiveAdd(result);
        break;
      case CMD_ACTIVE_NEXT:
        dependencies.applyActiveNext(result);
        break;
      case CMD_SHOW_DEVICES: {
        boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, JSON_KEY_JSON));
        dependencies.applyShowResult(result, dependencies.buildDevicesText(), dependencies.buildDevicesJson(), wantsJson);
        break;
      }
      case CMD_SHOW_DEVICE: {
        String deviceName = dependencies.parseUiArgString(args, "name");
        if (deviceName == null) {
          result.ok = false;
          result.message = "showDevice requires args.name.";
          break;
        }
        BringupUtil.DeviceEntry entry = dependencies.findDeviceEntryByLabel(deviceName);
        if (entry == null) {
          result.ok = false;
          result.message = "Device not found: " + deviceName;
          break;
        }
        boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, JSON_KEY_JSON));
        dependencies.applyShowResult(result, dependencies.buildDeviceText(entry), dependencies.buildDeviceJson(entry), wantsJson);
        break;
      }
      case CMD_SHOW_BINDINGS: {
        boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, JSON_KEY_JSON));
        dependencies.applyShowResult(result, dependencies.buildBindingsText(), dependencies.buildBindingsJson(), wantsJson);
        break;
      }
      case CMD_SHOW_SELECTED_DEVICE: {
        boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, JSON_KEY_JSON));
        dependencies.applyShowResult(result, dependencies.buildSelectedDeviceText(), dependencies.buildSelectedDeviceJson(), wantsJson);
        break;
      }
      case CMD_SHOW_RUNTIME_STATE: {
        boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, JSON_KEY_JSON));
        String text = dependencies.buildStatusText() + "\n" + dependencies.buildGroupsText();
        dependencies.applyShowResult(result, text, dependencies.buildRuntimeStateJson(), wantsJson);
        break;
      }
      case CMD_GROUP_CREATE: {
        String groupName = dependencies.parseUiArgString(args, "name");
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
      case CMD_GROUP_DELETE: {
        String groupName = dependencies.parseUiArgString(args, "name");
        Boolean confirm = dependencies.parseUiArgBoolean(args, "confirm");
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
      case CMD_GROUP_ADD_DEVICE:
        executeGroupAddDevice(name, args, result, bridgeGroups);
        break;
      case CMD_GROUP_REMOVE_DEVICE:
        executeGroupRemoveDevice(args, result, bridgeGroups);
        break;
      case CMD_GROUP_MEMBER_ENABLE:
      case CMD_GROUP_MEMBER_DISABLE:
      case CMD_GROUP_MEMBER_TOGGLE:
        executeGroupMemberCommand(name, args, result, bridgeGroups);
        break;
      case CMD_GROUP_BIND:
        executeGroupBind(args, result, bridgeGroups);
        break;
      case CMD_GROUP_UNBIND:
        executeGroupUnbind(args, result, bridgeGroups);
        break;
      case CMD_GROUP_ENABLE:
      case CMD_GROUP_DISABLE:
        executeGroupEnableDisable(name, args, result, bridgeGroups);
        break;
      case CMD_GROUP_RUN_TEST:
        executeGroupRunTest(args, result, bridgeGroups);
        break;
      case CMD_SELECTED_DEVICE_SET: {
        String deviceName = dependencies.parseUiArgString(args, "name");
        if (deviceName == null) {
          result.ok = false;
          result.message = "selectedDeviceSet requires args.name.";
          break;
        }
        if (dependencies.findDeviceEntryByLabel(deviceName) == null) {
          result.ok = false;
          result.message = "Unknown device: " + deviceName;
          break;
        }
        dependencies.getBridgeSelected().device = deviceName;
        result.message = "Selected device: " + deviceName;
        result.outText = result.message;
        break;
      }
      case CMD_SELECTED_MODE_SET: {
        Boolean enabled = dependencies.parseUiArgBoolean(args, "enabled");
        if (enabled == null) {
          result.ok = false;
          result.message = "selectedModeSet requires args.enabled.";
          break;
        }
        BridgeGroupManager.SelectedState selected = dependencies.getBridgeSelected();
        if (enabled && (selected.device == null || selected.device.isBlank())) {
          result.ok = false;
          result.message = "No selected device set.";
          break;
        }
        selected.enabled = enabled;
        result.message = "Selected mode " + (enabled ? "on" : "off") + ".";
        result.outText = result.message;
        break;
      }
      case CMD_MANUAL_DEVICE_DUTY_SET: {
        String deviceName = dependencies.parseUiArgString(args, "name");
        Double duty = dependencies.parseUiArgDouble(args, "duty");
        if (deviceName == null || duty == null) {
          result.ok = false;
          result.message = "manualDeviceDutySet requires args.name and args.duty.";
          break;
        }
        if (dependencies.findDeviceEntryByLabel(deviceName) == null) {
          result.ok = false;
          result.message = "Unknown device: " + deviceName;
          break;
        }
        if (!dependencies.applyManualDeviceDuty(deviceName, duty)) {
          result.ok = false;
          result.message = "Manual duty apply failed: " + deviceName;
          break;
        }
        result.message = "Manual duty applied: " + deviceName;
        result.outText = result.message;
        break;
      }
      case CMD_MANUAL_DEVICE_DUTY_CLEAR: {
        String deviceName = dependencies.parseUiArgString(args, "name");
        if (!dependencies.clearManualDeviceDuty(deviceName)) {
          result.ok = false;
          result.message = "Manual duty clear failed.";
          break;
        }
        result.message = "Manual duty cleared.";
        result.outText = result.message;
        break;
      }
      default:
        result.ok = false;
        result.message = "Unknown command: " + name;
        break;
    }

    return result;
  }

  private void executeGroupAddDevice(
      String name,
      JsonObject args,
      BridgeUiCommandResult result,
      BridgeGroupManager bridgeGroups) {
    String groupName = dependencies.parseUiArgString(args, "group");
    String deviceName = dependencies.parseUiArgString(args, "device");
    String policy = dependencies.parseUiArgString(args, "conflictPolicy");
    Boolean forceMove = dependencies.parseUiArgBoolean(args, "forceMove");
    if (groupName == null || deviceName == null) {
      result.ok = false;
      result.message = "groupAddDevice requires args.group and args.device.";
      return;
    }
    if (bridgeGroups.getGroup(groupName) == null) {
      result.ok = false;
      result.message = "Group not found: " + groupName;
      return;
    }
    if (dependencies.findDeviceEntryByLabel(deviceName) == null) {
      result.ok = false;
      result.message = "Unknown device: " + deviceName;
      return;
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
      return;
    }
    boolean added = bridgeGroups.addDevice(groupName, deviceName, wantsMove);
    if (!added) {
      result.ok = false;
      result.message = "Failed to add device to group.";
      return;
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
  }

  private void executeGroupRemoveDevice(
      JsonObject args,
      BridgeUiCommandResult result,
      BridgeGroupManager bridgeGroups) {
    String groupName = dependencies.parseUiArgString(args, "group");
    String deviceName = dependencies.parseUiArgString(args, "device");
    if (groupName == null || deviceName == null) {
      result.ok = false;
      result.message = "groupRemoveDevice requires args.group and args.device.";
      return;
    }
    BridgeGroupManager.Group group = bridgeGroups.getGroup(groupName);
    if (group == null) {
      result.ok = false;
      result.message = "Group not found: " + groupName;
      return;
    }
    String current = bridgeGroups.getDeviceGroup(deviceName);
    if (current == null || !current.equalsIgnoreCase(groupName)) {
      result.ok = false;
      result.message = "Device not in group: " + deviceName;
      return;
    }
    bridgeGroups.removeDevice(groupName, deviceName);
    result.message = "Device removed: " + deviceName + " from " + groupName;
    result.outText = result.message;
  }

  private void executeGroupMemberCommand(
      String commandName,
      JsonObject args,
      BridgeUiCommandResult result,
      BridgeGroupManager bridgeGroups) {
    String groupName = dependencies.parseUiArgString(args, "group");
    String deviceName = dependencies.parseUiArgString(args, "device");
    if (groupName == null || deviceName == null) {
      result.ok = false;
      result.message = commandName + " requires args.group and args.device.";
      return;
    }
    BridgeGroupManager.Group group = bridgeGroups.getGroup(groupName);
    if (group == null) {
      result.ok = false;
      result.message = "Group not found: " + groupName;
      return;
    }
    String current = bridgeGroups.getDeviceGroup(deviceName);
    if (current == null || !current.equalsIgnoreCase(groupName)) {
      result.ok = false;
      result.message = "Device not in group: " + deviceName;
      return;
    }
    boolean ok;
    if (CMD_GROUP_MEMBER_ENABLE.equals(commandName)) {
      ok = bridgeGroups.setMemberEnabled(groupName, deviceName, true);
    } else if (CMD_GROUP_MEMBER_DISABLE.equals(commandName)) {
      ok = bridgeGroups.setMemberEnabled(groupName, deviceName, false);
    } else {
      ok = bridgeGroups.toggleMember(groupName, deviceName);
    }
    if (!ok) {
      result.ok = false;
      result.message = "Failed to update member: " + deviceName;
      return;
    }
    result.message = "Member updated: " + deviceName;
    result.outText = result.message;
  }

  private void executeGroupBind(
      JsonObject args,
      BridgeUiCommandResult result,
      BridgeGroupManager bridgeGroups) {
    String groupName = dependencies.parseUiArgString(args, "group");
    String input = dependencies.parseUiArgString(args, "input");
    String kindRaw = dependencies.parseUiArgString(args, "kind");
    Double value = dependencies.parseUiArgDouble(args, "value");
    if (groupName == null || input == null || kindRaw == null) {
      result.ok = false;
      result.message = "groupBind requires args.group, args.input, args.kind.";
      return;
    }
    BridgeGroupManager.Group group = bridgeGroups.getGroup(groupName);
    if (group == null) {
      result.ok = false;
      result.message = "Group not found: " + groupName;
      return;
    }
    if (!dependencies.isValidBindingInput(input)) {
      result.ok = false;
      result.message = "Unknown input: " + input;
      return;
    }
    BridgeGroupManager.BindingKind kind = BridgeGroupManager.BindingKind.parse(kindRaw);
    if (kind == null) {
      result.ok = false;
      result.message = "Unknown binding kind: " + kindRaw;
      return;
    }
    if (kind != BridgeGroupManager.BindingKind.ANALOG && value == null) {
      result.ok = false;
      result.message = "Binding value required for " + kind.label() + ".";
      return;
    }
    double bindValue = value != null ? value : 0.0;
    boolean ok = bridgeGroups.addBinding(groupName, input, kind, bindValue);
    if (!ok) {
      result.ok = false;
      result.message = "Failed to add binding.";
      return;
    }
    result.message = "Binding added.";
    result.outText = result.message;
  }

  private void executeGroupUnbind(
      JsonObject args,
      BridgeUiCommandResult result,
      BridgeGroupManager bridgeGroups) {
    String groupName = dependencies.parseUiArgString(args, "group");
    if (groupName == null) {
      result.ok = false;
      result.message = "groupUnbind requires args.group.";
      return;
    }
    boolean ok = bridgeGroups.clearBindings(groupName);
    if (!ok) {
      result.ok = false;
      result.message = "Group not found: " + groupName;
      return;
    }
    result.message = "Bindings cleared for " + groupName;
    result.outText = result.message;
  }

  private void executeGroupEnableDisable(
      String commandName,
      JsonObject args,
      BridgeUiCommandResult result,
      BridgeGroupManager bridgeGroups) {
    String groupName = dependencies.parseUiArgString(args, "group");
    if (groupName == null) {
      result.ok = false;
      result.message = commandName + " requires args.group.";
      return;
    }
    boolean enabled = CMD_GROUP_ENABLE.equals(commandName);
    boolean ok = bridgeGroups.setGroupEnabled(groupName, enabled);
    if (!ok) {
      result.ok = false;
      result.message = "Group not found: " + groupName;
      return;
    }
    result.message = "Group " + groupName + " " + (enabled ? "enabled" : "disabled") + ".";
    result.outText = result.message;
  }

  private void executeGroupRunTest(
      JsonObject args,
      BridgeUiCommandResult result,
      BridgeGroupManager bridgeGroups) {
    String groupName = dependencies.parseUiArgString(args, "group");
    if (groupName == null) {
      result.ok = false;
      result.message = "groupRunTest requires args.group.";
      return;
    }
    if (bridgeGroups.getGroup(groupName) == null) {
      result.ok = false;
      result.message = "Group not found: " + groupName;
      return;
    }
    String groupTestName = dependencies.parseUiArgString(args, "name");
    if (groupTestName != null && !groupTestName.isBlank()) {
      boolean selected = dependencies.selectBringupTestByName(groupTestName);
      if (!selected) {
        result.ok = false;
        result.message = "Test not found: " + groupTestName;
        return;
      }
    }
    dependencies.runSelectedBringupTest();
    result.message = "Test started.";
    result.outText = result.message;
  }
}

