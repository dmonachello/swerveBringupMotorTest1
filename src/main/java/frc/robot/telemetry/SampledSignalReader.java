package frc.robot.telemetry;

/**
 * NAME
 *   SampledSignalReader - Single-sample supplier for a sampled telemetry signal.
 *
 * DESCRIPTION
 *   Provides the raw instantaneous value used by the shared sampled-telemetry
 *   service. Implementations may return null when the signal is unavailable.
 */
@FunctionalInterface
public interface SampledSignalReader {
  Double readNow();
}
