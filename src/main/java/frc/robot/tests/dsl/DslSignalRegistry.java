package frc.robot.tests.dsl;

import com.google.gson.JsonObject;
import frc.robot.tests.dsl.signals.DslDeviceSignalProvider;
import frc.robot.tests.dsl.signals.DslSignalMeta;
import frc.robot.tests.dsl.signals.EncoderExternalSignalProvider;
import frc.robot.tests.dsl.signals.ImuSignalProvider;
import frc.robot.tests.dsl.signals.LimitSwitchSignalProvider;
import frc.robot.tests.dsl.signals.MotorSignalProvider;
import frc.robot.tests.dsl.signals.PowerDistributionSignalProvider;
import frc.robot.tests.dsl.signals.RobotControllerSignalProvider;
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
  public static final String DEVICE_TYPE_CANCODER = "CANCoder";
  public static final String DEVICE_TYPE_IMU = "imu";
  public static final String DEVICE_TYPE_PIGEON = "Pigeon";
  public static final String DEVICE_TYPE_XBOX_CONTROLLER = "xboxController";
  public static final String DEVICE_TYPE_TEST_TIMER = "TestTimer";
  public static final String DEVICE_TYPE_PDH = "PDH";
  public static final String DEVICE_TYPE_PDP = "PDP";
  public static final String DEVICE_TYPE_ROBOT_CONTROLLER = "robotController";
  public static final String DEVICE_TYPE_SYSTEM_CORE = "SystemCore";
  public static final int PDP_CHANNEL_COUNT = 16;
  public static final int PDH_CHANNEL_COUNT = 24;
  public static final String VALUE_TYPE_BOOLEAN = "boolean";
  public static final String VALUE_TYPE_NUMBER = "number";
  public static final String SIGNAL_OUTPUT = "output";
  public static final String SIGNAL_OUTPUT_PERCENT_CMD = "output_percent_cmd";
  public static final String SIGNAL_OUTPUT_PERCENT_APPLIED = "output_percent_applied";
  public static final String SIGNAL_CURRENT = "current";
  public static final String SIGNAL_CURRENT_ACTUAL = "current_actual";
  public static final String SIGNAL_CURRENT_ACTUAL_MAX = "current_actual_max";
  public static final String SIGNAL_TEMPERATURE = "temperature";
  public static final String SIGNAL_TEMPERATURE_ACTUAL = "temperature_actual";
  public static final String SIGNAL_VELOCITY = "velocity";
  public static final String SIGNAL_VELOCITY_ACTUAL = "velocity_actual";
  public static final String SIGNAL_VELOCITY_ACTUAL_MAX_ABS = "velocity_actual_max_abs";
  public static final String SIGNAL_POSITION = "position";
  public static final String SIGNAL_POSITION_ACTUAL = "position_actual";
  public static final String SIGNAL_POSITION_DELTA = "position_delta";
  public static final String SIGNAL_POSITION_DELTA_MAX_ABS = "position_delta_max_abs";
  public static final String SIGNAL_YAW = "yaw";
  public static final String SIGNAL_PITCH = "pitch";
  public static final String SIGNAL_ROLL = "roll";
  public static final String SIGNAL_YAW_DELTA = "yaw_delta";
  public static final String SIGNAL_PITCH_DELTA = "pitch_delta";
  public static final String SIGNAL_ROLL_DELTA = "roll_delta";
  public static final String SIGNAL_YAW_DELTA_MAX_ABS = "yaw_delta_max_abs";
  public static final String SIGNAL_PITCH_DELTA_MAX_ABS = "pitch_delta_max_abs";
  public static final String SIGNAL_ROLL_DELTA_MAX_ABS = "roll_delta_max_abs";
  public static final String SIGNAL_ANGULAR_VELOCITY_X = "angular_velocity_x";
  public static final String SIGNAL_ANGULAR_VELOCITY_Y = "angular_velocity_y";
  public static final String SIGNAL_ANGULAR_VELOCITY_Z = "angular_velocity_z";
  public static final String SIGNAL_ACCEL_X = "accel_x";
  public static final String SIGNAL_ACCEL_Y = "accel_y";
  public static final String SIGNAL_ACCEL_Z = "accel_z";
  public static final String SIGNAL_FAULTS = "faults";
  public static final String SIGNAL_VOLTAGE = "voltage";
  public static final String SIGNAL_SUPPLY_VOLTAGE = "supply_voltage";
  public static final String SIGNAL_TOTAL_CURRENT = "total_current";
  public static final String SIGNAL_SWITCHABLE_ENABLED = "switchable_enabled";
  public static final String SIGNAL_PRESSED = "pressed";
  public static final String SIGNAL_ELAPSED = "elapsed";
  public static final String SIGNAL_BROWNOUT = "brownout";
  public static final String SIGNAL_CAN_WARNING = "can_warning";
  public static final String SIGNAL_HARDWARE_FAULT = "hardware_fault";
  public static final String SIGNAL_STICKY_BROWNOUT = "sticky_brownout";
  public static final String SIGNAL_STICKY_CAN_WARNING = "sticky_can_warning";
  public static final String SIGNAL_STICKY_CAN_BUS_OFF = "sticky_can_bus_off";
  public static final String SIGNAL_STICKY_HAS_RESET = "sticky_has_reset";
  public static final String SIGNAL_INPUT_VOLTAGE = "input_voltage";
  public static final String SIGNAL_CAN_UTILIZATION = "can_utilization";
  public static final String SIGNAL_CAN_TX_ERROR_COUNT = "can_tx_error_count";
  public static final String SIGNAL_CAN_RX_ERROR_COUNT = "can_rx_error_count";
  public static final String SIGNAL_CAN_BUS_OFF_COUNT = "can_bus_off_count";
  public static final String SIGNAL_CAN_TX_FULL_COUNT = "can_tx_full_count";
  public static final String SIGNAL_BROWNOUT_VOLTAGE = "brownout_voltage";
  public static final String SIGNAL_RAIL_3V3_VOLTAGE = "rail_3v3_voltage";
  public static final String SIGNAL_RAIL_5V_VOLTAGE = "rail_5v_voltage";
  public static final String SIGNAL_RAIL_6V_VOLTAGE = "rail_6v_voltage";
  public static final String SIGNAL_RAIL_3V3_ENABLED = "rail_3v3_enabled";
  public static final String SIGNAL_RAIL_5V_ENABLED = "rail_5v_enabled";
  public static final String SIGNAL_RAIL_6V_ENABLED = "rail_6v_enabled";
  public static final String SIGNAL_RAIL_3V3_FAULT_COUNT = "rail_3v3_fault_count";
  public static final String SIGNAL_RAIL_5V_FAULT_COUNT = "rail_5v_fault_count";
  public static final String SIGNAL_RAIL_6V_FAULT_COUNT = "rail_6v_fault_count";
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
      new ImuSignalProvider(),
      new PowerDistributionSignalProvider(DEVICE_TYPE_PDP, PDP_CHANNEL_COUNT),
      new PowerDistributionSignalProvider(DEVICE_TYPE_PDH, PDH_CHANNEL_COUNT),
      new RobotControllerSignalProvider(),
      new XboxControllerSignalProvider(),
      new TestTimerSignalProvider());

  private static final Map<String, Map<String, DslSignalMeta>> REGISTRY = buildRegistry();
  private static final Map<String, String> DEVICE_TYPE_ALIASES = buildDeviceTypeAliases();

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
    JsonObject aliases = new JsonObject();
    for (Map.Entry<String, String> entry : DEVICE_TYPE_ALIASES.entrySet()) {
      aliases.addProperty(entry.getKey(), entry.getValue());
    }
    root.add("deviceTypeAliases", aliases);
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

  public static String canonicalDeviceType(String deviceType) {
    if (deviceType == null || deviceType.isBlank()) {
      return deviceType;
    }
    String trimmed = deviceType.trim();
    for (Map.Entry<String, String> entry : DEVICE_TYPE_ALIASES.entrySet()) {
      if (entry.getKey().equalsIgnoreCase(trimmed)) {
        return entry.getValue();
      }
    }
    return trimmed;
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

  private static Map<String, String> buildDeviceTypeAliases() {
    Map<String, String> aliases = new LinkedHashMap<>();
    aliases.put(DEVICE_TYPE_CANCODER, DEVICE_TYPE_ENCODER_EXTERNAL);
    aliases.put(DEVICE_TYPE_PIGEON, DEVICE_TYPE_IMU);
    aliases.put("roboRIO", DEVICE_TYPE_ROBOT_CONTROLLER);
    aliases.put(DEVICE_TYPE_SYSTEM_CORE, DEVICE_TYPE_ROBOT_CONTROLLER);
    return aliases;
  }
}
