package frc.robot.diag.snapshots;

/**
 * NAME
 *   LedStatusAttachment - LED status inference attachment.
 */
public final class LedStatusAttachment extends DeviceAttachment {
  public String expectedPattern = "";
  public String expectedMeaning = "";
  public String likelyPattern = "";
  public String likelyMeaning = "";
  public String confidence = "";
  public String note = "";

  /**
   * NAME
   *   LedStatusAttachment - Construct with attachment type name.
   */
  public LedStatusAttachment() {
    super("ledStatus");
  }
}
