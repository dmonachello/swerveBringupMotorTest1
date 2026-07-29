package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class BridgeUiCommandHandlerSelectionTest {
  private static final String DEVICE_LABEL = "FALCON 9";
  private static final String GROUP_NAME = "motors";
  private static final String MEMBER_ONE = "FALCON 9";
  private static final String MEMBER_TWO = "SPARKMAX/NEO 25";
  private static final BringupUtil.DeviceEntry PDP_ENTRY =
      new BringupUtil.DeviceEntry(
          20, 4, 8, "CAN", "CTRE", "pdp", "pdp", "PDP", null, null, null);
  private static final BringupUtil.DeviceEntry FALCON_ENTRY =
      new BringupUtil.DeviceEntry(
          9, 4, 2, "CAN", "CTRE", "falcon", DEVICE_LABEL, "FALCON", null, null, null);

  @Test
  void stageManualDeviceSelectionClearsGroupOwnershipAndPublishesDeviceOwner() {
    BridgeGroupManager.SelectedState selected = new BridgeGroupManager.SelectedState();
    selected.group = GROUP_NAME;
    selected.groupEnabled = true;
    selected.groupMembers.add(MEMBER_ONE.toLowerCase());

    BridgeUiCommandHandler.stageManualDeviceSelection(selected, DEVICE_LABEL);

    assertEquals(DEVICE_LABEL, selected.device);
    assertTrue(selected.enabled);
    assertEquals("", selected.group);
    assertFalse(selected.groupEnabled);
    assertTrue(selected.groupMembers.isEmpty());
  }

  @Test
  void stageManualGroupSelectionPublishesOwnershipBeforeWrites() {
    BridgeGroupManager.SelectedState selected = new BridgeGroupManager.SelectedState();
    selected.device = DEVICE_LABEL;
    selected.enabled = true;
    BridgeGroupManager.Group group = new BridgeGroupManager.Group(GROUP_NAME);
    group.members.put("falcon", new BridgeGroupManager.MemberState(MEMBER_ONE, true));
    group.members.put("neo", new BridgeGroupManager.MemberState(MEMBER_TWO, true));

    BridgeUiCommandHandler.stageManualGroupSelection(selected, group);

    assertEquals("", selected.device);
    assertFalse(selected.enabled);
    assertEquals(GROUP_NAME, selected.group);
    assertTrue(selected.groupEnabled);
    assertEquals(2, selected.groupMembers.size());
    assertTrue(selected.groupMembers.contains(MEMBER_ONE.toLowerCase()));
    assertTrue(selected.groupMembers.contains(MEMBER_TWO.toLowerCase()));
  }

  @Test
  void stageManualGroupSelectionClearsOwnershipWhenGroupMissing() {
    BridgeGroupManager.SelectedState selected = new BridgeGroupManager.SelectedState();
    selected.device = DEVICE_LABEL;
    selected.enabled = true;
    selected.group = GROUP_NAME;
    selected.groupEnabled = true;
    selected.groupMembers.add(MEMBER_ONE.toLowerCase());

    BridgeUiCommandHandler.stageManualGroupSelection(selected, null);

    assertEquals("", selected.device);
    assertFalse(selected.enabled);
    assertEquals("", selected.group);
    assertFalse(selected.groupEnabled);
    assertTrue(selected.groupMembers.isEmpty());
  }

  @Test
  void runtimeLifecycleKindForEntryUsesDeviceTypeInsteadOfLabelHeuristics() {
    assertEquals("SINGLETON", BridgeUiCommandHandler.runtimeLifecycleKindForEntry(PDP_ENTRY));
    assertEquals("NORMAL", BridgeUiCommandHandler.runtimeLifecycleKindForEntry(FALCON_ENTRY));
  }
}
