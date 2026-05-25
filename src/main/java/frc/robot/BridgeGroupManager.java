package frc.robot;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import frc.robot.input.InputAliasResolver;

/**
 * NAME
 *   BridgeGroupManager - Runtime group/binding manager for bridge CLI/GUI.
 *
 * DESCRIPTION
 *   Holds group membership, bindings, and per-member enable state. Group
 *   membership is label-based over the shared object set. Runtime actions
 *   apply only to members whose labels resolve to supported device functions.
 */
public final class BridgeGroupManager {
  private static final String EMPTY_STRING = "";
  /**
   * NAME
   *   BindingKind - Supported binding behavior.
   */
  public enum BindingKind {
    ANALOG("analog"),
    HOLD("hold"),
    TOGGLE("toggle"),
    JOG_FORWARD("jog-forward"),
    JOG_REVERSE("jog-reverse");

    private final String label;

    BindingKind(String label) {
      this.label = label;
    }

    public String label() {
      return label;
    }

    public static BindingKind parse(String value) {
      if (value == null) {
        return null;
      }
      String key = value.trim().toLowerCase(Locale.ROOT);
      for (BindingKind kind : values()) {
        if (kind.label.equals(key)) {
          return kind;
        }
      }
      return null;
    }
  }

  /**
   * NAME
   *   MemberState - Per-label membership state.
   */
  public static final class MemberState {
    public final String label;
    public boolean enabled;

    public MemberState(String label, boolean enabled) {
      this.label = label;
      this.enabled = enabled;
    }
  }

  /**
   * NAME
   *   Binding - Group binding definition.
   */
  public static final class Binding {
    public final String input;
    public final BindingKind kind;
    public final double value;
    public boolean toggled;

    public Binding(String input, BindingKind kind, double value) {
      this.input = input;
      this.kind = kind;
      this.value = value;
      this.toggled = false;
    }
  }

  /**
   * NAME
   *   Group - Group configuration and runtime state.
   */
  public static final class Group {
    public final String name;
    public boolean enabled;
    public final Map<String, MemberState> members;
    public final List<Binding> bindings;
    public final List<String> lastSkippedMembers;

    public Group(String name) {
      this.name = name;
      this.enabled = true;
      this.members = new LinkedHashMap<>();
      this.bindings = new ArrayList<>();
      this.lastSkippedMembers = new ArrayList<>();
    }
  }

  /**
   * NAME
   *   SelectedState - Selected device override state.
   */
  public static final class SelectedState {
    public String device;
    public boolean enabled;
  }

  /**
   * NAME
   *   InputSnapshot - Controller input snapshot for binding evaluation.
   */
  public static final class InputSnapshot {
    public double driverLeftY;
    public double driverRightY;
    public boolean driverA;
    public boolean driverB;
    public boolean driverX;
    public boolean driverY;
    public boolean driverLb;
    public boolean driverRb;
    public boolean driverBack;
    public boolean driverStart;
    public boolean driverLs;
    public boolean driverRs;
    public boolean driverDpadUp;
    public boolean driverDpadRight;
    public boolean driverDpadDown;
    public boolean driverDpadLeft;
    public double driverLeftX;
    public double driverRightX;
    public double driverLeftTrigger;
    public double driverRightTrigger;

    public double operatorLeftY;
    public double operatorRightY;
    public boolean operatorA;
    public boolean operatorB;
    public boolean operatorX;
    public boolean operatorY;
    public boolean operatorLb;
    public boolean operatorRb;
    public boolean operatorBack;
    public boolean operatorStart;
    public boolean operatorLs;
    public boolean operatorRs;
    public boolean operatorDpadUp;
    public boolean operatorDpadRight;
    public boolean operatorDpadDown;
    public boolean operatorDpadLeft;
    public double operatorLeftX;
    public double operatorRightX;
    public double operatorLeftTrigger;
    public double operatorRightTrigger;

    public double uiSlider1;
    public double uiSlider2;
    public boolean uiButton1;
    public boolean uiButton2;
  }

  private final Map<String, Group> groups = new LinkedHashMap<>();
  private final EdgeTrigger edge = new EdgeTrigger();
  private Map<String, String> inputAliases = new LinkedHashMap<>();

  /**
   * NAME
   *   setInputAliases - Update input alias mapping for bindings.
   *
   * PARAMETERS
   *   aliases - Alias map (alias -> canonical input key).
   */
  public void setInputAliases(Map<String, String> aliases) {
    inputAliases = aliases != null ? new LinkedHashMap<>(aliases) : new LinkedHashMap<>();
  }

  /**
   * NAME
   *   clear - Remove all groups and bindings.
   */
  public void clear() {
    groups.clear();
    edge.reset();
  }

  /**
   * NAME
   *   syncGroupMembers - Replace group membership with a label list.
   *
   * DESCRIPTION
   *   Ensures the group exists, clears its membership, and repopulates it
   *   with the provided labels. Labels already assigned to another
   *   group are left untouched to preserve explicit group assignments.
   *
   * PARAMETERS
   *   groupName - Group name to sync.
   *   devices - Member labels to include.
   */
  public void syncGroupMembers(String groupName, List<String> devices) {
    String key = normalize(groupName);
    if (key.isEmpty()) {
      return;
    }
    Group group = groups.get(key);
    if (group == null) {
      group = new Group(groupName);
      groups.put(key, group);
    }
    group.members.clear();
    if (devices == null || devices.isEmpty()) {
      return;
    }
    for (String device : devices) {
      String deviceKey = normalize(device);
      if (deviceKey.isEmpty()) {
        continue;
      }
      group.members.put(deviceKey, new MemberState(device, true));
    }
  }

  /**
   * NAME
   *   getGroups - Return all configured groups in insertion order.
   *
   * RETURNS
   *   List of groups (copy) for read-only inspection.
   */
  public List<Group> getGroups() {
    return new ArrayList<>(groups.values());
  }

  /**
   * NAME
   *   getActiveBindingInputs - Return normalized inputs for enabled group bindings.
   *
   * DESCRIPTION
   *   Collects the binding input identifiers for groups that are currently
   *   enabled so callers can apply input overrides without re-parsing group
   *   state.
   *
   * RETURNS
   *   List of normalized binding input identifiers.
   */
  public List<String> getActiveBindingInputs() {
    List<String> inputs = new ArrayList<>();
    for (Group group : groups.values()) {
      if (group == null || !group.enabled) {
        continue;
      }
      for (Binding binding : group.bindings) {
        if (binding == null) {
          continue;
        }
        String input = normalize(binding.input);
        if (!input.isEmpty()) {
          inputs.add(input);
        }
      }
    }
    return inputs;
  }

  /**
   * NAME
   *   getGroup - Lookup a group by name.
   *
   * PARAMETERS
   *   name - Group name (case-insensitive).
   *
   * RETURNS
   *   Group instance or null when not found.
   */
  public Group getGroup(String name) {
    return groups.get(normalize(name));
  }

  /**
   * NAME
   *   getDeviceGroup - Return the group owning a member label.
   *
   * PARAMETERS
   *   device - Device label.
   *
   * RETURNS
   *   Group name or null when unassigned.
   */
  public String getDeviceGroup(String device) {
    String deviceKey = normalize(device);
    if (deviceKey.isEmpty()) {
      return null;
    }
    for (Group group : groups.values()) {
      if (group != null && group.members.containsKey(deviceKey)) {
        return group.name;
      }
    }
    return null;
  }

  /**
   * NAME
   *   createGroup - Create a new group by name.
   *
   * PARAMETERS
   *   name - Group name.
   *
   * RETURNS
   *   True when created, false if invalid or already exists.
   */
  public boolean createGroup(String name) {
    String key = normalize(name);
    if (key.isEmpty() || groups.containsKey(key)) {
      return false;
    }
    groups.put(key, new Group(name));
    return true;
  }

  /**
   * NAME
   *   deleteGroup - Remove a group and its membership.
   *
   * PARAMETERS
   *   name - Group name.
   *
   * RETURNS
   *   True when removed, false if missing.
   */
  public boolean deleteGroup(String name) {
    String key = normalize(name);
    Group removed = groups.remove(key);
    if (removed == null) {
      return false;
    }
    return true;
  }

  /**
   * NAME
   *   setGroupEnabled - Enable or disable a group.
   *
   * PARAMETERS
   *   name - Group name.
   *   enabled - Desired enabled state.
   *
   * RETURNS
   *   True when the group exists and was updated.
   */
  public boolean setGroupEnabled(String name, boolean enabled) {
    Group group = groups.get(normalize(name));
    if (group == null) {
      return false;
    }
    group.enabled = enabled;
    return true;
  }

  /**
   * NAME
   *   addMember - Add a labeled member to a group with optional move.
   *
   * PARAMETERS
   *   groupName - Target group name.
   *   device - Device label.
   *   forceMove - When true, move device from any existing group.
   *
   * RETURNS
   *   True when added or moved successfully.
   */
  public boolean addMember(String groupName, String device, boolean forceMove) {
    Group group = groups.get(normalize(groupName));
    if (group == null) {
      return false;
    }
    String deviceKey = normalize(device);
    if (deviceKey.isEmpty()) {
      return false;
    }
    if (group.members.containsKey(deviceKey)) {
      return true;
    }
    group.members.put(deviceKey, new MemberState(device, true));
    return true;
  }

  public boolean addDevice(String groupName, String device, boolean forceMove) {
    return addMember(groupName, device, forceMove);
  }

  /**
   * NAME
   *   removeDevice - Remove a member label from a group.
   *
   * PARAMETERS
   *   groupName - Group name.
   *   device - Device label.
   *
   * RETURNS
   *   True when removed, false if missing.
   */
  public boolean removeDevice(String groupName, String device) {
    Group group = groups.get(normalize(groupName));
    if (group == null) {
      return false;
    }
    String deviceKey = normalize(device);
    group.members.remove(deviceKey);
    return true;
  }

  /**
   * NAME
   *   setMemberEnabled - Enable or disable a member label.
   *
   * PARAMETERS
   *   groupName - Group name.
   *   device - Device label.
   *   enabled - Desired enabled state.
   *
   * RETURNS
   *   True when updated, false if missing.
   */
  public boolean setMemberEnabled(String groupName, String device, boolean enabled) {
    Group group = groups.get(normalize(groupName));
    if (group == null) {
      return false;
    }
    MemberState member = group.members.get(normalize(device));
    if (member == null) {
      return false;
    }
    member.enabled = enabled;
    return true;
  }

  /**
   * NAME
   *   toggleMember - Toggle a member's enabled state.
   *
   * PARAMETERS
   *   groupName - Group name.
   *   device - Device label.
   *
   * RETURNS
   *   True when toggled, false if missing.
   */
  public boolean toggleMember(String groupName, String device) {
    Group group = groups.get(normalize(groupName));
    if (group == null) {
      return false;
    }
    MemberState member = group.members.get(normalize(device));
    if (member == null) {
      return false;
    }
    member.enabled = !member.enabled;
    return true;
  }

  /**
   * NAME
   *   clearBindings - Remove all bindings from a group.
   *
   * PARAMETERS
   *   groupName - Group name.
   *
   * RETURNS
   *   True when cleared, false if missing.
   */
  public boolean clearBindings(String groupName) {
    Group group = groups.get(normalize(groupName));
    if (group == null) {
      return false;
    }
    group.bindings.clear();
    return true;
  }

  /**
   * NAME
   *   addBinding - Add a binding to a group.
   *
   * PARAMETERS
   *   groupName - Group name.
   *   input - Input identifier (driver/operator/ui).
   *   kind - Binding kind.
   *   value - Binding value (ignored for analog).
   *
   * RETURNS
   *   True when binding added, false if group or kind invalid.
   */
  public boolean addBinding(String groupName, String input, BindingKind kind, double value) {
    Group group = groups.get(normalize(groupName));
    if (group == null || kind == null) {
      return false;
    }
    group.bindings.add(new Binding(input, kind, value));
    return true;
  }

  /**
   * NAME
   *   applyBindings - Apply group outputs to devices each loop.
   *
   * PARAMETERS
   *   input - Snapshot of controller inputs.
   *   core - Bringup core for device outputs.
   *   selected - Selected device override state.
   *
   * SIDE EFFECTS
   *   Sends duty-cycle commands to supported member devices and records labels
   *   skipped because they do not resolve to runtime-capable devices.
   */
  public void applyBindings(InputSnapshot input, BringupCore core, SelectedState selected) {
    if (input == null || core == null) {
      return;
    }
    if (core.isTestRunning()) {
      return;
    }
    for (Group group : groups.values()) {
      group.lastSkippedMembers.clear();
      if (!group.enabled) {
        continue;
      }
      double output = computeGroupOutput(group, input);
      if (Math.abs(output) < 1e-6) {
        continue;
      }
      for (MemberState member : group.members.values()) {
        if (!member.enabled) {
          continue;
        }
        if (selected != null && selected.enabled && sameKey(selected.device, member.label)) {
          continue;
        }
        if (!core.setDutyByDeviceLabel(member.label, output)) {
          group.lastSkippedMembers.add(member.label);
        }
      }
    }
  }

  /**
   * NAME
   *   computeGroupOutput - Sum all binding outputs for a group.
   */
  private double computeGroupOutput(Group group, InputSnapshot input) {
    double sum = 0.0;
    for (Binding binding : group.bindings) {
      double value = computeBindingOutput(binding, input, group.name);
      sum += value;
    }
    return clamp(sum, -1.0, 1.0);
  }

  /**
   * NAME
   *   computeBindingOutput - Resolve a binding's output based on input.
   */
  private double computeBindingOutput(Binding binding, InputSnapshot input, String groupName) {
    double inputValue = resolveInput(binding.input, input);
    boolean pressed = Math.abs(inputValue) > 0.5;
    String key = groupName + ":" + binding.input + ":" + binding.kind.label();
    switch (binding.kind) {
      case ANALOG:
        return inputValue;
      case HOLD:
        return pressed ? binding.value : 0.0;
      case TOGGLE:
        if (edge.pressed(key, pressed)) {
          binding.toggled = !binding.toggled;
        }
        return binding.toggled ? binding.value : 0.0;
      case JOG_FORWARD:
        return pressed ? Math.abs(binding.value) : 0.0;
      case JOG_REVERSE:
        return pressed ? -Math.abs(binding.value) : 0.0;
      default:
        return 0.0;
    }
  }

  /**
   * NAME
   *   resolveInput - Map an input identifier to a numeric value.
   */
  private double resolveInput(String input, InputSnapshot snapshot) {
    String key = InputAliasResolver.resolve(input, inputAliases);
    if (key.equals(InputAliasResolver.KEY_DRIVER_LEFT_Y)) {
      return snapshot.driverLeftY;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_RIGHT_Y)) {
      return snapshot.driverRightY;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_LEFT_X)) {
      return snapshot.driverLeftX;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_RIGHT_X)) {
      return snapshot.driverRightX;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_LEFT_TRIGGER)) {
      return snapshot.driverLeftTrigger;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_RIGHT_TRIGGER)) {
      return snapshot.driverRightTrigger;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_A)) {
      return snapshot.driverA ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_B)) {
      return snapshot.driverB ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_X)) {
      return snapshot.driverX ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_Y)) {
      return snapshot.driverY ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_LB)) {
      return snapshot.driverLb ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_RB)) {
      return snapshot.driverRb ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_BACK)) {
      return snapshot.driverBack ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_START)) {
      return snapshot.driverStart ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_LS)) {
      return snapshot.driverLs ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_RS)) {
      return snapshot.driverRs ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_DPAD_UP)) {
      return snapshot.driverDpadUp ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_DPAD_RIGHT)) {
      return snapshot.driverDpadRight ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_DPAD_DOWN)) {
      return snapshot.driverDpadDown ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_DRIVER_DPAD_LEFT)) {
      return snapshot.driverDpadLeft ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_LEFT_Y)) {
      return snapshot.operatorLeftY;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_RIGHT_Y)) {
      return snapshot.operatorRightY;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_LEFT_X)) {
      return snapshot.operatorLeftX;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_RIGHT_X)) {
      return snapshot.operatorRightX;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_LEFT_TRIGGER)) {
      return snapshot.operatorLeftTrigger;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_RIGHT_TRIGGER)) {
      return snapshot.operatorRightTrigger;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_A)) {
      return snapshot.operatorA ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_B)) {
      return snapshot.operatorB ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_X)) {
      return snapshot.operatorX ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_Y)) {
      return snapshot.operatorY ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_LB)) {
      return snapshot.operatorLb ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_RB)) {
      return snapshot.operatorRb ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_BACK)) {
      return snapshot.operatorBack ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_START)) {
      return snapshot.operatorStart ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_LS)) {
      return snapshot.operatorLs ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_RS)) {
      return snapshot.operatorRs ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_DPAD_UP)) {
      return snapshot.operatorDpadUp ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_DPAD_RIGHT)) {
      return snapshot.operatorDpadRight ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_DPAD_DOWN)) {
      return snapshot.operatorDpadDown ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_OPERATOR_DPAD_LEFT)) {
      return snapshot.operatorDpadLeft ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_UI_SLIDER_1)) {
      return snapshot.uiSlider1;
    }
    if (key.equals(InputAliasResolver.KEY_UI_SLIDER_2)) {
      return snapshot.uiSlider2;
    }
    if (key.equals(InputAliasResolver.KEY_UI_BUTTON_1)) {
      return snapshot.uiButton1 ? 1.0 : 0.0;
    }
    if (key.equals(InputAliasResolver.KEY_UI_BUTTON_2)) {
      return snapshot.uiButton2 ? 1.0 : 0.0;
    }
    return 0.0;
  }

  private static double clamp(double value, double min, double max) {
    return Math.max(min, Math.min(max, value));
  }

  private static String normalize(String value) {
    return value == null ? EMPTY_STRING : value.trim().toLowerCase(Locale.ROOT);
  }

  private static boolean sameKey(String a, String b) {
    return normalize(a).equals(normalize(b));
  }
}
