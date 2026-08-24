package frc.robot.diag.input;

import frc.robot.devices.DeviceUnit;
import frc.robot.devices.ni.DioLimitSwitchDevice;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.EncoderAttachment;
import frc.robot.diag.snapshots.ImuAttachment;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.diag.snapshots.RobotControllerBusAttachment;
import frc.robot.diag.snapshots.RobotControllerPowerAttachment;
import frc.robot.diag.snapshots.RobotControllerRailsAttachment;
import frc.robot.manufacturers.DeviceTypeBucket;
import frc.robot.manufacturers.ManufacturerGroup;
import frc.robot.manufacturers.microsoft.XboxControllerDevice;
import frc.robot.tests.dsl.DslSignalRegistry;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * NAME
 *   InputSensorStateModelBuilder - Build the shared input/sensor state view-model.
 *
 * DESCRIPTION
 *   Groups supported current-profile device families into ordered sections with
 *   display-ready field entries suitable for both text reports and UI panels.
 */
public final class InputSensorStateModelBuilder {
  public static final String SECTION_OPERATOR_CONTROLS_KEY = "operatorControls";
  public static final String SECTION_OPERATOR_CONTROLS_TITLE = "Operator Controls";
  public static final String SECTION_CONTACT_INPUTS_KEY = "contactInputs";
  public static final String SECTION_CONTACT_INPUTS_TITLE = "Contact Inputs";
  public static final String SECTION_POSITION_SENSORS_KEY = "positionSensors";
  public static final String SECTION_POSITION_SENSORS_TITLE = "Position Sensors";
  public static final String SECTION_IMU_SENSORS_KEY = "imuSensors";
  public static final String SECTION_IMU_SENSORS_TITLE = "IMU Sensors";
  public static final String SECTION_CONTROLLER_STATE_KEY = "controllerState";
  public static final String SECTION_CONTROLLER_STATE_TITLE = "Controller State";

  private static final String FIELD_USB = "usb";
  private static final String FIELD_DIO = "dio";
  private static final String FIELD_CAN = "can";
  private static final String FIELD_MODEL = "model";
  private static final String FIELD_PRESENT = "present";
  private static final String FIELD_LEFT_Y = "leftY";
  private static final String FIELD_RIGHT_Y = "rightY";
  private static final String FIELD_LEFT_X = "leftX";
  private static final String FIELD_RIGHT_X = "rightX";
  private static final String FIELD_LEFT_TRIGGER = "LT";
  private static final String FIELD_RIGHT_TRIGGER = "RT";
  private static final String FIELD_A = "A";
  private static final String FIELD_B = "B";
  private static final String FIELD_X = "X";
  private static final String FIELD_Y = "Y";
  private static final String FIELD_LB = "LB";
  private static final String FIELD_RB = "RB";
  private static final String FIELD_BACK = "BACK";
  private static final String FIELD_START = "START";
  private static final String FIELD_LS = "LS";
  private static final String FIELD_RS = "RS";
  private static final String FIELD_D_UP = "D_UP";
  private static final String FIELD_D_RIGHT = "D_RIGHT";
  private static final String FIELD_D_DOWN = "D_DOWN";
  private static final String FIELD_D_LEFT = "D_LEFT";
  private static final String FIELD_PRESSED = "pressed";
  private static final String FIELD_INVERT = "invert";
  private static final String FIELD_LAST_CHANGE = "lastChange";
  private static final String FIELD_TRANSITIONS = "transitions";
  private static final String FIELD_CHANGED_SINCE_ACTIVATE = "changedSinceActivate";
  private static final String FIELD_PROOF = "proof";
  private static final String FIELD_ABS_DEG = "absDeg";
  private static final String FIELD_ABS_ROT = "absRot";
  private static final String FIELD_VEL_RPS = "velRps";
  private static final String FIELD_LAST_ERR = "lastErr";
  private static final String FIELD_YAW = "yaw";
  private static final String FIELD_PITCH = "pitch";
  private static final String FIELD_ROLL = "roll";
  private static final String FIELD_VEL_X = "velX";
  private static final String FIELD_VEL_Y = "velY";
  private static final String FIELD_VEL_Z = "velZ";
  private static final String FIELD_ACCEL_X = "accelX";
  private static final String FIELD_ACCEL_Y = "accelY";
  private static final String FIELD_ACCEL_Z = "accelZ";
  private static final String FIELD_INPUT_V = "inputV";
  private static final String FIELD_BROWNOUT = "brownout";
  private static final String FIELD_BROWNOUT_V = "brownoutV";
  private static final String FIELD_CAN_UTIL = "canUtil";
  private static final String FIELD_CAN_RX_ERR = "canRxErr";
  private static final String FIELD_CAN_TX_ERR = "canTxErr";
  private static final String FIELD_CAN_BUS_OFF = "canBusOff";
  private static final String FIELD_CAN_TX_FULL = "canTxFull";
  private static final String FIELD_RAIL_3V3_V = "rail3v3V";
  private static final String FIELD_RAIL_3V3_ENABLED = "rail3v3Enabled";
  private static final String FIELD_RAIL_3V3_FAULTS = "rail3v3Faults";
  private static final String FIELD_RAIL_5V_V = "rail5vV";
  private static final String FIELD_RAIL_5V_ENABLED = "rail5vEnabled";
  private static final String FIELD_RAIL_5V_FAULTS = "rail5vFaults";
  private static final String FIELD_RAIL_6V_V = "rail6vV";
  private static final String FIELD_RAIL_6V_ENABLED = "rail6vEnabled";
  private static final String FIELD_RAIL_6V_FAULTS = "rail6vFaults";
  private static final String FIELD_CONFIDENCE = "confidence";

  private static final String FAMILY_XBOX = DslSignalRegistry.DEVICE_TYPE_XBOX_CONTROLLER;
  private static final String FAMILY_LIMIT_SWITCH = DslSignalRegistry.DEVICE_TYPE_LIMIT_SWITCH;
  private static final String FAMILY_CANCODER = DslSignalRegistry.DEVICE_TYPE_CANCODER;
  private static final String FAMILY_ENCODER_EXTERNAL = DslSignalRegistry.DEVICE_TYPE_ENCODER_EXTERNAL;
  private static final String FAMILY_PIGEON = DslSignalRegistry.DEVICE_TYPE_PIGEON;
  private static final String FAMILY_IMU = DslSignalRegistry.DEVICE_TYPE_IMU;
  private static final String FAMILY_ROBOT_CONTROLLER = DslSignalRegistry.DEVICE_TYPE_ROBOT_CONTROLLER;

  private static final String BOOLEAN_YES = "YES";
  private static final String BOOLEAN_NO = "NO";
  private static final String TEXT_EMPTY = "";
  private static final String TEXT_OK = "OK";
  private static final String FORMAT_NUMBER_1 = "%.1f";
  private static final String FORMAT_NUMBER_2 = "%.2f";
  private static final String FORMAT_NUMBER_4 = "%.4f";
  private static final String UNIT_PERCENT = "%";
  private static final String UNKNOWN_NOTE_LIMIT_SWITCH = "not yet proven";
  private static final String UNKNOWN_NOTE_LIMIT_SWITCH_PARTIAL = "single edge observed";
  private static final String TEXT_TIME_UNKNOWN = "--";
  private static final String TIME_SUFFIX_SECONDS = "s";
  private static final double TIME_PRESENT_MIN_SEC = 0.0;
  private static final int FIRST_LIMIT_INDEX = 0;
  private static final String SIGNAL_LEFT_X = DslSignalRegistry.SIGNAL_LEFT_X;
  private static final String SIGNAL_RIGHT_X = DslSignalRegistry.SIGNAL_RIGHT_X;
  private static final String SIGNAL_LEFT_TRIGGER = DslSignalRegistry.SIGNAL_LEFT_TRIGGER;
  private static final String SIGNAL_RIGHT_TRIGGER = DslSignalRegistry.SIGNAL_RIGHT_TRIGGER;

  /**
   * NAME
   *   build - Build the shared view-model for supported input/sensor families.
   *
   * PARAMETERS
   *   groups - manufacturer groups populated from the current profile.
   *   selectedLabel - optional selected device label for row highlighting.
   *
   * RETURNS
   *   Shared sectioned input/sensor state model.
   */
  public InputSensorStateModel build(
      List<ManufacturerGroup> groups,
      String selectedLabel) {
    List<InputSensorStateModel.Row> controllerRows = new ArrayList<>();
    List<InputSensorStateModel.Row> limitRows = new ArrayList<>();
    List<InputSensorStateModel.Row> encoderRows = new ArrayList<>();
    List<InputSensorStateModel.Row> imuRows = new ArrayList<>();
    List<InputSensorStateModel.Row> robotControllerRows = new ArrayList<>();
    String normalizedSelected = normalizeLabel(selectedLabel);

    if (groups != null) {
      for (ManufacturerGroup group : groups) {
        if (group == null) {
          continue;
        }
        for (DeviceTypeBucket bucket : group.getDeviceBuckets()) {
          if (bucket == null) {
            continue;
          }
          for (DeviceUnit device : bucket.getDevices()) {
            if (device == null) {
              continue;
            }
            addDeviceRow(
                controllerRows,
                limitRows,
                encoderRows,
                imuRows,
                robotControllerRows,
                device,
                normalizedSelected);
          }
        }
      }
    }

    List<InputSensorStateModel.Section> sections = new ArrayList<>();
    addSection(sections, SECTION_OPERATOR_CONTROLS_KEY, SECTION_OPERATOR_CONTROLS_TITLE, controllerRows);
    addSection(sections, SECTION_CONTACT_INPUTS_KEY, SECTION_CONTACT_INPUTS_TITLE, limitRows);
    addSection(sections, SECTION_POSITION_SENSORS_KEY, SECTION_POSITION_SENSORS_TITLE, encoderRows);
    addSection(sections, SECTION_IMU_SENSORS_KEY, SECTION_IMU_SENSORS_TITLE, imuRows);
    addSection(sections, SECTION_CONTROLLER_STATE_KEY, SECTION_CONTROLLER_STATE_TITLE, robotControllerRows);
    return new InputSensorStateModel(sections);
  }

  private void addSection(
      List<InputSensorStateModel.Section> sections,
      String key,
      String title,
      List<InputSensorStateModel.Row> rows) {
    if (rows == null || rows.isEmpty()) {
      return;
    }
    sections.add(new InputSensorStateModel.Section(key, title, rows));
  }

  private void addDeviceRow(
      List<InputSensorStateModel.Row> controllerRows,
      List<InputSensorStateModel.Row> limitRows,
      List<InputSensorStateModel.Row> encoderRows,
      List<InputSensorStateModel.Row> imuRows,
      List<InputSensorStateModel.Row> robotControllerRows,
      DeviceUnit device,
      String normalizedSelected) {
    String family = normalizeFamily(device.getDeviceType());
    if (FAMILY_XBOX.equals(family)) {
      controllerRows.add(buildXboxRow(device, normalizedSelected));
      return;
    }
    if (FAMILY_LIMIT_SWITCH.equals(family)) {
      limitRows.add(buildLimitSwitchRow(device, normalizedSelected));
      return;
    }
    if (FAMILY_ENCODER_EXTERNAL.equals(family)) {
      encoderRows.add(buildEncoderRow(device, normalizedSelected));
      return;
    }
    if (FAMILY_IMU.equals(family)) {
      imuRows.add(buildImuRow(device, normalizedSelected));
      return;
    }
    if (FAMILY_ROBOT_CONTROLLER.equals(family)) {
      robotControllerRows.add(buildRobotControllerRow(device, normalizedSelected));
    }
  }

  private InputSensorStateModel.Row buildXboxRow(DeviceUnit device, String normalizedSelected) {
    DeviceSnapshot snapshot = device.snapshot();
    List<InputSensorStateModel.Field> fields = new ArrayList<>();
    fields.add(field(FIELD_USB, device.getCanId()));
    fields.add(field(FIELD_PRESENT, formatBoolean(snapshot.present)));
    fields.add(field(FIELD_LEFT_Y, formatDouble(readNumber(device, XboxControllerDevice.SIGNAL_LEFT_Y), FORMAT_NUMBER_2)));
    fields.add(field(FIELD_RIGHT_Y, formatDouble(readNumber(device, XboxControllerDevice.SIGNAL_RIGHT_Y), FORMAT_NUMBER_2)));
    fields.add(field(FIELD_LEFT_X, formatDouble(readNumber(device, SIGNAL_LEFT_X), FORMAT_NUMBER_2)));
    fields.add(field(FIELD_RIGHT_X, formatDouble(readNumber(device, SIGNAL_RIGHT_X), FORMAT_NUMBER_2)));
    fields.add(field(FIELD_LEFT_TRIGGER, formatDouble(readNumber(device, SIGNAL_LEFT_TRIGGER), FORMAT_NUMBER_2)));
    fields.add(field(FIELD_RIGHT_TRIGGER, formatDouble(readNumber(device, SIGNAL_RIGHT_TRIGGER), FORMAT_NUMBER_2)));
    fields.add(field(FIELD_A, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_A))));
    fields.add(field(FIELD_B, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_B))));
    fields.add(field(FIELD_X, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_X))));
    fields.add(field(FIELD_Y, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_Y))));
    fields.add(field(FIELD_LB, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_LB))));
    fields.add(field(FIELD_RB, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_RB))));
    fields.add(field(FIELD_BACK, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_BACK))));
    fields.add(field(FIELD_START, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_START))));
    fields.add(field(FIELD_LS, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_LS))));
    fields.add(field(FIELD_RS, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_RS))));
    fields.add(field(FIELD_D_UP, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_D_UP))));
    fields.add(field(FIELD_D_RIGHT, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_D_RIGHT))));
    fields.add(field(FIELD_D_DOWN, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_D_DOWN))));
    fields.add(field(FIELD_D_LEFT, formatBoolean(readBoolean(device, XboxControllerDevice.SIGNAL_D_LEFT))));
    fields.add(field(FIELD_CONFIDENCE, snapshot.present
        ? InputSensorStateModel.CONFIDENCE_HIGH
        : InputSensorStateModel.CONFIDENCE_LOW));
    return row(device, familyForRow(FAMILY_XBOX), snapshot.present, confidenceForPresent(snapshot.present), TEXT_EMPTY,
        isSelected(device, normalizedSelected), fields);
  }

  private InputSensorStateModel.Row buildLimitSwitchRow(DeviceUnit device, String normalizedSelected) {
    DeviceSnapshot snapshot = device.snapshot();
    LimitsAttachment limits = snapshot.getAttachment(LimitsAttachment.class);
    LimitsAttachment.LimitSwitchState state =
        limits != null && limits.switches != null && limits.switches.size() > FIRST_LIMIT_INDEX
            ? limits.switches.get(FIRST_LIMIT_INDEX)
            : null;
    boolean pressed = state != null && Boolean.TRUE.equals(state.closed);
    boolean invert = state != null && state.invert;
    String proofState = state != null ? cleanText(state.proofState, LimitsAttachment.PROOF_STATE_UNKNOWN) : LimitsAttachment.PROOF_STATE_UNKNOWN;
    String notes = resolveLimitSwitchNote(snapshot.present, proofState);
    List<InputSensorStateModel.Field> fields = new ArrayList<>();
    fields.add(field(FIELD_DIO, device.getCanId()));
    fields.add(field(FIELD_PRESENT, formatBoolean(snapshot.present)));
    fields.add(field(FIELD_PRESSED, formatBoolean(pressed)));
    fields.add(field(FIELD_INVERT, formatBoolean(invert)));
    fields.add(field(FIELD_CHANGED_SINCE_ACTIVATE, formatBoolean(state != null && state.changedSinceActivate)));
    fields.add(field(FIELD_TRANSITIONS, state != null ? state.transitionCountSinceActivate : 0));
    fields.add(field(FIELD_LAST_CHANGE, formatLimitSwitchLastChange(state != null ? state.lastChangeSec : null)));
    fields.add(field(FIELD_PROOF, proofState));
    fields.add(field(FIELD_CONFIDENCE, snapshot.present
        ? resolveLimitSwitchConfidence(proofState)
        : InputSensorStateModel.CONFIDENCE_LOW));
    return row(device, familyForRow(FAMILY_LIMIT_SWITCH), snapshot.present,
        snapshot.present ? resolveLimitSwitchConfidence(proofState) : InputSensorStateModel.CONFIDENCE_LOW,
        notes,
        isSelected(device, normalizedSelected), fields);
  }

  private InputSensorStateModel.Row buildEncoderRow(DeviceUnit device, String normalizedSelected) {
    DeviceSnapshot snapshot = device.snapshot();
    EncoderAttachment encoder = snapshot.getAttachment(EncoderAttachment.class);
    List<InputSensorStateModel.Field> fields = new ArrayList<>();
    fields.add(field(FIELD_CAN, device.getCanId()));
    fields.add(field(FIELD_PRESENT, formatBoolean(snapshot.present)));
    fields.add(field(FIELD_ABS_DEG, formatDouble(encoder != null ? encoder.absDeg : null, FORMAT_NUMBER_1)));
    fields.add(field(FIELD_ABS_ROT, formatDouble(encoder != null ? encoder.absRot : null, FORMAT_NUMBER_4)));
    fields.add(field(FIELD_VEL_RPS, formatDouble(encoder != null ? encoder.velocityRps : null, FORMAT_NUMBER_2)));
    fields.add(field(FIELD_LAST_ERR, cleanText(encoder != null ? encoder.lastError : TEXT_EMPTY, TEXT_OK)));
    fields.add(field(FIELD_CONFIDENCE, confidenceForPresent(snapshot.present)));
    return row(device, familyForRow(FAMILY_ENCODER_EXTERNAL), snapshot.present, confidenceForPresent(snapshot.present),
        TEXT_EMPTY, isSelected(device, normalizedSelected), fields);
  }

  private InputSensorStateModel.Row buildImuRow(DeviceUnit device, String normalizedSelected) {
    DeviceSnapshot snapshot = device.snapshot();
    ImuAttachment imu = snapshot.getAttachment(ImuAttachment.class);
    List<InputSensorStateModel.Field> fields = new ArrayList<>();
    fields.add(field(FIELD_CAN, device.getCanId()));
    fields.add(field(FIELD_PRESENT, formatBoolean(snapshot.present)));
    fields.add(field(FIELD_YAW, formatDouble(imu != null ? imu.yawDeg : null, FORMAT_NUMBER_1)));
    fields.add(field(FIELD_PITCH, formatDouble(imu != null ? imu.pitchDeg : null, FORMAT_NUMBER_1)));
    fields.add(field(FIELD_ROLL, formatDouble(imu != null ? imu.rollDeg : null, FORMAT_NUMBER_1)));
    fields.add(field(FIELD_VEL_X, formatDouble(imu != null ? imu.angularVelocityXDps : null, FORMAT_NUMBER_1)));
    fields.add(field(FIELD_VEL_Y, formatDouble(imu != null ? imu.angularVelocityYDps : null, FORMAT_NUMBER_1)));
    fields.add(field(FIELD_VEL_Z, formatDouble(imu != null ? imu.angularVelocityZDps : null, FORMAT_NUMBER_1)));
    fields.add(field(FIELD_ACCEL_X, formatDouble(imu != null ? imu.accelXG : null, FORMAT_NUMBER_2)));
    fields.add(field(FIELD_ACCEL_Y, formatDouble(imu != null ? imu.accelYG : null, FORMAT_NUMBER_2)));
    fields.add(field(FIELD_ACCEL_Z, formatDouble(imu != null ? imu.accelZG : null, FORMAT_NUMBER_2)));
    fields.add(field(FIELD_LAST_ERR, cleanText(imu != null ? imu.lastError : TEXT_EMPTY, TEXT_OK)));
    fields.add(field(FIELD_CONFIDENCE, confidenceForPresent(snapshot.present)));
    return row(device, familyForRow(FAMILY_IMU), snapshot.present, confidenceForPresent(snapshot.present), TEXT_EMPTY,
        isSelected(device, normalizedSelected), fields);
  }

  private InputSensorStateModel.Row buildRobotControllerRow(DeviceUnit device, String normalizedSelected) {
    DeviceSnapshot snapshot = device.snapshot();
    RobotControllerPowerAttachment power = snapshot.getAttachment(RobotControllerPowerAttachment.class);
    RobotControllerBusAttachment bus = snapshot.getAttachment(RobotControllerBusAttachment.class);
    RobotControllerRailsAttachment rails = snapshot.getAttachment(RobotControllerRailsAttachment.class);
    List<InputSensorStateModel.Field> fields = new ArrayList<>();
    fields.add(field(FIELD_PRESENT, formatBoolean(snapshot.present)));
    fields.add(field(FIELD_MODEL, resolveModel(device)));
    fields.add(field(FIELD_INPUT_V, formatDouble(power != null ? power.inputVoltage : null, FORMAT_NUMBER_2)));
    fields.add(field(FIELD_BROWNOUT, formatBoolean(power != null && power.brownout)));
    fields.add(field(FIELD_BROWNOUT_V, formatDouble(power != null ? power.brownoutVoltage : null, FORMAT_NUMBER_2)));
    fields.add(field(FIELD_CAN_UTIL, formatPercent(bus != null ? bus.canUtilizationPct : null)));
    fields.add(field(FIELD_CAN_RX_ERR, bus != null ? bus.canRxErrorCount : 0));
    fields.add(field(FIELD_CAN_TX_ERR, bus != null ? bus.canTxErrorCount : 0));
    fields.add(field(FIELD_CAN_BUS_OFF, bus != null ? bus.canBusOffCount : 0));
    fields.add(field(FIELD_CAN_TX_FULL, bus != null ? bus.canTxFullCount : 0));
    fields.add(field(FIELD_RAIL_3V3_V, formatDouble(rails != null ? rails.rail3v3Voltage : null, FORMAT_NUMBER_2)));
    fields.add(field(FIELD_RAIL_3V3_ENABLED, formatBoolean(rails != null && rails.rail3v3Enabled)));
    fields.add(field(FIELD_RAIL_3V3_FAULTS, rails != null ? rails.rail3v3FaultCount : 0));
    fields.add(field(FIELD_RAIL_5V_V, formatDouble(rails != null ? rails.rail5vVoltage : null, FORMAT_NUMBER_2)));
    fields.add(field(FIELD_RAIL_5V_ENABLED, formatBoolean(rails != null && rails.rail5vEnabled)));
    fields.add(field(FIELD_RAIL_5V_FAULTS, rails != null ? rails.rail5vFaultCount : 0));
    fields.add(field(FIELD_RAIL_6V_V, formatDouble(rails != null ? rails.rail6vVoltage : null, FORMAT_NUMBER_2)));
    fields.add(field(FIELD_RAIL_6V_ENABLED, formatBoolean(rails != null && rails.rail6vEnabled)));
    fields.add(field(FIELD_RAIL_6V_FAULTS, rails != null ? rails.rail6vFaultCount : 0));
    fields.add(field(FIELD_CONFIDENCE, confidenceForPresent(snapshot.present)));
    return row(device, familyForRow(FAMILY_ROBOT_CONTROLLER), snapshot.present,
        confidenceForPresent(snapshot.present), TEXT_EMPTY, isSelected(device, normalizedSelected), fields);
  }

  private InputSensorStateModel.Row row(
      DeviceUnit device,
      String family,
      boolean present,
      String confidence,
      String notes,
      boolean selected,
      List<InputSensorStateModel.Field> fields) {
    return new InputSensorStateModel.Row(
        device.getLabel(),
        family,
        resolveModel(device),
        present,
        confidence,
        notes,
        selected,
        fields);
  }

  private InputSensorStateModel.Field field(String key, Object value) {
    return new InputSensorStateModel.Field(key, key + "=" + String.valueOf(value));
  }

  private boolean readBoolean(DeviceUnit device, String signalName) {
    Object value = device.readDslSignal(signalName);
    return value instanceof Boolean bool && bool;
  }

  private Double readNumber(DeviceUnit device, String signalName) {
    Object value = device.readDslSignal(signalName);
    return value instanceof Number number ? number.doubleValue() : null;
  }

  private String formatBoolean(boolean value) {
    return value ? BOOLEAN_YES : BOOLEAN_NO;
  }

  private String formatDouble(Double value, String pattern) {
    return value == null ? TEXT_EMPTY : String.format(pattern, value.doubleValue());
  }

  private String formatPercent(Double value) {
    return value == null ? TEXT_EMPTY : String.format(FORMAT_NUMBER_1, value.doubleValue()) + UNIT_PERCENT;
  }

  private String cleanText(String value, String fallback) {
    return value == null || value.isBlank() ? fallback : value;
  }

  private String confidenceForPresent(boolean present) {
    return present ? InputSensorStateModel.CONFIDENCE_HIGH : InputSensorStateModel.CONFIDENCE_LOW;
  }

  private String resolveLimitSwitchConfidence(String proofState) {
    if (LimitsAttachment.PROOF_STATE_PROVEN.equals(proofState)) {
      return InputSensorStateModel.CONFIDENCE_HIGH;
    }
    if (LimitsAttachment.PROOF_STATE_STUCK.equals(proofState)) {
      return InputSensorStateModel.CONFIDENCE_LOW;
    }
    if (LimitsAttachment.PROOF_STATE_UNKNOWN.equals(proofState)) {
      return InputSensorStateModel.CONFIDENCE_UNKNOWN;
    }
    return InputSensorStateModel.CONFIDENCE_MEDIUM;
  }

  private String resolveLimitSwitchNote(boolean present, String proofState) {
    if (!present) {
      return TEXT_EMPTY;
    }
    if (LimitsAttachment.PROOF_STATE_UNPROVEN.equals(proofState)) {
      return UNKNOWN_NOTE_LIMIT_SWITCH;
    }
    if (LimitsAttachment.PROOF_STATE_PARTIAL.equals(proofState)) {
      return UNKNOWN_NOTE_LIMIT_SWITCH_PARTIAL;
    }
    if (LimitsAttachment.PROOF_STATE_STUCK.equals(proofState)) {
      return LimitsAttachment.PROOF_STATE_STUCK.toLowerCase(Locale.ROOT);
    }
    return TEXT_EMPTY;
  }

  private String formatLimitSwitchLastChange(Double seconds) {
    if (seconds == null || seconds < TIME_PRESENT_MIN_SEC) {
      return TEXT_TIME_UNKNOWN;
    }
    return formatDouble(seconds, FORMAT_NUMBER_1) + TIME_SUFFIX_SECONDS;
  }

  private boolean isSelected(DeviceUnit device, String normalizedSelected) {
    return !normalizedSelected.isBlank()
        && normalizeLabel(device.getLabel()).equals(normalizedSelected);
  }

  private String normalizeLabel(String label) {
    return label == null ? TEXT_EMPTY : label.trim().toLowerCase(Locale.ROOT);
  }

  private String normalizeFamily(String family) {
    return DslSignalRegistry.canonicalDeviceType(family);
  }

  private String familyForRow(String family) {
    if (FAMILY_ENCODER_EXTERNAL.equals(family)) {
      return FAMILY_CANCODER;
    }
    if (FAMILY_IMU.equals(family)) {
      return FAMILY_PIGEON;
    }
    return family;
  }

  private String resolveModel(DeviceUnit device) {
    if (device == null || device.getHeader() == null || device.getHeader().name() == null) {
      return TEXT_EMPTY;
    }
    return device.getHeader().name();
  }
}
