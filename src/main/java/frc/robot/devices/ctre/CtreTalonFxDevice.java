package frc.robot.devices.ctre;

import com.ctre.phoenix6.hardware.TalonFX;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.readers.CtreTalonFxReader;
import frc.robot.diag.snapshots.DeviceSnapshot;

// Device wrapper for a CTRE TalonFX-based motor (Kraken/Falcon).
public final class CtreTalonFxDevice implements DeviceUnit {
  private final int canId;
  private final String label;
  private final String motorModelOverride;
  private final String deviceType;
  private TalonFX device;

  public CtreTalonFxDevice(int canId, String label, String motorModelOverride, String deviceType) {
    this.canId = canId;
    this.label = label;
    this.motorModelOverride = motorModelOverride;
    this.deviceType = deviceType;
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return deviceType;
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
    device = new TalonFX(canId);
  }

  @Override
  public void close() {
    BringupUtil.closeIfPossible(device);
    device = null;
  }

  @Override
  public void clearFaults() {
    if (device != null) {
      device.clearStickyFaults();
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
      snap.vendor = "CTRE";
      snap.deviceType = deviceType;
      snap.canId = canId;
      snap.present = false;
      snap.note = "not added";
      snap.label = label;
      return snap;
    }
    DeviceSnapshot snap = CtreTalonFxReader.read(device, deviceType, canId);
    snap.label = label;
    return snap;
  }
}
