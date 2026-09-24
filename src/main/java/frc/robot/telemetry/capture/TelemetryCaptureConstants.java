package frc.robot.telemetry.capture;

/** NAME TelemetryCaptureConstants - Robot-local WPILOG policy and resource limits. */
public final class TelemetryCaptureConstants {
  public static final int WRITER_QUEUE_RECORDS = 8_192;
  public static final int PRETRIGGER_PAGE_RECORDS = 2_000;
  public static final int PRETRIGGER_MAX_RECORDS = 100_000;
  public static final long STOP_DRAIN_TIMEOUT_MS = 1_000L;
  public static final long MAX_CAPTURE_DURATION_MS = 15L * 60L * 1_000L;
  public static final long MAX_CAPTURE_FILE_BYTES = 64L * 1_024L * 1_024L;
  public static final long RESERVED_FREE_BYTES = 128L * 1_024L * 1_024L;
  public static final int LIMIT_CHECK_RECORD_INTERVAL = 256;
  public static final long WRITER_IDLE_WAIT_MS = 100L;
  public static final long MATCH_DISABLE_POST_TRIGGER_MS = 5_000L;
  public static final long EXCEPTION_POST_TRIGGER_MS = 30_000L;
  public static final long EXCEPTION_TRIGGER_COOLDOWN_MS = 60_000L;
  public static final String USB_LOG_DIRECTORY = "/U/logs";
  public static final String INTERNAL_LOG_DIRECTORY = "/home/lvuser/logs";
  public static final String FILE_PREFIX = "signal-history-";
  public static final String FILE_SUFFIX = ".wpilog";
  public static final String EXTRA_HEADER = "frc-bringup-signal-history-v1";
  public static final String ENTRY_PREFIX = "/Telemetry/";
  public static final String GAP_ENTRY_NAME = "/Telemetry/_gaps";
  public static final String GAP_ENTRY_METADATA = "{\"type\":\"captureGap\"}";
  public static final String ANNOTATION_ENTRY_NAME = "/Telemetry/_annotations";
  public static final String ANNOTATION_ENTRY_METADATA = "{\"type\":\"captureAnnotation\"}";
  public static final String ANNOTATION_MATCH_ENABLE = "trigger=matchEnable";
  public static final String ANNOTATION_EXCEPTION = "trigger=exception";
  public static final String GAP_MESSAGE_PREFIX = "queueOverflow dropped=";
  public static final String SOURCE_RESET_MESSAGE_PREFIX = "sourceReset sourceInstanceId=";
  public static final String STOP_REASON_OPERATOR = "operator";
  public static final String STOP_REASON_DURATION_LIMIT = "durationLimit";
  public static final String STOP_REASON_FILE_LIMIT = "fileLimit";
  public static final String STOP_REASON_FREE_SPACE = "freeSpaceReserve";
  public static final String STOP_REASON_MATCH_DISABLED = "matchDisabledPostTrigger";
  public static final String STOP_REASON_EXCEPTION_WINDOW = "exceptionPostTrigger";
  public static final String STOP_REASON_WRITER_ERROR = "writerError";
  public static final String ERROR_REASON_SEPARATOR = ":";
  public static final String STOP_REASON_NONE = "";
  public static final String ERROR_ALREADY_RECORDING = "Capture is already recording.";
  public static final String ERROR_NOT_RECORDING = "Capture is not recording.";
  public static final String ERROR_START_PREFIX = "Unable to start capture: ";
  public static final String ERROR_FREE_SPACE = "Capture storage does not meet the free-space reserve.";

  private TelemetryCaptureConstants() {}
}
