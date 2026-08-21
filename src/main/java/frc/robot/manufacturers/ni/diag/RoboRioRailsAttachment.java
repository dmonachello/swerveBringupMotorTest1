package frc.robot.manufacturers.ni.diag;

import frc.robot.diag.snapshots.DeviceAttachment;

/**
 * NAME
 *   RoboRioRailsAttachment - roboRIO user-rail status snapshot attachment.
 *
 * DESCRIPTION
 *   Captures 3.3V, 5V, and 6V user-rail measurements and fault counters for
 *   future controller-family diagnostics.
 */
public final class RoboRioRailsAttachment extends DeviceAttachment {
  private static final String ATTACHMENT_TYPE = "roboRioRails";

  public double rail3v3Voltage;
  public double rail3v3Current;
  public boolean rail3v3Enabled;
  public int rail3v3FaultCount;
  public double rail5vVoltage;
  public double rail5vCurrent;
  public boolean rail5vEnabled;
  public int rail5vFaultCount;
  public double rail6vVoltage;
  public double rail6vCurrent;
  public boolean rail6vEnabled;
  public int rail6vFaultCount;

  /**
   * NAME
   *   RoboRioRailsAttachment - Construct with default type.
   */
  public RoboRioRailsAttachment() {
    super(ATTACHMENT_TYPE);
  }
}
