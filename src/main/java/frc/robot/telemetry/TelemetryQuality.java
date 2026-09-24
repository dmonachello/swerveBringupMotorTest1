package frc.robot.telemetry;

/**
 * NAME
 *   TelemetryQuality - Quality state attached to one accepted history record.
 */
public enum TelemetryQuality {
  GOOD,
  UNAVAILABLE,
  READ_ERROR,
  STALE
}
