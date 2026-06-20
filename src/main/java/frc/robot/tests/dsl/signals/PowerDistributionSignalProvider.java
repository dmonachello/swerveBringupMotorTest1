package frc.robot.tests.dsl.signals;

import frc.robot.tests.dsl.DslSignalRegistry;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   PowerDistributionSignalProvider - DSL signal contract for PDH/PDP devices.
 */
public final class PowerDistributionSignalProvider implements DslDeviceSignalProvider {
  private static final String CHANNEL_CURRENT_SUFFIX = "_current";
  private static final String CHANNEL_FAULT_SUFFIX = "_fault";
  private static final String CHANNEL_STICKY_FAULT_SUFFIX = "_sticky_fault";
  private final String deviceType;
  private final int channelCount;

  /**
   * NAME
   *   PowerDistributionSignalProvider - Construct one provider for one power-distribution device type.
   *
   * PARAMETERS
   *   deviceType - DSL device type name such as PDP or PDH.
   *   channelCount - number of breaker channels exported for this module type.
   */
  public PowerDistributionSignalProvider(String deviceType, int channelCount) {
    this.deviceType = deviceType;
    this.channelCount = channelCount;
  }

  @Override
  public String deviceType() {
    return deviceType;
  }

  @Override
  public Map<String, DslSignalMeta> signals() {
    Map<String, DslSignalMeta> signals = new LinkedHashMap<>();
    signals.put(
        DslSignalRegistry.SIGNAL_VOLTAGE,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_TOTAL_CURRENT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_TEMPERATURE,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_SWITCHABLE_ENABLED,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_BROWNOUT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_CAN_WARNING,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_HARDWARE_FAULT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_STICKY_BROWNOUT,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_STICKY_CAN_WARNING,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_STICKY_CAN_BUS_OFF,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_STICKY_HAS_RESET,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    signals.put(
        DslSignalRegistry.SIGNAL_FAULTS,
        new DslSignalMeta(
            DslSignalRegistry.VALUE_TYPE_BOOLEAN, false, false, true, null, false, false));
    for (int channel = 0; channel < channelCount; channel++) {
      signals.put(
          "channel" + channel + CHANNEL_CURRENT_SUFFIX,
          new DslSignalMeta(
              DslSignalRegistry.VALUE_TYPE_NUMBER, true, false, false, null, false, false));
      signals.put(
          "channel" + channel + CHANNEL_FAULT_SUFFIX,
          new DslSignalMeta(
              DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
      signals.put(
          "channel" + channel + CHANNEL_STICKY_FAULT_SUFFIX,
          new DslSignalMeta(
              DslSignalRegistry.VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    }
    return signals;
  }
}
