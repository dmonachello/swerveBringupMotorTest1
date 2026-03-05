package frc.robot.diag.snapshots;

// Best-effort LED status inference (expected vs likely).
public final class LedStatusAttachment extends DeviceAttachment {
  public String expectedPattern = "";
  public String expectedMeaning = "";
  public String likelyPattern = "";
  public String likelyMeaning = "";
  public String confidence = "";
  public String note = "";

  public LedStatusAttachment() {
    super("ledStatus");
  }
}
