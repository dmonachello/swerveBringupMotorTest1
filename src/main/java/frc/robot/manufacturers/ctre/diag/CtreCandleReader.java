package frc.robot.manufacturers.ctre.diag;

import com.ctre.phoenix6.hardware.CANdle;
import frc.robot.diag.snapshots.DeviceSnapshot;

// Reader for CTRE CANdle devices (LED controller).
public final class CtreCandleReader {
  private CtreCandleReader() {}

  public static DeviceSnapshot read(CANdle device, int canId) {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = "CTRE";
    snap.deviceType = "CANdle";
    snap.canId = canId;
    snap.present = true;
    // CANdle does not expose standard fault fields through Phoenix in the same
    // way as TalonFX; keep snapshot minimal until specific signals are needed.
    return snap;
  }
}
