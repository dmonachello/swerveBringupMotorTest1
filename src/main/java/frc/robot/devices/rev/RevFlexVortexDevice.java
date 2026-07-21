package frc.robot.devices.rev;

import frc.robot.BringupPrinter;
import com.revrobotics.PersistMode;
import com.revrobotics.ResetMode;
import com.revrobotics.spark.SparkFlex;
import com.revrobotics.spark.SparkLowLevel.MotorType;
import com.revrobotics.spark.config.SparkFlexConfig;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.manufacturers.rev.diag.RevSparkFlexReader;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.diag.snapshots.SnapshotDetail;
import frc.robot.registry.RegistrationHeader;
import frc.robot.telemetry.SampledSignalNames;
import frc.robot.telemetry.SampledSignalRegistration;
import edu.wpi.first.wpilibj.DigitalInput;
import java.util.List;

/**
 * NAME
 * RevFlexVortexDevice
 *
 * SYNOPSIS
 * Device wrapper for a REV Spark Flex controlling a Vortex/FLEX.
 *
 * DESCRIPTION
 * Provides bringup lifecycle, telemetry, and limit switch handling for Spark
 * Flex devices.
 */
public final class RevFlexVortexDevice implements DeviceUnit {
  private static final long CURRENT_WINDOW_MS = 500L;
  private static final double CURRENT_NONZERO_THRESHOLD_A = 0.05;
  private static final String SNAPSHOT_NOTE_NOT_ADDED = "not added";
  private static final String SNAPSHOT_NOTE_CLOSED = "closed";
  private static final String SNAPSHOT_NOTE_READ_FAILED_PREFIX = "read failed: ";
  private static final String ACTION_CLOSE = "close";
  private static final String ACTION_RECREATE = "recreate";
  private static final String ACTION_SNAPSHOT = "snapshot";
  private static final String ACTION_SAMPLED_CURRENT = "sampledCurrent";
  private static final String WARNING_CLOSE_FAILED_PREFIX =
      "Warning: SparkFlex CAN ";
  private static final String WARNING_CLOSE_FAILED_DURING = " close failed during ";
  private static final String WARNING_CLOSE_FAILED_SEPARATOR = ": ";
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "SparkFlex Vortex",
      "REV",
      "FLEX",
      "REVLib",
      "Team",
      "2026-03-02",
      "Spark Flex controlling a Vortex motor.");
  private final int canId;
  private final String label;
  private final String motorModelOverride;
  private final BringupUtil.LimitConfig limitConfig;
  private final java.util.List<DigitalInput> limitInputs = new java.util.ArrayList<>();
  private SparkFlex device;
  private boolean closed = false;

  /**
   * NAME
   * RevFlexVortexDevice
   *
   * SYNOPSIS
   * Construct a Spark Flex device wrapper.
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
  public RevFlexVortexDevice(
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
    return "FLEX";
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

  /**
   * NAME
   *   getActiveHandleForProbe - Return the current runtime-owned SparkFlex handle.
   *
   * RETURNS
   *   Active SparkFlex instance, or null when the runtime has not created it.
   */
  public SparkFlex getActiveHandleForProbe() {
    return device != null && !closed ? device : null;
  }

  @Override
  public boolean isCreated() {
    return device != null && !closed;
  }

  /**
   * NAME
   * ensureCreated
   *
   * SYNOPSIS
   * Construct and configure the Spark Flex device if needed.
   *
   * SIDE EFFECTS
   * Allocates a vendor device and configures it asynchronously.
   */
  @Override
  public void ensureCreated() {
    if (device != null && !closed) {
      BringupUtil.claimDeviceInstance(this);
      initLimitInputs();
      return;
    }
    initLimitInputs();
    if (device != null) {
      if (!releaseDeviceHandle(ACTION_RECREATE)) {
        return;
      }
    }
    if (!BringupUtil.claimDeviceInstance(this)) {
      return;
    }
    device = new SparkFlex(canId, MotorType.kBrushless);
    closed = false;
    device.pauseFollowerMode();
    device.configure(
        new SparkFlexConfig(),
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
    if (!releaseDeviceHandle(ACTION_CLOSE)) {
      return;
    }
    BringupUtil.closeInputs(limitInputs);
  }

  /**
   * NAME
   * clearFaults
   *
   * SYNOPSIS
   * Clear faults on the Spark Flex.
   *
   * SIDE EFFECTS
   * Sends vendor fault-clear commands.
   */
  @Override
  public void clearFaults() {
    if (device != null) {
      try {
        device.clearFaults();
      } catch (IllegalStateException ex) {
        handleClosed("clearFaults", ex);
      }
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
   * Commands motor output via the vendor API. Closed-handle failures do not
   * auto-recreate the vendor object here because lifecycle ownership must
   * remain centralized in explicit activation/instantiation paths.
   */
  @Override
  public void setDuty(double duty) {
    if (device != null) {
      try {
        device.set(applyLimit(duty));
      } catch (IllegalStateException ex) {
        handleClosed("set", ex);
      }
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
      try {
        device.stopMotor();
      } catch (IllegalStateException ex) {
        handleClosed("stop", ex);
      }
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

  private void handleClosed(String action, IllegalStateException ex) {
    BringupPrinter.enqueue(
        "Warning: SparkFlex CAN " + canId + " closed during " + action + "; recreating.");
    releaseDeviceHandle(action);
  }

  private boolean releaseDeviceHandle(String action) {
    if (device == null) {
      closed = true;
      BringupUtil.releaseDeviceInstance(this);
      return true;
    }
    String warningPrefix =
        WARNING_CLOSE_FAILED_PREFIX
            + canId
            + WARNING_CLOSE_FAILED_DURING
            + action
            + WARNING_CLOSE_FAILED_SEPARATOR;
    if (!BringupUtil.closeIfPossible(device, warningPrefix)) {
      closed = false;
      return false;
    }
    device = null;
    closed = true;
    BringupUtil.releaseDeviceInstance(this);
    return true;
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
    return snapshot(SnapshotDetail.FULL);
  }

  @Override
  public DeviceSnapshot snapshot(SnapshotDetail detail) {
    if (device == null || closed) {
      return snapshotUnavailable(SNAPSHOT_NOTE_NOT_ADDED);
    }
    try {
      DeviceSnapshot snap = RevSparkFlexReader.read(device, canId, detail);
      snap.deviceType = getDeviceType();
      snap.label = label;
      addLimitAttachment(snap);
      return snap;
    } catch (IllegalStateException ex) {
      handleClosed(ACTION_SNAPSHOT, ex);
      return snapshotUnavailable(SNAPSHOT_NOTE_CLOSED);
    } catch (RuntimeException ex) {
      return snapshotUnavailable(SNAPSHOT_NOTE_READ_FAILED_PREFIX + ex.getMessage());
    }
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

  @Override
  public List<SampledSignalRegistration> getSampledSignalRegistrations() {
    return List.of(
        new SampledSignalRegistration(
            SampledSignalNames.CURRENT_ACTUAL,
            CURRENT_WINDOW_MS,
            CURRENT_NONZERO_THRESHOLD_A,
            () -> {
              if (device == null || closed) {
                return null;
              }
              try {
                return device.getOutputCurrent();
              } catch (IllegalStateException ex) {
                handleClosed(ACTION_SAMPLED_CURRENT, ex);
                return null;
              }
            }));
  }

  private DeviceSnapshot snapshotUnavailable(String note) {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = "REV";
    snap.deviceType = getDeviceType();
    snap.canId = canId;
    snap.present = false;
    snap.note = note;
    snap.label = label;
    addLimitAttachment(snap);
    return snap;
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
    if (isAnyLimitClosed()) {
      return 0.0;
    }
    return duty;
  }

  private boolean isAnyLimitClosed() {
    for (int i = 0; i < limitConfig.switches.size(); i++) {
      if (Boolean.TRUE.equals(readLimit(i))) {
        return true;
      }
    }
    return false;
  }
}

