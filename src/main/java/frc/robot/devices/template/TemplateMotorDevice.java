package frc.robot.devices.template;

import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.BringupUtil;
import edu.wpi.first.wpilibj.DigitalInput;

/**
 * NAME
 * TemplateMotorDevice
 *
 * SYNOPSIS
 * Placeholder device implementation for new vendor integrations.
 *
 * DESCRIPTION
 * Provides a minimal CAN device wrapper with limit switch wiring to illustrate
 * how to integrate a vendor SDK into the bringup framework.
 */
public final class TemplateMotorDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "Template Motor",
      "TEMPLATE",
      "TEMPLATE_MOTOR",
      "Template SDK",
      "Team",
      "2026-03-02",
      "Clone this device when adding a new vendor.");
  private final int canId;
  private final String label;
  private final String deviceType;
  private final BringupUtil.LimitConfig limitConfig;
  private DigitalInput fwdLimit;
  private DigitalInput revLimit;
  private boolean created = false;

  /**
   * NAME
   * TemplateMotorDevice
   *
   * SYNOPSIS
   * Create a template device wrapper with optional limit switch config.
   *
   * PARAMETERS
   * canId - CAN device ID for the placeholder device.
   * label - human-readable label for reporting.
   * deviceType - device type token used in reports.
   * limitConfig - optional DIO limit switch configuration.
   *
   * SIDE EFFECTS
   * Initializes DIO inputs when limit switches are configured.
   */
  public TemplateMotorDevice(
      int canId,
      String label,
      String deviceType,
      BringupUtil.LimitConfig limitConfig) {
    this.canId = canId;
    this.label = label;
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

  @Override
  public boolean isCreated() {
    return created;
  }

  /**
   * NAME
   * ensureCreated
   *
   * SYNOPSIS
   * Mark the template device as created.
   *
   * DESCRIPTION
   * Placeholder behavior that mirrors SDK initialization steps.
   *
   * SIDE EFFECTS
   * Updates internal created state.
   */
  @Override
  public void ensureCreated() {
    created = true;
  }

  /**
   * NAME
   * close
   *
   * SYNOPSIS
   * Release DIO resources and clear created state.
   *
   * SIDE EFFECTS
   * Closes DIO inputs and resets internal references.
   */
  @Override
  public void close() {
    created = false;
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
   * Clear fault state on the device.
   *
   * DESCRIPTION
   * Placeholder for vendor SDK fault-clearing calls.
   */
  @Override
  public void clearFaults() {
  }

  /**
   * NAME
   * setDuty
   *
   * SYNOPSIS
   * Apply open-loop duty to the device.
   *
   * PARAMETERS
   * duty - requested output in [-1, 1].
   *
   * DESCRIPTION
   * Placeholder for vendor SDK motor output.
   */
  @Override
  public void setDuty(double duty) {
  }

  /**
   * NAME
   * stop
   *
   * SYNOPSIS
   * Stop the device output.
   *
   * DESCRIPTION
   * Placeholder for vendor SDK stop behavior.
   */
  @Override
  public void stop() {
  }

  /**
   * NAME
   * activate
   *
   * SYNOPSIS
   * Activate the template device.
   *
   * DESCRIPTION
   * Uses ensureCreated as the activation hook.
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
   * Deactivate the template device.
   *
   * DESCRIPTION
   * Uses stop as the deactivation hook.
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
   * Build a snapshot describing device presence and limits.
   *
   * RETURNS
   * A snapshot populated with template metadata and limit attachment data.
   */
  @Override
  public DeviceSnapshot snapshot() {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = "TEMPLATE";
    snap.deviceType = deviceType;
    snap.canId = canId;
    snap.label = label;
    if (created) {
      snap.present = true;
      snap.note = "template device (no SDK)";
    } else {
      snap.present = false;
      snap.note = "not added";
    }
    addLimitAttachment(snap);
    return snap;
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
}
