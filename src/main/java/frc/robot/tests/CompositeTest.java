package frc.robot.tests;

import frc.robot.BringupPrinter;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;

/**
 * NAME
 *   CompositeTest - Bringup test with multiple checks.
 *
 * DESCRIPTION
 *   Runs a motor duty test with optional rotation, time, limit, and hold
 *   checks, producing a combined result.
 */
public final class CompositeTest implements BringupTest {
  public static final String TYPE = "composite";
  private static final String ENCODER_INTERNAL = "internal";
  private static final String ENCODER_EXTERNAL = "external";
  private static final String ENCODER_ALT = "sparkmax_alt";
  private static final String ENCODER_ALT_ALT = "sparkmax_alternate";
  private static final String ENCODER_ALT_SHORT = "alternate";
  private static final String ENCODER_ALT_THROUGH = "through_bore";

  /**
   * NAME
   *   Config - Configuration payload for CompositeTest.
   */
  public static final class Config {
    public String name = "Composite Test";
    public boolean enabled = true;
    public java.util.List<String> motorLabels;
    public double duty = 0.2;
    public RotationCheck rotation;
    public TimeCheck time;
    public LimitSwitchCheck limitSwitch;
    public HoldCheck hold;
  }

  /**
   * NAME
   *   RotationCheck - Optional rotation/encoder check configuration.
   */
  public static final class RotationCheck {
    public double limitRot = 1.0;
    public String encoderKey = "internal"; // internal or device label
    public String encoderSource = "internal"; // internal | sparkmax_alt | external
    public Integer encoderCountsPerRev = null;
    public int encoderMotorIndex = 0;
  }

  /**
   * NAME
   *   TimeCheck - Optional time-based check configuration.
   */
  public static final class TimeCheck {
    public double timeoutSec = 2.0;
    public String onTimeout = "pass"; // pass | fail
  }

  /**
   * NAME
   *   LimitSwitchCheck - Optional limit switch check configuration.
   */
  public static final class LimitSwitchCheck {
    public boolean enabled = true;
    public String onHit = "pass"; // pass | fail
  }

  /**
   * NAME
   *   HoldCheck - Optional hold-to-run check configuration.
   */
  public static final class HoldCheck {
    public boolean enabled = false;
    public String onRelease = "pass"; // pass | fail
  }

  private final Config config;
  private BringupTestResult result = BringupTestResult.NOT_RUN;
  private final java.util.List<DeviceUnit> motors = new java.util.ArrayList<>();
  private DeviceUnit encoder;
  private DeviceUnit lastLimitDevice = null;
  private String encoderSource = "internal";
  private Integer encoderCountsPerRev = null;
  private double startRot = 0.0;
  private double startTime = 0.0;
  private String status = "";
  private boolean holdSignal = false;

  /**
   * NAME
   *   CompositeTest - Construct from config.
   */
  public CompositeTest(Config config) {
    this.config = config;
  }

  /**
   * NAME
   *   getName - Return test name.
   */
  @Override
  public String getName() {
    return config.name != null && !config.name.isBlank() ? config.name : "Composite Test";
  }

  /**
   * NAME
   *   getDisplayName - Return display name for UI.
   */
  @Override
  public String getDisplayName() {
    String base = getName();
    if (config.time != null && config.time.timeoutSec > 0.0) {
      return base + " (t=" + String.format("%.2f", config.time.timeoutSec) + "s)";
    }
    return base;
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
   *   getMotorKeys - Return motor labels used by this test.
   */
  @Override
  public java.util.List<String> getMotorKeys() {
    if (config.motorLabels == null || config.motorLabels.isEmpty()) {
      return java.util.Collections.emptyList();
    }
    return new java.util.ArrayList<>(config.motorLabels);
  }

  /**
   * NAME
   *   start - Start the composite test.
   */
  @Override
  public boolean start(BringupTestContext context, double nowSec) {
    if (config.motorLabels == null || config.motorLabels.isEmpty()) {
      status = "Motor not found";
      result = BringupTestResult.FAIL;
      return false;
    }
    motors.clear();
    for (String label : config.motorLabels) {
      DeviceUnit device = context.findDeviceByLabel(label);
      if (device != null && !motors.contains(device)) {
        motors.add(device);
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

    if (isLimitClosed() && isLimitCheckEnabled()) {
      status = buildLimitStatus("Limit switch already closed");
      result = BringupTestResult.FAIL;
      return false;
    }

    encoder = resolveEncoder(context);
    if (isRotationCheckEnabled()) {
      if (encoder == null) {
        status = "Encoder not found";
        result = BringupTestResult.FAIL;
        return false;
      }
      encoder.ensureCreated();
      Double rot = encoder.getPositionRotations(encoderSource, encoderCountsPerRev);
      if (rot == null) {
        status = "Encoder position unavailable";
        result = BringupTestResult.FAIL;
        return false;
      }
      startRot = rot;
    }

    startTime = nowSec;
    result = BringupTestResult.RUNNING;
    status = "Running";
    applyConfiguredDuty();
    long runId = context != null ? context.getRunId() : 0;
    String prefix = runId > 0 ? ("Test started #" + runId + ": ") : "Test started: ";
    BringupPrinter.enqueue(prefix + getName());
    return true;
  }

  /**
   * NAME
   *   update - Update test checks and motor outputs.
   */
  @Override
  public void update(BringupTestContext context, double nowSec) {
    if (result != BringupTestResult.RUNNING) {
      return;
    }

    if (isHoldCheckEnabled() && !holdSignal) {
      status = "Hold released";
      result = passOrFail(config.hold.onRelease);
      stop(context);
      return;
    }

    if (isLimitCheckEnabled() && isLimitClosed()) {
      status = buildLimitStatus("Limit switch hit");
      result = passOrFail(config.limitSwitch.onHit);
      stop(context);
      return;
    }

    if (isRotationCheckEnabled()) {
      Double rot = encoder != null ? encoder.getPositionRotations(encoderSource, encoderCountsPerRev) : null;
      if (rot == null) {
        status = "Encoder read failed";
        result = BringupTestResult.FAIL;
        stop(context);
        return;
      }
      double delta = Math.abs(rot - startRot);
      if (delta >= Math.abs(config.rotation.limitRot)) {
        status = buildRotationStatus("Reached rotation limit");
        result = BringupTestResult.PASS;
        stop(context);
        return;
      }
    }

    if (isTimeCheckEnabled()) {
      if (config.time.timeoutSec > 0.0 && (nowSec - startTime) >= config.time.timeoutSec) {
        status = "Time limit reached";
        result = passOrFail(config.time.onTimeout);
        stop(context);
        return;
      }
    }

    applyConfiguredDuty();
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
  }

  private void applyConfiguredDuty() {
    double duty = clampDuty(config.duty);
    for (DeviceUnit device : motors) {
      device.setDuty(duty);
    }
  }

  /**
   * NAME
   *   onHoldSignal - Update hold-to-run state.
   */
  @Override
  public void onHoldSignal(boolean held) {
    holdSignal = held;
  }

  /**
   * NAME
   *   resolveEncoder - Resolve encoder device for rotation checks.
   */
  private DeviceUnit resolveEncoder(BringupTestContext context) {
    if (!isRotationCheckEnabled()) {
      return null;
    }
    String key = config.rotation.encoderKey != null ? config.rotation.encoderKey.trim() : "";
    String source = config.rotation.encoderSource != null ? config.rotation.encoderSource.trim() : "";
    if (source.isBlank()) {
      source = ENCODER_INTERNAL;
    }
    if (!key.isBlank() && isAltEncoderKey(key) && ENCODER_INTERNAL.equalsIgnoreCase(source)) {
      source = ENCODER_ALT;
    }
    if (!key.isBlank()
        && !isAltEncoderKey(key)
        && !ENCODER_INTERNAL.equalsIgnoreCase(key)
        && ENCODER_INTERNAL.equalsIgnoreCase(source)) {
      source = ENCODER_EXTERNAL;
    }
    encoderSource = source;
    encoderCountsPerRev = config.rotation.encoderCountsPerRev;
    if (key.isBlank() || ENCODER_INTERNAL.equalsIgnoreCase(key) || isAltEncoderKey(key)) {
      if (motors.isEmpty()) {
        return null;
      }
      int index = config.rotation.encoderMotorIndex;
      if (index < 0 || index >= motors.size()) {
        index = 0;
      }
      return motors.get(index);
    }
    return context.findDeviceByLabel(key);
  }

  /**
   * NAME
   *   isAltEncoderKey - Check if an encoder key targets an alternate encoder.
   */
  private boolean isAltEncoderKey(String key) {
    if (key == null) {
      return false;
    }
    String normalized = key.trim().toLowerCase();
    return normalized.equals(ENCODER_ALT)
        || normalized.equals(ENCODER_ALT_ALT)
        || normalized.equals(ENCODER_ALT_SHORT)
        || normalized.equals(ENCODER_ALT_THROUGH);
  }

  /**
   * NAME
   *   isRotationCheckEnabled - Return whether rotation check is enabled.
   */
  private boolean isRotationCheckEnabled() {
    return config.rotation != null && config.rotation.limitRot != 0.0;
  }

  /**
   * NAME
   *   isTimeCheckEnabled - Return whether time check is enabled.
   */
  private boolean isTimeCheckEnabled() {
    return config.time != null && config.time.timeoutSec > 0.0;
  }

  /**
   * NAME
   *   isLimitCheckEnabled - Return whether limit check is enabled.
   */
  private boolean isLimitCheckEnabled() {
    return config.limitSwitch != null && config.limitSwitch.enabled;
  }

  /**
   * NAME
   *   isHoldCheckEnabled - Return whether hold-to-run check is enabled.
   */
  private boolean isHoldCheckEnabled() {
    return config.hold != null && config.hold.enabled;
  }

  /**
   * NAME
   *   passOrFail - Resolve a pass/fail action string.
   */
  private BringupTestResult passOrFail(String mode) {
    if (mode != null && mode.trim().equalsIgnoreCase("fail")) {
      return BringupTestResult.FAIL;
    }
    return BringupTestResult.PASS;
  }

  /**
   * NAME
   *   isLimitClosed - Determine if the limit switch is closed.
   */
  private boolean isLimitClosed() {
    if (motors.isEmpty()) {
      return false;
    }
    lastLimitDevice = null;
    for (DeviceUnit device : motors) {
      DeviceSnapshot snap = device.snapshot();
      if (snap == null) {
        continue;
      }
      LimitsAttachment limits = snap.getAttachment(LimitsAttachment.class);
      if (limits == null || limits.switches == null) {
        continue;
      }
      for (LimitsAttachment.LimitSwitchState state : limits.switches) {
        if (state == null) {
          continue;
        }
        if (Boolean.TRUE.equals(state.closed)) {
          lastLimitDevice = device;
          return true;
        }
      }
    }
    return false;
  }

  private String buildLimitStatus(String base) {
    if (lastLimitDevice == null) {
      return base;
    }
    return base + " (" + formatDeviceLabel(lastLimitDevice) + ")";
  }

  private String buildRotationStatus(String base) {
    if (encoder == null) {
      return base;
    }
    return base + " (" + formatDeviceLabel(encoder) + ")";
  }

  private String formatDeviceLabel(DeviceUnit device) {
    if (device == null) {
      return "unknown";
    }
    String type = device.getDeviceType();
    String label = type != null ? type : "device";
    return label + " CAN " + device.getCanId();
  }

  /**
   * NAME
   *   clampDuty - Clamp duty cycle to [-1, 1].
   */
  private double clampDuty(double duty) {
    if (duty > 1.0) {
      return 1.0;
    }
    if (duty < -1.0) {
      return -1.0;
    }
    return duty;
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
    if (config.motorLabels != null && !config.motorLabels.isEmpty()) {
      entry.put("motorLabels", new java.util.ArrayList<>(config.motorLabels));
    }
    entry.put("duty", config.duty);
    if (config.rotation != null) {
      java.util.Map<String, Object> rotation = new java.util.LinkedHashMap<>();
      rotation.put("limitRot", config.rotation.limitRot);
      rotation.put("encoderKey", config.rotation.encoderKey);
      rotation.put("encoderSource", config.rotation.encoderSource);
      rotation.put("encoderMotorIndex", config.rotation.encoderMotorIndex);
      if (config.rotation.encoderCountsPerRev != null) {
        rotation.put("encoderCountsPerRev", config.rotation.encoderCountsPerRev);
      }
      entry.put("rotation", rotation);
    }
    if (config.time != null) {
      java.util.Map<String, Object> time = new java.util.LinkedHashMap<>();
      time.put("timeoutSec", config.time.timeoutSec);
      time.put("onTimeout", config.time.onTimeout);
      entry.put("time", time);
    }
    if (config.limitSwitch != null) {
      java.util.Map<String, Object> limit = new java.util.LinkedHashMap<>();
      limit.put("enabled", config.limitSwitch.enabled);
      limit.put("onHit", config.limitSwitch.onHit);
      entry.put("limitSwitch", limit);
    }
    if (config.hold != null) {
      java.util.Map<String, Object> hold = new java.util.LinkedHashMap<>();
      hold.put("enabled", config.hold.enabled);
      hold.put("onRelease", config.hold.onRelease);
      entry.put("hold", hold);
    }
    return entry;
  }

}
