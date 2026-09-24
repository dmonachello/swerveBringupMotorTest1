package frc.robot.telemetry;

/**
 * NAME
 *   TelemetryConstants - Shared limits and cadence defaults for signal history.
 */
public final class TelemetryConstants {
  public static final int ROBOT_JOURNAL_MAX_RECORDS = 100_000;
  public static final int JOURNAL_MAX_READ_RECORDS = 2_000;
  public static final long ROBOT_JOURNAL_DURATION_US = 10_000_000L;
  public static final long DEFAULT_NOMINAL_CADENCE_US = 20_000L;
  public static final long DEFAULT_STALE_AFTER_US = 100_000L;
  public static final long MICROSECONDS_PER_MILLISECOND = 1_000L;
  public static final String CAPACITY_ERROR_MESSAGE = "capacity must be positive";
  public static final String SIGNAL_ID_SEPARATOR = ":";

  private TelemetryConstants() {}
}
