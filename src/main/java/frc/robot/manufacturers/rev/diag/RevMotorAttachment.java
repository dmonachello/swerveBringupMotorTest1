package frc.robot.manufacturers.rev.diag;

import frc.robot.diag.snapshots.DeviceAttachment;
import java.util.ArrayList;
import java.util.List;

/**
 * NAME
 * RevMotorAttachment
 *
 * SYNOPSIS
 * REV motor telemetry and fault data attachment.
 *
 * DESCRIPTION
 * Carries REV motor diagnostics for inclusion in device snapshots.
 */
public final class RevMotorAttachment extends DeviceAttachment {
  public int faultsRaw = 0;
  public int stickyFaultsRaw = 0;
  public int warningsRaw = 0;
  public int stickyWarningsRaw = 0;
  public String lastError = "";
  public boolean reset = false;
  public Double busV;
  public Double appliedDuty;
  public Double appliedV;
  public Double motorCurrentA;
  public Double tempC;
  public Double cmdDuty;
  public boolean follower = false;
  public String healthNote = "";
  public String lowCurrentNote = "";
  public final List<String> faultFlags = new ArrayList<>();
  public final List<String> stickyFaultFlags = new ArrayList<>();
  public final List<String> warningFlags = new ArrayList<>();
  public final List<String> stickyWarningFlags = new ArrayList<>();

  /**
   * NAME
   * RevMotorAttachment
   *
   * SYNOPSIS
   * Construct a REV motor attachment with the standard type tag.
   */
  public RevMotorAttachment() {
    super("revMotor");
  }
}
