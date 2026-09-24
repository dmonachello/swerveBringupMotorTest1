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
  private final TelemetryUnit unit;
  private final long nominalCadenceUs;
  private final long staleAfterUs;
  private final boolean historyEnabled;
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
    this(
        signalName,
        windowMs,
        nonzeroThreshold,
        TelemetryUnit.UNSPECIFIED,
        TelemetryConstants.DEFAULT_NOMINAL_CADENCE_US,
        TelemetryConstants.DEFAULT_STALE_AFTER_US,
        true,
        reader);
  }

  /**
   * NAME
   *   SampledSignalRegistration - Construct a sampled signal with history metadata.
   *
   * PARAMETERS
   *   unit - Canonical unit, dimension, and value kind.
   *   nominalCadenceUs - Expected source cadence for display and staleness hints.
   *   staleAfterUs - Age after which consumers may mark the signal stale.
   *   historyEnabled - Whether accepted values enter the telemetry journal.
   */
  public SampledSignalRegistration(
      String signalName,
      long windowMs,
      double nonzeroThreshold,
      TelemetryUnit unit,
      long nominalCadenceUs,
      long staleAfterUs,
      boolean historyEnabled,
      SampledSignalReader reader) {
    this.signalName = signalName != null ? signalName : "";
    this.windowMs = windowMs;
    this.nonzeroThreshold = nonzeroThreshold;
    this.unit = unit != null ? unit : TelemetryUnit.UNSPECIFIED;
    this.nominalCadenceUs = nominalCadenceUs;
    this.staleAfterUs = staleAfterUs;
    this.historyEnabled = historyEnabled;
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

  public TelemetryUnit unit() {
    return unit;
  }

  public long nominalCadenceUs() {
    return nominalCadenceUs;
  }

  public long staleAfterUs() {
    return staleAfterUs;
  }

  public boolean historyEnabled() {
    return historyEnabled;
  }

  public SampledSignalReader reader() {
    return reader;
  }
}
