package frc.robot.tests;

import frc.robot.BringupPrinter;
import frc.robot.devices.DeviceUnit;

public final class JoystickTest implements BringupTest {
  public static final String TYPE = "joystick";

  public static final class Config {
    public String name = "Joystick";
    public boolean enabled = true;
    public java.util.List<BringupTestRegistry.MotorRef> motors;
    public double deadband = 0.12;
    public String inputAxis = "primary"; // primary | secondary
  }

  private final Config config;
  private BringupTestResult result = BringupTestResult.NOT_RUN;
  private final java.util.List<DeviceUnit> motors = new java.util.ArrayList<>();
  private double inputValue = 0.0;
  private String status = "";

  public JoystickTest(Config config) {
    this.config = config;
  }

  @Override
  public String getName() {
    return config.name != null && !config.name.isBlank() ? config.name : "Joystick";
  }

  @Override
  public boolean isEnabled() {
    return config.enabled;
  }

  @Override
  public void setEnabled(boolean enabled) {
    config.enabled = enabled;
  }

  @Override
  public boolean isRunning() {
    return result == BringupTestResult.RUNNING;
  }

  @Override
  public boolean isFinished() {
    return result == BringupTestResult.PASS || result == BringupTestResult.FAIL;
  }

  @Override
  public BringupTestResult getResult() {
    return result;
  }

  @Override
  public String getStatus() {
    return status;
  }

  @Override
  public boolean start(BringupTestContext context, double nowSec) {
    if (config.motors == null || config.motors.isEmpty()) {
      status = "Motor not found";
      result = BringupTestResult.FAIL;
      return false;
    }
    motors.clear();
    if (config.motors != null && !config.motors.isEmpty()) {
      for (BringupTestRegistry.MotorRef ref : config.motors) {
        if (ref == null || ref.vendor == null || ref.type == null) {
          continue;
        }
        DeviceUnit device = context.findDevice(ref.vendor, ref.type, ref.id);
        if (device != null && !motors.contains(device)) {
          motors.add(device);
        }
      }
    }
    if (motors.isEmpty()) {
      status = "Motor not found";
      result = BringupTestResult.FAIL;
      return false;
    }
    for (DeviceUnit device : motors) {
      device.ensureCreated();
    }
    result = BringupTestResult.RUNNING;
    status = "Running";
    BringupPrinter.enqueue("Joystick test started: " + getName());
    return true;
  }

  @Override
  public void update(BringupTestContext context, double nowSec) {
    if (result != BringupTestResult.RUNNING) {
      return;
    }
    double duty = applyDeadband(inputValue, config.deadband);
    for (DeviceUnit device : motors) {
      device.setDuty(duty);
    }
  }

  @Override
  public void stop(BringupTestContext context) {
    for (DeviceUnit device : motors) {
      device.stop();
    }
    if (result == BringupTestResult.RUNNING) {
      result = BringupTestResult.PASS;
      status = "Stopped";
    }
  }

  public void setInputValue(double value) {
    inputValue = value;
  }

  public String getInputAxis() {
    return config.inputAxis != null ? config.inputAxis : "primary";
  }

  private double applyDeadband(double value, double deadband) {
    return Math.abs(value) < deadband ? 0.0 : value;
  }

  public java.util.Map<String, Object> toEntry() {
    java.util.Map<String, Object> entry = new java.util.LinkedHashMap<>();
    entry.put("type", TYPE);
    entry.put("name", getName());
    entry.put("enabled", config.enabled);
    if (config.motors != null && !config.motors.isEmpty()) {
      java.util.List<String> motorKeys = new java.util.ArrayList<>();
      for (BringupTestRegistry.MotorRef ref : config.motors) {
        String key = buildMotorKey(ref);
        if (!key.isBlank()) {
          motorKeys.add(key);
        }
      }
      entry.put("motorKeys", motorKeys);
    }
    entry.put("deadband", config.deadband);
    entry.put("inputAxis", getInputAxis());
    return entry;
  }

  private String buildMotorKey(BringupTestRegistry.MotorRef motorRef) {
    if (motorRef == null || motorRef.vendor == null || motorRef.type == null) {
      return "";
    }
    return motorRef.vendor.trim() + ":" + motorRef.type.trim() + ":" + motorRef.id;
  }
}
