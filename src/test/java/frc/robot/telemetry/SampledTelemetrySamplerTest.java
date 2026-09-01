package frc.robot.telemetry;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class SampledTelemetrySamplerTest {
  private static final String VENDOR = "TEST";
  private static final String DEVICE_TYPE = "motor";
  private static final String SIGNAL_NAME = SampledSignalNames.CURRENT_ACTUAL;
  private static final long WINDOW_MS = 1000L;
  private static final double NONZERO_THRESHOLD = 0.01;
  private static final long NOW_MS = 1000L;
  private static final int MAX_SIGNAL_READS_PER_PASS = 1;
  private static final int DEVICE_ONE_ID = 1;
  private static final int DEVICE_TWO_ID = 2;
  private static final String DEVICE_ONE_LABEL = "dev1";
  private static final String DEVICE_TWO_LABEL = "dev2";
  private static final double DEVICE_ONE_VALUE = 1.0;
  private static final double DEVICE_TWO_VALUE = 2.0;
  private static final long NEXT_NOW_MS = 1020L;

  @Test
  void boundedSamplingUsesRoundRobinAcrossDevices() {
    SampledTelemetrySampler sampler = new SampledTelemetrySampler();
    AtomicInteger readsOne = new AtomicInteger();
    AtomicInteger readsTwo = new AtomicInteger();
    DeviceUnit deviceOne =
        new TestDevice(
            DEVICE_ONE_ID,
            DEVICE_ONE_LABEL,
            () -> {
              readsOne.incrementAndGet();
              return DEVICE_ONE_VALUE;
            });
    DeviceUnit deviceTwo =
        new TestDevice(
            DEVICE_TWO_ID,
            DEVICE_TWO_LABEL,
            () -> {
              readsTwo.incrementAndGet();
              return DEVICE_TWO_VALUE;
            });

    sampler.sampleDevices(
        List.of(deviceOne, deviceTwo),
        NOW_MS,
        MAX_SIGNAL_READS_PER_PASS);

    assertEquals(1, readsOne.get());
    assertEquals(0, readsTwo.get());
    assertEquals(
        1,
        sampler.getDeviceSummaries(deviceOne).get(SIGNAL_NAME).sampleCount);
    assertTrue(sampler.getDeviceSummaries(deviceTwo).containsKey(SIGNAL_NAME));
    assertEquals(
        0,
        sampler.getDeviceSummaries(deviceTwo).get(SIGNAL_NAME).sampleCount);

    sampler.sampleDevices(
        List.of(deviceOne, deviceTwo),
        NEXT_NOW_MS,
        MAX_SIGNAL_READS_PER_PASS);

    assertEquals(1, readsOne.get());
    assertEquals(1, readsTwo.get());
    assertEquals(
        1,
        sampler.getDeviceSummaries(deviceTwo).get(SIGNAL_NAME).sampleCount);
  }

  private static final class TestDevice implements DeviceUnit {
    private final int canId;
    private final String label;
    private final SampledSignalReader reader;

    private TestDevice(int canId, String label, SampledSignalReader reader) {
      this.canId = canId;
      this.label = label;
      this.reader = reader;
    }

    @Override
    public void ensureCreated() {}

    @Override
    public void close() {}

    @Override
    public void clearFaults() {}

    @Override
    public int getCanId() {
      return canId;
    }

    @Override
    public String getLabel() {
      return label;
    }

    @Override
    public RegistrationHeader getHeader() {
      return new RegistrationHeader(
          label,
          VENDOR,
          DEVICE_TYPE,
          "",
          "",
          "",
          "");
    }

    @Override
    public String getDeviceType() {
      return DEVICE_TYPE;
    }

    @Override
    public DeviceSnapshot snapshot() {
      DeviceSnapshot snap = new DeviceSnapshot();
      snap.label = label;
      snap.canId = canId;
      snap.deviceType = DEVICE_TYPE;
      snap.vendor = VENDOR;
      snap.present = true;
      return snap;
    }

    @Override
    public boolean isCreated() {
      return true;
    }

    @Override
    public List<SampledSignalRegistration> getSampledSignalRegistrations() {
      return List.of(
          new SampledSignalRegistration(
              SIGNAL_NAME,
              WINDOW_MS,
              NONZERO_THRESHOLD,
              reader));
    }
  }
}
