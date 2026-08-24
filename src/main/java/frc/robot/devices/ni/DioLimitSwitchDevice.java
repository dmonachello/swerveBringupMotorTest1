package frc.robot.devices.ni;

import edu.wpi.first.wpilibj.DigitalInput;
import edu.wpi.first.wpilibj.Timer;
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
  private static final double TIME_NONE = -1.0;
  private static final int TRANSITIONS_NONE = 0;
  private static final int TRANSITIONS_PARTIAL = 1;
  private static final int TRANSITIONS_PROVEN = 2;

  private final int dioChannel;
  private final String label;
  private final boolean invert;
  private DigitalInput input;
  private boolean created;
  private Boolean lastObservedClosed;
  private double lastChangeTimestampSec = TIME_NONE;
  private int transitionCountSinceActivate = TRANSITIONS_NONE;

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
    lastObservedClosed = null;
    lastChangeTimestampSec = TIME_NONE;
    transitionCountSinceActivate = TRANSITIONS_NONE;
  }

  @Override
  public void close() {
    BringupUtil.releaseSharedDioInput(input);
    input = null;
    created = false;
    lastObservedClosed = null;
    lastChangeTimestampSec = TIME_NONE;
    transitionCountSinceActivate = TRANSITIONS_NONE;
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
    Boolean closed = BringupUtil.readLimitInput(input, invert);
    double nowSec = Timer.getFPGATimestamp();
    updateTransitionTracking(closed, nowSec);
    LimitsAttachment limits = new LimitsAttachment();
    LimitsAttachment.LimitSwitchState state = new LimitsAttachment.LimitSwitchState();
    state.label = label;
    state.dio = dioChannel;
    state.invert = invert;
    state.closed = closed;
    state.lastChangeSec = lastChangeTimestampSec >= 0.0 ? nowSec - lastChangeTimestampSec : null;
    state.transitionCountSinceActivate = transitionCountSinceActivate;
    state.changedSinceActivate = transitionCountSinceActivate > TRANSITIONS_NONE;
    state.proofState = resolveProofState(closed);
    limits.switches.add(state);
    snap.addAttachment(limits);
    return snap;
  }

  @Override
  public Object readDslSignal(String signalName) {
    return DeviceDslSupport.readLimitSwitchSignal(this, signalName);
  }

  /**
   * NAME
   *   updateTransitionTracking - Record transition state for the current activation session.
   *
   * PARAMETERS
   *   closed - current logical switch state.
   *   nowSec - current FPGA timestamp.
   */
  private void updateTransitionTracking(Boolean closed, double nowSec) {
    if (closed == null) {
      return;
    }
    if (lastObservedClosed == null) {
      lastObservedClosed = closed;
      return;
    }
    if (!closed.equals(lastObservedClosed)) {
      transitionCountSinceActivate++;
      lastChangeTimestampSec = nowSec;
      lastObservedClosed = closed;
    }
  }

  /**
   * NAME
   *   resolveProofState - Summarize behavioral proof state for the current session.
   *
   * PARAMETERS
   *   closed - current logical switch state.
   *
   * RETURNS
   *   One shared operator-facing proof token.
   */
  private String resolveProofState(Boolean closed) {
    if (!created || closed == null) {
      return LimitsAttachment.PROOF_STATE_UNKNOWN;
    }
    if (transitionCountSinceActivate >= TRANSITIONS_PROVEN) {
      return LimitsAttachment.PROOF_STATE_PROVEN;
    }
    if (transitionCountSinceActivate >= TRANSITIONS_PARTIAL) {
      return LimitsAttachment.PROOF_STATE_PARTIAL;
    }
    return LimitsAttachment.PROOF_STATE_UNPROVEN;
  }
}
