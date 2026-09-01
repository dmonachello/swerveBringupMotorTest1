package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.diag.snapshots.DevicePresenceCheckAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   DeviceLifecycleRegistryTest - Regression tests for lifecycle refresh semantics.
 */
class DeviceLifecycleRegistryTest {
  private static final long NOW_MS = 1000L;
  private static final String PROFILE_NAME = "test_profile";
  private static final String LABEL_FALCON = "FALCON 9";
  private static final int CAN_ID_FALCON = 9;
  private static final int MANUFACTURER_CTRE = 4;
  private static final int DEVICE_TYPE_MOTOR = 2;
  private static final String INTERFACE_CAN = "CAN";
  private static final String VENDOR_CTRE = "CTRE";
  private static final String TYPE_FALCON = "falcon";
  private static final String MODEL_FALCON = "FALCON";

  @Test
  void refreshKeepsInstantiatedDevicePresentWhenSnapshotIsSkipped() {
    DeviceLifecycleRegistry registry = new DeviceLifecycleRegistry();
    registry.resetForProfile(PROFILE_NAME, List.of(deviceEntry(LABEL_FALCON)), NOW_MS);

    registry.refresh(
        List.of(deviceEntry(LABEL_FALCON)),
        Map.of(LABEL_FALCON.toLowerCase(), presentSnapshot(LABEL_FALCON, CAN_ID_FALCON)),
        Map.of(LABEL_FALCON.toLowerCase(), true),
        Map.of(LABEL_FALCON.toLowerCase(), true),
        NOW_MS);

    DeviceLifecycleRegistry.DeviceLifecycleView initial = registry.viewForLabel(LABEL_FALCON);
    assertTrue(initial.testable);
    assertEquals("instantiated-present", initial.lifecycleState);

    registry.refresh(
        List.of(deviceEntry(LABEL_FALCON)),
        Map.of(),
        Map.of(LABEL_FALCON.toLowerCase(), true),
        Map.of(LABEL_FALCON.toLowerCase(), true),
        NOW_MS + 20L);

    DeviceLifecycleRegistry.DeviceLifecycleView skipped = registry.viewForLabel(LABEL_FALCON);
    assertTrue(skipped.testable);
    assertEquals("instantiated-present", skipped.lifecycleState);
  }

  private static BringupUtil.DeviceEntry deviceEntry(String label) {
    return new BringupUtil.DeviceEntry(
        CAN_ID_FALCON,
        MANUFACTURER_CTRE,
        DEVICE_TYPE_MOTOR,
        INTERFACE_CAN,
        VENDOR_CTRE,
        TYPE_FALCON,
        label,
        MODEL_FALCON,
        null,
        null,
        null);
  }

  private static DeviceSnapshot presentSnapshot(String label, int canId) {
    DeviceSnapshot snapshot = new DeviceSnapshot();
    snapshot.label = label;
    snapshot.canId = canId;
    snapshot.present = true;
    DevicePresenceCheckAttachment attachment = new DevicePresenceCheckAttachment();
    attachment.score = DevicePresenceCheckAttachment.SCORE_PRESENT;
    attachment.maxScore = DevicePresenceCheckAttachment.MAX_SCORE;
    snapshot.addAttachment(attachment);
    return snapshot;
  }
}
