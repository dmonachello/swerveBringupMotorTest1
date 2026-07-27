package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Map;
import frc.robot.telemetry.SampledTelemetrySampler;
import org.junit.jupiter.api.Test;

class BridgeGroupManagerTest {
  private static final String GROUP_NAME = "motors";
  private static final String DEVICE_LABEL = "FALCON 9";
  private static final String INPUT_RIGHT_Y = "controller0.rightY";
  private static final double INPUT_VALUE = 0.30;

  @Test
  void applyBindingsRunsWithoutActiveTestAndAttemptsMemberOutput() {
    BridgeGroupManager groups = new BridgeGroupManager();
    groups.createGroup(GROUP_NAME);
    groups.addDevice(GROUP_NAME, DEVICE_LABEL, false);
    groups.addBinding(GROUP_NAME, INPUT_RIGHT_Y, BridgeGroupManager.BindingKind.ANALOG, 0.0);

    BridgeGroupManager.InputSnapshot inputs = new BridgeGroupManager.InputSnapshot();
    inputs.controllers[0].rightY = INPUT_VALUE;

    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());

    groups.applyBindings(inputs, core, new BridgeGroupManager.SelectedState());

    BridgeGroupManager.Group group = groups.getGroup(GROUP_NAME);
    assertTrue(group != null);
    assertEquals(1, group.lastSkippedMembers.size());
    assertEquals(DEVICE_LABEL, group.lastSkippedMembers.get(0));
  }

  @Test
  void applyBindingsSkipsGroupWhenManualGroupOverrideIsActive() {
    BridgeGroupManager groups = new BridgeGroupManager();
    groups.createGroup(GROUP_NAME);
    groups.addDevice(GROUP_NAME, DEVICE_LABEL, false);
    groups.addBinding(GROUP_NAME, INPUT_RIGHT_Y, BridgeGroupManager.BindingKind.ANALOG, 0.0);

    BridgeGroupManager.InputSnapshot inputs = new BridgeGroupManager.InputSnapshot();
    inputs.controllers[0].rightY = INPUT_VALUE;

    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    BridgeGroupManager.SelectedState selected = new BridgeGroupManager.SelectedState();
    selected.group = GROUP_NAME;
    selected.groupEnabled = true;

    groups.applyBindings(inputs, core, selected);

    BridgeGroupManager.Group group = groups.getGroup(GROUP_NAME);
    assertTrue(group != null);
    assertTrue(group.lastSkippedMembers.isEmpty());
  }

  @Test
  void applyBindingsSkipsOverlappingBindingGroupWhenManualOverrideTargetsDifferentGroupName() {
    BridgeGroupManager groups = new BridgeGroupManager();
    groups.createGroup("motors");
    groups.createGroup("active-group");
    groups.addDevice("motors", DEVICE_LABEL, false);
    groups.addDevice("active-group", DEVICE_LABEL, false);
    groups.addBinding("motors", INPUT_RIGHT_Y, BridgeGroupManager.BindingKind.ANALOG, 0.0);

    BridgeGroupManager.InputSnapshot inputs = new BridgeGroupManager.InputSnapshot();
    inputs.controllers[0].rightY = INPUT_VALUE;

    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    BridgeGroupManager.SelectedState selected = new BridgeGroupManager.SelectedState();
    selected.group = "active-group";
    selected.groupEnabled = true;
    selected.groupMembers.add(DEVICE_LABEL.toLowerCase());

    groups.applyBindings(inputs, core, selected);

    BridgeGroupManager.Group motors = groups.getGroup("motors");
    assertTrue(motors != null);
    assertTrue(motors.lastSkippedMembers.isEmpty());
  }

  @Test
  void applyBindingsSkipsOverlappingBindingGroupWhenManualDeviceOverrideIsActive() {
    BridgeGroupManager groups = new BridgeGroupManager();
    groups.createGroup("motors");
    groups.createGroup("active-group");
    groups.addDevice("motors", DEVICE_LABEL, false);
    groups.addDevice("active-group", DEVICE_LABEL, false);
    groups.addBinding("motors", INPUT_RIGHT_Y, BridgeGroupManager.BindingKind.ANALOG, 0.0);

    BridgeGroupManager.InputSnapshot inputs = new BridgeGroupManager.InputSnapshot();
    inputs.controllers[0].rightY = INPUT_VALUE;

    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    BridgeGroupManager.SelectedState selected = new BridgeGroupManager.SelectedState();
    selected.device = DEVICE_LABEL;
    selected.enabled = true;

    groups.applyBindings(inputs, core, selected);

    BridgeGroupManager.Group motors = groups.getGroup("motors");
    assertTrue(motors != null);
    assertTrue(motors.lastSkippedMembers.isEmpty());
  }

  @Test
  void activeBindingTracksOverlappingDeviceOwnershipWhileOutputIsNonzero() {
    BridgeGroupManager groups = new BridgeGroupManager();
    groups.createGroup("motors");
    groups.createGroup("active-group");
    groups.addDevice("motors", DEVICE_LABEL, false);
    groups.addDevice("active-group", DEVICE_LABEL, false);
    groups.addBinding("motors", INPUT_RIGHT_Y, BridgeGroupManager.BindingKind.ANALOG, 0.0);

    BridgeGroupManager.InputSnapshot inputs = new BridgeGroupManager.InputSnapshot();
    inputs.controllers[0].rightY = INPUT_VALUE;

    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());

    groups.applyBindings(inputs, core, new BridgeGroupManager.SelectedState());

    assertTrue(groups.hasActiveBindingForDevice(DEVICE_LABEL));
    assertTrue(groups.hasActiveBindingForGroup("active-group"));
  }

  @Test
  void activeBindingClearsWhenOutputReturnsToZero() {
    BridgeGroupManager groups = new BridgeGroupManager();
    groups.createGroup(GROUP_NAME);
    groups.addDevice(GROUP_NAME, DEVICE_LABEL, false);
    groups.addBinding(GROUP_NAME, INPUT_RIGHT_Y, BridgeGroupManager.BindingKind.ANALOG, 0.0);

    BridgeGroupManager.InputSnapshot activeInputs = new BridgeGroupManager.InputSnapshot();
    activeInputs.controllers[0].rightY = INPUT_VALUE;
    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());

    groups.applyBindings(activeInputs, core, new BridgeGroupManager.SelectedState());
    assertTrue(groups.hasActiveBindingForDevice(DEVICE_LABEL));

    BridgeGroupManager.InputSnapshot zeroInputs = new BridgeGroupManager.InputSnapshot();
    groups.applyBindings(zeroInputs, core, new BridgeGroupManager.SelectedState());

    assertFalse(groups.hasActiveBindingForDevice(DEVICE_LABEL));
    assertFalse(groups.hasActiveBindingForGroup(GROUP_NAME));
  }

  @Test
  void snapshotHelpersAreStableAfterUnderlyingGroupMutation() {
    BridgeGroupManager groups = new BridgeGroupManager();
    groups.createGroup(GROUP_NAME);
    groups.addDevice(GROUP_NAME, DEVICE_LABEL, false);
    groups.addDevice(GROUP_NAME, "SPARKMAX/NEO 25", false);
    groups.addBinding(GROUP_NAME, INPUT_RIGHT_Y, BridgeGroupManager.BindingKind.ANALOG, 0.0);

    BridgeGroupManager.Group group = groups.getGroup(GROUP_NAME);
    assertTrue(group != null);
    var groupSnapshot = BridgeGroupManager.snapshotGroups(Map.of("motors", group));
    var memberSnapshot = BridgeGroupManager.snapshotMembers(group);
    var bindingSnapshot = BridgeGroupManager.snapshotBindings(group);

    groups.removeDevice(GROUP_NAME, "SPARKMAX/NEO 25");
    groups.clearBindings(GROUP_NAME);

    assertEquals(1, groupSnapshot.size());
    assertEquals(2, memberSnapshot.size());
    assertEquals(1, bindingSnapshot.size());
    assertEquals(1, group.members.size());
    assertTrue(group.bindings.isEmpty());
  }
}
