package frc.robot.manufacturers.ctre.diag;

import frc.robot.diag.snapshots.DeviceAttachment;

/**
 * NAME
 *   PdpStatusAttachment - PDP status snapshot attachment.
 *
 * DESCRIPTION
 *   Captures CTRE PDP status values, faults, and per-channel currents.
 */
public final class PdpStatusAttachment extends DeviceAttachment {
  private static final String ATTACHMENT_TYPE = "pdpStatus";
  private static final int EMPTY_LENGTH = 0;
  public double voltage;
  public double totalCurrent;
  public boolean switchableEnabled;
  public double temperature;
  public boolean brownout;
  public boolean canWarning;
  public boolean hardwareFault;
  public boolean stickyBrownout;
  public boolean stickyCanWarning;
  public boolean stickyCanBusOff;
  public boolean stickyHasReset;
  public double[] channelCurrentA = new double[EMPTY_LENGTH];
  public boolean[] channelFault = new boolean[EMPTY_LENGTH];
  public boolean[] channelStickyFault = new boolean[EMPTY_LENGTH];

  /**
   * NAME
   *   PdpStatusAttachment - Construct with default type.
   */
  public PdpStatusAttachment() {
    super(ATTACHMENT_TYPE);
  }
}
