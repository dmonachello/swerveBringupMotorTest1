package frc.robot.tests;

import frc.robot.devices.DeviceUnit;
import frc.robot.tests.BringupTestRegistry.EncoderRef;
import frc.robot.tests.BringupTestRegistry.MotorRef;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * NAME
 *   DeadbandSweepTest - Sweep duty until motion is detected.
 *
 * DESCRIPTION
 *   Applies small duty steps and watches encoder movement to estimate the
 *   minimum duty that causes motion. Intended for low-risk validation of
 *   deadband behavior.
 */
public final class DeadbandSweepTest implements BringupTest {
  public static final String TYPE = "deadbandSweep";

  /**
   * NAME
   *   Config - Deadband sweep configuration.
   */
  public static final class Config {
    public String name = "Deadband sweep";
    public boolean enabled = false;
    public double startDuty = 0.0;
    public double maxDuty = 0.2;
    public double stepDuty = 0.01;
    public double stepHoldSec = 0.25;
    public double motionThresholdRot = 0.02;
    public int requiredSamples = 3;
    public String encoderKey = "internal";
    public String encoderSource = null;
    public Integer encoderCountsPerRev = null;
    public int encoderMotorIndex = 0;
    public List<MotorRef> motors = Collections.emptyList();
  }

  /**
   * NAME
   *   SweepConfig - JSON sweep configuration block.
   */
  public static final class SweepConfig {
    public double startDuty = 0.0;
    public double maxDuty = 0.2;
    public double stepDuty = 0.01;
    public double stepHoldSec = 0.25;
    public double motionThresholdRot = 0.02;
    public int requiredSamples = 3;
    public String encoderKey = "internal";
    public String encoderSource = null;
    public Integer encoderCountsPerRev = null;
    public int encoderMotorIndex = 0;
  }

  private final Config config;
  private final List<DeviceUnit> motors = new ArrayList<>();
  private DeviceUnit encoder;
  private String encoderSource = "internal";
  private Integer encoderCountsPerRev = null;
  private double currentDuty = 0.0;
  private double stepStartTime = 0.0;
  private double stepStartRot = 0.0;
  private int motionHits = 0;
  private Double foundDuty = null;
  private BringupTestResult result = BringupTestResult.NOT_RUN;
  private String status = "Idle";

  /**
   * NAME
   *   DeadbandSweepTest - Construct from config.
   */
  public DeadbandSweepTest(Config config) {
    this.config = config != null ? config : new Config();
  }

  /**
   * NAME
   *   getName - Return the test name.
   */
  @Override
  public String getName() {
    return config.name != null && !config.name.isBlank() ? config.name : "Deadband sweep";
  }

  /**
   * NAME
   *   isEnabled - Return whether the test is enabled.
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
   *   isRunning - Return whether the test is currently active.
   */
  @Override
  public boolean isRunning() {
    return result == BringupTestResult.RUNNING;
  }

  /**
   * NAME
   *   isFinished - Return whether the test has completed.
   */
  @Override
  public boolean isFinished() {
    return result == BringupTestResult.PASS || result == BringupTestResult.FAIL;
  }

  /**
   * NAME
   *   getResult - Return the final test result.
   */
  @Override
  public BringupTestResult getResult() {
    return result;
  }

  /**
   * NAME
   *   getStatus - Return a human-readable status string.
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
  public List<String> getMotorKeys() {
    if (config.motors == null || config.motors.isEmpty()) {
      return Collections.emptyList();
    }
    List<String> keys = new ArrayList<>();
    for (MotorRef ref : config.motors) {
      if (ref == null || ref.vendor == null || ref.type == null) {
        continue;
      }
      keys.add(ref.vendor.trim() + ":" + ref.type.trim() + ":" + ref.id);
    }
    return keys;
  }

  /**
   * NAME
   *   start - Start the deadband sweep test.
   */
  @Override
  public boolean start(BringupTestContext context, double nowSec) {
    resetState();
    if (context == null) {
      status = "Missing context";
      result = BringupTestResult.FAIL;
      return false;
    }
    if (config.stepDuty <= 0.0 || config.stepHoldSec <= 0.0 || config.maxDuty <= config.startDuty) {
      status = "Invalid sweep config";
      result = BringupTestResult.FAIL;
      return false;
    }
    if (config.motors == null || config.motors.isEmpty()) {
      status = "Motor not configured";
      result = BringupTestResult.FAIL;
      return false;
    }
    for (MotorRef ref : config.motors) {
      DeviceUnit device = context.findDevice(ref.vendor, ref.type, ref.id);
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
    encoder = resolveEncoder(context);
    if (encoder == null) {
      status = "Encoder not found";
      result = BringupTestResult.FAIL;
      return false;
    }
    Double rot = encoder.getPositionRotations(encoderSource, encoderCountsPerRev);
    if (rot == null) {
      status = "Encoder read failed";
      result = BringupTestResult.FAIL;
      return false;
    }
    currentDuty = clampDuty(config.startDuty);
    stepStartTime = nowSec;
    stepStartRot = rot;
    motionHits = 0;
    result = BringupTestResult.RUNNING;
    status = "Sweeping";
    applyDuty(currentDuty);
    return true;
  }

  /**
   * NAME
   *   update - Update the deadband sweep state.
   */
  @Override
  public void update(BringupTestContext context, double nowSec) {
    if (result != BringupTestResult.RUNNING) {
      return;
    }
    if (encoder == null) {
      status = "Encoder missing";
      result = BringupTestResult.FAIL;
      stop(context);
      return;
    }
    Double rot = encoder.getPositionRotations(encoderSource, encoderCountsPerRev);
    if (rot == null) {
      status = "Encoder read failed";
      result = BringupTestResult.FAIL;
      stop(context);
      return;
    }
    double delta = Math.abs(rot - stepStartRot);
    if (delta >= Math.abs(config.motionThresholdRot)) {
      motionHits++;
    } else {
      motionHits = 0;
    }
    if (motionHits >= Math.max(1, config.requiredSamples)) {
      foundDuty = currentDuty;
      status = "Deadband found at duty " + formatDuty(foundDuty);
      result = BringupTestResult.PASS;
      stop(context);
      return;
    }
    if ((nowSec - stepStartTime) >= config.stepHoldSec) {
      currentDuty = clampDuty(currentDuty + config.stepDuty);
      if (currentDuty > config.maxDuty + 1e-6) {
        status = "No motion up to max duty " + formatDuty(config.maxDuty);
        result = BringupTestResult.FAIL;
        stop(context);
        return;
      }
      stepStartTime = nowSec;
      stepStartRot = rot;
      motionHits = 0;
      status = "Sweeping duty " + formatDuty(currentDuty);
      applyDuty(currentDuty);
    }
  }

  /**
   * NAME
   *   stop - Stop the sweep and motor outputs.
   */
  @Override
  public void stop(BringupTestContext context) {
    for (DeviceUnit device : motors) {
      device.stop();
    }
  }

  /**
   * NAME
   *   toEntry - Serialize this test to a JSON-friendly map.
   */
  public Map<String, Object> toEntry() {
    Map<String, Object> entry = new java.util.LinkedHashMap<>();
    entry.put("type", TYPE);
    entry.put("name", getName());
    entry.put("enabled", config.enabled);
    if (config.motors != null && !config.motors.isEmpty()) {
      List<String> motorKeys = new ArrayList<>();
      for (MotorRef ref : config.motors) {
        if (ref == null || ref.vendor == null || ref.type == null) {
          continue;
        }
        motorKeys.add(ref.vendor.trim() + ":" + ref.type.trim() + ":" + ref.id);
      }
      entry.put("motorKeys", motorKeys);
    }
    Map<String, Object> sweep = new java.util.LinkedHashMap<>();
    sweep.put("startDuty", config.startDuty);
    sweep.put("maxDuty", config.maxDuty);
    sweep.put("stepDuty", config.stepDuty);
    sweep.put("stepHoldSec", config.stepHoldSec);
    sweep.put("motionThresholdRot", config.motionThresholdRot);
    sweep.put("requiredSamples", config.requiredSamples);
    sweep.put("encoderKey", config.encoderKey);
    sweep.put("encoderSource", config.encoderSource);
    sweep.put("encoderCountsPerRev", config.encoderCountsPerRev);
    sweep.put("encoderMotorIndex", config.encoderMotorIndex);
    entry.put("deadbandSweep", sweep);
    if (foundDuty != null) {
      entry.put("foundDuty", foundDuty);
    }
    return entry;
  }

  private void resetState() {
    motors.clear();
    encoder = null;
    encoderSource = "internal";
    encoderCountsPerRev = null;
    currentDuty = 0.0;
    stepStartTime = 0.0;
    stepStartRot = 0.0;
    motionHits = 0;
    foundDuty = null;
    result = BringupTestResult.NOT_RUN;
    status = "Idle";
  }

  private void applyDuty(double duty) {
    for (DeviceUnit device : motors) {
      device.setDuty(clampDuty(duty));
    }
  }

  private DeviceUnit resolveEncoder(BringupTestContext context) {
    String key = config.encoderKey != null ? config.encoderKey.trim() : "internal";
    EncoderRef ref = BringupTestRegistry.parseEncoderRef(key);
    if (ref == null) {
      return null;
    }
    if ("internal".equalsIgnoreCase(ref.source)) {
      int index = config.encoderMotorIndex < 0 ? 0 : config.encoderMotorIndex;
      if (index >= motors.size()) {
        index = 0;
      }
      encoderSource = config.encoderSource != null ? config.encoderSource : "internal";
      encoderCountsPerRev = config.encoderCountsPerRev;
      return motors.get(index);
    }
    DeviceUnit device = context.findDevice(ref.vendor, ref.type, ref.id);
    if (device == null) {
      return null;
    }
    encoderSource = config.encoderSource != null ? config.encoderSource : ref.source;
    encoderCountsPerRev = config.encoderCountsPerRev;
    device.ensureCreated();
    return device;
  }

  private static double clampDuty(double duty) {
    if (duty > 1.0) {
      return 1.0;
    }
    if (duty < -1.0) {
      return -1.0;
    }
    return duty;
  }

  private static String formatDuty(double duty) {
    return String.format("%.2f", duty);
  }
}
