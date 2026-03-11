package frc.robot.diag.snapshots;

/**
 * NAME
 *   EncoderAttachment - Encoder telemetry for a device.
 */
public final class EncoderAttachment extends DeviceAttachment {
  public Double absDeg;
  public String lastError = "";

  /**
   * NAME
   *   EncoderAttachment - Construct with attachment type name.
   */
  public EncoderAttachment() {
    super("encoder");
  }
}
