package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.manufacturers.DeviceAddResult;
import frc.robot.manufacturers.DeviceRegistration;
import frc.robot.manufacturers.DeviceRole;
import frc.robot.manufacturers.DeviceTypeBucket;
import frc.robot.manufacturers.ManufacturerGroup;
import frc.robot.registry.RegistrationHeader;
import frc.robot.tests.BringupTestContext;
import frc.robot.tests.BringupTestResult;
import frc.robot.tests.CompositeTest;
import java.util.List;
import org.junit.jupiter.api.Test;

class CompositeTestTest {
  private static final String TEST_NAME = "spin";
  private static final String MOTOR_LABEL = "motor-a";
  private static final String VENDOR = "REV";
  private static final String DEVICE_TYPE = "NEO";
  private static final String SOURCE = "test";
  private static final String OWNER = "unit";
  private static final String EMPTY = "";
  private static final String RESULT_PASS = "pass";
  private static final int CAN_ID = 25;
  private static final double DUTY = 0.15;
  private static final double START_SEC = 10.0;
  private static final double UPDATE_SEC = 10.02;
  private static final double FINISH_SEC = 11.51;
  private static final double TIMEOUT_SEC = 1.5;

  @Test
  void compositeTestReappliesDutyUntilFinished() {
    RecordingDevice device = new RecordingDevice();
    CompositeTest test = new CompositeTest(config());
    BringupTestContext context = context(device);

    assertTrue(test.start(context, START_SEC));
    test.update(context, UPDATE_SEC);
    test.update(context, FINISH_SEC);

    assertEquals(BringupTestResult.PASS, test.getResult());
    assertEquals(2, device.dutyWrites);
    assertEquals(1, device.stopWrites);
    assertEquals(DUTY, device.lastDuty);
  }

  private static CompositeTest.Config config() {
    CompositeTest.Config config = new CompositeTest.Config();
    config.name = TEST_NAME;
    config.motorLabels = List.of(MOTOR_LABEL);
    config.duty = DUTY;
    config.time = new CompositeTest.TimeCheck();
    config.time.timeoutSec = TIMEOUT_SEC;
    config.time.onTimeout = RESULT_PASS;
    return config;
  }

  private static BringupTestContext context(DeviceUnit device) {
    RegistrationHeader header =
        new RegistrationHeader(VENDOR, VENDOR, DEVICE_TYPE, SOURCE, OWNER, EMPTY, EMPTY);
    DeviceRegistration registration =
        new DeviceRegistration(header, VENDOR, DEVICE_TYPE, DEVICE_TYPE, DeviceRole.MOTOR, false, null);
    DeviceTypeBucket bucket = new DeviceTypeBucket(registration, List.of(device), false);
    return new BringupTestContext(List.of(new SingleGroup(header, bucket)));
  }

  private static final class RecordingDevice implements DeviceUnit {
    private int dutyWrites;
    private int stopWrites;
    private double lastDuty;
    private boolean created;

    @Override
    public int getCanId() {
      return CAN_ID;
    }

    @Override
    public RegistrationHeader getHeader() {
      return new RegistrationHeader(VENDOR, VENDOR, DEVICE_TYPE, SOURCE, OWNER, EMPTY, EMPTY);
    }

    @Override
    public String getDeviceType() {
      return DEVICE_TYPE;
    }

    @Override
    public String getLabel() {
      return MOTOR_LABEL;
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
    public void close() {}

    @Override
    public void clearFaults() {}

    @Override
    public DeviceSnapshot snapshot() {
      return new DeviceSnapshot();
    }

    @Override
    public void setDuty(double duty) {
      dutyWrites++;
      lastDuty = duty;
    }

    @Override
    public void stop() {
      stopWrites++;
    }
  }

  private static final class SingleGroup implements ManufacturerGroup {
    private final RegistrationHeader header;
    private final DeviceTypeBucket bucket;

    private SingleGroup(RegistrationHeader header, DeviceTypeBucket bucket) {
      this.header = header;
      this.bucket = bucket;
    }

    @Override
    public RegistrationHeader getHeader() {
      return header;
    }

    @Override
    public List<DeviceTypeBucket> getDeviceBuckets() {
      return List.of(bucket);
    }

    @Override
    public DeviceAddResult addNextMotor() {
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
}
