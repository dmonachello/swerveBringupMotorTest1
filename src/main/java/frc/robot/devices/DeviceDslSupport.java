package frc.robot.devices;

import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
import frc.robot.tests.dsl.DslSignalRegistry;

/**
 * NAME
 *   DeviceDslSupport - Shared helpers for the DeviceUnit DSL runtime contract.
 *
 * DESCRIPTION
 *   Centralizes the common read/write/clear/range behavior used by multiple
 *   device implementations so each concrete device only needs a small template
 *   method block when participating in the DSL runtime.
 */
public final class DeviceDslSupport {
  private static final double MOTOR_OUTPUT_MIN = -1.0;
  private static final double MOTOR_OUTPUT_MAX = 1.0;
  private static final int LIMIT_INDEX_ZERO = 0;

  private DeviceDslSupport() {}

  public static Object readMotorSignal(DeviceUnit device, String signalName) {
    if (device == null || signalName == null) {
      return null;
    }
    if (DslSignalRegistry.SIGNAL_POSITION.equals(signalName)) {
      return device.getPositionRotations();
    }
    DeviceSnapshot snapshot = device.snapshot();
    RevMotorAttachment rev = snapshot.getAttachment(RevMotorAttachment.class);
    CtreMotorAttachment ctre = snapshot.getAttachment(CtreMotorAttachment.class);
    if (DslSignalRegistry.SIGNAL_CURRENT.equals(signalName)) {
      if (rev != null) {
        return rev.motorCurrentA;
      }
      if (ctre != null) {
        return ctre.motorCurrentA;
      }
    }
    if (DslSignalRegistry.SIGNAL_TEMPERATURE.equals(signalName)) {
      if (rev != null) {
        return rev.tempC;
      }
      if (ctre != null) {
        return ctre.tempC;
      }
    }
    if (DslSignalRegistry.SIGNAL_VELOCITY.equals(signalName)) {
      if (rev != null) {
        return rev.velRpm;
      }
      if (ctre != null) {
        return ctre.velRpm;
      }
    }
    return null;
  }

  public static Object readLimitSwitchSignal(DeviceUnit device, String signalName) {
    if (device == null
        || signalName == null
        || !DslSignalRegistry.SIGNAL_PRESSED.equals(signalName)) {
      return null;
    }
    DeviceSnapshot snapshot = device.snapshot();
    LimitsAttachment limits = snapshot.getAttachment(LimitsAttachment.class);
    if (limits == null || limits.switches == null || limits.switches.isEmpty()) {
      return null;
    }
    LimitsAttachment.LimitSwitchState state = limits.switches.get(LIMIT_INDEX_ZERO);
    return state != null && Boolean.TRUE.equals(state.closed);
  }

  public static Object readEncoderSignal(DeviceUnit device, String signalName) {
    if (device == null
        || signalName == null
        || !DslSignalRegistry.SIGNAL_POSITION.equals(signalName)) {
      return null;
    }
    return device.getPositionRotations();
  }

  public static boolean writeMotorSignal(DeviceUnit device, String signalName, double value) {
    if (device == null
        || signalName == null
        || !DslSignalRegistry.SIGNAL_OUTPUT.equals(signalName)) {
      return false;
    }
    device.setDuty(value);
    return true;
  }

  public static boolean clearFaultSignal(DeviceUnit device, String signalName) {
    if (device == null
        || signalName == null
        || !DslSignalRegistry.SIGNAL_FAULTS.equals(signalName)) {
      return false;
    }
    device.clearFaults();
    return true;
  }

  public static boolean isMotorWritableValueInRange(String signalName, double value) {
    if (signalName == null) {
      return false;
    }
    if (DslSignalRegistry.SIGNAL_OUTPUT.equals(signalName)) {
      return value >= MOTOR_OUTPUT_MIN && value <= MOTOR_OUTPUT_MAX;
    }
    return true;
  }
}
