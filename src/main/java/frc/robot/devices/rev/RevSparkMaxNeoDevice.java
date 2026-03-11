package frc.robot.devices.rev;

import com.revrobotics.PersistMode;
import com.revrobotics.ResetMode;
import com.revrobotics.spark.SparkLowLevel.MotorType;
import com.revrobotics.spark.SparkMax;
import com.revrobotics.spark.config.SparkMaxConfig;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.manufacturers.rev.diag.RevSparkMaxReader;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.registry.RegistrationHeader;
import edu.wpi.first.wpilibj.DigitalInput;

/**
 * NAME
 * RevSparkMaxNeoDevice
 *
 * SYNOPSIS
 * Device wrapper for a REV Spark Max controlling a NEO.
 *
 * DESCRIPTION
 * Provides bringup lifecycle, telemetry, limit switch handling, and optional
 * alternate encoder access for Spark Max devices.
 */
public final class RevSparkMaxNeoDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "SparkMax NEO",
      "REV",
      "NEO",
      "REVLib",
      "Team",
      "2026-03-02",
      "Spark Max controlling a NEO motor.");
  private final int canId;
  private final String label;
  private final String motorModelOverride;
  private final BringupUtil.LimitConfig limitConfig;
  private DigitalInput fwdLimit;
  private DigitalInput revLimit;
  private SparkMax device;
  private boolean altEncoderConfigured = false;
  private int altEncoderCpr = 8192;

  /**
   * NAME
   * RevSparkMaxNeoDevice
   *
   * SYNOPSIS
   * Construct a Spark Max NEO device wrapper.
   *
   * PARAMETERS
   * canId - CAN ID of the motor controller.
   * label - human-readable label for reporting.
   * motorModelOverride - optional motor model override for spec lookup.
   * limitConfig - optional limit switch configuration.
   *
   * SIDE EFFECTS
   * Initializes DIO inputs when limit switches are configured.
   */
  public RevSparkMaxNeoDevice(
      int canId,
      String label,
      String motorModelOverride,
      BringupUtil.LimitConfig limitConfig) {
    this.canId = canId;
    this.label = label;
    this.motorModelOverride = motorModelOverride;
    this.limitConfig = limitConfig != null ? limitConfig : new BringupUtil.LimitConfig();
    initLimitInputs();
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return "NEO";
  }

  @Override
  public String getLabel() {
    return label;
  }

  @Override
  public RegistrationHeader getHeader() {
    return HEADER;
  }
  public String getMotorModelOverride() {
    return motorModelOverride;
  }

  @Override
  public boolean isCreated() {
    return device != null;
  }

  /**
   * NAME
   * ensureCreated
   *
   * SYNOPSIS
   * Construct and configure the Spark Max device if needed.
   *
   * SIDE EFFECTS
   * Allocates a vendor device and configures it asynchronously.
   */
  @Override
  public void ensureCreated() {
    if (device != null) {
      return;
    }
    device = new SparkMax(canId, MotorType.kBrushless);
    device.pauseFollowerModeAsync();
    device.configureAsync(
        new SparkMaxConfig(),
        ResetMode.kResetSafeParameters,
        PersistMode.kNoPersistParameters);
  }

  /**
   * NAME
   * close
   *
   * SYNOPSIS
   * Release vendor and DIO resources.
   *
   * SIDE EFFECTS
   * Closes device handles and limit switch inputs.
   */
  @Override
  public void close() {
    BringupUtil.closeIfPossible(device);
    device = null;
    BringupUtil.closeIfPossible(fwdLimit);
    BringupUtil.closeIfPossible(revLimit);
    fwdLimit = null;
    revLimit = null;
  }

  /**
   * NAME
   * clearFaults
   *
   * SYNOPSIS
   * Clear faults on the Spark Max.
   *
   * SIDE EFFECTS
   * Sends vendor fault-clear commands.
   */
  @Override
  public void clearFaults() {
    if (device != null) {
      device.clearFaults();
    }
  }

  /**
   * NAME
   * setDuty
   *
   * SYNOPSIS
   * Apply open-loop duty with limit switch enforcement.
   *
   * PARAMETERS
   * duty - requested output in [-1, 1].
   *
   * SIDE EFFECTS
   * Commands motor output via the vendor API.
   */
  @Override
  public void setDuty(double duty) {
    if (device != null) {
      device.set(applyLimit(duty));
    }
  }

  /**
   * NAME
   * stop
   *
   * SYNOPSIS
   * Stop the motor output.
   */
  @Override
  public void stop() {
    if (device != null) {
      device.stopMotor();
    }
  }

  /**
   * NAME
   * activate
   *
   * SYNOPSIS
   * Activate the device by ensuring it is created.
   */
  @Override
  public void activate() {
    ensureCreated();
  }

  /**
   * NAME
   * deactivate
   *
   * SYNOPSIS
   * Deactivate the device by stopping output.
   */
  @Override
  public void deactivate() {
    stop();
  }

  /**
   * NAME
   * snapshot
   *
   * SYNOPSIS
   * Capture a diagnostic snapshot of the device.
   *
   * RETURNS
   * A snapshot containing vendor telemetry and limit switch state.
   */
  @Override
  public DeviceSnapshot snapshot() {
    if (device == null) {
      DeviceSnapshot snap = new DeviceSnapshot();
      snap.vendor = "REV";
      snap.deviceType = getDeviceType();
      snap.canId = canId;
      snap.present = false;
      snap.note = "not added";
      snap.label = label;
      addLimitAttachment(snap);
      return snap;
    }
    DeviceSnapshot snap = RevSparkMaxReader.read(device, canId);
    snap.deviceType = getDeviceType();
    snap.label = label;
    addLimitAttachment(snap);
    return snap;
  }

  /**
   * NAME
   * getPositionRotations
   *
   * SYNOPSIS
   * Return the integrated encoder position in rotations.
   *
   * RETURNS
   * Position in rotations, or null on read error or when not created.
   */
  @Override
  public Double getPositionRotations() {
    if (device == null) {
      return null;
    }
    try {
      return device.getEncoder().getPosition();
    } catch (Exception ex) {
      return null;
    }
  }

  /**
   * NAME
   * getPositionRotations
   *
   * SYNOPSIS
   * Return position from the selected encoder source.
   *
   * PARAMETERS
   * encoderSource - encoder source selector string.
   * countsPerRev - optional counts per revolution for alternate encoders.
   *
   * RETURNS
   * Position in rotations, or null when unavailable.
   */
  @Override
  public Double getPositionRotations(String encoderSource, Integer countsPerRev) {
    if (isAltEncoder(encoderSource)) {
      return readAlternateEncoder(countsPerRev);
    }
    return getPositionRotations();
  }

  /**
   * NAME
   * initLimitInputs
   *
   * SYNOPSIS
   * Initialize DIO inputs for configured limit switches.
   *
   * SIDE EFFECTS
   * Allocates DigitalInput instances when DIO channels are configured.
   */
  private void initLimitInputs() {
    if (limitConfig.hasForward()) {
      fwdLimit = new DigitalInput(limitConfig.fwdDio);
    }
    if (limitConfig.hasReverse()) {
      revLimit = new DigitalInput(limitConfig.revDio);
    }
  }

  /**
   * NAME
   * addLimitAttachment
   *
   * SYNOPSIS
   * Attach limit switch telemetry to a device snapshot.
   *
   * PARAMETERS
   * snap - snapshot to populate with limit data.
   */
  private void addLimitAttachment(DeviceSnapshot snap) {
    if (!limitConfig.hasForward() && !limitConfig.hasReverse()) {
      return;
    }
    LimitsAttachment limits = new LimitsAttachment();
    limits.invert = limitConfig.invert;
    if (limitConfig.hasForward()) {
      limits.fwdDio = limitConfig.fwdDio;
      limits.fwdClosed = readLimit(fwdLimit);
    }
    if (limitConfig.hasReverse()) {
      limits.revDio = limitConfig.revDio;
      limits.revClosed = readLimit(revLimit);
    }
    snap.addAttachment(limits);
  }

  /**
   * NAME
   * readLimit
   *
   * SYNOPSIS
   * Read a limit input and apply inversion if configured.
   *
   * PARAMETERS
   * input - DIO input to sample.
   *
   * RETURNS
   * True if closed, false if open, or null when input is absent.
   */
  private Boolean readLimit(DigitalInput input) {
    if (input == null) {
      return null;
    }
    boolean raw = input.get();
    return limitConfig.invert ? !raw : raw;
  }

  /**
   * NAME
   * isAltEncoder
   *
   * SYNOPSIS
   * Determine whether the requested source targets the alternate encoder.
   *
   * PARAMETERS
   * encoderSource - encoder source selector string.
   *
   * RETURNS
   * True when the alternate encoder should be used.
   */
  private boolean isAltEncoder(String encoderSource) {
    if (encoderSource == null) {
      return false;
    }
    String normalized = encoderSource.trim().toLowerCase();
    return normalized.equals("sparkmax_alt")
        || normalized.equals("sparkmax_alternate")
        || normalized.equals("alternate")
        || normalized.equals("through_bore");
  }

  /**
   * NAME
   * readAlternateEncoder
   *
   * SYNOPSIS
   * Read the alternate encoder position, configuring CPR if needed.
   *
   * PARAMETERS
   * countsPerRev - optional counts per revolution for the alternate encoder.
   *
   * RETURNS
   * Position in rotations, or null on read error or when not created.
   *
   * SIDE EFFECTS
   * Reconfigures the alternate encoder CPR when it changes.
   */
  private Double readAlternateEncoder(Integer countsPerRev) {
    if (device == null) {
      return null;
    }
    int cpr = countsPerRev != null && countsPerRev > 0 ? countsPerRev.intValue() : 8192;
    if (!altEncoderConfigured || altEncoderCpr != cpr) {
      SparkMaxConfig config = new SparkMaxConfig();
      config.alternateEncoder.setSparkMaxDataPortConfig().countsPerRevolution(cpr);
      device.configureAsync(config, ResetMode.kNoResetSafeParameters, PersistMode.kNoPersistParameters);
      altEncoderConfigured = true;
      altEncoderCpr = cpr;
    }
    try {
      return device.getAlternateEncoder().getPosition();
    } catch (Exception ex) {
      return null;
    }
  }

  /**
   * NAME
   * applyLimit
   *
   * SYNOPSIS
   * Enforce limit switches by clamping duty to zero when tripped.
   *
   * PARAMETERS
   * duty - requested output in [-1, 1].
   *
   * RETURNS
   * Duty command after limit switch enforcement.
   */
  private double applyLimit(double duty) {
    Boolean fwdClosed = readLimit(fwdLimit);
    if (Boolean.TRUE.equals(fwdClosed) && duty > 0.0) {
      return 0.0;
    }
    Boolean revClosed = readLimit(revLimit);
    if (Boolean.TRUE.equals(revClosed) && duty < 0.0) {
      return 0.0;
    }
    return duty;
  }
}

