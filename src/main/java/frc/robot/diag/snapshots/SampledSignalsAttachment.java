package frc.robot.diag.snapshots;

import frc.robot.telemetry.SampledSignalSummary;
import java.util.ArrayList;
import java.util.List;

/**
 * NAME
 *   SampledSignalsAttachment - Rolling sampled-telemetry summaries for a device.
 *
 * DESCRIPTION
 *   Carries processed recent-window telemetry for device signals such as
 *   current, velocity, and other bursty measurements that are poorly
 *   represented by a single instantaneous sample.
 */
public final class SampledSignalsAttachment extends DeviceAttachment {
  public final List<SampledSignalSummary> signals = new ArrayList<>();

  /**
   * NAME
   *   SampledSignalsAttachment - Construct with the standard attachment type.
   */
  public SampledSignalsAttachment() {
    super("sampledSignals");
  }
}
