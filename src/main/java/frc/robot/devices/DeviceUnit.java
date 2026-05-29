package frc.robot.devices;

import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.SnapshotDetail;
import frc.robot.registry.HasRegistrationHeader;

/**
 * NAME
 * DeviceUnit
 *
 * SYNOPSIS
 * Interface for a single hardware device slot in bringup.
 *
 * DESCRIPTION
 * Defines common identity, lifecycle, and optional actuator/sensor hooks used
 * by the bringup harness.
 */
public interface DeviceUnit extends HasRegistrationHeader {
  int getCanId();

  String getDeviceType();

  String getLabel();

  boolean isCreated();

  /**
   * NAME
   * ensureCreated
   *
   * SYNOPSIS
   * Ensure the underlying vendor device is created.
   *
   * SIDE EFFECTS
   * Allocates vendor resources and may touch hardware.
   */
  void ensureCreated();

  /**
   * NAME
   * close
   *
   * SYNOPSIS
   * Release vendor resources for this device.
   *
   * SIDE EFFECTS
   * May free device handles and stop communication.
   */
  void close();

  /**
   * NAME
   * clearFaults
   *
   * SYNOPSIS
   * Clear device fault status where supported.
   *
   * SIDE EFFECTS
   * Sends vendor-specific fault clear commands.
   */
  void clearFaults();

  /**
   * NAME
   * snapshot
   *
   * SYNOPSIS
   * Capture a diagnostic snapshot for reporting.
   *
   * RETURNS
   * A populated device snapshot for the report pipeline.
   */
  DeviceSnapshot snapshot();

  /**
   * NAME
   *   snapshot
   *
   * SYNOPSIS
   *   Capture a diagnostic snapshot with an explicit detail/cost target.
   *
   * PARAMETERS
   *   detail - desired snapshot detail level.
   *
   * RETURNS
   *   A populated device snapshot for the requested detail level.
   */
  default DeviceSnapshot snapshot(SnapshotDetail detail) {
    return snapshot();
  }

  /**
   * NAME
   * setDuty
   *
   * SYNOPSIS
   * Apply an open-loop duty request to a motor-like device.
   *
   * PARAMETERS
   * duty - requested output in [-1, 1].
   *
   * SIDE EFFECTS
   * Commands actuator output where supported.
   */
  default void setDuty(double duty) {}

  /**
   * NAME
   * applyDuty
   *
   * SYNOPSIS
   * Apply duty only when the device is created.
   *
   * PARAMETERS
   * duty - requested output in [-1, 1].
   *
   * SIDE EFFECTS
   * Calls setDuty for created devices.
   */
  default void applyDuty(double duty) {
    if (isCreated()) {
      setDuty(duty);
    }
  }

  /**
   * NAME
   * stop
   *
   * SYNOPSIS
   * Stop actuator output if applicable.
   *
   * SIDE EFFECTS
   * Commands device output to a safe idle state.
   */
  default void stop() {}

  default String getMotorModelOverride() {
    return null;
  }

  // Optional hooks for non-motor devices (no-op by default).
  /**
   * NAME
   * activate
   *
   * SYNOPSIS
   * Activate non-motor devices that require an explicit enable.
   *
   * SIDE EFFECTS
   * May start device-specific behavior.
   */
  default void activate() {}

  /**
   * NAME
   * deactivate
   *
   * SYNOPSIS
   * Deactivate non-motor devices that require an explicit disable.
   *
   * SIDE EFFECTS
   * May stop device-specific behavior.
   */
  default void deactivate() {}

  // Optional test hook for non-motor devices (no-op by default).
  /**
   * NAME
   * hasTest
   *
   * SYNOPSIS
   * Indicate whether this device exposes a custom test.
   *
   * RETURNS
   * True if runTest should be exposed to users.
   */
  default boolean hasTest() {
    return false;
  }

  /**
   * NAME
   * getTestName
   *
   * SYNOPSIS
   * Provide a display name for the device test.
   *
   * RETURNS
   * A short name or empty string when no test is available.
   */
  default String getTestName() {
    return "";
  }

  /**
   * NAME
   * runTest
   *
   * SYNOPSIS
   * Execute the device-specific test routine.
   *
   * SIDE EFFECTS
   * May move hardware or change device state.
   */
  default void runTest() {}

  /**
   * NAME
   * applyDeviceAction
   *
   * SYNOPSIS
   * Apply a device-specific action from a test definition.
   *
   * PARAMETERS
   * request - Parsed action request payload.
   *
   * RETURNS
   * True when the action was accepted and applied.
   */
  default boolean applyDeviceAction(DeviceActionRequest request) {
    return false;
  }

  // Optional encoder position in rotations (internal or external sensor).
  /**
   * NAME
   * getPositionRotations
   *
   * SYNOPSIS
   * Return an optional encoder position in rotations.
   *
   * RETURNS
   * Encoder position in rotations, or null if unavailable.
   */
  default Double getPositionRotations() {
    return null;
  }

  // Optional encoder position in rotations with source-specific handling.
  /**
   * NAME
   * getPositionRotations
   *
   * SYNOPSIS
   * Return an optional encoder position in rotations with extra context.
   *
   * PARAMETERS
   * encoderSource - logical source label for an external encoder.
   * countsPerRev - encoder counts per revolution for scaling.
   *
   * RETURNS
   * Encoder position in rotations, or null if unavailable.
   */
  default Double getPositionRotations(String encoderSource, Integer countsPerRev) {
    return getPositionRotations();
  }

  /**
   * NAME
   *   readDslSignal
   *
   * SYNOPSIS
   * Return a named DSL signal exposed by this device.
   *
   * PARAMETERS
   *   signalName - DSL signal name.
   *
   * RETURNS
   *   Signal value, or null when unsupported or unavailable.
   */
  default Object readDslSignal(String signalName) {
    return DeviceDslSupport.readMotorSignal(this, signalName);
  }

  /**
   * NAME
   *   writeDslSignal
   *
   * SYNOPSIS
   * Apply a writable DSL signal target on this device.
   *
   * PARAMETERS
   *   signalName - DSL signal name.
   *   value - Numeric value to apply.
   *
   * RETURNS
   *   True when the signal is supported and the value was applied.
   */
  default boolean writeDslSignal(String signalName, double value) {
    return DeviceDslSupport.writeMotorSignal(this, signalName, value);
  }

  /**
   * NAME
   *   clearDslSignal
   *
   * SYNOPSIS
   * Clear a clearable DSL signal on this device.
   *
   * PARAMETERS
   *   signalName - DSL signal name.
   *
   * RETURNS
   *   True when the signal is supported and the clear was applied.
   */
  default boolean clearDslSignal(String signalName) {
    return DeviceDslSupport.clearFaultSignal(this, signalName);
  }

  /**
   * NAME
   *   isDslWritableValueInRange
   *
   * SYNOPSIS
   * Validate a numeric write value for a DSL signal before applying it.
   *
   * PARAMETERS
   *   signalName - DSL signal name.
   *   value - Numeric value to validate.
   *
   * RETURNS
   *   True when the value is acceptable for the writable signal.
   */
  default boolean isDslWritableValueInRange(String signalName, double value) {
    return DeviceDslSupport.isMotorWritableValueInRange(signalName, value);
  }
}
