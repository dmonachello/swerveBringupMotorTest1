package frc.robot.diag.snapshots;

import java.util.ArrayList;
import java.util.List;

// Bundle of all snapshot data for a single diagnostics report.
public final class SnapshotBundle {
  public double timestampSec = 0.0;
  public BusSnapshot bus;
  public PcSnapshot pc;
  public final List<DeviceSnapshot> devices = new ArrayList<>();
}
