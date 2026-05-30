package frc.robot.telemetry;

/**
 * NAME
 *   SampledSignalSummary - Rolling aggregate values for a sampled signal.
 *
 * DESCRIPTION
 *   Carries the latest instantaneous value plus recent-window aggregates
 *   computed by the shared robot-side sampled-telemetry service.
 */
public final class SampledSignalSummary {
  public String signalName = "";
  public Double instantValue;
  public Double avgValue;
  public Double peakValue;
  public Double nonzeroRatio;
  public Integer sampleCount;
  public Long windowMs;
}
