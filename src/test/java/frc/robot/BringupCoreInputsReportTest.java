package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import frc.robot.diag.input.InputSensorStateModel;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.EncoderAttachment;
import frc.robot.diag.snapshots.ImuAttachment;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.diag.snapshots.RobotControllerBusAttachment;
import frc.robot.diag.snapshots.RobotControllerPowerAttachment;
import frc.robot.diag.snapshots.RobotControllerRailsAttachment;
import frc.robot.devices.DeviceUnit;
import frc.robot.devices.ni.DioLimitSwitchDevice;
import frc.robot.manufacturers.DeviceRegistration;
import frc.robot.manufacturers.DeviceRole;
import frc.robot.manufacturers.DeviceTypeBucket;
import frc.robot.manufacturers.ManufacturerGroup;
import frc.robot.manufacturers.microsoft.XboxControllerDevice;
import frc.robot.registry.RegistrationHeader;
import frc.robot.telemetry.SampledTelemetrySampler;
import frc.robot.tests.dsl.DslSignalRegistry;
import java.lang.reflect.Field;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   BringupCoreInputsReportTest - Regression tests for shared input/sensor state modeling.
 */
class BringupCoreInputsReportTest {
  private static final RegistrationHeader TEST_GROUP_HEADER =
      new RegistrationHeader("Test", "Test", "Manufacturer", "test", "test", "2026-08-23", "test");
  private static final RegistrationHeader TEST_DEVICE_HEADER =
      new RegistrationHeader("Test Device", "Test", "device", "test", "test", "2026-08-23", "test");
  private static final RegistrationHeader TEST_ROBORIO_HEADER =
      new RegistrationHeader("roboRIO", "NI", "robotController", "test", "test", "2026-08-23", "test");
  private static final String VENDOR_TEST = "Test";
  private static final String DISPLAY_XBOX = "Xbox Controller";
  private static final String DISPLAY_LIMIT_SWITCH = "Limit Switch";
  private static final String DISPLAY_CANCODER = "CANcoder";
  private static final String DISPLAY_PIGEON = "Pigeon";
  private static final String DISPLAY_ROBOT_CONTROLLER = "robotController";
  private static final String LABEL_CONTROLLER0 = "controller0";
  private static final String LABEL_LIMIT_SWITCH = "lmtSw0";
  private static final String LABEL_CANCODER = "cancoder";
  private static final String LABEL_PIGEON = "pigeon 2";
  private static final String LABEL_ROBORIO = "roborio";

  private static final String SIGNAL_LEFT_Y = DslSignalRegistry.SIGNAL_LEFT_Y;
  private static final String SIGNAL_RIGHT_Y = DslSignalRegistry.SIGNAL_RIGHT_Y;
  private static final String SIGNAL_LEFT_X = DslSignalRegistry.SIGNAL_LEFT_X;
  private static final String SIGNAL_RIGHT_X = DslSignalRegistry.SIGNAL_RIGHT_X;
  private static final String SIGNAL_LEFT_TRIGGER = DslSignalRegistry.SIGNAL_LEFT_TRIGGER;
  private static final String SIGNAL_RIGHT_TRIGGER = DslSignalRegistry.SIGNAL_RIGHT_TRIGGER;
  private static final String SIGNAL_A = XboxControllerDevice.SIGNAL_A;
  private static final String SIGNAL_B = XboxControllerDevice.SIGNAL_B;
  private static final String SIGNAL_X = XboxControllerDevice.SIGNAL_X;
  private static final String SIGNAL_Y = XboxControllerDevice.SIGNAL_Y;
  private static final String SIGNAL_LB = XboxControllerDevice.SIGNAL_LB;
  private static final String SIGNAL_RB = XboxControllerDevice.SIGNAL_RB;
  private static final String SIGNAL_BACK = XboxControllerDevice.SIGNAL_BACK;
  private static final String SIGNAL_START = XboxControllerDevice.SIGNAL_START;
  private static final String SIGNAL_LS = XboxControllerDevice.SIGNAL_LS;
  private static final String SIGNAL_RS = XboxControllerDevice.SIGNAL_RS;
  private static final String SIGNAL_D_UP = XboxControllerDevice.SIGNAL_D_UP;
  private static final String SIGNAL_D_RIGHT = XboxControllerDevice.SIGNAL_D_RIGHT;
  private static final String SIGNAL_D_DOWN = XboxControllerDevice.SIGNAL_D_DOWN;
  private static final String SIGNAL_D_LEFT = XboxControllerDevice.SIGNAL_D_LEFT;
  private static final String SIGNAL_PRESSED = DioLimitSwitchDevice.SIGNAL_PRESSED;

  private static final int USB_PORT_0 = 0;
  private static final int DIO_CHANNEL_0 = 0;
  private static final int CANCODER_CAN_ID = 18;
  private static final int PIGEON_CAN_ID = 19;
  private static final int ROBORIO_CAN_ID = 0;
  private static final double LEFT_Y_VALUE = 0.25;
  private static final double RIGHT_Y_VALUE = -0.75;
  private static final double LEFT_X_VALUE = 0.10;
  private static final double RIGHT_X_VALUE = -0.20;
  private static final double LEFT_TRIGGER_VALUE = 0.15;
  private static final double RIGHT_TRIGGER_VALUE = 0.85;
  private static final double CANCODER_ABS_DEG = 45.2;
  private static final double CANCODER_ABS_ROT = 0.1256;
  private static final double CANCODER_VEL_RPS = 0.0;
  private static final double PIGEON_YAW = 37.1;
  private static final double PIGEON_PITCH = 0.3;
  private static final double PIGEON_ROLL = -0.1;
  private static final double PIGEON_VEL_X = 0.0;
  private static final double PIGEON_VEL_Y = 0.0;
  private static final double PIGEON_VEL_Z = 0.0;
  private static final double PIGEON_ACCEL_X = 0.00;
  private static final double PIGEON_ACCEL_Y = 0.01;
  private static final double PIGEON_ACCEL_Z = 1.00;
  private static final double ROBORIO_INPUT_V = 12.04;
  private static final double ROBORIO_BROWNOUT_V = 6.30;
  private static final double ROBORIO_CAN_UTIL = 18.2;
  private static final double RAIL_3V3_V = 3.30;
  private static final double RAIL_5V_V = 5.02;
  private static final double RAIL_6V_V = 6.01;
  private static final double LIMIT_LAST_CHANGE_SEC = 1.2;
  private static final int LIMIT_TRANSITIONS = 3;

  @Test
  void buildInputSensorStateModelIncludesAllFirstSliceFamiliesAndSelection() throws Exception {
    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    setManufacturerGroups(core, buildTestGroups());

    InputSensorStateModel model = core.buildInputSensorStateModel(LABEL_PIGEON);

    assertEquals(5, model.sections.size());
    assertEquals("Operator Controls", model.sections.get(0).title);
    assertEquals("Contact Inputs", model.sections.get(1).title);
    assertEquals("Position Sensors", model.sections.get(2).title);
    assertEquals("IMU Sensors", model.sections.get(3).title);
    assertEquals("Controller State", model.sections.get(4).title);
    assertEquals(LABEL_CONTROLLER0, model.sections.get(0).rows.get(0).label);
    assertEquals(LABEL_LIMIT_SWITCH, model.sections.get(1).rows.get(0).label);
    assertEquals(LABEL_CANCODER, model.sections.get(2).rows.get(0).label);
    assertEquals(LABEL_PIGEON, model.sections.get(3).rows.get(0).label);
    assertEquals(LABEL_ROBORIO, model.sections.get(4).rows.get(0).label);
    assertFalse(model.sections.get(0).rows.get(0).selected);
    assertTrue(model.sections.get(3).rows.get(0).selected);
    assertEquals(InputSensorStateModel.CONFIDENCE_HIGH, model.sections.get(1).rows.get(0).stateConfidence);
    assertEquals("", model.sections.get(1).rows.get(0).notes);
  }

  @Test
  void buildInputsReportTextRendersSharedModelForAllFirstSliceFamilies() throws Exception {
    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    setManufacturerGroups(core, buildTestGroups());

    String report = core.buildInputsReportText();

    assertTrue(report.contains("Operator Controls:"));
    assertTrue(report.contains(
        "controller0 usb=0 present=YES leftY=0.25 rightY=-0.75 leftX=0.10 rightX=-0.20 LT=0.15 RT=0.85 A=YES B=NO"));
    assertTrue(report.contains("Contact Inputs:"));
    assertTrue(report.contains(
        "lmtSw0 dio=0 present=YES pressed=YES invert=NO changedSinceActivate=YES transitions=3 lastChange=1.2s proof=PROVEN confidence=HIGH"));
    assertTrue(report.contains("Position Sensors:"));
    assertTrue(report.contains("cancoder can=18 present=YES absDeg=45.2 absRot=0.1256 velRps=0.00 lastErr=OK"));
    assertTrue(report.contains("IMU Sensors:"));
    assertTrue(report.contains("pigeon 2 can=19 present=YES yaw=37.1 pitch=0.3 roll=-0.1"));
    assertTrue(report.contains("Controller State:"));
    assertTrue(report.contains("roborio present=YES model=roboRIO inputV=12.04 brownout=NO"));
  }

  @Test
  void buildInputSensorStateJsonCarriesSharedSectionsAndSelectedRow() throws Exception {
    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    setManufacturerGroups(core, buildTestGroups());

    JsonObject json = core.buildInputSensorStateJson(LABEL_ROBORIO);
    JsonArray sections = json.getAsJsonArray("sections");

    assertEquals(5, sections.size());
    JsonObject controllerStateSection = sections.get(4).getAsJsonObject();
    assertEquals("controllerState", controllerStateSection.get("key").getAsString());
    JsonObject roborioRow = controllerStateSection.getAsJsonArray("rows").get(0).getAsJsonObject();
    assertEquals(LABEL_ROBORIO, roborioRow.get("label").getAsString());
    assertTrue(roborioRow.get("selected").getAsBoolean());
    assertEquals("robotController", roborioRow.get("family").getAsString());
  }

  private static List<ManufacturerGroup> buildTestGroups() {
    return List.of(
        new TestManufacturerGroup(
            List.of(
                buildBucket(
                    DISPLAY_XBOX,
                    XboxControllerDevice.DEVICE_TYPE,
                    List.of(
                        new FakeXboxControllerDevice(
                            USB_PORT_0,
                            LABEL_CONTROLLER0))))),
        new TestManufacturerGroup(
            List.of(
                buildBucket(
                    DISPLAY_LIMIT_SWITCH,
                    DioLimitSwitchDevice.DEVICE_TYPE,
                    List.of(
                        new FakeLimitSwitchDevice(
                            DIO_CHANNEL_0,
                            LABEL_LIMIT_SWITCH,
                            true,
                            false,
                            LIMIT_LAST_CHANGE_SEC,
                            LIMIT_TRANSITIONS,
                            LimitsAttachment.PROOF_STATE_PROVEN))))),
        new TestManufacturerGroup(
            List.of(
                buildBucket(
                    DISPLAY_CANCODER,
                    DslSignalRegistry.DEVICE_TYPE_CANCODER,
                    List.of(new FakeEncoderDevice(CANCODER_CAN_ID, LABEL_CANCODER))))),
        new TestManufacturerGroup(
            List.of(
                buildBucket(
                    DISPLAY_PIGEON,
                    DslSignalRegistry.DEVICE_TYPE_PIGEON,
                    List.of(new FakeImuDevice(PIGEON_CAN_ID, LABEL_PIGEON))))),
        new TestManufacturerGroup(
            List.of(
                buildBucket(
                    DISPLAY_ROBOT_CONTROLLER,
                    DslSignalRegistry.DEVICE_TYPE_ROBOT_CONTROLLER,
                    List.of(new FakeRobotControllerDevice(ROBORIO_CAN_ID, LABEL_ROBORIO))))));
  }

  private static DeviceTypeBucket buildBucket(
      String displayName,
      String deviceType,
      List<DeviceUnit> devices) {
    return new DeviceTypeBucket(
        new DeviceRegistration(
            TEST_DEVICE_HEADER,
            VENDOR_TEST,
            deviceType,
            displayName,
            DeviceRole.MISC,
            false,
            config -> null),
        devices,
        false);
  }

  private static void setManufacturerGroups(BringupCore core, List<ManufacturerGroup> groups)
      throws Exception {
    Field manufacturerGroupsField = BringupCore.class.getDeclaredField("manufacturerGroups");
    manufacturerGroupsField.setAccessible(true);
    manufacturerGroupsField.set(core, groups);

    Field manufacturerByVendorField = BringupCore.class.getDeclaredField("manufacturerByVendor");
    manufacturerByVendorField.setAccessible(true);
    manufacturerByVendorField.set(core, Map.of());
  }

  private static final class TestManufacturerGroup implements ManufacturerGroup {
    private final List<DeviceTypeBucket> buckets;

    private TestManufacturerGroup(List<DeviceTypeBucket> buckets) {
      this.buckets = buckets;
    }

    @Override
    public RegistrationHeader getHeader() {
      return TEST_GROUP_HEADER;
    }

    @Override
    public List<DeviceTypeBucket> getDeviceBuckets() {
      return buckets;
    }

    @Override
    public frc.robot.manufacturers.DeviceAddResult addNextMotor() {
      return null;
    }

    @Override
    public void resetLowCurrentTimers() {}

    @Override
    public List<DeviceUnit> getTestDevices() {
      return List.of();
    }

    @Override
    public void addAll() {}

    @Override
    public void setDuty(double duty) {}

    @Override
    public void stopAll() {}

    @Override
    public void clearFaults() {}

    @Override
    public void closeAll() {}

    @Override
    public List<DeviceSnapshot> captureSnapshots(double nowSec) {
      return List.of();
    }
  }

  private static final class FakeXboxControllerDevice implements DeviceUnit {
    private final int port;
    private final String label;

    private FakeXboxControllerDevice(int port, String label) {
      this.port = port;
      this.label = label;
    }

    @Override
    public int getCanId() {
      return port;
    }

    @Override
    public String getDeviceType() {
      return XboxControllerDevice.DEVICE_TYPE;
    }

    @Override
    public String getLabel() {
      return label;
    }

    @Override
    public RegistrationHeader getHeader() {
      return TEST_DEVICE_HEADER;
    }

    @Override
    public boolean isCreated() {
      return true;
    }

    @Override
    public void ensureCreated() {}

    @Override
    public void close() {}

    @Override
    public void clearFaults() {}

    @Override
    public DeviceSnapshot snapshot() {
      DeviceSnapshot snapshot = new DeviceSnapshot();
      snapshot.deviceType = XboxControllerDevice.DEVICE_TYPE;
      snapshot.canId = port;
      snapshot.label = label;
      snapshot.present = true;
      return snapshot;
    }

    @Override
    public Object readDslSignal(String signalName) {
      return switch (signalName) {
        case SIGNAL_LEFT_Y -> LEFT_Y_VALUE;
        case SIGNAL_RIGHT_Y -> RIGHT_Y_VALUE;
        case SIGNAL_LEFT_X -> LEFT_X_VALUE;
        case SIGNAL_RIGHT_X -> RIGHT_X_VALUE;
        case SIGNAL_LEFT_TRIGGER -> LEFT_TRIGGER_VALUE;
        case SIGNAL_RIGHT_TRIGGER -> RIGHT_TRIGGER_VALUE;
        case SIGNAL_A -> true;
        case SIGNAL_B -> false;
        case SIGNAL_X -> false;
        case SIGNAL_Y -> false;
        case SIGNAL_LB -> false;
        case SIGNAL_RB -> false;
        case SIGNAL_BACK -> false;
        case SIGNAL_START -> false;
        case SIGNAL_LS -> false;
        case SIGNAL_RS -> false;
        case SIGNAL_D_UP -> false;
        case SIGNAL_D_RIGHT -> false;
        case SIGNAL_D_DOWN -> false;
        case SIGNAL_D_LEFT -> false;
        default -> null;
      };
    }
  }

  private static final class FakeLimitSwitchDevice implements DeviceUnit {
    private final int dioChannel;
    private final String label;
    private final boolean pressed;
    private final boolean invert;
    private final double lastChangeSec;
    private final int transitionCountSinceActivate;
    private final String proofState;

    private FakeLimitSwitchDevice(
        int dioChannel,
        String label,
        boolean pressed,
        boolean invert,
        double lastChangeSec,
        int transitionCountSinceActivate,
        String proofState) {
      this.dioChannel = dioChannel;
      this.label = label;
      this.pressed = pressed;
      this.invert = invert;
      this.lastChangeSec = lastChangeSec;
      this.transitionCountSinceActivate = transitionCountSinceActivate;
      this.proofState = proofState;
    }

    @Override
    public int getCanId() {
      return dioChannel;
    }

    @Override
    public String getDeviceType() {
      return DioLimitSwitchDevice.DEVICE_TYPE;
    }

    @Override
    public String getLabel() {
      return label;
    }

    @Override
    public RegistrationHeader getHeader() {
      return TEST_DEVICE_HEADER;
    }

    @Override
    public boolean isCreated() {
      return true;
    }

    @Override
    public void ensureCreated() {}

    @Override
    public void close() {}

    @Override
    public void clearFaults() {}

    @Override
    public DeviceSnapshot snapshot() {
      DeviceSnapshot snapshot = new DeviceSnapshot();
      snapshot.deviceType = DioLimitSwitchDevice.DEVICE_TYPE;
      snapshot.canId = dioChannel;
      snapshot.label = label;
      snapshot.present = true;
      LimitsAttachment limits = new LimitsAttachment();
      LimitsAttachment.LimitSwitchState state = new LimitsAttachment.LimitSwitchState();
      state.label = label;
      state.dio = dioChannel;
      state.invert = invert;
      state.closed = pressed;
      state.lastChangeSec = lastChangeSec;
      state.transitionCountSinceActivate = transitionCountSinceActivate;
      state.changedSinceActivate = transitionCountSinceActivate > 0;
      state.proofState = proofState;
      limits.switches.add(state);
      snapshot.addAttachment(limits);
      return snapshot;
    }

    @Override
    public Object readDslSignal(String signalName) {
      return SIGNAL_PRESSED.equals(signalName) ? pressed : null;
    }
  }

  private static final class FakeEncoderDevice implements DeviceUnit {
    private final int canId;
    private final String label;

    private FakeEncoderDevice(int canId, String label) {
      this.canId = canId;
      this.label = label;
    }

    @Override
    public int getCanId() {
      return canId;
    }

    @Override
    public String getDeviceType() {
      return DslSignalRegistry.DEVICE_TYPE_CANCODER;
    }

    @Override
    public String getLabel() {
      return label;
    }

    @Override
    public RegistrationHeader getHeader() {
      return TEST_DEVICE_HEADER;
    }

    @Override
    public boolean isCreated() {
      return true;
    }

    @Override
    public void ensureCreated() {}

    @Override
    public void close() {}

    @Override
    public void clearFaults() {}

    @Override
    public DeviceSnapshot snapshot() {
      DeviceSnapshot snapshot = new DeviceSnapshot();
      snapshot.deviceType = DslSignalRegistry.DEVICE_TYPE_CANCODER;
      snapshot.canId = canId;
      snapshot.label = label;
      snapshot.present = true;
      EncoderAttachment encoder = new EncoderAttachment();
      encoder.absDeg = CANCODER_ABS_DEG;
      encoder.absRot = CANCODER_ABS_ROT;
      encoder.velocityRps = CANCODER_VEL_RPS;
      encoder.lastError = "OK";
      snapshot.addAttachment(encoder);
      return snapshot;
    }
  }

  private static final class FakeImuDevice implements DeviceUnit {
    private final int canId;
    private final String label;

    private FakeImuDevice(int canId, String label) {
      this.canId = canId;
      this.label = label;
    }

    @Override
    public int getCanId() {
      return canId;
    }

    @Override
    public String getDeviceType() {
      return DslSignalRegistry.DEVICE_TYPE_PIGEON;
    }

    @Override
    public String getLabel() {
      return label;
    }

    @Override
    public RegistrationHeader getHeader() {
      return TEST_DEVICE_HEADER;
    }

    @Override
    public boolean isCreated() {
      return true;
    }

    @Override
    public void ensureCreated() {}

    @Override
    public void close() {}

    @Override
    public void clearFaults() {}

    @Override
    public DeviceSnapshot snapshot() {
      DeviceSnapshot snapshot = new DeviceSnapshot();
      snapshot.deviceType = DslSignalRegistry.DEVICE_TYPE_PIGEON;
      snapshot.canId = canId;
      snapshot.label = label;
      snapshot.present = true;
      ImuAttachment imu = new ImuAttachment();
      imu.yawDeg = PIGEON_YAW;
      imu.pitchDeg = PIGEON_PITCH;
      imu.rollDeg = PIGEON_ROLL;
      imu.angularVelocityXDps = PIGEON_VEL_X;
      imu.angularVelocityYDps = PIGEON_VEL_Y;
      imu.angularVelocityZDps = PIGEON_VEL_Z;
      imu.accelXG = PIGEON_ACCEL_X;
      imu.accelYG = PIGEON_ACCEL_Y;
      imu.accelZG = PIGEON_ACCEL_Z;
      imu.lastError = "OK";
      snapshot.addAttachment(imu);
      return snapshot;
    }
  }

  private static final class FakeRobotControllerDevice implements DeviceUnit {
    private final int canId;
    private final String label;

    private FakeRobotControllerDevice(int canId, String label) {
      this.canId = canId;
      this.label = label;
    }

    @Override
    public int getCanId() {
      return canId;
    }

    @Override
    public String getDeviceType() {
      return DslSignalRegistry.DEVICE_TYPE_ROBOT_CONTROLLER;
    }

    @Override
    public String getLabel() {
      return label;
    }

    @Override
    public RegistrationHeader getHeader() {
      return TEST_ROBORIO_HEADER;
    }

    @Override
    public boolean isCreated() {
      return true;
    }

    @Override
    public void ensureCreated() {}

    @Override
    public void close() {}

    @Override
    public void clearFaults() {}

    @Override
    public DeviceSnapshot snapshot() {
      DeviceSnapshot snapshot = new DeviceSnapshot();
      snapshot.deviceType = DslSignalRegistry.DEVICE_TYPE_ROBOT_CONTROLLER;
      snapshot.canId = canId;
      snapshot.label = label;
      snapshot.present = true;
      RobotControllerPowerAttachment power = new RobotControllerPowerAttachment();
      power.inputVoltage = ROBORIO_INPUT_V;
      power.brownout = false;
      power.brownoutVoltage = ROBORIO_BROWNOUT_V;
      snapshot.addAttachment(power);
      RobotControllerBusAttachment bus = new RobotControllerBusAttachment();
      bus.canUtilizationPct = ROBORIO_CAN_UTIL;
      snapshot.addAttachment(bus);
      RobotControllerRailsAttachment rails = new RobotControllerRailsAttachment();
      rails.rail3v3Voltage = RAIL_3V3_V;
      rails.rail3v3Enabled = true;
      rails.rail5vVoltage = RAIL_5V_V;
      rails.rail5vEnabled = true;
      rails.rail6vVoltage = RAIL_6V_V;
      rails.rail6vEnabled = true;
      snapshot.addAttachment(rails);
      return snapshot;
    }
  }
}
