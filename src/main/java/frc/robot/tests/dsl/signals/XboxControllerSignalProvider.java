package frc.robot.tests.dsl.signals;

import frc.robot.tests.dsl.DslSignalRegistry;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   XboxControllerSignalProvider - DSL signal contract for Xbox controller devices.
 */
public final class XboxControllerSignalProvider implements DslDeviceSignalProvider {
  @Override
  public String deviceType() {
    return DslSignalRegistry.DEVICE_TYPE_XBOX_CONTROLLER;
  }

  @Override
  public Map<String, DslSignalMeta> signals() {
    Map<String, DslSignalMeta> signals = new LinkedHashMap<>();
    addBoolean(signals, DslSignalRegistry.SIGNAL_A);
    addBoolean(signals, DslSignalRegistry.SIGNAL_B);
    addBoolean(signals, DslSignalRegistry.SIGNAL_X);
    addBoolean(signals, DslSignalRegistry.SIGNAL_Y);
    addBoolean(signals, DslSignalRegistry.SIGNAL_LB);
    addBoolean(signals, DslSignalRegistry.SIGNAL_RB);
    addBoolean(signals, DslSignalRegistry.SIGNAL_BACK);
    addBoolean(signals, DslSignalRegistry.SIGNAL_START);
    addBoolean(signals, DslSignalRegistry.SIGNAL_LS);
    addBoolean(signals, DslSignalRegistry.SIGNAL_RS);
    addBoolean(signals, DslSignalRegistry.SIGNAL_D_UP);
    addBoolean(signals, DslSignalRegistry.SIGNAL_D_RIGHT);
    addBoolean(signals, DslSignalRegistry.SIGNAL_D_DOWN);
    addBoolean(signals, DslSignalRegistry.SIGNAL_D_LEFT);
    addNumber(signals, DslSignalRegistry.SIGNAL_LEFT_X);
    addNumber(signals, DslSignalRegistry.SIGNAL_LEFT_Y);
    addNumber(signals, DslSignalRegistry.SIGNAL_RIGHT_X);
    addNumber(signals, DslSignalRegistry.SIGNAL_RIGHT_Y);
    addNumber(signals, DslSignalRegistry.SIGNAL_LEFT_TRIGGER);
    addNumber(signals, DslSignalRegistry.SIGNAL_RIGHT_TRIGGER);
    return signals;
  }

  private void addBoolean(Map<String, DslSignalMeta> signals, String name) {
    signals.put(
        name,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
  }

  private void addNumber(Map<String, DslSignalMeta> signals, String name) {
    signals.put(
        name,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
  }
}
