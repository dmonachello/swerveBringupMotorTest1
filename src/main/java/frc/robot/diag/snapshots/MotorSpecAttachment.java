package frc.robot.diag.snapshots;

/**
 * NAME
 *   MotorSpecAttachment - Motor specification metadata.
 */
public final class MotorSpecAttachment extends DeviceAttachment {
  public static final String ATTACHMENT_TYPE = "motorSpec";
  public String model = "";
  public boolean matched = false;
  public String requestedModel = "";
  public Double nominalV;
  public Double freeCurrentA;
  public Double stallCurrentA;

  /**
   * NAME
   *   MotorSpecAttachment - Construct with attachment type name.
   */
  public MotorSpecAttachment() {
    super(ATTACHMENT_TYPE);
  }
}
