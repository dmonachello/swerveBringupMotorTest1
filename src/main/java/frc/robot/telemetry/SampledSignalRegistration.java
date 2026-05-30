package frc.robot.telemetry;

/**
 * NAME
 *   SampledSignalRegistration - Robot-side sampled telemetry descriptor.
 *
 * DESCRIPTION
 *   Binds a canonical signal name to a raw read function plus rolling-window
 *   aggregation parameters owned by the shared sampled-telemetry service.
 */
public final class SampledSignalRegistration {
  private final String signalName;
  private final long windowMs;
  private final double nonzeroThreshold;
  private final SampledSignalReader reader;

  /**
   * NAME
   *   SampledSignalRegistration - Construct a sampled-signal descriptor.
   *
   * PARAMETERS
   *   signalName - Canonical signal name.
   *   windowMs - Rolling window length in milliseconds.
   *   nonzeroThreshold - Threshold used for nonzero-ratio aggregation.
   *   reader - Raw single-sample supplier.
   */
  public SampledSignalRegistration(
      String signalName,
      long windowMs,
      double nonzeroThreshold,
      SampledSignalReader reader) {
    this.signalName = signalName != null ? signalName : "";
    this.windowMs = windowMs;
    this.nonzeroThreshold = nonzeroThreshold;
    this.reader = reader;
  }

  public String signalName() {
    return signalName;
  }

  public long windowMs() {
    return windowMs;
  }

  public double nonzeroThreshold() {
    return nonzeroThreshold;
  }

  public SampledSignalReader reader() {
    return reader;
  }
}
