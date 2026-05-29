package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;

import frc.robot.devices.DeviceDslSupport;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.registry.RegistrationHeader;
import frc.robot.tests.dsl.DslSignalRegistry;
import org.junit.jupiter.api.Test;

class DeviceDslSupportTest {
  private static final double CMD_DUTY = 0.26;
  private static final int CAN_ID = 9;

  @Test
  void readMotorSignalReturnsCtreCommandDuty() {
    RecordingCtreDevice device = new RecordingCtreDevice();

    Object value = DeviceDslSupport.readMotorSignal(device, DslSignalRegistry.SIGNAL_OUTPUT_PERCENT_CMD);

    assertEquals(CMD_DUTY, value);
  }

  private static final class RecordingCtreDevice implements DeviceUnit {
    private final DeviceSnapshot snapshot;

    private RecordingCtreDevice() {
      snapshot = new DeviceSnapshot();
      snapshot.vendor = "CTRE";
      snapshot.deviceType = "FALCON";
      snapshot.canId = CAN_ID;
      snapshot.present = true;
      CtreMotorAttachment ctre = new CtreMotorAttachment();
      ctre.cmdDuty = CMD_DUTY;
      snapshot.addAttachment(ctre);
    }

    @Override
    public int getCanId() {
      return CAN_ID;
    }

    @Override
    public String getDeviceType() {
      return "FALCON";
    }

    @Override
    public String getLabel() {
      return "FALCON 9";
    }

    @Override
    public boolean isCreated() {
      return true;
    }

    @Override
    public void ensureCreated() {}

    @Override
    public void close() {}

    @Override
    public void clearFaults() {}

    @Override
    public DeviceSnapshot snapshot() {
      return snapshot;
    }

    @Override
    public RegistrationHeader getHeader() {
      return CtreHeaderHolder.HEADER;
    }
  }

  private static final class CtreHeaderHolder {
    private static final RegistrationHeader HEADER = new RegistrationHeader(
        "Test TalonFX",
        "CTRE",
        "TalonFX",
        "Phoenix 6",
        "Team",
        "2026-05-29",
        "Test header.");
  }
}
