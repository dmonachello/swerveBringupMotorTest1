package frc.robot.diag.snapshots;

/**
 * NAME
 *   MotorSpecAttachment - Motor specification metadata.
 */
public final class MotorSpecAttachment extends DeviceAttachment {
  public String model = "";
  public Double nominalV;
  public Double freeCurrentA;
  public Double stallCurrentA;

  /**
   * NAME
   *   MotorSpecAttachment - Construct with attachment type name.
   */
  public MotorSpecAttachment() {
    super("motorSpec");
  }
}
