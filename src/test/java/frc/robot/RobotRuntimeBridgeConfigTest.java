package frc.robot;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   RobotRuntimeBridgeConfigTest - Regression tests for Robot bridge-config sync.
 */
class RobotRuntimeBridgeConfigTest {

  @Test
  void synchronizeRuntimeBridgeConfigPreservesManualActiveGroupMembers() {
    BridgeGroupManager groups = new BridgeGroupManager();
    groups.createGroup("active-group");
    groups.addDevice("active-group", "FALCON 9", false);
    groups.addDevice("active-group", "SPARKMAX/NEO 25", false);
    groups.setMemberEnabled("active-group", "SPARKMAX/NEO 25", false);

    BridgeGroupManager.SelectedState selected = new BridgeGroupManager.SelectedState();
    selected.group = "active-group";
    selected.groupEnabled = true;
    selected.groupMembers.add("FALCON 9");

    BringupUtil.BridgeProfileRuntimeConfig config =
        new BringupUtil.BridgeProfileRuntimeConfig(
            List.of(
                new BringupUtil.BridgeProfileGroupConfig(
                    "motors",
                    true,
                    List.of(
                        new BringupUtil.BridgeProfileMemberConfig("FALCON 9", true),
                        new BringupUtil.BridgeProfileMemberConfig("SPARKMAX/NEO 25", true)),
                    List.of())),
            new BringupUtil.BridgeProfileSelectedDeviceConfig("FALCON 9", true));

    Robot.synchronizeRuntimeBridgeConfig(groups, selected, config, List.of());

    assertTrue(groups.hasDevice("active-group", "FALCON 9"));
    assertTrue(groups.hasDevice("active-group", "SPARKMAX/NEO 25"));
    assertFalse(groups.getGroup("active-group").members.get("sparkmax/neo 25").enabled);
    assertTrue(selected.groupMembers.isEmpty());
  }
}
