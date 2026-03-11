package frc.robot.tests;

import frc.robot.BringupPrinter;
import frc.robot.devices.DeviceUnit;

/**
 * NAME
 *   JoystickTest - Manual joystick-driven motor test.
 *
 * DESCRIPTION
 *   Maps joystick input to a set of motors with deadband filtering.
 */
public final class JoystickTest implements BringupTest {
  public static final String TYPE = "joystick";

  /**
   * NAME
   *   Config - Configuration payload for JoystickTest.
   */
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

  /**
   * NAME
   *   JoystickTest - Construct from config.
   */
  public JoystickTest(Config config) {
    this.config = config;
  }

  /**
   * NAME
   *   getName - Return test name.
   */
  @Override
  public String getName() {
    return config.name != null && !config.name.isBlank() ? config.name : "Joystick";
  }

  /**
   * NAME
   *   isEnabled - Return enabled state.
   */
  @Override
  public boolean isEnabled() {
    return config.enabled;
  }

  /**
   * NAME
   *   setEnabled - Enable or disable the test.
   */
  @Override
  public void setEnabled(boolean enabled) {
    config.enabled = enabled;
  }

  /**
   * NAME
   *   isRunning - Return running state.
   */
  @Override
  public boolean isRunning() {
    return result == BringupTestResult.RUNNING;
  }

  /**
   * NAME
   *   isFinished - Return finished state.
   */
  @Override
  public boolean isFinished() {
    return result == BringupTestResult.PASS || result == BringupTestResult.FAIL;
  }

  /**
   * NAME
   *   getResult - Return result state.
   */
  @Override
  public BringupTestResult getResult() {
    return result;
  }

  /**
   * NAME
   *   getStatus - Return status message.
   */
  @Override
  public String getStatus() {
    return status;
  }

  /**
   * NAME
   *   getMotorKeys - Return motor keys used by this test.
   */
  @Override
  public java.util.List<String> getMotorKeys() {
    if (config.motors == null || config.motors.isEmpty()) {
      return java.util.Collections.emptyList();
    }
    java.util.List<String> keys = new java.util.ArrayList<>();
    for (BringupTestRegistry.MotorRef ref : config.motors) {
      String key = buildMotorKey(ref);
      if (!key.isBlank()) {
        keys.add(key);
      }
    }
    return keys;
  }

  /**
   * NAME
   *   start - Start the joystick test.
   */
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

  /**
   * NAME
   *   update - Apply joystick input to motors.
   */
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

  /**
   * NAME
   *   stop - Stop the test and set motors to zero.
   */
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

  /**
   * NAME
   *   setInputValue - Update current joystick input.
   */
  public void setInputValue(double value) {
    inputValue = value;
  }

  /**
   * NAME
   *   getInputAxis - Return configured input axis name.
   */
  public String getInputAxis() {
    return config.inputAxis != null ? config.inputAxis : "primary";
  }

  private double applyDeadband(double value, double deadband) {
    return Math.abs(value) < deadband ? 0.0 : value;
  }

  /**
   * NAME
   *   toEntry - Serialize this test to a JSON-friendly map.
   */
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
