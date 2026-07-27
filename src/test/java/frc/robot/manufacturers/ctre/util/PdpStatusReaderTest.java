package frc.robot.manufacturers.ctre.util;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import edu.wpi.first.hal.PowerDistributionFaults;
import edu.wpi.first.hal.PowerDistributionStickyFaults;
import org.junit.jupiter.api.Test;

class PdpStatusReaderTest {
  private static final long INITIAL_TIME_NS = 0L;
  private static final long RETRY_AFTER_COOLDOWN_NS = 30_100_000_000L;
  private static final int ZERO_FAULTS = 0;
  private static final int MODULE_ID = 20;
  private static final int ZERO_CHANNELS = 0;
  private static final String ERROR_MESSAGE_NOT_FOUND = "CAN: Message not found";
  private static final String ERROR_PREFIX_CACHED = "cached unavailable: ";

  @Test
  void snapshotCachesReadFailureDuringCooldown() {
    MutableClock clock = new MutableClock(INITIAL_TIME_NS);
    RecordingPowerDistributionAccess access = new RecordingPowerDistributionAccess();
    access.throwOnVoltage = true;
    PdpStatusReader reader = new PdpStatusReader(access, clock);

    IllegalStateException first = assertThrows(IllegalStateException.class, reader::snapshot);
    IllegalStateException second = assertThrows(IllegalStateException.class, reader::snapshot);

    assertEquals(ERROR_MESSAGE_NOT_FOUND, first.getMessage());
    assertEquals(ERROR_PREFIX_CACHED + ERROR_MESSAGE_NOT_FOUND, second.getMessage());
    assertEquals(1, access.voltageReads);
  }

  @Test
  void snapshotRetriesAfterCooldownExpires() {
    MutableClock clock = new MutableClock(INITIAL_TIME_NS);
    RecordingPowerDistributionAccess access = new RecordingPowerDistributionAccess();
    access.throwOnVoltage = true;
    PdpStatusReader reader = new PdpStatusReader(access, clock);

    assertThrows(IllegalStateException.class, reader::snapshot);
    clock.nowNs = RETRY_AFTER_COOLDOWN_NS;
    assertThrows(IllegalStateException.class, reader::snapshot);

    assertEquals(2, access.voltageReads);
  }

  private static final class MutableClock implements java.util.function.LongSupplier {
    private long nowNs;

    private MutableClock(long nowNs) {
      this.nowNs = nowNs;
    }

    @Override
    public long getAsLong() {
      return nowNs;
    }
  }

  private static final class RecordingPowerDistributionAccess
      implements PdpStatusReader.PowerDistributionAccess {
    private int voltageReads;
    private boolean throwOnVoltage;

    @Override
    public PowerDistributionFaults getFaults() {
      return new PowerDistributionFaults(ZERO_FAULTS);
    }

    @Override
    public PowerDistributionStickyFaults getStickyFaults() {
      return new PowerDistributionStickyFaults(ZERO_FAULTS);
    }

    @Override
    public double getVoltage() {
      voltageReads++;
      if (throwOnVoltage) {
        throw new IllegalStateException(ERROR_MESSAGE_NOT_FOUND);
      }
      return 12.0;
    }

    @Override
    public double getTotalCurrent() {
      return 0.0;
    }

    @Override
    public boolean getSwitchableChannel() {
      return false;
    }

    @Override
    public double getTemperature() {
      return 0.0;
    }

    @Override
    public int getNumChannels() {
      return ZERO_CHANNELS;
    }

    @Override
    public double getCurrent(int channel) {
      return 0.0;
    }

    @Override
    public void clearStickyFaults() {}

    @Override
    public int getModule() {
      return MODULE_ID;
    }

    @Override
    public void close() {}
  }
}
