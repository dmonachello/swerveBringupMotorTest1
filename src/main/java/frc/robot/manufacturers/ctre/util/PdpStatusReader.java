package frc.robot.manufacturers.ctre.util;

import edu.wpi.first.hal.PowerDistributionFaults;
import edu.wpi.first.hal.PowerDistributionStickyFaults;
import edu.wpi.first.wpilibj.PowerDistribution;
import frc.robot.manufacturers.ctre.diag.PdpStatusAttachment;
import java.util.function.LongSupplier;

/**
 * NAME
 *   PdpStatusReader - Read PDP status without printing.
 *
 * DESCRIPTION
 *   Provides snapshot data for CTRE PDP via the WPILib PowerDistribution API.
 */
public final class PdpStatusReader implements AutoCloseable {
  private static final int INDEX_START = 0;
  private static final int MIN_CHANNELS = 1;
  private static final long READ_FAILURE_COOLDOWN_NS = 1_000_000_000L;
  private static final long NEVER_FAILED_AT_NS = Long.MIN_VALUE;
  private static final String ERROR_READ_UNAVAILABLE_PREFIX = "cached unavailable: ";

  private final PowerDistributionAccess pdp;
  private final LongSupplier clock;
  private long lastReadFailureAtNs = NEVER_FAILED_AT_NS;
  private String lastReadFailureMessage = "";

  /**
   * NAME
   *   PdpStatusReader - Construct a reader for a specific CAN ID.
   */
  public PdpStatusReader(int canId) {
    this(new WpiPowerDistributionAccess(canId), System::nanoTime);
  }

  PdpStatusReader(PowerDistributionAccess pdp, LongSupplier clock) {
    this.pdp = pdp;
    this.clock = clock != null ? clock : System::nanoTime;
  }

  /**
   * NAME
   *   snapshot - Capture a PDP status attachment.
   */
  public PdpStatusAttachment snapshot() {
    long nowNs = clock.getAsLong();
    if (isReadFailureCooldownActive(nowNs)) {
      throw cachedReadUnavailable();
    }
    try {
      PdpStatusAttachment attachment = snapshotNow();
      clearReadFailure();
      return attachment;
    } catch (RuntimeException ex) {
      rememberReadFailure(nowNs, ex);
      throw ex;
    }
  }

  private PdpStatusAttachment snapshotNow() {
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

  private boolean isReadFailureCooldownActive(long nowNs) {
    if (lastReadFailureAtNs == NEVER_FAILED_AT_NS) {
      return false;
    }
    return nowNs - lastReadFailureAtNs < READ_FAILURE_COOLDOWN_NS;
  }

  private void rememberReadFailure(long nowNs, RuntimeException ex) {
    lastReadFailureAtNs = nowNs;
    String message = ex != null && ex.getMessage() != null ? ex.getMessage().trim() : "";
    lastReadFailureMessage = message;
  }

  private void clearReadFailure() {
    lastReadFailureAtNs = NEVER_FAILED_AT_NS;
    lastReadFailureMessage = "";
  }

  private RuntimeException cachedReadUnavailable() {
    String message = lastReadFailureMessage;
    if (message == null || message.isBlank()) {
      message = "power distribution reader unavailable";
    }
    return new IllegalStateException(ERROR_READ_UNAVAILABLE_PREFIX + message);
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

  /**
   * NAME
   *   close - Release the WPILib PDP allocation.
   */
  @Override
  public void close() {
    pdp.close();
  }

  interface PowerDistributionAccess extends AutoCloseable {
    PowerDistributionFaults getFaults();
    PowerDistributionStickyFaults getStickyFaults();
    double getVoltage();
    double getTotalCurrent();
    boolean getSwitchableChannel();
    double getTemperature();
    int getNumChannels();
    double getCurrent(int channel);
    void clearStickyFaults();
    int getModule();
    @Override
    void close();
  }

  private static final class WpiPowerDistributionAccess implements PowerDistributionAccess {
    private final PowerDistribution pdp;

    private WpiPowerDistributionAccess(int canId) {
      this.pdp = new PowerDistribution(canId, PowerDistribution.ModuleType.kCTRE);
    }

    @Override
    public PowerDistributionFaults getFaults() {
      return pdp.getFaults();
    }

    @Override
    public PowerDistributionStickyFaults getStickyFaults() {
      return pdp.getStickyFaults();
    }

    @Override
    public double getVoltage() {
      return pdp.getVoltage();
    }

    @Override
    public double getTotalCurrent() {
      return pdp.getTotalCurrent();
    }

    @Override
    public boolean getSwitchableChannel() {
      return pdp.getSwitchableChannel();
    }

    @Override
    public double getTemperature() {
      return pdp.getTemperature();
    }

    @Override
    public int getNumChannels() {
      return pdp.getNumChannels();
    }

    @Override
    public double getCurrent(int channel) {
      return pdp.getCurrent(channel);
    }

    @Override
    public void clearStickyFaults() {
      pdp.clearStickyFaults();
    }

    @Override
    public int getModule() {
      return pdp.getModule();
    }

    @Override
    public void close() {
      pdp.close();
    }
  }
}
