package frc.robot.tests.dsl.signals;

import frc.robot.tests.dsl.DslSignalRegistry;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   LimitSwitchSignalProvider - DSL signal contract for limit switch devices.
 */
public final class LimitSwitchSignalProvider implements DslDeviceSignalProvider {
  @Override
  public String deviceType() {
    return DslSignalRegistry.DEVICE_TYPE_LIMIT_SWITCH;
  }

  @Override
  public Map<String, DslSignalMeta> signals() {
    Map<String, DslSignalMeta> signals = new LinkedHashMap<>();
    signals.put(
        DslSignalRegistry.SIGNAL_PRESSED,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    return signals;
  }
}
