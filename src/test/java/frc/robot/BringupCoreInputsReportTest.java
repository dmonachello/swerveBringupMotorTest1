package frc.robot;

import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.devices.DeviceUnit;
import frc.robot.devices.ni.DioLimitSwitchDevice;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.manufacturers.DeviceRegistration;
import frc.robot.manufacturers.DeviceRole;
import frc.robot.manufacturers.DeviceTypeBucket;
import frc.robot.manufacturers.ManufacturerGroup;
import frc.robot.manufacturers.microsoft.XboxControllerDevice;
import frc.robot.registry.RegistrationHeader;
import frc.robot.telemetry.SampledTelemetrySampler;
import java.lang.reflect.Field;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   BringupCoreInputsReportTest - Regression tests for configured input reporting.
 */
class BringupCoreInputsReportTest {
  private static final RegistrationHeader TEST_GROUP_HEADER =
      new RegistrationHeader("Test", "Test", "Manufacturer", "test", "test", "2026-08-23", "test");
  private static final RegistrationHeader TEST_DEVICE_HEADER =
      new RegistrationHeader("Test Device", "Test", "device", "test", "test", "2026-08-23", "test");
  private static final String VENDOR_TEST = "Test";
  private static final String DISPLAY_XBOX = "Xbox Controller";
  private static final String DISPLAY_LIMIT_SWITCH = "Limit Switch";
  private static final String LABEL_CONTROLLER0 = "controller0";
  private static final String LABEL_LIMIT_SWITCH = "lmtSw0";
  private static final String SIGNAL_LEFT_Y = XboxControllerDevice.SIGNAL_LEFT_Y;
  private static final String SIGNAL_RIGHT_Y = XboxControllerDevice.SIGNAL_RIGHT_Y;
  private static final String SIGNAL_A = XboxControllerDevice.SIGNAL_A;
  private static final String SIGNAL_B = XboxControllerDevice.SIGNAL_B;
  private static final String SIGNAL_PRESSED = DioLimitSwitchDevice.SIGNAL_PRESSED;
  private static final int USB_PORT_0 = 0;
  private static final int DIO_CHANNEL_0 = 0;
  private static final double LEFT_Y_VALUE = 0.25;
  private static final double RIGHT_Y_VALUE = -0.75;

  @Test
  void buildInputsReportTextUsesConfiguredControllerAndLimitSwitchDevices() throws Exception {
    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    setManufacturerGroups(
        core,
        List.of(
            new TestManufacturerGroup(
                List.of(
                    buildBucket(
                        DISPLAY_XBOX,
                        XboxControllerDevice.DEVICE_TYPE,
                        List.of(
                            new FakeXboxControllerDevice(
                                USB_PORT_0,
                                LABEL_CONTROLLER0,
                                LEFT_Y_VALUE,
                                RIGHT_Y_VALUE,
                                true,
                                false))))),
            new TestManufacturerGroup(
                List.of(
                    buildBucket(
                        DISPLAY_LIMIT_SWITCH,
                        DioLimitSwitchDevice.DEVICE_TYPE,
                        List.of(new FakeLimitSwitchDevice(DIO_CHANNEL_0, LABEL_LIMIT_SWITCH, true, false)))))));

    String report = core.buildInputsReportText();

    assertTrue(report.contains("Controllers:"));
    assertTrue(report.contains("controller0 usb=0 present=YES leftY=0.25 rightY=-0.75 A=YES B=NO"));
    assertTrue(report.contains("Digital Inputs:"));
    assertTrue(report.contains("lmtSw0 DIO=0 present=YES pressed=YES invert=NO"));
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
    private final double leftY;
    private final double rightY;
    private final boolean buttonA;
    private final boolean buttonB;

    private FakeXboxControllerDevice(
        int port,
        String label,
        double leftY,
        double rightY,
        boolean buttonA,
        boolean buttonB) {
      this.port = port;
      this.label = label;
      this.leftY = leftY;
      this.rightY = rightY;
      this.buttonA = buttonA;
      this.buttonB = buttonB;
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
        case SIGNAL_LEFT_Y -> leftY;
        case SIGNAL_RIGHT_Y -> rightY;
        case SIGNAL_A -> buttonA;
        case SIGNAL_B -> buttonB;
        default -> null;
      };
    }
  }

  private static final class FakeLimitSwitchDevice implements DeviceUnit {
    private final int dioChannel;
    private final String label;
    private final boolean pressed;
    private final boolean invert;

    private FakeLimitSwitchDevice(int dioChannel, String label, boolean pressed, boolean invert) {
      this.dioChannel = dioChannel;
      this.label = label;
      this.pressed = pressed;
      this.invert = invert;
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
      limits.switches.add(state);
      snapshot.addAttachment(limits);
      return snapshot;
    }

    @Override
    public Object readDslSignal(String signalName) {
      return SIGNAL_PRESSED.equals(signalName) ? pressed : null;
    }
  }
}
