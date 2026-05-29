package frc.robot.diag.snapshots;

/**
 * NAME
 *   SnapshotDetail - Snapshot cost/detail selector for telemetry reads.
 *
 * DESCRIPTION
 *   Lets callers request lighter-weight snapshots for high-frequency UI
 *   polling without removing the richer reads used by reports and diagnostics.
 */
public enum SnapshotDetail {
  FULL,
  LIGHT,
}
