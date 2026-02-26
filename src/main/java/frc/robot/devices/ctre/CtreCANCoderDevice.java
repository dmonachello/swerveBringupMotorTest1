package frc.robot.devices.ctre;

import com.ctre.phoenix6.hardware.CANcoder;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.readers.CtreCANCoderReader;
import frc.robot.diag.snapshots.DeviceSnapshot;

// Device wrapper for a CTRE CANCoder.
public final class CtreCANCoderDevice implements DeviceUnit {
  private final int canId;
  private final String label;
  private CANcoder device;

  public CtreCANCoderDevice(int canId, String label) {
    this.canId = canId;
    this.label = label;
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return "CANCoder";
  }

  @Override
  public String getLabel() {
    return label;
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
    device = new CANcoder(canId);
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
  public DeviceSnapshot snapshot() {
    if (device == null) {
      DeviceSnapshot snap = new DeviceSnapshot();
      snap.vendor = "CTRE";
      snap.deviceType = getDeviceType();
      snap.canId = canId;
      snap.present = false;
      snap.note = "not added";
      snap.label = label;
      return snap;
    }
    DeviceSnapshot snap = CtreCANCoderReader.read(device, canId);
    snap.label = label;
    return snap;
  }
}
