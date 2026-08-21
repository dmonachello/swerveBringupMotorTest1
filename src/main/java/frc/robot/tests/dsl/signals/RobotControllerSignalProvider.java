package frc.robot.tests.dsl.signals;

import frc.robot.tests.dsl.DslSignalRegistry;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   RobotControllerSignalProvider - DSL signal contract for robot controllers.
 */
public final class RobotControllerSignalProvider implements DslDeviceSignalProvider {
  private static final String DEVICE_TYPE = DslSignalRegistry.DEVICE_TYPE_ROBOT_CONTROLLER;

  @Override
  public String deviceType() {
    return DEVICE_TYPE;
  }

  @Override
  public Map<String, DslSignalMeta> signals() {
    Map<String, DslSignalMeta> signals = new LinkedHashMap<>();
    signals.put(
        DslSignalRegistry.SIGNAL_INPUT_VOLTAGE,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_BROWNOUT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_BROWNOUT_VOLTAGE,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_CAN_UTILIZATION,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_CAN_TX_ERROR_COUNT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_CAN_RX_ERROR_COUNT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_CAN_BUS_OFF_COUNT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_CAN_TX_FULL_COUNT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_RAIL_3V3_VOLTAGE,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_RAIL_5V_VOLTAGE,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_RAIL_6V_VOLTAGE,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_RAIL_3V3_ENABLED,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_RAIL_5V_ENABLED,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_RAIL_6V_ENABLED,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_RAIL_3V3_FAULT_COUNT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_RAIL_5V_FAULT_COUNT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_RAIL_6V_FAULT_COUNT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    return signals;
  }
}
