package frc.robot.telemetry.capture;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import edu.wpi.first.util.datalog.DataLogReader;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import frc.robot.telemetry.SampledSignalNames;
import frc.robot.telemetry.SampledSignalRegistration;
import frc.robot.telemetry.SampledTelemetrySampler;
import frc.robot.telemetry.TelemetryUnit;
import java.io.IOException;
import java.lang.reflect.Field;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** NAME WpilogTelemetryRecorderTest - Robot-local capture round-trip regression. */
final class WpilogTelemetryRecorderTest {
  private static final long NOW_MS = 1_000L;
  private static final long SOURCE_TIMESTAMP_US = 1_000_000L;
  private static final int READ_BUDGET = 1;
  private static final int DEVICE_ID = 1;
  private static final double CURRENT_A = 12.5;
  private static final String LABEL = "motor1";
  private static final String VENDOR = "TEST";
  private static final String DEVICE_TYPE = "motor";
  private static final long DELETE_TIMEOUT_MS = 2_000L;
  private static final long DELETE_RETRY_MS = 10L;

  @TempDir Path temporaryDirectory;

  @Test
  void manualCaptureWritesReadableWpilog() throws Exception {
    SampledTelemetrySampler sampler = new SampledTelemetrySampler();
    DeviceUnit device = new TestDevice();
    sampler.sampleDevices(List.of(device), NOW_MS, SOURCE_TIMESTAMP_US, READ_BUDGET);
    WpilogTelemetryRecorder recorder =
        new WpilogTelemetryRecorder(sampler, temporaryDirectory);

    WpilogTelemetryRecorder.CaptureStatus started = recorder.start();
    sampler.sampleDevices(
        List.of(device),
        NOW_MS,
        SOURCE_TIMESTAMP_US,
        READ_BUDGET);
    WpilogTelemetryRecorder.CaptureStatus stopped = recorder.stop();
    recorder.close();

    assertTrue(started.ok());
    assertTrue(stopped.ok());
    Path capture = Path.of(started.path());
    assertTrue(Files.exists(capture));
    assertTrue(Files.size(capture) > 0L);
    DataLogReader reader = new DataLogReader(ByteBuffer.wrap(Files.readAllBytes(capture)));
    assertTrue(reader.isValid());
    assertFalse(reader.getExtraHeader().isBlank());
    deleteAfterBackgroundWriterReleases(capture);
  }

  @Test
  void matchEnableTriggerIsOptInAndStartsOffPeriodicThread() throws Exception {
    SampledTelemetrySampler sampler = new SampledTelemetrySampler();
    WpilogTelemetryRecorder recorder =
        new WpilogTelemetryRecorder(sampler, temporaryDirectory);
    recorder.configureAutomaticTriggers(true, false);

    recorder.updateRobotEnabled(false);
    recorder.updateRobotEnabled(true);
    long deadline = System.currentTimeMillis() + DELETE_TIMEOUT_MS;
    while (!recorder.status().recording() && System.currentTimeMillis() < deadline) {
      Thread.sleep(DELETE_RETRY_MS);
    }

    assertTrue(recorder.status().recording());
    Path capture = Path.of(recorder.status().path());
    recorder.stop();
    recorder.close();
    deleteAfterBackgroundWriterReleases(capture);
  }

  @Test
  void exceptionAutomaticStartPreservesPostTriggerDeadline() throws Exception {
    SampledTelemetrySampler sampler = new SampledTelemetrySampler();
    WpilogTelemetryRecorder recorder =
        new WpilogTelemetryRecorder(sampler, temporaryDirectory);
    recorder.configureAutomaticTriggers(false, true);

    recorder.onUncaughtException();
    long requestedDeadline = longField(recorder, "automaticStopAtMs");
    long deadline = System.currentTimeMillis() + DELETE_TIMEOUT_MS;
    while (!recorder.status().recording() && System.currentTimeMillis() < deadline) {
      Thread.sleep(DELETE_RETRY_MS);
    }

    assertTrue(recorder.status().recording());
    assertEquals(requestedDeadline, longField(recorder, "automaticStopAtMs"));
    Path capture = Path.of(recorder.status().path());
    recorder.stop();
    recorder.close();
    deleteAfterBackgroundWriterReleases(capture);
  }

  @Test
  void matchDisableDoesNotScheduleStopForManualCapture() throws Exception {
    SampledTelemetrySampler sampler = new SampledTelemetrySampler();
    WpilogTelemetryRecorder recorder =
        new WpilogTelemetryRecorder(sampler, temporaryDirectory);
    recorder.configureAutomaticTriggers(true, false);
    WpilogTelemetryRecorder.CaptureStatus started = recorder.start();

    recorder.updateRobotEnabled(true);
    recorder.updateRobotEnabled(false);

    assertEquals(0L, longField(recorder, "automaticStopAtMs"));
    Path capture = Path.of(started.path());
    recorder.stop();
    recorder.close();
    deleteAfterBackgroundWriterReleases(capture);
  }

  private static long longField(
      WpilogTelemetryRecorder recorder,
      String fieldName) throws Exception {
    Field field = WpilogTelemetryRecorder.class.getDeclaredField(fieldName);
    field.setAccessible(true);
    return field.getLong(recorder);
  }

  private static void deleteAfterBackgroundWriterReleases(Path capture) throws Exception {
    long deadline = System.currentTimeMillis() + DELETE_TIMEOUT_MS;
    IOException lastFailure = null;
    while (System.currentTimeMillis() < deadline) {
      try {
        Files.deleteIfExists(capture);
        return;
      } catch (IOException ex) {
        lastFailure = ex;
        Thread.sleep(DELETE_RETRY_MS);
      }
    }
    if (lastFailure != null) {
      throw lastFailure;
    }
  }

  private static final class TestDevice implements DeviceUnit {
    @Override public void ensureCreated() {}
    @Override public void close() {}
    @Override public void clearFaults() {}
    @Override public int getCanId() { return DEVICE_ID; }
    @Override public String getLabel() { return LABEL; }
    @Override public String getDeviceType() { return DEVICE_TYPE; }
    @Override public boolean isCreated() { return true; }

    @Override
    public RegistrationHeader getHeader() {
      return new RegistrationHeader(LABEL, VENDOR, DEVICE_TYPE, "", "", "", "");
    }

    @Override
    public DeviceSnapshot snapshot() {
      return new DeviceSnapshot();
    }

    @Override
    public List<SampledSignalRegistration> getSampledSignalRegistrations() {
      return List.of(
          new SampledSignalRegistration(
              SampledSignalNames.CURRENT_ACTUAL,
              NOW_MS,
              CURRENT_A,
              TelemetryUnit.AMPERE,
              SOURCE_TIMESTAMP_US,
              SOURCE_TIMESTAMP_US,
              true,
              () -> CURRENT_A));
    }
  }
}
