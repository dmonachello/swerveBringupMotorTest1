package frc.robot.devices.ctre;

import com.ctre.phoenix6.controls.SolidColor;
import com.ctre.phoenix6.hardware.CANdle;
import com.ctre.phoenix6.signals.RGBWColor;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceDslSupport;
import frc.robot.devices.DeviceActionRequest;
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
  private final java.util.List<DigitalInput> limitInputs = new java.util.ArrayList<>();
  private CANdle device;
  private boolean testOn = false;
  private final SolidColor testColor = new SolidColor(0, 7);
  private static final int COLOR_COMPONENT_OFF = 0;
  private static final int COLOR_COMPONENT_RED = 0;
  private static final int COLOR_COMPONENT_GREEN = 128;
  private static final int COLOR_COMPONENT_BLUE = 255;

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
      BringupUtil.claimDeviceInstance(this);
      initLimitInputs();
      return;
    }
    initLimitInputs();
    if (!BringupUtil.claimDeviceInstance(this)) {
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
    BringupUtil.releaseDeviceInstance(this);
    BringupUtil.closeInputs(limitInputs);
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
    RGBWColor color = testOn
        ? new RGBWColor(COLOR_COMPONENT_OFF, COLOR_COMPONENT_OFF, COLOR_COMPONENT_OFF)
        : new RGBWColor(COLOR_COMPONENT_RED, COLOR_COMPONENT_GREEN, COLOR_COMPONENT_BLUE);
    device.setControl(testColor.withColor(color));
    testOn = !testOn;
  }

  /**
   * NAME
   * applyDeviceAction
   *
   * SYNOPSIS
   * Apply a device action command to the CANdle.
   *
   * RETURNS
   * True when the action is supported and applied.
   */
  @Override
  public boolean applyDeviceAction(DeviceActionRequest request) {
    if (request == null) {
      return false;
    }
    ensureCreated();
    if (device == null) {
      return false;
    }
    if (request.isAction(DeviceActionRequest.ACTION_TOGGLE_LED)) {
      runTest();
      return true;
    }
    if (request.isAction(DeviceActionRequest.ACTION_SET_COLOR)) {
      if (!request.isSolidPattern()) {
        return false;
      }
      DeviceActionRequest.RgbColor color = request.color;
      if (color == null) {
        return false;
      }
      int red = DeviceActionRequest.scaleComponent(color.red, request.brightness);
      int green = DeviceActionRequest.scaleComponent(color.green, request.brightness);
      int blue = DeviceActionRequest.scaleComponent(color.blue, request.brightness);
      RGBWColor rgb = new RGBWColor(red, green, blue);
      device.setControl(testColor.withColor(rgb));
      return true;
    }
    return false;
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

  @Override
  public Object readDslSignal(String signalName) {
    return DeviceDslSupport.readLimitSwitchSignal(this, signalName);
  }

  @Override
  public boolean writeDslSignal(String signalName, double value) {
    return false;
  }

  @Override
  public boolean clearDslSignal(String signalName) {
    return false;
  }

  @Override
  public boolean isDslWritableValueInRange(String signalName, double value) {
    return true;
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
