package frc.robot.manufacturers.ctre.util;

import edu.wpi.first.hal.PowerDistributionFaults;
import edu.wpi.first.hal.PowerDistributionStickyFaults;
import edu.wpi.first.wpilibj.PowerDistribution;
import frc.robot.manufacturers.ctre.diag.PdpStatusAttachment;

/**
 * NAME
 *   PdpStatusReader - Read PDP status without printing.
 *
 * DESCRIPTION
 *   Provides snapshot data for CTRE PDP via the WPILib PowerDistribution API.
 */
public final class PdpStatusReader {
  private static final int INDEX_START = 0;
  private static final int MIN_CHANNELS = 1;
  private final PowerDistribution pdp;

  /**
   * NAME
   *   PdpStatusReader - Construct a reader for a specific CAN ID.
   */
  public PdpStatusReader(int canId) {
    this.pdp = new PowerDistribution(canId, PowerDistribution.ModuleType.kCTRE);
  }

  /**
   * NAME
   *   snapshot - Capture a PDP status attachment.
   */
  public PdpStatusAttachment snapshot() {
    PdpStatusAttachment out = new PdpStatusAttachment();
    PowerDistributionFaults faults = pdp.getFaults();
    PowerDistributionStickyFaults sticky = pdp.getStickyFaults();
    out.voltage = pdp.getVoltage();
    out.totalCurrent = pdp.getTotalCurrent();
    out.switchableEnabled = pdp.getSwitchableChannel();
    out.temperature = pdp.getTemperature();
    out.brownout = faults.Brownout;
    out.canWarning = faults.CanWarning;
    out.hardwareFault = faults.HardwareFault;
    out.stickyBrownout = sticky.Brownout;
    out.stickyCanWarning = sticky.CanWarning;
    out.stickyCanBusOff = sticky.CanBusOff;
    out.stickyHasReset = sticky.HasReset;

    int channels = pdp.getNumChannels();
    if (channels >= MIN_CHANNELS) {
      out.channelCurrentA = new double[channels];
      out.channelFault = new boolean[channels];
      out.channelStickyFault = new boolean[channels];
      for (int ch = INDEX_START; ch < channels; ch++) {
        out.channelCurrentA[ch] = pdp.getCurrent(ch);
        out.channelFault[ch] = faults.getBreakerFault(ch);
        out.channelStickyFault[ch] = sticky.getBreakerFault(ch);
      }
    }
    return out;
  }

  /**
   * NAME
   *   clearStickyFaults - Clear sticky PDP faults.
   */
  public void clearStickyFaults() {
    pdp.clearStickyFaults();
  }

  /**
   * NAME
   *   getCanId - Return the PDP CAN ID.
   */
  public int getCanId() {
    return pdp.getModule();
  }
}
