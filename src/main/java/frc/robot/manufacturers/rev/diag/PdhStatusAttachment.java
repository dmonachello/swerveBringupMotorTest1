package frc.robot.manufacturers.rev.diag;

import frc.robot.diag.snapshots.DeviceAttachment;

/**
 * NAME
 *   PdhStatusAttachment - PDH status snapshot attachment.
 *
 * DESCRIPTION
 *   Captures REV PDH status values, faults, and per-channel currents.
 */
public final class PdhStatusAttachment extends DeviceAttachment {
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
  public double[] channelCurrentA = new double[0];
  public boolean[] channelFault = new boolean[0];
  public boolean[] channelStickyFault = new boolean[0];

  /**
   * NAME
   *   PdhStatusAttachment - Construct with default type.
   */
  public PdhStatusAttachment() {
    super("pdhStatus");
  }
}
