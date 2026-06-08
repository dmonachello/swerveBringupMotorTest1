package frc.robot.diag.snapshots;

/**
 * NAME
 *   DevicePresenceCheckAttachment - Lightweight live presence-check evidence for one snapshot.
 *
 * DESCRIPTION
 *   Separates cheap current presence evidence from the heavier one-shot
 *   full-device probe so lifecycle and live UI surfaces can consume a
 *   current low-cost signal without implying deeper diagnostic state.
 */
public final class DevicePresenceCheckAttachment extends DeviceAttachment {
  private static final String ATTACHMENT_TYPE = "presenceCheck";

  public static final String SOURCE_LOCAL_SNAPSHOT = "localSnapshot";
  public static final String BUCKET_PRESENT = "present";
  public static final String BUCKET_ABSENT = "absent";
  public static final String STATUS_OK = "ok";
  public static final String STATUS_WARNING = "warning";
  public static final int MAX_SCORE = 100;
  public static final int SCORE_PRESENT = 100;
  public static final int SCORE_ABSENT = 0;
  public static final String MESSAGE_PRESENT = "Runtime snapshot indicates device present.";
  public static final String MESSAGE_ABSENT = "Runtime snapshot did not observe device present.";

  public String source = SOURCE_LOCAL_SNAPSHOT;
  public String bucket = BUCKET_ABSENT;
  public String status = STATUS_WARNING;
  public int score = SCORE_ABSENT;
  public int maxScore = MAX_SCORE;
  public long updatedAtMs;
  public String message = MESSAGE_ABSENT;

  /**
   * NAME
   *   DevicePresenceCheckAttachment - Construct with the canonical type tag.
   */
  public DevicePresenceCheckAttachment() {
    super(ATTACHMENT_TYPE);
  }

  /**
   * NAME
   *   copy - Return a detached copy suitable for one snapshot instance.
   */
  public DevicePresenceCheckAttachment copy() {
    DevicePresenceCheckAttachment out = new DevicePresenceCheckAttachment();
    out.source = source;
    out.bucket = bucket;
    out.status = status;
    out.score = score;
    out.maxScore = maxScore;
    out.updatedAtMs = updatedAtMs;
    out.message = message;
    return out;
  }
}
