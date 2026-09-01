package frc.robot.diag.probe;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.BringupUtil;
import frc.robot.devices.ctre.CtreCANCoderDevice;
import frc.robot.devices.ctre.CtrePigeonDevice;
import frc.robot.devices.ni.RoboRioDevice;
import frc.robot.diag.snapshots.RobotControllerBusAttachment;
import frc.robot.diag.snapshots.RobotControllerRailsAttachment;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ActiveDevicePresenceProbeTest {
  private static BringupUtil.DeviceEntry deviceEntry(
      int id,
      String deviceInterface,
      String vendor,
      String type,
      String label) {
    return new BringupUtil.DeviceEntry(
        id,
        0,
        0,
        deviceInterface,
        vendor,
        type,
        label,
        "",
        null,
        List.of(),
        null);
  }

  @Test
  void mergeProbeEntriesAddsSupplementalProbeCapableSingletonsWithoutDuplicates() {
    List<BringupUtil.DeviceEntry> activeEntries =
        List.of(deviceEntry(9, "CAN", "CTRE", "motor", "FALCON 9"));
    List<BringupUtil.DeviceEntry> profileEntries =
        List.of(
            deviceEntry(9, "CAN", "CTRE", "motor", "FALCON 9"),
            deviceEntry(20, "CAN", "CTRE", "PDP", "pdp"),
            deviceEntry(0, "CAN", "NI", "robotController", "roborio"));

    List<BringupUtil.DeviceEntry> merged =
        ActiveDevicePresenceProbe.mergeProbeEntries(
            activeEntries,
            profileEntries,
            Map.of("pdp", "PDP"));

    assertEquals(2, merged.size());
    assertEquals("FALCON 9", merged.get(0).label);
    assertEquals("pdp", merged.get(1).label);
  }

  @Test
  void supplementalProbeTargetsOnlyIncludeSafePowerDistributionModels() {
    assertTrue(ActiveDevicePresenceProbe.isSupplementalProbeTarget("PDP"));
    assertTrue(ActiveDevicePresenceProbe.isSupplementalProbeTarget("PDH"));
    assertFalse(ActiveDevicePresenceProbe.isSupplementalProbeTarget("TALON_FX"));
    assertFalse(ActiveDevicePresenceProbe.isSupplementalProbeTarget("UNSUPPORTED"));
  }

  @Test
  void inferProbeModelRecognizesCancoderAndPigeonTargets() {
    assertEquals(
        "CANCODER",
        ActiveDevicePresenceProbe.inferProbeModel(
            new CtreCANCoderDevice(18, "cancoder", new BringupUtil.LimitConfig())));
    assertEquals(
        "PIGEON",
        ActiveDevicePresenceProbe.inferProbeModel(
            new CtrePigeonDevice(19, "pigeon 2")));
    assertEquals(
        "ROBORIO",
        ActiveDevicePresenceProbe.inferProbeModel(
            new RoboRioDevice(0, "roborio")));
  }

  @Test
  void readableRobotControllerBusAttachmentCountsAsReadableProbeEvidence() {
    RobotControllerBusAttachment bus = new RobotControllerBusAttachment();
    bus.canUtilizationPct = 18.5;
    bus.canRxErrorCount = 0;
    bus.canTxErrorCount = 1;
    bus.canBusOffCount = 0;
    bus.canTxFullCount = 2;

    assertTrue(ActiveDevicePresenceProbe.hasReadableRobotControllerBusAttachment(bus));

    bus.canUtilizationPct = 120.0;
    assertFalse(ActiveDevicePresenceProbe.hasReadableRobotControllerBusAttachment(bus));
  }

  @Test
  void robotControllerRailHealthHelpersRequireEnabledRailsAndZeroFaults() {
    RobotControllerRailsAttachment rails = new RobotControllerRailsAttachment();
    rails.rail3v3FaultCount = 0;
    rails.rail5vFaultCount = 0;
    rails.rail6vFaultCount = 0;

    assertTrue(ActiveDevicePresenceProbe.isHealthyRobotControllerRail(true, 3.3, 2.5, 4.0));
    assertFalse(ActiveDevicePresenceProbe.isHealthyRobotControllerRail(false, 3.3, 2.5, 4.0));
    assertTrue(ActiveDevicePresenceProbe.hasNoRobotControllerRailFaults(rails));

    rails.rail6vFaultCount = 1;
    assertFalse(ActiveDevicePresenceProbe.hasNoRobotControllerRailFaults(rails));
  }

  @Test
  void weakPowerProbeEvidenceForcesAbsentBucket() {
    assertTrue(ActiveDevicePresenceProbe.shouldForceAbsentForPowerProbe(false, 95));
    assertFalse(ActiveDevicePresenceProbe.shouldForceAbsentForPowerProbe(true, 0));
  }

  @Test
  void idlePowerSnapshotStillCountsAsStrongPresenceEvidence() {
    assertTrue(
        ActiveDevicePresenceProbe.hasStrongPowerPresenceEvidence(
            12.4,
            0.0,
            0.0,
            new double[] {0.0, 0.0, 0.0}));
  }

  @Test
  void invalidPowerSnapshotDoesNotCountAsStrongPresenceEvidence() {
    assertFalse(
        ActiveDevicePresenceProbe.hasStrongPowerPresenceEvidence(
            0.0,
            25.0,
            0.0,
            new double[] {0.0}));
    assertFalse(
        ActiveDevicePresenceProbe.hasStrongPowerPresenceEvidence(
            12.4,
            25.0,
            0.0,
            null));
    assertFalse(
        ActiveDevicePresenceProbe.hasStrongPowerPresenceEvidence(
            12.4,
            25.0,
            Double.NaN,
            new double[] {0.0}));
  }

  @Test
  void incrementalRunWithNullCoreCompletesWithFailureSession() {
    ActiveDevicePresenceProbe probe = new ActiveDevicePresenceProbe();

    ActiveDevicePresenceProbe.ProbeStepResult step = probe.beginRun(null, true).advance();

    assertTrue(step.complete);
    assertEquals("error", step.session.status);
    assertEquals("incremental", step.session.mode);
  }
}
