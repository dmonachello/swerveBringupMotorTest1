package frc.robot.manufacturers.ctre.diag;

import frc.robot.diag.snapshots.DeviceAttachment;
import java.util.ArrayList;
import java.util.List;

/**
 * NAME
 * CtreMotorAttachment
 *
 * SYNOPSIS
 * CTRE motor telemetry and fault data attachment.
 *
 * DESCRIPTION
 * Carries CTRE motor diagnostics for inclusion in device snapshots.
 */
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

  /**
   * NAME
   * CtreMotorAttachment
   *
   * SYNOPSIS
   * Construct a CTRE motor attachment with the standard type tag.
   */
  public CtreMotorAttachment() {
    super("ctreMotor");
  }
}
