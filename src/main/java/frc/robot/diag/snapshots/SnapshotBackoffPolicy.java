package frc.robot.diag.snapshots;

/**
 * NAME
 *   SnapshotBackoffPolicy - Shared failure/backoff helpers for device snapshot polling.
 *
 * DESCRIPTION
 *   Centralizes the note-pattern checks that indicate a repeated live read is
 *   likely to emit more vendor/HAL console faults without yielding new data.
 */
public final class SnapshotBackoffPolicy {
  public static final long FAILURE_BACKOFF_MS = 15000L;

  private static final String NOTE_READ_FAIL_PREFIX = "read failed";
  private static final String NOTE_CACHED_UNAVAILABLE_PREFIX = "cached unavailable";
  private static final String NOTE_TIMEOUT_TOKEN = "timed out";
  private static final String NOTE_MESSAGE_NOT_FOUND_TOKEN = "message not found";
  private static final String NOTE_TOO_STALE_TOKEN = "too stale";

  private SnapshotBackoffPolicy() {}

  /**
   * NAME
   *   noteSuggestsReadBackoff - Return whether a snapshot note indicates repeated reads should back off.
   */
  public static boolean noteSuggestsReadBackoff(String note) {
    if (note == null || note.isBlank()) {
      return false;
    }
    String normalized = note.trim().toLowerCase();
    return normalized.contains(NOTE_READ_FAIL_PREFIX)
        || normalized.contains(NOTE_CACHED_UNAVAILABLE_PREFIX)
        || normalized.contains(NOTE_TIMEOUT_TOKEN)
        || normalized.contains(NOTE_MESSAGE_NOT_FOUND_TOKEN)
        || normalized.contains(NOTE_TOO_STALE_TOKEN);
  }

  /**
   * NAME
   *   copySnapshot - Create a detached copy of one device snapshot for cached reuse.
   */
  public static DeviceSnapshot copySnapshot(DeviceSnapshot source) {
    DeviceSnapshot copy = new DeviceSnapshot();
    if (source == null) {
      return copy;
    }
    copy.vendor = source.vendor;
    copy.deviceType = source.deviceType;
    copy.canId = source.canId;
    copy.present = source.present;
    copy.label = source.label;
    copy.note = source.note;
    copy.attachments.addAll(source.attachments);
    return copy;
  }
}
