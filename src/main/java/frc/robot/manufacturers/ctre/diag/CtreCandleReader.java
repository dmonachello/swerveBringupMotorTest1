package frc.robot.manufacturers.ctre.diag;

import com.ctre.phoenix6.hardware.CANdle;
import frc.robot.diag.snapshots.DeviceSnapshot;

/**
 * NAME
 * CtreCandleReader
 *
 * SYNOPSIS
 * Reader for CTRE CANdle devices (LED controller).
 *
 * DESCRIPTION
 * Builds minimal snapshots for CANdle devices until richer signals are needed.
 */
public final class CtreCandleReader {
  private CtreCandleReader() {}

  /**
   * NAME
   * read
   *
   * SYNOPSIS
   * Capture a snapshot from a CANdle device.
   *
   * PARAMETERS
   * device - CANdle instance to read.
   * canId - CAN ID of the device.
   *
   * RETURNS
   * A populated device snapshot with basic identity fields.
   */
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
