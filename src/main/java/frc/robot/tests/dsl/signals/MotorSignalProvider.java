package frc.robot.tests.dsl.signals;

import frc.robot.tests.dsl.DslSignalRegistry;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   MotorSignalProvider - DSL signal contract for motor devices.
 */
public final class MotorSignalProvider implements DslDeviceSignalProvider {
  @Override
  public String deviceType() {
    return DslSignalRegistry.DEVICE_TYPE_MOTOR;
  }

  @Override
  public Map<String, DslSignalMeta> signals() {
    Map<String, DslSignalMeta> signals = new LinkedHashMap<>();
    signals.put(
        DslSignalRegistry.SIGNAL_OUTPUT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, false, true, false, 0.0, false, true));
    signals.put(
        DslSignalRegistry.SIGNAL_OUTPUT_PERCENT_CMD,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, true, false, null, true, true));
    signals.put(
        DslSignalRegistry.SIGNAL_OUTPUT_PERCENT_APPLIED,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_CURRENT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_CURRENT_ACTUAL,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_TEMPERATURE,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_TEMPERATURE_ACTUAL,
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
        DslSignalRegistry.SIGNAL_FAULTS,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, false, false, true, null, false, false));
    return signals;
  }
}
