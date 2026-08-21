package frc.robot.manufacturers.ni.diag;

import frc.robot.diag.snapshots.DeviceAttachment;

/**
 * NAME
 *   RoboRioPowerAttachment - roboRIO power-health snapshot attachment.
 *
 * DESCRIPTION
 *   Captures controller input-voltage and brownout-related state used by the
 *   future robot-controller family contract while preserving current operator
 *   report behavior.
 */
public final class RoboRioPowerAttachment extends DeviceAttachment {
  private static final String ATTACHMENT_TYPE = "roboRioPower";

  public double inputVoltage;
  public boolean brownedOut;
  public double brownoutVoltage;

  /**
   * NAME
   *   RoboRioPowerAttachment - Construct with default type.
   */
  public RoboRioPowerAttachment() {
    super(ATTACHMENT_TYPE);
  }
}
