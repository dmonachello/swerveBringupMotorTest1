package frc.robot.telemetry;

/**
 * NAME
 *   SampledSignalNames - Canonical names for sampled robot-side telemetry.
 *
 * DESCRIPTION
 *   Defines shared signal identifiers used by sampled-telemetry providers,
 *   the rolling sampler, and downstream JSON/export surfaces.
 */
public final class SampledSignalNames {
  public static final String CURRENT_ACTUAL = "current_actual";
  public static final String VELOCITY_ACTUAL = "velocity_actual";
  public static final String TEMPERATURE_ACTUAL = "temperature_actual";
  public static final String BUS_VOLTAGE = "bus_voltage";
  public static final String OUTPUT_PERCENT_APPLIED = "output_percent_applied";

  private SampledSignalNames() {}
}
