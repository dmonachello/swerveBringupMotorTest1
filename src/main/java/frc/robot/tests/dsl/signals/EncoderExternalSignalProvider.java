package frc.robot.tests.dsl.signals;

import frc.robot.tests.dsl.DslSignalRegistry;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   EncoderExternalSignalProvider - DSL signal contract for external encoders.
 */
public final class EncoderExternalSignalProvider implements DslDeviceSignalProvider {
  @Override
  public String deviceType() {
    return DslSignalRegistry.DEVICE_TYPE_ENCODER_EXTERNAL;
  }

  @Override
  public Map<String, DslSignalMeta> signals() {
    Map<String, DslSignalMeta> signals = new LinkedHashMap<>();
    signals.put(
        DslSignalRegistry.SIGNAL_POSITION,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_POSITION_ACTUAL,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_POSITION_DELTA,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_POSITION_DELTA_MAX_ABS,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_VELOCITY,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_VELOCITY_ACTUAL,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_VELOCITY_ACTUAL_MAX_ABS,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    return signals;
  }
}
