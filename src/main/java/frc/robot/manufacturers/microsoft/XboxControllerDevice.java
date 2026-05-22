package frc.robot.manufacturers.microsoft;

import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import frc.robot.tests.dsl.DslSignalRegistry;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *   XboxControllerDevice - Configured Xbox controller device wrapper.
 *
 * DESCRIPTION
 *   Exposes Driver Station Xbox controller samples through the same device
 *   lifecycle and DSL signal path used by other configured bringup devices.
 */
public final class XboxControllerDevice implements DeviceUnit {
  public static final String DEVICE_TYPE = "xboxController";
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
  public static final String SIGNAL_LEFT_Y = "leftY";
  public static final String SIGNAL_RIGHT_Y = "rightY";
  private static final String SIGNAL_LEFT_X = "leftX";
  private static final String SIGNAL_RIGHT_X = "rightX";
  private static final String SIGNAL_LEFT_TRIGGER = "leftTrigger";
  private static final String SIGNAL_RIGHT_TRIGGER = "rightTrigger";
  private static final String DEVICE_DISPLAY_NAME = "Xbox Controller";
  private static final String HEADER_SOURCE = "WPILib";
  private static final String HEADER_OWNER = "Team";
  private static final String HEADER_VERSION = "2026-05-06";
  private static final String HEADER_DESCRIPTION = "Microsoft Xbox controller input wrapper.";
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      DEVICE_DISPLAY_NAME,
      MicrosoftDeviceGroup.VENDOR,
      DEVICE_TYPE,
      HEADER_SOURCE,
      HEADER_OWNER,
      HEADER_VERSION,
      HEADER_DESCRIPTION);

  private static final String NOTE_VIRTUAL = "driverStationInput";
  private static final double BUTTON_ACTIVE_THRESHOLD = 0.5;
  private static final double ACTIVE_VALUE = 1.0;
  private static final double INACTIVE_VALUE = 0.0;
  private static final int POV_UP_DEGREES = 0;
  private static final int POV_RIGHT_DEGREES = 90;
  private static final int POV_DOWN_DEGREES = 180;
  private static final int POV_LEFT_DEGREES = 270;
  private static final Map<String, Map<String, Double>> INPUTS = new HashMap<>();

  private final int id;
  private final String label;
  private boolean created;

  /**
   * NAME
   *   XboxControllerDevice - Construct a configured Xbox controller wrapper.
   *
   * PARAMETERS
   *   id - Optional configured controller id or port.
   *   label - Device label from bringup_system.json.
   */
  public XboxControllerDevice(int id, String label) {
    this.id = id;
    this.label = label;
  }

  /**
   * NAME
   *   setControllerInputs - Replace the latest controller input snapshot.
   *
   * PARAMETERS
   *   inputs - Controller signal values keyed by controller label.
   */
  public static void setControllerInputs(Map<String, Map<String, Double>> inputs) {
    synchronized (INPUTS) {
      INPUTS.clear();
      if (inputs == null) {
        return;
      }
      for (Map.Entry<String, Map<String, Double>> entry : inputs.entrySet()) {
        String controller = entry.getKey();
        Map<String, Double> values = entry.getValue();
        if (controller == null || controller.isBlank() || values == null) {
          continue;
        }
        INPUTS.put(controller.trim(), new LinkedHashMap<>(values));
      }
    }
  }

  /**
   * NAME
   *   buildControllerInputs - Build a DSL-ready controller input snapshot.
   *
   * PARAMETERS
   *   controllers - WPILib Xbox controller map keyed by configured label.
   *
   * RETURNS
   *   Snapshot keyed by controller label and DSL signal name.
   */
  public static Map<String, Map<String, Double>> buildControllerInputs(
      Map<String, edu.wpi.first.wpilibj.XboxController> controllers) {
    Map<String, Map<String, Double>> axisInputs = new HashMap<>();
    if (controllers == null) {
      return axisInputs;
    }
    for (Map.Entry<String, edu.wpi.first.wpilibj.XboxController> entry : controllers.entrySet()) {
      String name = entry.getKey();
      edu.wpi.first.wpilibj.XboxController controller = entry.getValue();
      if (name == null || controller == null) {
        continue;
      }
      Map<String, Double> values = new HashMap<>();
      values.put(SIGNAL_A, controller.getAButton() ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_B, controller.getBButton() ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_X, controller.getXButton() ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_Y, controller.getYButton() ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_LB, controller.getLeftBumperButton() ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_RB, controller.getRightBumperButton() ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_BACK, controller.getBackButton() ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_START, controller.getStartButton() ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_LS, controller.getLeftStickButton() ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_RS, controller.getRightStickButton() ? ACTIVE_VALUE : INACTIVE_VALUE);
      int pov = controller.getPOV();
      values.put(SIGNAL_D_UP, pov == POV_UP_DEGREES ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_D_RIGHT, pov == POV_RIGHT_DEGREES ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_D_DOWN, pov == POV_DOWN_DEGREES ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_D_LEFT, pov == POV_LEFT_DEGREES ? ACTIVE_VALUE : INACTIVE_VALUE);
      values.put(SIGNAL_LEFT_X, controller.getLeftX());
      values.put(SIGNAL_LEFT_Y, controller.getLeftY());
      values.put(SIGNAL_RIGHT_X, controller.getRightX());
      values.put(SIGNAL_RIGHT_Y, controller.getRightY());
      values.put(SIGNAL_LEFT_TRIGGER, controller.getLeftTriggerAxis());
      values.put(SIGNAL_RIGHT_TRIGGER, controller.getRightTriggerAxis());
      axisInputs.put(name, values);
    }
    return axisInputs;
  }

  @Override
  public int getCanId() {
    return id;
  }

  @Override
  public String getDeviceType() {
    return DEVICE_TYPE;
  }

  @Override
  public String getLabel() {
    return label;
  }

  @Override
  public RegistrationHeader getHeader() {
    return HEADER;
  }

  @Override
  public boolean isCreated() {
    return created;
  }

  @Override
  public void ensureCreated() {
    created = true;
  }

  @Override
  public void close() {
    created = false;
  }

  @Override
  public void clearFaults() {}

  @Override
  public DeviceSnapshot snapshot() {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = MicrosoftDeviceGroup.VENDOR;
    snap.deviceType = DEVICE_TYPE;
    snap.canId = id;
    snap.label = label;
    snap.present = created;
    snap.note = NOTE_VIRTUAL;
    return snap;
  }

  @Override
  public Object readDslSignal(String signalName) {
    Double value;
    synchronized (INPUTS) {
      Map<String, Double> values = INPUTS.get(label);
      value = values != null ? values.get(signalName) : null;
    }
    if (value == null) {
      return null;
    }
    if (isBooleanSignal(signalName)) {
      return value.doubleValue() >= BUTTON_ACTIVE_THRESHOLD;
    }
    return value;
  }

  private static boolean isBooleanSignal(String signalName) {
    return SIGNAL_A.equals(signalName)
        || SIGNAL_B.equals(signalName)
        || SIGNAL_X.equals(signalName)
        || SIGNAL_Y.equals(signalName)
        || SIGNAL_LB.equals(signalName)
        || SIGNAL_RB.equals(signalName)
        || SIGNAL_BACK.equals(signalName)
        || SIGNAL_START.equals(signalName)
        || SIGNAL_LS.equals(signalName)
        || SIGNAL_RS.equals(signalName)
        || SIGNAL_D_UP.equals(signalName)
        || SIGNAL_D_RIGHT.equals(signalName)
        || SIGNAL_D_DOWN.equals(signalName)
        || SIGNAL_D_LEFT.equals(signalName);
  }
}
