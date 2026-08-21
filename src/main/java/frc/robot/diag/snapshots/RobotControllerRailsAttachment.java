package frc.robot.diag.snapshots;

/**
 * NAME
 *   RobotControllerRailsAttachment - Shared controller-family rail snapshot.
 *
 * DESCRIPTION
 *   Captures user-rail voltage/current/enable/fault state behind the shared
 *   robot-controller family contract.
 */
public final class RobotControllerRailsAttachment extends DeviceAttachment {
  private static final String ATTACHMENT_TYPE = "robotControllerRails";

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
   *   RobotControllerRailsAttachment - Construct with default type.
   */
  public RobotControllerRailsAttachment() {
    super(ATTACHMENT_TYPE);
  }
}
