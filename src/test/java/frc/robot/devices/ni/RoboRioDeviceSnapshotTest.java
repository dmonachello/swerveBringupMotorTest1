package frc.robot.devices.ni;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.RobotControllerBusAttachment;
import frc.robot.diag.snapshots.RobotControllerPowerAttachment;
import frc.robot.diag.snapshots.RobotControllerRailsAttachment;
import frc.robot.manufacturers.ni.diag.RoboRioPowerAttachment;
import frc.robot.manufacturers.ni.diag.RoboRioRailsAttachment;
import frc.robot.manufacturers.ni.util.RoboRioStatusReader;
import org.junit.jupiter.api.Test;

class RoboRioDeviceSnapshotTest {
  private static final int CAN_ID = 0;
  private static final String LABEL = "roborio";
  private static final double INPUT_VOLTAGE = 12.6;
  private static final double RAIL_6V_CURRENT = 1.75;

  @Test
  void snapshotPreservesCurrentVirtualNoteAndAddsStructuredNiAttachments() {
    RoboRioDevice device =
        new RoboRioDevice(CAN_ID, LABEL, new RoboRioStatusReader(new FakeTelemetrySource()));

    DeviceSnapshot snapshot = device.snapshot();
    RobotControllerPowerAttachment sharedPower = snapshot.getAttachment(RobotControllerPowerAttachment.class);
    RobotControllerRailsAttachment sharedRails = snapshot.getAttachment(RobotControllerRailsAttachment.class);
    RobotControllerBusAttachment sharedBus = snapshot.getAttachment(RobotControllerBusAttachment.class);
    RoboRioPowerAttachment power = snapshot.getAttachment(RoboRioPowerAttachment.class);
    RoboRioRailsAttachment rails = snapshot.getAttachment(RoboRioRailsAttachment.class);

    assertTrue(snapshot.present);
    assertEquals("virtual", snapshot.note);
    assertNotNull(sharedPower);
    assertNotNull(sharedRails);
    assertNotNull(sharedBus);
    assertNotNull(power);
    assertNotNull(rails);
    assertEquals(INPUT_VOLTAGE, power.inputVoltage);
    assertEquals(INPUT_VOLTAGE, sharedPower.inputVoltage);
    assertEquals(RAIL_6V_CURRENT, rails.rail6vCurrent);
    assertEquals(RAIL_6V_CURRENT, sharedRails.rail6vCurrent);
    assertEquals(18.5, sharedBus.canUtilizationPct);
  }

  private static final class FakeTelemetrySource implements RoboRioStatusReader.TelemetrySource {
    @Override
    public double inputVoltage() {
      return INPUT_VOLTAGE;
    }

    @Override
    public boolean brownedOut() {
      return false;
    }

    @Override
    public double brownoutVoltage() {
      return 6.4;
    }

    @Override
    public double rail3v3Voltage() {
      return 3.3;
    }

    @Override
    public double rail3v3Current() {
      return 0.2;
    }

    @Override
    public boolean rail3v3Enabled() {
      return true;
    }

    @Override
    public int rail3v3FaultCount() {
      return 0;
    }

    @Override
    public double rail5vVoltage() {
      return 5.0;
    }

    @Override
    public double rail5vCurrent() {
      return 0.8;
    }

    @Override
    public boolean rail5vEnabled() {
      return true;
    }

    @Override
    public int rail5vFaultCount() {
      return 0;
    }

    @Override
    public double rail6vVoltage() {
      return 6.1;
    }

    @Override
    public double rail6vCurrent() {
      return RAIL_6V_CURRENT;
    }

    @Override
    public boolean rail6vEnabled() {
      return true;
    }

    @Override
    public int rail6vFaultCount() {
      return 1;
    }

    @Override
    public double canUtilizationPct() {
      return 18.5;
    }

    @Override
    public int canRxErrorCount() {
      return 2;
    }

    @Override
    public int canTxErrorCount() {
      return 3;
    }

    @Override
    public int canBusOffCount() {
      return 0;
    }

    @Override
    public int canTxFullCount() {
      return 1;
    }
  }
}
