package frc.robot.diag.snapshots;

// Best-effort CAN health suspicion per device (expected vs likely).
public final class CanSuspicionAttachment extends DeviceAttachment {
  public String expectedState = "";
  public String expectedMeaning = "";
  public String likelyState = "";
  public String likelyMeaning = "";
  public String confidence = "";
  public String note = "";

  public CanSuspicionAttachment() {
    super("canSuspicion");
  }
}
