package frc.robot.tests.dsl.signals;

import frc.robot.tests.dsl.DslSignalRegistry;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   TestTimerSignalProvider - DSL signal contract for the built-in test timer.
 */
public final class TestTimerSignalProvider implements DslDeviceSignalProvider {
  @Override
  public String deviceType() {
    return DslSignalRegistry.DEVICE_TYPE_TEST_TIMER;
  }

  @Override
  public Map<String, DslSignalMeta> signals() {
    Map<String, DslSignalMeta> signals = new LinkedHashMap<>();
    signals.put(
        DslSignalRegistry.SIGNAL_ELAPSED,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    return signals;
  }
}
