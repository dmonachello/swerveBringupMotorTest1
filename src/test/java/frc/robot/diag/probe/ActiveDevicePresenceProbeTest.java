package frc.robot.diag.probe;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.BringupUtil;
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
            deviceEntry(0, "CAN", "NI", "roboRIO", "roborio"));

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
}
