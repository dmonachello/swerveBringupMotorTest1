package frc.robot;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.diag.snapshots.DeviceSnapshot;
import java.util.List;
import org.junit.jupiter.api.Test;

class BridgeUiCommandHandlerRuntimeStateBackoffTest {

  private static final String LABEL = "SPARKMAX/NEO 7";
  private static final String VENDOR = "REV";
  private static final String TYPE = "motor";

  @Test
  void noteDrivenBackoffRecognizesKnownTimeoutFailurePhrases() {
    assertTrue(BridgeUiCommandHandler.noteSuggestsRuntimeStateReadBackoff("read failed: HAL: CAN Receive has Timed Out"));
    assertTrue(BridgeUiCommandHandler.noteSuggestsRuntimeStateReadBackoff("cached unavailable: CAN: Message not found"));
    assertTrue(BridgeUiCommandHandler.noteSuggestsRuntimeStateReadBackoff("CAN message is stale, data is valid but old / too stale"));
    assertFalse(BridgeUiCommandHandler.noteSuggestsRuntimeStateReadBackoff("present"));
  }

  @Test
  void selectedSnapshotAlsoTriggersBackoffWhenLightSnapshotsLookHealthy() {
    DeviceSnapshot healthyLightSnapshot = snapshotWithNote("present");
    DeviceSnapshot failingSelectedSnapshot = snapshotWithNote("read failed: HAL: CAN Receive has Timed Out");

    assertTrue(
        BridgeUiCommandHandler.shouldBackoffRuntimeStateDeviceReads(
            List.of(healthyLightSnapshot),
            failingSelectedSnapshot));
  }

  @Test
  void healthySnapshotsDoNotTriggerBackoff() {
    DeviceSnapshot healthyLightSnapshot = snapshotWithNote("present");

    assertFalse(
        BridgeUiCommandHandler.shouldBackoffRuntimeStateDeviceReads(
            List.of(healthyLightSnapshot),
            null));
  }

  private static DeviceSnapshot snapshotWithNote(String note) {
    DeviceSnapshot snapshot = new DeviceSnapshot();
    snapshot.label = LABEL;
    snapshot.canId = 7;
    snapshot.vendor = VENDOR;
    snapshot.deviceType = TYPE;
    snapshot.present = true;
    snapshot.note = note;
    return snapshot;
  }
}
