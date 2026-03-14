package frc.robot.manufacturers.rev.util;

import edu.wpi.first.hal.PowerDistributionFaults;
import edu.wpi.first.hal.PowerDistributionStickyFaults;
import edu.wpi.first.wpilibj.PowerDistribution;
import frc.robot.manufacturers.rev.diag.PdhStatusAttachment;

/**
 * NAME
 *   PdhStatusReader - Read PDH status without printing.
 *
 * DESCRIPTION
 *   Provides snapshot data for REV PDH via the WPILib PowerDistribution API.
 */
public final class PdhStatusReader {
  private final PowerDistribution pdh;
  private final int canId;

  /**
   * NAME
   *   PdhStatusReader - Construct a reader for a specific CAN ID.
   */
  public PdhStatusReader(int canId) {
    this.canId = canId;
    this.pdh = new PowerDistribution(canId, PowerDistribution.ModuleType.kRev);
  }

  /**
   * NAME
   *   snapshot - Capture a PDH status attachment.
   */
  public PdhStatusAttachment snapshot() {
    PdhStatusAttachment out = new PdhStatusAttachment();
    PowerDistributionFaults faults = pdh.getFaults();
    PowerDistributionStickyFaults sticky = pdh.getStickyFaults();

    out.voltage = pdh.getVoltage();
    out.totalCurrent = pdh.getTotalCurrent();
    out.switchableEnabled = pdh.getSwitchableChannel();
    out.temperature = pdh.getTemperature();

    out.brownout = faults.Brownout;
    out.canWarning = faults.CanWarning;
    out.hardwareFault = faults.HardwareFault;

    out.stickyBrownout = sticky.Brownout;
    out.stickyCanWarning = sticky.CanWarning;
    out.stickyCanBusOff = sticky.CanBusOff;
    out.stickyHasReset = sticky.HasReset;

    int channels = pdh.getNumChannels();
    out.channelCurrentA = new double[channels];
    out.channelFault = new boolean[channels];
    out.channelStickyFault = new boolean[channels];
    for (int ch = 0; ch < channels; ch++) {
      out.channelCurrentA[ch] = pdh.getCurrent(ch);
      out.channelFault[ch] = faults.getBreakerFault(ch);
      out.channelStickyFault[ch] = sticky.getBreakerFault(ch);
    }
    return out;
  }

  /**
   * NAME
   *   clearStickyFaults - Clear sticky PDH faults.
   */
  public void clearStickyFaults() {
    pdh.clearStickyFaults();
  }

  /**
   * NAME
   *   getCanId - Return the PDH CAN ID.
   */
  public int getCanId() {
    return canId;
  }
}

