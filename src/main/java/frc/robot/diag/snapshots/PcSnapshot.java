package frc.robot.diag.snapshots;

import java.util.ArrayList;
import java.util.List;

// Plain data snapshot for PC sniffer/NetworkTables state.
public final class PcSnapshot {
  public double heartbeatAgeSec = -1.0;
  public boolean openOk = false;
  public double framesPerSec = Double.NaN;
  public double framesTotal = Double.NaN;
  public double readErrors = Double.NaN;
  public double lastFrameAgeSec = Double.NaN;

  public int missingCount = 0;
  public int totalCount = 0;
  public int flappingCount = 0;
  public final List<SeenNotLocalEntry> seenNotLocal = new ArrayList<>();
  public final List<ProfileMismatchEntry> profileMismatch = new ArrayList<>();
  public final List<StaleDeviceEntry> staleDevices = new ArrayList<>();

  public static final class SeenNotLocalEntry {
    public String key = "";
    public Double ageSec;
  }

  public static final class ProfileMismatchEntry {
    public String expected = "";
    public final List<Integer> seenIds = new ArrayList<>();
  }

  public static final class StaleDeviceEntry {
    public String key = "";
    public Double ageSec;
  }
}
