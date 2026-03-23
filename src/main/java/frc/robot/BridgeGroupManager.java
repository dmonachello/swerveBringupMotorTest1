package frc.robot;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * NAME
 *   BridgeGroupManager - Runtime group/binding manager for bridge CLI/GUI.
 *
 * DESCRIPTION
 *   Holds group membership, bindings, and per-member enable state. Applies
 *   binding outputs to devices via BringupCore without persisting state on
 *   the robot.
 */
public final class BridgeGroupManager {
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
   *   MemberState - Per-device membership state.
   */
  public static final class MemberState {
    public final String device;
    public boolean enabled;

    public MemberState(String device, boolean enabled) {
      this.device = device;
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

    public Group(String name) {
      this.name = name;
      this.enabled = true;
      this.members = new LinkedHashMap<>();
      this.bindings = new ArrayList<>();
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

    public double operatorLeftY;
    public double operatorRightY;
    public boolean operatorA;
    public boolean operatorB;
    public boolean operatorX;
    public boolean operatorY;
    public boolean operatorLb;
    public boolean operatorRb;

    public double uiSlider1;
    public double uiSlider2;
    public boolean uiButton1;
    public boolean uiButton2;
  }

  private final Map<String, Group> groups = new LinkedHashMap<>();
  private final Map<String, String> deviceToGroup = new LinkedHashMap<>();
  private final EdgeTrigger edge = new EdgeTrigger();

  /**
   * NAME
   *   clear - Remove all groups and bindings.
   */
  public void clear() {
    groups.clear();
    deviceToGroup.clear();
    edge.reset();
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
   *   getDeviceGroup - Return the group owning a device.
   *
   * PARAMETERS
   *   device - Device label.
   *
   * RETURNS
   *   Group name or null when unassigned.
   */
  public String getDeviceGroup(String device) {
    return deviceToGroup.get(normalize(device));
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
    for (MemberState member : removed.members.values()) {
      deviceToGroup.remove(normalize(member.device));
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
   *   addDevice - Add a device to a group with optional move.
   *
   * PARAMETERS
   *   groupName - Target group name.
   *   device - Device label.
   *   forceMove - When true, move device from any existing group.
   *
   * RETURNS
   *   True when added or moved successfully.
   */
  public boolean addDevice(String groupName, String device, boolean forceMove) {
    Group group = groups.get(normalize(groupName));
    if (group == null) {
      return false;
    }
    String deviceKey = normalize(device);
    if (deviceKey.isEmpty()) {
      return false;
    }
    String existing = deviceToGroup.get(deviceKey);
    if (existing != null && !normalize(existing).equals(normalize(groupName))) {
      if (!forceMove) {
        return false;
      }
      Group other = groups.get(normalize(existing));
      if (other != null) {
        other.members.remove(deviceKey);
      }
    }
    deviceToGroup.put(deviceKey, group.name);
    group.members.put(deviceKey, new MemberState(device, true));
    return true;
  }

  /**
   * NAME
   *   removeDevice - Remove a device from a group.
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
    deviceToGroup.remove(deviceKey);
    return true;
  }

  /**
   * NAME
   *   setMemberEnabled - Enable or disable a member device.
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
   *   Sends duty-cycle commands to member devices.
   */
  public void applyBindings(InputSnapshot input, BringupCore core, SelectedState selected) {
    if (input == null || core == null) {
      return;
    }
    if (core.isTestRunning()) {
      return;
    }
    for (Group group : groups.values()) {
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
        if (selected != null && selected.enabled && sameKey(selected.device, member.device)) {
          continue;
        }
        core.setDutyByDeviceLabel(member.device, output);
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
    String key = normalize(input);
    if (key.equals("driver.left.y")) {
      return snapshot.driverLeftY;
    }
    if (key.equals("driver.right.y")) {
      return snapshot.driverRightY;
    }
    if (key.equals("driver.a")) {
      return snapshot.driverA ? 1.0 : 0.0;
    }
    if (key.equals("driver.b")) {
      return snapshot.driverB ? 1.0 : 0.0;
    }
    if (key.equals("driver.x")) {
      return snapshot.driverX ? 1.0 : 0.0;
    }
    if (key.equals("driver.y")) {
      return snapshot.driverY ? 1.0 : 0.0;
    }
    if (key.equals("driver.lb")) {
      return snapshot.driverLb ? 1.0 : 0.0;
    }
    if (key.equals("driver.rb")) {
      return snapshot.driverRb ? 1.0 : 0.0;
    }
    if (key.equals("operator.left.y")) {
      return snapshot.operatorLeftY;
    }
    if (key.equals("operator.right.y")) {
      return snapshot.operatorRightY;
    }
    if (key.equals("operator.a")) {
      return snapshot.operatorA ? 1.0 : 0.0;
    }
    if (key.equals("operator.b")) {
      return snapshot.operatorB ? 1.0 : 0.0;
    }
    if (key.equals("operator.x")) {
      return snapshot.operatorX ? 1.0 : 0.0;
    }
    if (key.equals("operator.y")) {
      return snapshot.operatorY ? 1.0 : 0.0;
    }
    if (key.equals("operator.lb")) {
      return snapshot.operatorLb ? 1.0 : 0.0;
    }
    if (key.equals("operator.rb")) {
      return snapshot.operatorRb ? 1.0 : 0.0;
    }
    if (key.equals("ui.slider1")) {
      return snapshot.uiSlider1;
    }
    if (key.equals("ui.slider2")) {
      return snapshot.uiSlider2;
    }
    if (key.equals("ui.button1")) {
      return snapshot.uiButton1 ? 1.0 : 0.0;
    }
    if (key.equals("ui.button2")) {
      return snapshot.uiButton2 ? 1.0 : 0.0;
    }
    return 0.0;
  }

  private static double clamp(double value, double min, double max) {
    return Math.max(min, Math.min(max, value));
  }

  private static String normalize(String value) {
    return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
  }

  private static boolean sameKey(String a, String b) {
    return normalize(a).equals(normalize(b));
  }
}
