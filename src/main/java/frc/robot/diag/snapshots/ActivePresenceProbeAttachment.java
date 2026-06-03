package frc.robot.diag.snapshots;

/**
 * NAME
 *   ActivePresenceProbeAttachment - Cached one-shot active probe result for one device.
 *
 * DESCRIPTION
 *   Carries the latest active vendor-API probe outcome so runtime-state,
 *   reports, and UI surfaces can consume the same per-device contract.
 */
public final class ActivePresenceProbeAttachment extends DeviceAttachment {
  private static final String ATTACHMENT_TYPE = "activePresenceProbe";

  public int code;
  public String status = "";
  public String message = "";
  public String bucket = "";
  public int score;
  public int maxScore;
  public long updatedAtMs;

  /**
   * NAME
   *   ActivePresenceProbeAttachment - Construct with the canonical type tag.
   */
  public ActivePresenceProbeAttachment() {
    super(ATTACHMENT_TYPE);
  }

  /**
   * NAME
   *   copy - Return a detached copy suitable for one snapshot instance.
   */
  public ActivePresenceProbeAttachment copy() {
    ActivePresenceProbeAttachment out = new ActivePresenceProbeAttachment();
    out.code = code;
    out.status = status;
    out.message = message;
    out.bucket = bucket;
    out.score = score;
    out.maxScore = maxScore;
    out.updatedAtMs = updatedAtMs;
    return out;
  }
}
