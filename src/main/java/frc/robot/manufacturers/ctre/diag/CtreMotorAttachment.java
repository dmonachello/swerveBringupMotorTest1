package frc.robot.manufacturers.ctre.diag;

import frc.robot.diag.snapshots.DeviceAttachment;
import java.util.ArrayList;
import java.util.List;

// CTRE motor telemetry + fault data.
public final class CtreMotorAttachment extends DeviceAttachment {
  public int faultsRaw = 0;
  public int stickyFaultsRaw = 0;
  public String faultStatus = "";
  public String stickyStatus = "";
  public Double busV;
  public Double appliedDuty;
  public Double appliedV;
  public Double motorCurrentA;
  public Double tempC;
  public Double motorV;
  public final List<String> faultFlags = new ArrayList<>();
  public final List<String> stickyFaultFlags = new ArrayList<>();

  public CtreMotorAttachment() {
    super("ctreMotor");
  }
}
