package frc.robot.tests.dsl.signals;

import frc.robot.tests.dsl.DslSignalRegistry;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   ImuSignalProvider - DSL signal contract for IMU devices.
 */
public final class ImuSignalProvider implements DslDeviceSignalProvider {
  @Override
  public String deviceType() {
    return DslSignalRegistry.DEVICE_TYPE_IMU;
  }

  @Override
  public Map<String, DslSignalMeta> signals() {
    Map<String, DslSignalMeta> signals = new LinkedHashMap<>();
    signals.put(
        DslSignalRegistry.SIGNAL_YAW,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_PITCH,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_ROLL,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_YAW_DELTA,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_PITCH_DELTA,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_ROLL_DELTA,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_YAW_DELTA_MAX_ABS,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_PITCH_DELTA_MAX_ABS,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_ROLL_DELTA_MAX_ABS,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_ANGULAR_VELOCITY_X,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_ANGULAR_VELOCITY_Y,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_ANGULAR_VELOCITY_Z,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_ACCEL_X,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_ACCEL_Y,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_ACCEL_Z,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_SUPPLY_VOLTAGE,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_FAULTS,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, true, null, false, false));
    return signals;
  }
}
