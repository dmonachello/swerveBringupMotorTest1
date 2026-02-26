package frc.robot.diag.snapshots;

import java.util.ArrayList;
import java.util.List;

// Plain data snapshot for a single device at a moment in time.
public final class DeviceSnapshot {
  public String vendor = "";
  public String deviceType = "";
  public int canId = -1;
  public boolean present = false;

  public int faultsRaw = 0;
  public int stickyFaultsRaw = 0;
  public int warningsRaw = 0;
  public int stickyWarningsRaw = 0;
  public String lastError = "";
  public String faultStatus = "";
  public String stickyStatus = "";
  public boolean reset = false;

  public Double busV;
  public Double appliedDuty;
  public Double appliedV;
  public Double motorCurrentA;
  public Double tempC;
  public Double cmdDuty;
  public Double motorV;
  public Double absDeg;

  public String label = "";
  public String model = "";
  public Double specNominalV;
  public Double specFreeA;
  public Double specStallA;

  public String healthNote = "";
  public String lowCurrentNote = "";
  public String note = "";

  public final List<String> faultFlags = new ArrayList<>();
  public final List<String> stickyFaultFlags = new ArrayList<>();
  public final List<String> warningFlags = new ArrayList<>();
  public final List<String> stickyWarningFlags = new ArrayList<>();
}
