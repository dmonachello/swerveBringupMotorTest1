package frc.robot.telemetry;

import frc.robot.devices.DeviceUnit;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * NAME
 *   SampledTelemetrySampler - Shared rolling-window sampler for device signals.
 *
 * DESCRIPTION
 *   Samples registered device signals on robot cadence and computes stable
 *   recent-window aggregates such as instantaneous value, average, peak,
 *   nonzero ratio, and sample count.
 */
public final class SampledTelemetrySampler {
  private static final int KEY_INITIAL_BUILDER_CAPACITY = 96;
  private static final int UNBOUNDED_SIGNAL_READS = Integer.MAX_VALUE;

  private final Map<String, SignalWindowState> signalStates = new LinkedHashMap<>();
  private int periodicReadCursor = 0;

  /**
   * NAME
   *   sampleDevices - Sample all available registered signals for active devices.
   *
   * PARAMETERS
   *   devices - Devices to inspect for sampled-signal registrations.
   *   nowMs - Current wall-clock time in milliseconds.
   *
   * SIDE EFFECTS
   *   Updates rolling windows and prunes states for signals not seen in the
   *   current runtime device set.
   */
  public void sampleDevices(List<DeviceUnit> devices, long nowMs) {
    sampleDevices(devices, nowMs, UNBOUNDED_SIGNAL_READS);
  }

  /**
   * NAME
   *   sampleDevices - Sample a bounded subset of available registered signals.
   *
   * PARAMETERS
   *   devices - Devices to inspect for sampled-signal registrations.
   *   nowMs - Current wall-clock time in milliseconds.
   *   maxSignalReads - Maximum raw signal reads to perform this pass.
   *
   * SIDE EFFECTS
   *   Updates rolling windows for selected signals, trims stale state for
   *   active-but-not-sampled signals, and prunes state for signals no longer
   *   present in the runtime device set.
   */
  public void sampleDevices(List<DeviceUnit> devices, long nowMs, int maxSignalReads) {
    Set<String> seenKeys = new HashSet<>();
    List<SignalReadPlanEntry> activePlans = new ArrayList<>();
    if (devices != null) {
      for (DeviceUnit device : devices) {
        if (device == null || !device.isCreated()) {
          continue;
        }
        List<SampledSignalRegistration> registrations = device.getSampledSignalRegistrations();
        if (registrations == null || registrations.isEmpty()) {
          continue;
        }
        for (SampledSignalRegistration registration : registrations) {
          if (registration == null
              || registration.signalName() == null
              || registration.signalName().isBlank()
              || registration.reader() == null) {
            continue;
          }
          String key = buildSignalKey(device, registration.signalName());
          seenKeys.add(key);
          SignalWindowState state =
              signalStates.computeIfAbsent(
                  key,
                  ignored ->
                      new SignalWindowState(
                          registration.signalName(),
                          registration.windowMs(),
                          registration.nonzeroThreshold()));
          state.windowMs = registration.windowMs();
          state.nonzeroThreshold = registration.nonzeroThreshold();
          activePlans.add(new SignalReadPlanEntry(key, registration, state));
        }
      }
    }
    applyBoundedReadPlan(activePlans, nowMs, maxSignalReads);
    signalStates.keySet().removeIf(key -> !seenKeys.contains(key));
  }

  /**
   * NAME
   *   clearAll - Remove all sampled telemetry state.
   */
  public void clearAll() {
    signalStates.clear();
    periodicReadCursor = 0;
  }

  /**
   * NAME
   *   getDeviceSummaries - Return rolling summaries for a single device.
   *
   * PARAMETERS
   *   device - Device whose sampled signals should be summarized.
   *
   * RETURNS
   *   Per-signal summaries keyed by canonical signal name.
   */
  public Map<String, SampledSignalSummary> getDeviceSummaries(DeviceUnit device) {
    Map<String, SampledSignalSummary> summaries = new LinkedHashMap<>();
    if (device == null) {
      return summaries;
    }
    for (SampledSignalRegistration registration : device.getSampledSignalRegistrations()) {
      if (registration == null
          || registration.signalName() == null
          || registration.signalName().isBlank()) {
        continue;
      }
      SignalWindowState state = signalStates.get(buildSignalKey(device, registration.signalName()));
      if (state == null) {
        continue;
      }
      summaries.put(registration.signalName(), state.toSummary());
    }
    return summaries;
  }

  private String buildSignalKey(DeviceUnit device, String signalName) {
    StringBuilder sb = new StringBuilder(KEY_INITIAL_BUILDER_CAPACITY);
    sb.append(device.getHeader() != null ? device.getHeader().vendor() : "");
    sb.append('|');
    sb.append(device.getDeviceType() != null ? device.getDeviceType() : "");
    sb.append('|');
    sb.append(device.getCanId());
    sb.append('|');
    sb.append(device.getLabel() != null ? device.getLabel() : "");
    sb.append('|');
    sb.append(signalName != null ? signalName : "");
    return sb.toString();
  }

  private void applyBoundedReadPlan(
      List<SignalReadPlanEntry> activePlans,
      long nowMs,
      int maxSignalReads) {
    if (activePlans == null || activePlans.isEmpty()) {
      periodicReadCursor = 0;
      return;
    }
    int planSize = activePlans.size();
    int normalizedMaxReads =
        maxSignalReads <= 0 ? 0 : Math.min(maxSignalReads, planSize);
    Set<String> sampledKeys = new HashSet<>();
    if (normalizedMaxReads > 0) {
      int startCursor = Math.floorMod(periodicReadCursor, planSize);
      for (int offset = 0; offset < normalizedMaxReads; offset++) {
        SignalReadPlanEntry entry = activePlans.get((startCursor + offset) % planSize);
        sampledKeys.add(entry.key);
        readSignalEntry(entry, nowMs);
      }
      periodicReadCursor = (startCursor + normalizedMaxReads) % planSize;
    } else {
      periodicReadCursor = Math.floorMod(periodicReadCursor, planSize);
    }
    for (SignalReadPlanEntry entry : activePlans) {
      if (!sampledKeys.contains(entry.key)) {
        entry.state.trim(nowMs);
      }
    }
  }

  private void readSignalEntry(SignalReadPlanEntry entry, long nowMs) {
    if (entry == null || entry.registration == null || entry.state == null) {
      return;
    }
    try {
      Double value = entry.registration.reader().readNow();
      if (value != null) {
        entry.state.addSample(nowMs, value);
      } else {
        entry.state.trim(nowMs);
      }
    } catch (RuntimeException ex) {
      entry.state.trim(nowMs);
    }
  }

  private static final class SignalReadPlanEntry {
    private final String key;
    private final SampledSignalRegistration registration;
    private final SignalWindowState state;

    private SignalReadPlanEntry(
        String key,
        SampledSignalRegistration registration,
        SignalWindowState state) {
      this.key = key;
      this.registration = registration;
      this.state = state;
    }
  }

  private static final class SignalWindowState {
    private final String signalName;
    private final ArrayDeque<ValueSample> samples = new ArrayDeque<>();
    private long windowMs;
    private double nonzeroThreshold;

    private SignalWindowState(String signalName, long windowMs, double nonzeroThreshold) {
      this.signalName = signalName;
      this.windowMs = windowMs;
      this.nonzeroThreshold = nonzeroThreshold;
    }

    private void addSample(long nowMs, double value) {
      samples.addLast(new ValueSample(nowMs, value));
      trim(nowMs);
    }

    private void trim(long nowMs) {
      while (!samples.isEmpty()) {
        ValueSample sample = samples.peekFirst();
        if (sample == null || nowMs - sample.timestampMs <= windowMs) {
          return;
        }
        samples.removeFirst();
      }
    }

    private SampledSignalSummary toSummary() {
      SampledSignalSummary summary = new SampledSignalSummary();
      summary.signalName = signalName;
      summary.windowMs = windowMs;
      if (samples.isEmpty()) {
        summary.sampleCount = 0;
        summary.nonzeroRatio = 0.0;
        return summary;
      }
      double sum = 0.0;
      double peak = 0.0;
      int nonzeroCount = 0;
      List<ValueSample> values = new ArrayList<>(samples);
      for (ValueSample sample : values) {
        double magnitude = Math.abs(sample.value);
        sum += sample.value;
        peak = Math.max(peak, magnitude);
        if (magnitude > nonzeroThreshold) {
          nonzeroCount++;
        }
      }
      ValueSample last = samples.peekLast();
      summary.instantValue = last != null ? last.value : null;
      summary.avgValue = sum / values.size();
      summary.peakValue = peak;
      summary.sampleCount = values.size();
      summary.nonzeroRatio = values.isEmpty() ? 0.0 : ((double) nonzeroCount) / values.size();
      return summary;
    }
  }

  private static final class ValueSample {
    private final long timestampMs;
    private final double value;

    private ValueSample(long timestampMs, double value) {
      this.timestampMs = timestampMs;
      this.value = value;
    }
  }
}
