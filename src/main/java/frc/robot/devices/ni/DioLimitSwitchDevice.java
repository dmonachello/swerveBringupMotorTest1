package frc.robot.devices.ni;

import edu.wpi.first.wpilibj.DigitalInput;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceDslSupport;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.registry.RegistrationHeader;

/**
 * NAME
 *   DioLimitSwitchDevice - Standalone DeviceUnit for a DIO-backed limit switch.
 *
 * DESCRIPTION
 *   Exposes a configured DIO limit switch through the standard bringup device
 *   lifecycle so DSL tests can reference it directly by label.
 */
public final class DioLimitSwitchDevice implements DeviceUnit {
  public static final String DEVICE_TYPE = "limitSwitch";
  public static final String SIGNAL_PRESSED = "pressed";
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "Limit Switch",
      "NI",
      DEVICE_TYPE,
      "WPILib",
      "Team",
      "2026-05-10",
      "Standalone DIO limit switch wrapper.");

  private static final String VENDOR = "NI";
  private static final String NOTE_VIRTUAL = "dioInput";

  private final int dioChannel;
  private final String label;
  private final boolean invert;
  private DigitalInput input;
  private boolean created;

  public DioLimitSwitchDevice(int dioChannel, String label, boolean invert) {
    this.dioChannel = dioChannel;
    this.label = label;
    this.invert = invert;
  }

  @Override
  public int getCanId() {
    return dioChannel;
  }

  @Override
  public String getDeviceType() {
    return DEVICE_TYPE;
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

  @Override
  public void ensureCreated() {
    if (created) {
      return;
    }
    input = BringupUtil.acquireSharedDioInput(dioChannel);
    created = true;
  }

  @Override
  public void close() {
    BringupUtil.releaseSharedDioInput(input);
    input = null;
    created = false;
  }

  @Override
  public void clearFaults() {}

  @Override
  public DeviceSnapshot snapshot() {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = VENDOR;
    snap.deviceType = DEVICE_TYPE;
    snap.canId = dioChannel;
    snap.label = label;
    snap.present = created;
    snap.note = NOTE_VIRTUAL;
    LimitsAttachment limits = new LimitsAttachment();
    LimitsAttachment.LimitSwitchState state = new LimitsAttachment.LimitSwitchState();
    state.label = label;
    state.dio = dioChannel;
    state.invert = invert;
    state.closed = BringupUtil.readLimitInput(input, invert);
    limits.switches.add(state);
    snap.addAttachment(limits);
    return snap;
  }

  @Override
  public Object readDslSignal(String signalName) {
    return DeviceDslSupport.readLimitSwitchSignal(this, signalName);
  }
}
