package frc.robot.diag.snapshots;

/**
 * NAME
 *   RobotControllerPowerAttachment - Shared controller-family power snapshot.
 *
 * DESCRIPTION
 *   Captures controller input-voltage and brownout state behind the shared
 *   robot-controller family contract.
 */
public final class RobotControllerPowerAttachment extends DeviceAttachment {
  private static final String ATTACHMENT_TYPE = "robotControllerPower";

  public double inputVoltage;
  public boolean brownout;
  public double brownoutVoltage;

  /**
   * NAME
   *   RobotControllerPowerAttachment - Construct with default type.
   */
  public RobotControllerPowerAttachment() {
    super(ATTACHMENT_TYPE);
  }
}
