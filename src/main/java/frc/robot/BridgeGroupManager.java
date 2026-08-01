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
  private static final String DUTY_WRITE_SOURCE_BINDING_PREFIX = "bridge-binding:";
  private static final int MAX_CONTROLLER_COUNT = 6;
  private final Object stateLock = new Object();
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
    public boolean bindingActive;
    public double lastBindingOutput;

    public Group(String name) {
      this.name = name;
      this.enabled = true;
      this.members = new LinkedHashMap<>();
      this.bindings = new ArrayList<>();
      this.lastSkippedMembers = new ArrayList<>();
      this.bindingActive = false;
      this.lastBindingOutput = 0.0;
    }
  }

  /**
   * NAME
   *   SelectedState - Selected device override state.
   */
  public static final class SelectedState {
    public String device;
    public boolean enabled;
    public String group;
    public boolean groupEnabled;
    public final List<String> groupMembers = new ArrayList<>();
  }

  /**
   * NAME
   *   InputSnapshot - Controller input snapshot for binding evaluation.
   */
  public static final class InputSnapshot {
    public final ControllerState[] controllers = createControllers();

    public double uiSlider1;
    public double uiSlider2;
    public boolean uiButton1;
    public boolean uiButton2;

    private static ControllerState[] createControllers() {
      ControllerState[] states = new ControllerState[MAX_CONTROLLER_COUNT];
      for (int index = 0; index < MAX_CONTROLLER_COUNT; index++) {
        states[index] = new ControllerState();
      }
      return states;
    }
  }

  /**
   * NAME
   *   ControllerState - Per-controller input values keyed by USB port index.
   */
  public static final class ControllerState {
    public double leftY;
    public double rightY;
    public boolean a;
    public boolean b;
    public boolean x;
    public boolean y;
    public boolean lb;
    public boolean rb;
    public boolean back;
    public boolean start;
    public boolean ls;
    public boolean rs;
    public boolean dpadUp;
    public boolean dpadRight;
    public boolean dpadDown;
    public boolean dpadLeft;
    public double leftX;
    public double rightX;
    public double leftTrigger;
    public double rightTrigger;
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
    synchronized (stateLock) {
      inputAliases = aliases != null ? new LinkedHashMap<>(aliases) : new LinkedHashMap<>();
    }
  }

  /**
   * NAME
   *   clear - Remove all groups and bindings.
   */
  public void clear() {
    synchronized (stateLock) {
      groups.clear();
      edge.reset();
    }
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
    synchronized (stateLock) {
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
  }

  /**
   * NAME
   *   getGroups - Return all configured groups in insertion order.
   *
   * RETURNS
   *   List of groups (copy) for read-only inspection.
   */
  public List<Group> getGroups() {
    synchronized (stateLock) {
      return copyGroups(groups.values());
    }
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
    synchronized (stateLock) {
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
    synchronized (stateLock) {
      return copyGroup(groups.get(normalize(name)));
    }
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
    synchronized (stateLock) {
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
    synchronized (stateLock) {
      String key = normalize(name);
      if (key.isEmpty() || groups.containsKey(key)) {
        return false;
      }
      groups.put(key, new Group(name));
      return true;
    }
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
    synchronized (stateLock) {
      String key = normalize(name);
      Group removed = groups.remove(key);
      if (removed == null) {
        return false;
      }
      return true;
    }
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
    synchronized (stateLock) {
      Group group = groups.get(normalize(name));
      if (group == null) {
        return false;
      }
      group.enabled = enabled;
      return true;
    }
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
    synchronized (stateLock) {
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
  }

  public boolean addDevice(String groupName, String device, boolean forceMove) {
    return addMember(groupName, device, forceMove);
  }

  /**
   * NAME
   *   hasDevice - Return whether one specific group contains a device label.
   *
   * PARAMETERS
   *   groupName - Group name.
   *   device - Device label.
   *
   * RETURNS
   *   True when the target group's member map contains the normalized label.
   */
  public boolean hasDevice(String groupName, String device) {
    synchronized (stateLock) {
      Group group = groups.get(normalize(groupName));
      if (group == null) {
        return false;
      }
      String deviceKey = normalize(device);
      if (deviceKey.isEmpty()) {
        return false;
      }
      return group.members.containsKey(deviceKey);
    }
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
    synchronized (stateLock) {
      Group group = groups.get(normalize(groupName));
      if (group == null) {
        return false;
      }
      String deviceKey = normalize(device);
      group.members.remove(deviceKey);
      return true;
    }
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
    synchronized (stateLock) {
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
    synchronized (stateLock) {
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
    synchronized (stateLock) {
      Group group = groups.get(normalize(groupName));
      if (group == null) {
        return false;
      }
      group.bindings.clear();
      return true;
    }
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
    synchronized (stateLock) {
      Group group = groups.get(normalize(groupName));
      if (group == null || kind == null) {
        return false;
      }
      group.bindings.add(new Binding(input, kind, value));
      return true;
    }
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
      clearBindingActivity();
      return;
    }
    if (core.isTestRunning()) {
      clearBindingActivity();
      return;
    }
    List<Group> groupSnapshot;
    synchronized (stateLock) {
      groupSnapshot = copyGroups(groups.values());
    }
    Map<String, GroupActivity> activityByGroupKey = new LinkedHashMap<>();
    for (Group group : groupSnapshot) {
      group.lastSkippedMembers.clear();
      group.bindingActive = false;
      group.lastBindingOutput = 0.0;
      if (!group.enabled) {
        continue;
      }
      if (selected != null && selected.enabled && groupHasSelectedDevice(group, selected)) {
        continue;
      }
      if (selected != null
          && selected.groupEnabled
          && (sameKey(selected.group, group.name)
              || groupHasManualOverrideMember(group, selected))) {
        continue;
      }
      double output = computeGroupOutput(group, input);
      String dutyWriteSource = bindingDutyWriteSource(group.name);
      if (Math.abs(output) < 1e-6 && group.bindings.isEmpty()) {
        continue;
      }
      if (Math.abs(output) >= 1e-6) {
        group.bindingActive = true;
        group.lastBindingOutput = output;
      }
      for (MemberState member : snapshotMembers(group)) {
        if (!member.enabled) {
          continue;
        }
        if (!core.setDutyByDeviceLabel(member.label, output, dutyWriteSource)) {
          group.lastSkippedMembers.add(member.label);
        }
      }
      activityByGroupKey.put(
          normalize(group.name),
          new GroupActivity(group.bindingActive, group.lastBindingOutput, group.lastSkippedMembers));
    }
    synchronized (stateLock) {
      applyGroupActivityUpdates(activityByGroupKey);
    }
  }

  /**
   * NAME
   *   bindingDutyWriteSource - Build a stable source tag for binding-owned writes.
   */
  private String bindingDutyWriteSource(String groupName) {
    String suffix = groupName != null ? groupName.trim() : EMPTY_STRING;
    return DUTY_WRITE_SOURCE_BINDING_PREFIX + suffix;
  }

  /**
   * NAME
   *   computeGroupOutput - Sum all binding outputs for a group.
   */
  private double computeGroupOutput(Group group, InputSnapshot input) {
    double sum = 0.0;
    for (Binding binding : snapshotBindings(group)) {
      double value = computeBindingOutput(binding, input, group.name);
      sum += value;
    }
    return clamp(sum, -1.0, 1.0);
  }

  static List<Group> snapshotGroups(Map<String, Group> groupsByKey) {
    return groupsByKey == null ? List.of() : new ArrayList<>(groupsByKey.values());
  }

  static List<MemberState> snapshotMembers(Group group) {
    return group == null ? List.of() : new ArrayList<>(group.members.values());
  }

  static List<Binding> snapshotBindings(Group group) {
    return group == null ? List.of() : new ArrayList<>(group.bindings);
  }

  private boolean groupHasManualOverrideMember(Group group, SelectedState selected) {
    if (group == null || selected == null || selected.groupMembers.isEmpty()) {
      return false;
    }
    for (MemberState member : group.members.values()) {
      if (member == null || member.label == null || member.label.isBlank()) {
        continue;
      }
      if (selected.groupMembers.contains(normalize(member.label))) {
        return true;
      }
    }
    return false;
  }

  private boolean groupHasSelectedDevice(Group group, SelectedState selected) {
    if (group == null
        || selected == null
        || selected.device == null
        || selected.device.isBlank()) {
      return false;
    }
    for (MemberState member : group.members.values()) {
      if (member == null || member.label == null || member.label.isBlank()) {
        continue;
      }
      if (sameKey(selected.device, member.label)) {
        return true;
      }
    }
    return false;
  }

  /**
   * NAME
   *   hasActiveBindingForDevice - Return whether a nonzero binding currently owns one device.
   *
   * PARAMETERS
   *   device - Device label.
   *
   * RETURNS
   *   True when any enabled runtime group with a nonzero current binding output contains the device.
   */
  public boolean hasActiveBindingForDevice(String device) {
    synchronized (stateLock) {
      String deviceKey = normalize(device);
      if (deviceKey.isEmpty()) {
        return false;
      }
      for (Group group : groups.values()) {
        if (group == null || !group.bindingActive || !group.enabled) {
          continue;
        }
        if (group.members.containsKey(deviceKey)) {
          return true;
        }
      }
      return false;
    }
  }

  /**
   * NAME
   *   hasActiveBindingForGroup - Return whether any member of one group is currently owned by a binding.
   *
   * PARAMETERS
   *   groupName - Group name to inspect.
   *
   * RETURNS
   *   True when any enabled member overlaps a nonzero active binding group.
   */
  public boolean hasActiveBindingForGroup(String groupName) {
    synchronized (stateLock) {
      Group group = groups.get(normalize(groupName));
      if (group == null) {
        return false;
      }
      for (MemberState member : group.members.values()) {
        if (member == null || !member.enabled || member.label == null || member.label.isBlank()) {
          continue;
        }
        if (hasActiveBindingForDeviceUnsafe(member.label)) {
          return true;
        }
      }
      return false;
    }
  }

  private void clearBindingActivity() {
    synchronized (stateLock) {
      for (Group group : groups.values()) {
        if (group == null) {
          continue;
        }
        group.bindingActive = false;
        group.lastBindingOutput = 0.0;
        group.lastSkippedMembers.clear();
      }
    }
  }

  private boolean hasActiveBindingForDeviceUnsafe(String device) {
    String deviceKey = normalize(device);
    if (deviceKey.isEmpty()) {
      return false;
    }
    for (Group group : groups.values()) {
      if (group == null || !group.bindingActive || !group.enabled) {
        continue;
      }
      if (group.members.containsKey(deviceKey)) {
        return true;
      }
    }
    return false;
  }

  private void applyGroupActivityUpdates(Map<String, GroupActivity> activityByGroupKey) {
    for (Map.Entry<String, GroupActivity> entry : activityByGroupKey.entrySet()) {
      Group group = groups.get(entry.getKey());
      GroupActivity activity = entry.getValue();
      if (group == null || activity == null) {
        continue;
      }
      group.bindingActive = activity.bindingActive;
      group.lastBindingOutput = activity.lastBindingOutput;
      group.lastSkippedMembers.clear();
      group.lastSkippedMembers.addAll(activity.lastSkippedMembers);
    }
  }

  private static List<Group> copyGroups(Iterable<Group> sourceGroups) {
    List<Group> copies = new ArrayList<>();
    if (sourceGroups == null) {
      return copies;
    }
    for (Group group : sourceGroups) {
      Group copy = copyGroup(group);
      if (copy != null) {
        copies.add(copy);
      }
    }
    return copies;
  }

  private static Group copyGroup(Group group) {
    if (group == null) {
      return null;
    }
    Group copy = new Group(group.name);
    copy.enabled = group.enabled;
    for (Map.Entry<String, MemberState> memberEntry : group.members.entrySet()) {
      MemberState member = memberEntry.getValue();
      if (member == null) {
        continue;
      }
      copy.members.put(memberEntry.getKey(), new MemberState(member.label, member.enabled));
    }
    for (Binding binding : group.bindings) {
      if (binding == null) {
        continue;
      }
      Binding bindingCopy = new Binding(binding.input, binding.kind, binding.value);
      bindingCopy.toggled = binding.toggled;
      copy.bindings.add(bindingCopy);
    }
    copy.lastSkippedMembers.addAll(group.lastSkippedMembers);
    copy.bindingActive = group.bindingActive;
    copy.lastBindingOutput = group.lastBindingOutput;
    return copy;
  }

  private static final class GroupActivity {
    final boolean bindingActive;
    final double lastBindingOutput;
    final List<String> lastSkippedMembers;

    GroupActivity(boolean bindingActive, double lastBindingOutput, List<String> lastSkippedMembers) {
      this.bindingActive = bindingActive;
      this.lastBindingOutput = lastBindingOutput;
      this.lastSkippedMembers =
          lastSkippedMembers != null ? new ArrayList<>(lastSkippedMembers) : List.of();
    }
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
    double controllerValue = resolveControllerInput(key, snapshot);
    if (!Double.isNaN(controllerValue)) {
      return controllerValue;
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

  private double resolveControllerInput(String key, InputSnapshot snapshot) {
    if (key == null || snapshot == null || !key.startsWith(InputAliasResolver.KEY_CONTROLLER_PREFIX)) {
      return Double.NaN;
    }
    int firstSep = key.indexOf('.');
    if (firstSep <= InputAliasResolver.KEY_CONTROLLER_PREFIX.length()) {
      return Double.NaN;
    }
    int controllerIndex;
    try {
      controllerIndex = Integer.parseInt(
          key.substring(InputAliasResolver.KEY_CONTROLLER_PREFIX.length(), firstSep));
    } catch (NumberFormatException ex) {
      return Double.NaN;
    }
    if (controllerIndex < 0 || controllerIndex >= snapshot.controllers.length) {
      return Double.NaN;
    }
    ControllerState state = snapshot.controllers[controllerIndex];
    String suffix = key.substring(firstSep + 1);
    if (sameKey(suffix, "left.y")) {
      return state.leftY;
    }
    if (sameKey(suffix, "right.y")) {
      return state.rightY;
    }
    if (sameKey(suffix, "left.x")) {
      return state.leftX;
    }
    if (sameKey(suffix, "right.x")) {
      return state.rightX;
    }
    if (sameKey(suffix, "left.trigger")) {
      return state.leftTrigger;
    }
    if (sameKey(suffix, "right.trigger")) {
      return state.rightTrigger;
    }
    if (sameKey(suffix, "a")) {
      return state.a ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "b")) {
      return state.b ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "x")) {
      return state.x ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "y")) {
      return state.y ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "lb")) {
      return state.lb ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "rb")) {
      return state.rb ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "back")) {
      return state.back ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "start")) {
      return state.start ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "ls")) {
      return state.ls ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "rs")) {
      return state.rs ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "dpad.up")) {
      return state.dpadUp ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "dpad.right")) {
      return state.dpadRight ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "dpad.down")) {
      return state.dpadDown ? 1.0 : 0.0;
    }
    if (sameKey(suffix, "dpad.left")) {
      return state.dpadLeft ? 1.0 : 0.0;
    }
    return Double.NaN;
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
