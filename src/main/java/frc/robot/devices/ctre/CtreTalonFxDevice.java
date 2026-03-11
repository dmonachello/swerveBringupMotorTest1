package frc.robot.devices.ctre;

import com.ctre.phoenix6.hardware.TalonFX;
import edu.wpi.first.units.Units;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.manufacturers.ctre.diag.CtreTalonFxReader;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.registry.RegistrationHeader;
import edu.wpi.first.wpilibj.DigitalInput;

/**
 * NAME
 * CtreTalonFxDevice
 *
 * SYNOPSIS
 * Device wrapper for a CTRE TalonFX-based motor (Kraken/Falcon).
 *
 * DESCRIPTION
 * Provides bringup lifecycle, telemetry, and limit switch handling for TalonFX
 * motors using Phoenix 6.
 */
public final class CtreTalonFxDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "TalonFX",
      "CTRE",
      "TalonFX",
      "Phoenix 6",
      "Team",
      "2026-03-02",
      "TalonFX-based motor controller (Kraken/Falcon).");
  private final int canId;
  private final String label;
  private final String motorModelOverride;
  private final String deviceType;
  private final BringupUtil.LimitConfig limitConfig;
  private DigitalInput fwdLimit;
  private DigitalInput revLimit;
  private TalonFX device;

  /**
   * NAME
   * CtreTalonFxDevice
   *
   * SYNOPSIS
   * Construct a TalonFX device wrapper.
   *
   * PARAMETERS
   * canId - CAN ID of the motor controller.
   * label - human-readable label for reporting.
   * motorModelOverride - optional motor model override for spec lookup.
   * deviceType - device type token (e.g., KRAKEN/FALCON).
   * limitConfig - optional limit switch configuration.
   *
   * SIDE EFFECTS
   * Initializes DIO inputs when limit switches are configured.
   */
  public CtreTalonFxDevice(
      int canId,
      String label,
      String motorModelOverride,
      String deviceType,
      BringupUtil.LimitConfig limitConfig) {
    this.canId = canId;
    this.label = label;
    this.motorModelOverride = motorModelOverride;
    this.deviceType = deviceType;
    this.limitConfig = limitConfig != null ? limitConfig : new BringupUtil.LimitConfig();
    initLimitInputs();
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return deviceType;
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
   * Construct the TalonFX device if not already created.
   *
   * SIDE EFFECTS
   * Allocates a vendor device and starts CAN communication.
   */
  @Override
  public void ensureCreated() {
    if (device != null) {
      return;
    }
    device = new TalonFX(canId);
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
   * Clear sticky faults on the TalonFX.
   *
   * SIDE EFFECTS
   * Sends vendor fault-clear commands.
   */
  @Override
  public void clearFaults() {
    if (device != null) {
      device.clearStickyFaults();
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
      snap.vendor = "CTRE";
      snap.deviceType = deviceType;
      snap.canId = canId;
      snap.present = false;
      snap.note = "not added";
      snap.label = label;
      addLimitAttachment(snap);
      return snap;
    }
    DeviceSnapshot snap = CtreTalonFxReader.read(device, deviceType, canId);
    snap.label = label;
    addLimitAttachment(snap);
    return snap;
  }

  /**
   * NAME
   * getPositionRotations
   *
   * SYNOPSIS
   * Return the integrated sensor position in rotations.
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
      return device.getPosition().getValue().in(Units.Rotations);
    } catch (Exception ex) {
      return null;
    }
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
