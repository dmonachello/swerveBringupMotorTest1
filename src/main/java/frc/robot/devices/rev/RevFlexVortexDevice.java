package frc.robot.devices.rev;

import com.revrobotics.PersistMode;
import com.revrobotics.ResetMode;
import com.revrobotics.spark.SparkFlex;
import com.revrobotics.spark.SparkLowLevel.MotorType;
import com.revrobotics.spark.config.SparkFlexConfig;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.readers.RevSparkFlexReader;
import frc.robot.diag.snapshots.DeviceSnapshot;

// Device wrapper for a REV Spark Flex controlling a Vortex/FLEX.
public final class RevFlexVortexDevice implements DeviceUnit {
  private final int canId;
  private final String label;
  private final String motorModelOverride;
  private SparkFlex device;

  public RevFlexVortexDevice(int canId, String label, String motorModelOverride) {
    this.canId = canId;
    this.label = label;
    this.motorModelOverride = motorModelOverride;
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return "FLEX";
  }

  @Override
  public String getLabel() {
    return label;
  }

  public String getMotorModelOverride() {
    return motorModelOverride;
  }

  @Override
  public boolean isCreated() {
    return device != null;
  }

  @Override
  public void ensureCreated() {
    if (device != null) {
      return;
    }
    device = new SparkFlex(canId, MotorType.kBrushless);
    device.pauseFollowerModeAsync();
    device.configureAsync(
        new SparkFlexConfig(),
        ResetMode.kResetSafeParameters,
        PersistMode.kNoPersistParameters);
  }

  @Override
  public void close() {
    BringupUtil.closeIfPossible(device);
    device = null;
  }

  @Override
  public void clearFaults() {
    if (device != null) {
      device.clearFaults();
    }
  }

  @Override
  public void setDuty(double duty) {
    if (device != null) {
      device.set(duty);
    }
  }

  @Override
  public void stop() {
    if (device != null) {
      device.stopMotor();
    }
  }

  @Override
  public DeviceSnapshot snapshot() {
    if (device == null) {
      DeviceSnapshot snap = new DeviceSnapshot();
      snap.vendor = "REV";
      snap.deviceType = getDeviceType();
      snap.canId = canId;
      snap.present = false;
      snap.note = "not added";
      snap.label = label;
      return snap;
    }
    DeviceSnapshot snap = RevSparkFlexReader.read(device, canId);
    snap.deviceType = getDeviceType();
    snap.label = label;
    return snap;
  }
}

