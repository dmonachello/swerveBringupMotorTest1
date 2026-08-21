package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import frc.robot.devices.DeviceDslSupport;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.ImuAttachment;
import frc.robot.diag.snapshots.RobotControllerBusAttachment;
import frc.robot.diag.snapshots.RobotControllerPowerAttachment;
import frc.robot.diag.snapshots.RobotControllerRailsAttachment;
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

  @Test
  void readImuSignalReturnsExtendedPigeonTelemetry() {
    RecordingImuDevice device = new RecordingImuDevice();

    assertEquals(42.5, DeviceDslSupport.readImuSignal(device, DslSignalRegistry.SIGNAL_ANGULAR_VELOCITY_Z));
    assertEquals(0.98, DeviceDslSupport.readImuSignal(device, DslSignalRegistry.SIGNAL_ACCEL_Z));
    assertEquals(12.4, DeviceDslSupport.readImuSignal(device, DslSignalRegistry.SIGNAL_SUPPLY_VOLTAGE));
    assertFalse((Boolean) DeviceDslSupport.readImuSignal(device, DslSignalRegistry.SIGNAL_FAULTS));
  }

  @Test
  void readRobotControllerSignalReturnsSharedControllerTelemetry() {
    RecordingRobotControllerDevice device = new RecordingRobotControllerDevice();

    assertEquals(
        12.2,
        DeviceDslSupport.readRobotControllerSignal(device, DslSignalRegistry.SIGNAL_INPUT_VOLTAGE));
    assertEquals(
        6.2,
        DeviceDslSupport.readRobotControllerSignal(
            device,
            DslSignalRegistry.SIGNAL_BROWNOUT_VOLTAGE));
    assertEquals(
        21.5,
        DeviceDslSupport.readRobotControllerSignal(device, DslSignalRegistry.SIGNAL_CAN_UTILIZATION));
    assertEquals(
        3,
        DeviceDslSupport.readRobotControllerSignal(
            device,
            DslSignalRegistry.SIGNAL_CAN_TX_ERROR_COUNT));
    assertEquals(
        1,
        DeviceDslSupport.readRobotControllerSignal(
            device,
            DslSignalRegistry.SIGNAL_CAN_BUS_OFF_COUNT));
    assertEquals(
        2,
        DeviceDslSupport.readRobotControllerSignal(
            device,
            DslSignalRegistry.SIGNAL_CAN_TX_FULL_COUNT));
    assertEquals(
        3.28,
        DeviceDslSupport.readRobotControllerSignal(
            device,
            DslSignalRegistry.SIGNAL_RAIL_3V3_VOLTAGE));
    assertEquals(
        true,
        DeviceDslSupport.readRobotControllerSignal(
            device,
            DslSignalRegistry.SIGNAL_RAIL_3V3_ENABLED));
    assertEquals(
        4,
        DeviceDslSupport.readRobotControllerSignal(
            device,
            DslSignalRegistry.SIGNAL_RAIL_6V_FAULT_COUNT));
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

  private static final class RecordingImuDevice implements DeviceUnit {
    private final DeviceSnapshot snapshot;

    private RecordingImuDevice() {
      snapshot = new DeviceSnapshot();
      snapshot.vendor = "CTRE";
      snapshot.deviceType = "Pigeon";
      snapshot.canId = CAN_ID;
      snapshot.present = true;
      ImuAttachment imu = new ImuAttachment();
      imu.angularVelocityZDps = 42.5;
      imu.accelZG = 0.98;
      imu.supplyVoltage = 12.4;
      imu.faults = false;
      snapshot.addAttachment(imu);
    }

    @Override
    public int getCanId() {
      return CAN_ID;
    }

    @Override
    public String getDeviceType() {
      return "Pigeon";
    }

    @Override
    public String getLabel() {
      return "pigeon 2";
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

  private static final class RecordingRobotControllerDevice implements DeviceUnit {
    private final DeviceSnapshot snapshot;

    private RecordingRobotControllerDevice() {
      snapshot = new DeviceSnapshot();
      snapshot.vendor = "NI";
      snapshot.deviceType = "robotController";
      snapshot.canId = CAN_ID;
      snapshot.present = true;
      RobotControllerPowerAttachment power = new RobotControllerPowerAttachment();
      power.inputVoltage = 12.2;
      power.brownout = false;
      power.brownoutVoltage = 6.2;
      snapshot.addAttachment(power);
      RobotControllerBusAttachment bus = new RobotControllerBusAttachment();
      bus.canUtilizationPct = 21.5;
      bus.canTxErrorCount = 3;
      bus.canRxErrorCount = 1;
      bus.canBusOffCount = 1;
      bus.canTxFullCount = 2;
      snapshot.addAttachment(bus);
      RobotControllerRailsAttachment rails = new RobotControllerRailsAttachment();
      rails.rail3v3Voltage = 3.28;
      rails.rail3v3Enabled = true;
      rails.rail5vVoltage = 5.0;
      rails.rail6vVoltage = 6.1;
      rails.rail6vFaultCount = 4;
      snapshot.addAttachment(rails);
    }

    @Override
    public int getCanId() {
      return CAN_ID;
    }

    @Override
    public String getDeviceType() {
      return "robotController";
    }

    @Override
    public String getLabel() {
      return "roborio";
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
