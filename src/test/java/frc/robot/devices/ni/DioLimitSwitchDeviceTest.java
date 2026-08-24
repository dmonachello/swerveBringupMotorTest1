package frc.robot.devices.ni;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import edu.wpi.first.wpilibj.simulation.DIOSim;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   DioLimitSwitchDeviceTest - Regression tests for limit-switch proof tracking.
 */
class DioLimitSwitchDeviceTest {
  private static final int TEST_DIO_CHANNEL = 0;
  private static final String TEST_LABEL = "lmtSw0";

  @Test
  void snapshotTracksTransitionsAndProofStateAcrossObservedEdges() {
    DioLimitSwitchDevice device = new DioLimitSwitchDevice(TEST_DIO_CHANNEL, TEST_LABEL, false);
    device.ensureCreated();
    try {
      DIOSim dioSim = new DIOSim(TEST_DIO_CHANNEL);
      dioSim.setValue(false);

      LimitsAttachment.LimitSwitchState initial = extractState(device.snapshot());
      assertEquals(0, initial.transitionCountSinceActivate);
      assertEquals(false, initial.changedSinceActivate);
      assertEquals(LimitsAttachment.PROOF_STATE_UNPROVEN, initial.proofState);

      dioSim.setValue(true);
      LimitsAttachment.LimitSwitchState firstEdge = extractState(device.snapshot());
      assertEquals(1, firstEdge.transitionCountSinceActivate);
      assertEquals(true, firstEdge.changedSinceActivate);
      assertEquals(LimitsAttachment.PROOF_STATE_PARTIAL, firstEdge.proofState);
      assertNotNull(firstEdge.lastChangeSec);

      dioSim.setValue(false);
      LimitsAttachment.LimitSwitchState secondEdge = extractState(device.snapshot());
      assertEquals(2, secondEdge.transitionCountSinceActivate);
      assertEquals(true, secondEdge.changedSinceActivate);
      assertEquals(LimitsAttachment.PROOF_STATE_PROVEN, secondEdge.proofState);
      assertNotNull(secondEdge.lastChangeSec);
    } finally {
      device.close();
    }
  }

  private static LimitsAttachment.LimitSwitchState extractState(DeviceSnapshot snapshot) {
    LimitsAttachment limits = snapshot.getAttachment(LimitsAttachment.class);
    return limits != null && !limits.switches.isEmpty() ? limits.switches.get(0) : null;
  }
}
