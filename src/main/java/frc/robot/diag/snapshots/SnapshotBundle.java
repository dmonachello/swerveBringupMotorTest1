package frc.robot.diag.snapshots;

import java.util.ArrayList;
import java.util.List;

/**
 * NAME
 *   SnapshotBundle - Aggregated snapshot data for diagnostics reports.
 */
public final class SnapshotBundle {
  public double timestampSec = 0.0;
  public BusSnapshot bus;
  public PcSnapshot pc;
  public final List<DeviceSnapshot> devices = new ArrayList<>();
}
