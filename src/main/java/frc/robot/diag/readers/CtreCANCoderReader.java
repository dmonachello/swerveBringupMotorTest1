package frc.robot.diag.readers;

import com.ctre.phoenix6.BaseStatusSignal;
import com.ctre.phoenix6.hardware.CANcoder;
import edu.wpi.first.units.Units;
import frc.robot.diag.snapshots.DeviceSnapshot;

// Reader for CTRE CANCoder devices.
public final class CtreCANCoderReader {
  private CtreCANCoderReader() {}

  public static DeviceSnapshot read(CANcoder device, int canId) {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = "CTRE";
    snap.deviceType = "CANCoder";
    snap.canId = canId;
    snap.present = true;

    var absolute = device.getAbsolutePosition();
    BaseStatusSignal.refreshAll(absolute);
    double rotations = absolute.getValue().in(Units.Rotations);
    snap.absDeg = rotations * 360.0;
    snap.lastError = String.valueOf(absolute.getStatus());
    return snap;
  }
}
