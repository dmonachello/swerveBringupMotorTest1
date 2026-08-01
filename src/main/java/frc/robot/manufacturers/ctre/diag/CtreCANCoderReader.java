package frc.robot.manufacturers.ctre.diag;

import com.ctre.phoenix6.BaseStatusSignal;
import com.ctre.phoenix6.hardware.CANcoder;
import edu.wpi.first.units.Units;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.EncoderAttachment;

/**
 * NAME
 * CtreCANCoderReader
 *
 * SYNOPSIS
 * Reader for CTRE CANCoder devices.
 *
 * DESCRIPTION
 * Samples absolute position status signals and packages telemetry into snapshots.
 */
public final class CtreCANCoderReader {
  private static final double DEGREES_PER_ROTATION = 360.0;

  private CtreCANCoderReader() {}

  /**
   * NAME
   * read
   *
   * SYNOPSIS
   * Capture a snapshot from a CANCoder device.
   *
   * PARAMETERS
   * device - CANCoder instance to read.
   * canId - CAN ID of the device.
   *
   * RETURNS
   * A populated device snapshot with encoder telemetry.
   *
   * SIDE EFFECTS
   * Refreshes Phoenix status signals.
   */
  public static DeviceSnapshot read(CANcoder device, int canId) {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = "CTRE";
    snap.deviceType = "CANCoder";
    snap.canId = canId;
    snap.present = true;

    EncoderAttachment encoder = new EncoderAttachment();
    var absolute = device.getAbsolutePosition();
    var velocity = device.getVelocity();
    BaseStatusSignal.refreshAll(absolute, velocity);
    double rotations = absolute.getValue().in(Units.Rotations);
    encoder.absRot = rotations;
    encoder.absDeg = rotations * DEGREES_PER_ROTATION;
    encoder.velocityRps = velocity.getValue().in(Units.RotationsPerSecond);
    encoder.lastError = String.valueOf(absolute.getStatus());
    snap.addAttachment(encoder);
    return snap;
  }
}
