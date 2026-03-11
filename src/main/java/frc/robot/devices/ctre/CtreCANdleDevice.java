package frc.robot.devices.ctre;

import com.ctre.phoenix6.controls.SolidColor;
import com.ctre.phoenix6.hardware.CANdle;
import com.ctre.phoenix6.signals.RGBWColor;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.manufacturers.ctre.diag.CtreCandleReader;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.registry.RegistrationHeader;
import edu.wpi.first.wpilibj.DigitalInput;

/**
 * NAME
 * CtreCANdleDevice
 *
 * SYNOPSIS
 * Device wrapper for a CTRE CANdle LED controller.
 *
 * DESCRIPTION
 * Provides bringup lifecycle, LED test toggling, and limit switch handling for
 * CANdle devices.
 */
public final class CtreCANdleDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "CANdle",
      "CTRE",
      "CANdle",
      "Phoenix 6",
      "Team",
      "2026-03-02",
      "CTRE CANdle LED controller.");
  private final int canId;
  private final String label;
  private final BringupUtil.LimitConfig limitConfig;
  private DigitalInput fwdLimit;
  private DigitalInput revLimit;
  private CANdle device;
  private boolean testOn = false;
  private final SolidColor testColor = new SolidColor(0, 7);

  /**
   * NAME
   * CtreCANdleDevice
   *
   * SYNOPSIS
   * Construct a CANdle device wrapper.
   *
   * PARAMETERS
   * canId - CAN ID of the CANdle.
   * label - human-readable label for reporting.
   * limitConfig - optional limit switch configuration.
   *
   * SIDE EFFECTS
   * Initializes DIO inputs when limit switches are configured.
   */
  public CtreCANdleDevice(int canId, String label, BringupUtil.LimitConfig limitConfig) {
    this.canId = canId;
    this.label = label;
    this.limitConfig = limitConfig != null ? limitConfig : new BringupUtil.LimitConfig();
    initLimitInputs();
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return "CANdle";
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
    return device != null;
  }

  /**
   * NAME
   * ensureCreated
   *
   * SYNOPSIS
   * Construct the CANdle device if not already created.
   *
   * SIDE EFFECTS
   * Allocates a vendor device and starts CAN communication.
   */
  @Override
  public void ensureCreated() {
    if (device != null) {
      return;
    }
    device = new CANdle(canId);
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
   * Clear sticky faults on the CANdle.
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
   * hasTest
   *
   * SYNOPSIS
   * Indicate that the device exposes a LED toggle test.
   *
   * RETURNS
   * True for CANdle devices.
   */
  @Override
  public boolean hasTest() {
    return true;
  }

  /**
   * NAME
   * getTestName
   *
   * SYNOPSIS
   * Return the test command name for the LED toggle.
   *
   * RETURNS
   * "toggle_led".
   */
  @Override
  public String getTestName() {
    return "toggle_led";
  }

  /**
   * NAME
   * runTest
   *
   * SYNOPSIS
   * Toggle the CANdle LED color.
   *
   * SIDE EFFECTS
   * Sends a control command to change LED output.
   */
  @Override
  public void runTest() {
    ensureCreated();
    if (device == null) {
      return;
    }
    RGBWColor color = testOn ? new RGBWColor(0, 0, 0) : new RGBWColor(0, 128, 255);
    device.setControl(testColor.withColor(color));
    testOn = !testOn;
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
      snap.deviceType = getDeviceType();
      snap.canId = canId;
      snap.present = false;
      snap.note = "not added";
      snap.label = label;
      addLimitAttachment(snap);
      return snap;
    }
    DeviceSnapshot snap = CtreCandleReader.read(device, canId);
    snap.label = label;
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
