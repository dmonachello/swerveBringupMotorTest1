package frc.robot.tests.dsl;

import com.google.gson.JsonObject;
import frc.robot.tests.dsl.signals.DslDeviceSignalProvider;
import frc.robot.tests.dsl.signals.DslSignalMeta;
import frc.robot.tests.dsl.signals.EncoderExternalSignalProvider;
import frc.robot.tests.dsl.signals.LimitSwitchSignalProvider;
import frc.robot.tests.dsl.signals.MotorSignalProvider;
import frc.robot.tests.dsl.signals.TestTimerSignalProvider;
import frc.robot.tests.dsl.signals.XboxControllerSignalProvider;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   DslSignalRegistry - Canonical DSL signal registry aggregator.
 *
 * DESCRIPTION
 *   Owns stable device/signal names and aggregates explicit per-device-type
 *   signal providers into the exported registry used by runtime and host-side
 *   validation artifacts.
 */
public final class DslSignalRegistry {
  public static final String DEVICE_TYPE_MOTOR = "motor";
  public static final String DEVICE_TYPE_LIMIT_SWITCH = "limitSwitch";
  public static final String DEVICE_TYPE_ENCODER_EXTERNAL = "encoderExternal";
  public static final String DEVICE_TYPE_XBOX_CONTROLLER = "xboxController";
  public static final String DEVICE_TYPE_TEST_TIMER = "TestTimer";
  public static final String VALUE_TYPE_BOOLEAN = "boolean";
  public static final String VALUE_TYPE_NUMBER = "number";
  public static final String SIGNAL_OUTPUT = "output";
  public static final String SIGNAL_CURRENT = "current";
  public static final String SIGNAL_TEMPERATURE = "temperature";
  public static final String SIGNAL_VELOCITY = "velocity";
  public static final String SIGNAL_POSITION = "position";
  public static final String SIGNAL_FAULTS = "faults";
  public static final String SIGNAL_PRESSED = "pressed";
  public static final String SIGNAL_ELAPSED = "elapsed";
  public static final String SIGNAL_A = "A";
  public static final String SIGNAL_B = "B";
  public static final String SIGNAL_X = "X";
  public static final String SIGNAL_Y = "Y";
  public static final String SIGNAL_LB = "LB";
  public static final String SIGNAL_RB = "RB";
  public static final String SIGNAL_BACK = "BACK";
  public static final String SIGNAL_START = "START";
  public static final String SIGNAL_LS = "LS";
  public static final String SIGNAL_RS = "RS";
  public static final String SIGNAL_D_UP = "D_UP";
  public static final String SIGNAL_D_RIGHT = "D_RIGHT";
  public static final String SIGNAL_D_DOWN = "D_DOWN";
  public static final String SIGNAL_D_LEFT = "D_LEFT";
  public static final String SIGNAL_LEFT_X = "leftX";
  public static final String SIGNAL_LEFT_Y = "leftY";
  public static final String SIGNAL_RIGHT_X = "rightX";
  public static final String SIGNAL_RIGHT_Y = "rightY";
  public static final String SIGNAL_LEFT_TRIGGER = "leftTrigger";
  public static final String SIGNAL_RIGHT_TRIGGER = "rightTrigger";

  private static final List<DslDeviceSignalProvider> PROVIDERS = List.of(
      new MotorSignalProvider(),
      new LimitSwitchSignalProvider(),
      new EncoderExternalSignalProvider(),
      new XboxControllerSignalProvider(),
      new TestTimerSignalProvider());

  private static final Map<String, Map<String, DslSignalMeta>> REGISTRY = buildRegistry();

  private DslSignalRegistry() {}

  public static Map<String, Map<String, DslSignalMeta>> registry() {
    return REGISTRY;
  }

  public static DslSignalMeta signal(String deviceType, String signalName) {
    if (deviceType == null || signalName == null) {
      return null;
    }
    Map<String, DslSignalMeta> signals = REGISTRY.get(deviceType);
    return signals != null ? signals.get(signalName) : null;
  }

  public static JsonObject exportJson() {
    JsonObject root = new JsonObject();
    root.addProperty("schemaVersion", 1);
    root.addProperty("generatedFrom", DslSignalRegistry.class.getName());
    JsonObject deviceTypes = new JsonObject();
    for (Map.Entry<String, Map<String, DslSignalMeta>> entry : REGISTRY.entrySet()) {
      JsonObject signals = new JsonObject();
      for (Map.Entry<String, DslSignalMeta> signalEntry : entry.getValue().entrySet()) {
        DslSignalMeta meta = signalEntry.getValue();
        JsonObject obj = new JsonObject();
        obj.addProperty("valueType", meta.valueType());
        obj.addProperty("readable", meta.readable());
        obj.addProperty("writable", meta.writable());
        obj.addProperty("clearable", meta.clearable());
        if (meta.safeValue() != null) {
          obj.addProperty("safeValue", meta.safeValue());
        } else {
          obj.add("safeValue", null);
        }
        obj.addProperty("safeProvider", meta.safeProvider());
        obj.addProperty("unsafeExitAllowed", meta.unsafeExitAllowed());
        signals.add(signalEntry.getKey(), obj);
      }
      deviceTypes.add(entry.getKey(), signals);
    }
    root.add("deviceTypes", deviceTypes);
    return root;
  }

  public static List<DslDeviceSignalProvider> providers() {
    return PROVIDERS;
  }

  private static Map<String, Map<String, DslSignalMeta>> buildRegistry() {
    Map<String, Map<String, DslSignalMeta>> root = new LinkedHashMap<>();
    for (DslDeviceSignalProvider provider : PROVIDERS) {
      if (provider == null) {
        continue;
      }
      String deviceType = provider.deviceType();
      if (deviceType == null || deviceType.isBlank()) {
        throw new IllegalStateException("DSL signal provider returned blank device type");
      }
      if (root.containsKey(deviceType)) {
        throw new IllegalStateException("Duplicate DSL signal provider for device type: " + deviceType);
      }
      root.put(deviceType, new LinkedHashMap<>(provider.signals()));
    }
    return root;
  }
}
