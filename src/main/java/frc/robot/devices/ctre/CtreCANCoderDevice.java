package frc.robot.devices.ctre;

import com.ctre.phoenix6.hardware.CANcoder;
import edu.wpi.first.units.Units;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.manufacturers.ctre.diag.CtreCANCoderReader;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.registry.RegistrationHeader;
import edu.wpi.first.wpilibj.DigitalInput;

/**
 * NAME
 * CtreCANCoderDevice
 *
 * SYNOPSIS
 * Device wrapper for a CTRE CANCoder.
 *
 * DESCRIPTION
 * Provides bringup lifecycle, telemetry, and limit switch handling for CTRE
 * CAN-based encoders.
 */
public final class CtreCANCoderDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "CANCoder",
      "CTRE",
      "CANCoder",
      "Phoenix 6",
      "Team",
      "2026-03-02",
      "CTRE CAN-based absolute encoder.");
  private final int canId;
  private final String label;
  private final BringupUtil.LimitConfig limitConfig;
  private final java.util.List<DigitalInput> limitInputs = new java.util.ArrayList<>();
  private CANcoder device;

  /**
   * NAME
   * CtreCANCoderDevice
   *
   * SYNOPSIS
   * Construct a CANCoder device wrapper.
   *
   * PARAMETERS
   * canId - CAN ID of the encoder.
   * label - human-readable label for reporting.
   * limitConfig - optional limit switch configuration.
   *
   * SIDE EFFECTS
   * Initializes DIO inputs when limit switches are configured.
   */
  public CtreCANCoderDevice(int canId, String label, BringupUtil.LimitConfig limitConfig) {
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
    return "CANCoder";
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
   * Construct the CANCoder device if not already created.
   *
   * SIDE EFFECTS
   * Allocates a vendor device and starts CAN communication.
   */
  @Override
  public void ensureCreated() {
    if (device != null) {
      BringupUtil.claimDeviceInstance(this);
      initLimitInputs();
      return;
    }
    initLimitInputs();
    if (!BringupUtil.claimDeviceInstance(this)) {
      return;
    }
    device = new CANcoder(canId);
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
    BringupUtil.releaseDeviceInstance(this);
    BringupUtil.closeInputs(limitInputs);
  }

  /**
   * NAME
   * clearFaults
   *
   * SYNOPSIS
   * Clear sticky faults on the CANCoder.
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
    DeviceSnapshot snap = CtreCANCoderReader.read(device, canId);
    snap.label = label;
    addLimitAttachment(snap);
    return snap;
  }

  /**
   * NAME
   * getPositionRotations
   *
   * SYNOPSIS
   * Return the absolute position in rotations.
   *
   * RETURNS
   * Absolute position in rotations, or null on read error or when not created.
   */
  @Override
  public Double getPositionRotations() {
    if (device == null) {
      return null;
    }
    try {
      return device.getAbsolutePosition().getValue().in(Units.Rotations);
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
    BringupUtil.ensureDioInputs(limitInputs, limitConfig.switches);
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
    if (!limitConfig.hasSwitches()) {
      return;
    }
    LimitsAttachment limits = new LimitsAttachment();
    for (int i = 0; i < limitConfig.switches.size(); i++) {
      BringupUtil.LimitSwitchConfig spec = limitConfig.switches.get(i);
      LimitsAttachment.LimitSwitchState state = new LimitsAttachment.LimitSwitchState();
      if (spec != null) {
        state.label = spec.label;
        state.dio = spec.dio;
        state.invert = spec.invert;
      }
      state.closed = readLimit(i);
      limits.switches.add(state);
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
  private Boolean readLimit(int index) {
    if (index < 0 || index >= limitConfig.switches.size()) {
      return null;
    }
    BringupUtil.LimitSwitchConfig spec = limitConfig.switches.get(index);
    DigitalInput input = index < limitInputs.size() ? limitInputs.get(index) : null;
    if (spec == null) {
      return null;
    }
    return BringupUtil.readLimitInput(input, spec.invert);
  }
}
