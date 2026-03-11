package frc.robot.diag.snapshots;

/**
 * NAME
 *   CanSuspicionAttachment - Suspicion summary for CAN device behavior.
 */
public final class CanSuspicionAttachment extends DeviceAttachment {
  public String expectedState = "";
  public String expectedMeaning = "";
  public String likelyState = "";
  public String likelyMeaning = "";
  public String confidence = "";
  public String note = "";

  /**
   * NAME
   *   CanSuspicionAttachment - Construct with the attachment type name.
   */
  public CanSuspicionAttachment() {
    super("canSuspicion");
  }
}
