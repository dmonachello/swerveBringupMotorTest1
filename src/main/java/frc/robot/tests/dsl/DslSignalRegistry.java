package frc.robot.tests.dsl;

import com.google.gson.JsonObject;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   DslSignalRegistry - Canonical Java-side signal capability registry for DSL tests.
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

  public record SignalMeta(
      String valueType,
      boolean readable,
      boolean writable,
      boolean clearable,
      Double safeValue,
      boolean safeProvider,
      boolean unsafeExitAllowed) {}

  private static final Map<String, Map<String, SignalMeta>> REGISTRY = buildRegistry();

  private DslSignalRegistry() {}

  public static Map<String, Map<String, SignalMeta>> registry() {
    return REGISTRY;
  }

  public static SignalMeta signal(String deviceType, String signalName) {
    if (deviceType == null || signalName == null) {
      return null;
    }
    Map<String, SignalMeta> signals = REGISTRY.get(deviceType);
    return signals != null ? signals.get(signalName) : null;
  }

  public static JsonObject exportJson() {
    JsonObject root = new JsonObject();
    root.addProperty("schemaVersion", 1);
    root.addProperty("generatedFrom", DslSignalRegistry.class.getName());
    JsonObject deviceTypes = new JsonObject();
    for (Map.Entry<String, Map<String, SignalMeta>> entry : REGISTRY.entrySet()) {
      JsonObject signals = new JsonObject();
      for (Map.Entry<String, SignalMeta> signalEntry : entry.getValue().entrySet()) {
        SignalMeta meta = signalEntry.getValue();
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

  private static Map<String, Map<String, SignalMeta>> buildRegistry() {
    Map<String, Map<String, SignalMeta>> root = new LinkedHashMap<>();
    root.put(DEVICE_TYPE_MOTOR, new LinkedHashMap<>());
    root.get(DEVICE_TYPE_MOTOR).put(SIGNAL_OUTPUT, new SignalMeta(VALUE_TYPE_NUMBER, false, true, false, 0.0, false, true));
    root.get(DEVICE_TYPE_MOTOR).put(SIGNAL_CURRENT, new SignalMeta(VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    root.get(DEVICE_TYPE_MOTOR).put(SIGNAL_TEMPERATURE, new SignalMeta(VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    root.get(DEVICE_TYPE_MOTOR).put(SIGNAL_VELOCITY, new SignalMeta(VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    root.get(DEVICE_TYPE_MOTOR).put(SIGNAL_POSITION, new SignalMeta(VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    root.get(DEVICE_TYPE_MOTOR).put(SIGNAL_FAULTS, new SignalMeta(VALUE_TYPE_BOOLEAN, false, false, true, null, false, false));

    root.put(DEVICE_TYPE_LIMIT_SWITCH, new LinkedHashMap<>());
    root.get(DEVICE_TYPE_LIMIT_SWITCH).put(SIGNAL_PRESSED, new SignalMeta(VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));

    root.put(DEVICE_TYPE_ENCODER_EXTERNAL, new LinkedHashMap<>());
    root.get(DEVICE_TYPE_ENCODER_EXTERNAL).put(SIGNAL_POSITION, new SignalMeta(VALUE_TYPE_NUMBER, true, false, false, null, false, false));

    root.put(DEVICE_TYPE_XBOX_CONTROLLER, new LinkedHashMap<>());
    root.get(DEVICE_TYPE_XBOX_CONTROLLER).put("A", new SignalMeta(VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    root.get(DEVICE_TYPE_XBOX_CONTROLLER).put("B", new SignalMeta(VALUE_TYPE_BOOLEAN, true, false, false, null, false, false));
    root.get(DEVICE_TYPE_XBOX_CONTROLLER).put("leftY", new SignalMeta(VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    root.get(DEVICE_TYPE_XBOX_CONTROLLER).put("rightY", new SignalMeta(VALUE_TYPE_NUMBER, true, false, false, null, false, false));

    root.put(DEVICE_TYPE_TEST_TIMER, new LinkedHashMap<>());
    root.get(DEVICE_TYPE_TEST_TIMER).put(SIGNAL_ELAPSED, new SignalMeta(VALUE_TYPE_NUMBER, true, false, false, null, false, false));
    return root;
  }
}
