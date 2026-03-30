package frc.robot.tests;

import frc.robot.devices.DeviceActionRequest;
import frc.robot.devices.DeviceUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * NAME
 *   DeviceActionTest - Execute a device-specific action from JSON.
 *
 * DESCRIPTION
 *   Applies non-motor device actions (such as CANdle LED commands) to one or
 *   more devices identified by label.
 */
public final class DeviceActionTest implements BringupTest {
  public static final String TYPE = "deviceAction";
  private static final String KEY_NAME = "name";
  private static final String KEY_TYPE = "type";
  private static final String KEY_ENABLED = "enabled";
  private static final String KEY_MOTOR_LABELS = "motorLabels";
  private static final String KEY_ACTION = "action";
  private static final String KEY_COLOR = "color";
  private static final String KEY_PATTERN = "pattern";
  private static final String KEY_BRIGHTNESS = "brightness";
  private static final String KEY_DURATION_SEC = "durationSec";
  private static final String STATUS_READY = "ready";
  private static final String STATUS_RUNNING = "running";
  private static final String STATUS_COMPLETE = "complete";
  private static final String STATUS_NO_DEVICES = "device not found";
  private static final String STATUS_INVALID_ACTION = "invalid action";
  private static final String STATUS_UNSUPPORTED = "unsupported action";
  private static final String STATUS_INVALID_COLOR = "invalid color";
  private static final double DURATION_ZERO = 0.0;

  /**
   * NAME
   *   Config - Device action test configuration.
   */
  public static final class Config {
    public String name = TYPE;
    public boolean enabled = false;
    public List<String> deviceLabels = new ArrayList<>();
    public String action = null;
    public String color = null;
    public String pattern = null;
    public Double brightness = null;
    public Double durationSec = null;
  }

  private final Config config;
  private final List<DeviceUnit> devices = new ArrayList<>();
  private BringupTestResult result = BringupTestResult.NOT_RUN;
  private String status = STATUS_READY;
  private double startSec = DURATION_ZERO;

  public DeviceActionTest(Config config) {
    this.config = config != null ? config : new Config();
  }

  @Override
  public String getName() {
    return config.name;
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
  public List<String> getMotorKeys() {
    if (config.deviceLabels == null || config.deviceLabels.isEmpty()) {
      return java.util.Collections.emptyList();
    }
    return new ArrayList<>(config.deviceLabels);
  }

  @Override
  public boolean start(BringupTestContext context, double nowSec) {
    if (config.deviceLabels == null || config.deviceLabels.isEmpty()) {
      status = STATUS_NO_DEVICES;
      result = BringupTestResult.FAIL;
      return false;
    }
    if (config.action == null || config.action.isBlank()) {
      status = STATUS_INVALID_ACTION;
      result = BringupTestResult.FAIL;
      return false;
    }
    devices.clear();
    for (String label : config.deviceLabels) {
      DeviceUnit device = context.findDeviceByLabel(label);
      if (device != null && !devices.contains(device)) {
        devices.add(device);
      }
    }
    if (devices.isEmpty()) {
      status = STATUS_NO_DEVICES;
      result = BringupTestResult.FAIL;
      return false;
    }
    DeviceActionRequest.RgbColor rgb = null;
    if (DeviceActionRequest.ACTION_SET_COLOR.equalsIgnoreCase(config.action)) {
      rgb = DeviceActionRequest.parseColor(config.color);
      if (rgb == null) {
        status = STATUS_INVALID_COLOR;
        result = BringupTestResult.FAIL;
        return false;
      }
    }
    DeviceActionRequest request = new DeviceActionRequest(
        config.action,
        rgb,
        config.pattern,
        config.brightness,
        config.durationSec);
    for (DeviceUnit device : devices) {
      if (!device.applyDeviceAction(request)) {
        status = STATUS_UNSUPPORTED;
        result = BringupTestResult.FAIL;
        return false;
      }
    }
    startSec = nowSec;
    result = BringupTestResult.RUNNING;
    status = STATUS_RUNNING;
    if (config.durationSec == null || config.durationSec.doubleValue() <= DURATION_ZERO) {
      result = BringupTestResult.PASS;
      status = STATUS_COMPLETE;
    }
    return result != BringupTestResult.FAIL;
  }

  @Override
  public void update(BringupTestContext context, double nowSec) {
    if (result != BringupTestResult.RUNNING) {
      return;
    }
    if (config.durationSec == null || config.durationSec.doubleValue() <= DURATION_ZERO) {
      result = BringupTestResult.PASS;
      status = STATUS_COMPLETE;
      return;
    }
    if ((nowSec - startSec) >= config.durationSec.doubleValue()) {
      result = BringupTestResult.PASS;
      status = STATUS_COMPLETE;
    }
  }

  @Override
  public void stop(BringupTestContext context) {}

  public Map<String, Object> toEntry() {
    java.util.Map<String, Object> entry = new java.util.LinkedHashMap<>();
    entry.put(KEY_NAME, config.name);
    entry.put(KEY_TYPE, TYPE);
    entry.put(KEY_ENABLED, config.enabled);
    entry.put(KEY_MOTOR_LABELS, config.deviceLabels);
    entry.put(KEY_ACTION, config.action);
    if (config.color != null) {
      entry.put(KEY_COLOR, config.color);
    }
    if (config.pattern != null) {
      entry.put(KEY_PATTERN, config.pattern);
    }
    if (config.brightness != null) {
      entry.put(KEY_BRIGHTNESS, config.brightness);
    }
    if (config.durationSec != null) {
      entry.put(KEY_DURATION_SEC, config.durationSec);
    }
    return entry;
  }
}
