package frc.robot.diag.lifecycle.groups;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.BridgeGroupManager;
import frc.robot.BringupUtil;
import frc.robot.DeviceLifecycleRegistry;
import frc.robot.diag.lifecycle.runtime.DeviceRuntimeState;
import frc.robot.diag.snapshots.DevicePresenceCheckAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ResolvedGroupStatesTest {
  private static final String PROFILE_NAME = "test_profile";
  private static final String GROUP_NAME = "motors";
  private static final String FALCON_LABEL = "FALCON 9";
  private static final String SPARK_LABEL = "SPARKMAX/NEO 25";
  private static final String FALCON_KEY = "falcon 9";
  private static final String SPARK_KEY = "sparkmax/neo 25";
  private static final String BUS_CAN = "CAN";
  private static final String VENDOR_CTRE = "CTRE";
  private static final String VENDOR_REV = "REV";
  private static final String TYPE_MOTOR = "motor";
  private static final String MOTOR_NAME_FALCON = "Talon FX";
  private static final String MOTOR_NAME_SPARK = "NEO";
  private static final int FALCON_ID = 9;
  private static final int SPARK_ID = 25;
  private static final int FALCON_MFG = 4;
  private static final int SPARK_MFG = 5;
  private static final int DEVICE_TYPE_MOTOR_NUMERIC = 2;
  private static final long NOW_MS = 1000L;

  @Test
  void resolveBuildsSharedGroupFactsFromLifecycleAndRuntimeState() {
    BridgeGroupManager.Group group = new BridgeGroupManager.Group(GROUP_NAME);
    group.members.put(FALCON_KEY, new BridgeGroupManager.MemberState(FALCON_LABEL, true));
    group.members.put(SPARK_KEY, new BridgeGroupManager.MemberState(SPARK_LABEL, false));

    DeviceLifecycleRegistry lifecycleRegistry = new DeviceLifecycleRegistry();
    List<BringupUtil.DeviceEntry> entries =
        List.of(
            new BringupUtil.DeviceEntry(
                FALCON_ID,
                FALCON_MFG,
                DEVICE_TYPE_MOTOR_NUMERIC,
                BUS_CAN,
                VENDOR_CTRE,
                TYPE_MOTOR,
                FALCON_LABEL,
                MOTOR_NAME_FALCON,
                null,
                null,
                null),
            new BringupUtil.DeviceEntry(
                SPARK_ID,
                SPARK_MFG,
                DEVICE_TYPE_MOTOR_NUMERIC,
                BUS_CAN,
                VENDOR_REV,
                TYPE_MOTOR,
                SPARK_LABEL,
                MOTOR_NAME_SPARK,
                null,
                null,
                null));
    lifecycleRegistry.resetForProfile(
        PROFILE_NAME,
        entries,
        NOW_MS);

    Map<String, DeviceSnapshot> snapshotsByLabel = new LinkedHashMap<>();
    snapshotsByLabel.put(FALCON_KEY, presentSnapshot(FALCON_LABEL));
    Map<String, Boolean> instantiatedByLabel = new LinkedHashMap<>();
    instantiatedByLabel.put(FALCON_KEY, true);
    instantiatedByLabel.put(SPARK_KEY, false);
    Map<String, Boolean> inScopeByLabel = new LinkedHashMap<>();
    inScopeByLabel.put(FALCON_KEY, true);
    inScopeByLabel.put(SPARK_KEY, false);
    lifecycleRegistry.refresh(entries, snapshotsByLabel, instantiatedByLabel, inScopeByLabel, NOW_MS);

    Map<String, DeviceRuntimeState> runtimeByLabel = new LinkedHashMap<>();
    DeviceRuntimeState falconRuntime = new DeviceRuntimeState();
    falconRuntime.markActivated("session-1", GROUP_NAME, "FORCE");
    runtimeByLabel.put(FALCON_LABEL, falconRuntime);

    ResolvedGroupStates.ResolvedGroupState resolved =
        ResolvedGroupStates.resolve(
            group,
            lifecycleRegistry::viewForLabel,
            runtimeByLabel::get,
            true);

    assertEquals(GROUP_NAME, resolved.name);
    assertEquals(FALCON_LABEL, resolved.primaryLabel);
    assertEquals(2, resolved.memberCount);
    assertEquals(1, resolved.enabledMemberCount);
    assertTrue(resolved.hasMembers);
    assertTrue(resolved.allEnabledMembersPresent);

    ResolvedGroupStates.ResolvedGroupMemberState falcon = resolved.members.get(0);
    assertEquals(FALCON_LABEL, falcon.label);
    assertTrue(falcon.enabled);
    assertTrue(falcon.locked);
    assertFalse(falcon.invalid);
    assertTrue(falcon.scopeActive);
    assertTrue(falcon.runtimePresent);
    assertTrue(falcon.instantiated);
    assertTrue(falcon.testable);

    ResolvedGroupStates.ResolvedGroupMemberState spark = resolved.members.get(1);
    assertEquals(SPARK_LABEL, spark.label);
    assertFalse(spark.enabled);
    assertTrue(spark.locked);
    assertFalse(spark.invalid);
    assertFalse(spark.scopeActive);
    assertFalse(spark.runtimePresent);
    assertFalse(spark.instantiated);
    assertFalse(spark.testable);
  }

  private static DeviceSnapshot presentSnapshot(String label) {
    DeviceSnapshot snapshot = new DeviceSnapshot();
    snapshot.label = label;
    DevicePresenceCheckAttachment presence = new DevicePresenceCheckAttachment();
    presence.score = DevicePresenceCheckAttachment.SCORE_PRESENT;
    presence.maxScore = DevicePresenceCheckAttachment.MAX_SCORE;
    snapshot.addAttachment(presence);
    return snapshot;
  }
}
