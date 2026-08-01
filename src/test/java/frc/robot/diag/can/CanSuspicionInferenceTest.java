package frc.robot.diag.can;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.CanSuspicionAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.ImuAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
import org.junit.jupiter.api.Test;

class CanSuspicionInferenceTest {

  @Test
  void ctreMotorStickyFaultsAreReportedAsStickyFault() {
    DeviceSnapshot snapshot = new DeviceSnapshot();
    snapshot.deviceType = "FALCON";
    snapshot.present = true;
    CtreMotorAttachment ctre = new CtreMotorAttachment();
    ctre.stickyFaultsRaw = 16;
    snapshot.addAttachment(ctre);

    CanSuspicionAttachment result = CanSuspicionInference.infer(snapshot, validBus());

    assertNotNull(result);
    assertEquals("STICKY_FAULT", result.likelyState);
    assertEquals("Device reports sticky faults.", result.likelyMeaning);
  }

  @Test
  void revActiveWarningsAreReportedAsActiveWarning() {
    DeviceSnapshot snapshot = new DeviceSnapshot();
    snapshot.deviceType = "NEO";
    snapshot.present = true;
    RevMotorAttachment rev = new RevMotorAttachment();
    rev.warningsRaw = 64;
    snapshot.addAttachment(rev);

    CanSuspicionAttachment result = CanSuspicionInference.infer(snapshot, validBus());

    assertNotNull(result);
    assertEquals("ACTIVE_WARNING", result.likelyState);
    assertEquals("Device reports active warnings.", result.likelyMeaning);
  }

  @Test
  void pigeonStickyFaultsAreReportedAsStickyFault() {
    DeviceSnapshot snapshot = new DeviceSnapshot();
    snapshot.deviceType = "Pigeon";
    snapshot.present = true;
    ImuAttachment imu = new ImuAttachment();
    imu.stickyFaultsRaw = 540672;
    snapshot.addAttachment(imu);

    CanSuspicionAttachment result = CanSuspicionInference.infer(snapshot, validBus());

    assertNotNull(result);
    assertEquals("STICKY_FAULT", result.likelyState);
    assertEquals("Device reports sticky faults.", result.likelyMeaning);
  }

  private static BusSnapshot validBus() {
    BusSnapshot bus = new BusSnapshot();
    bus.valid = true;
    return bus;
  }
}
