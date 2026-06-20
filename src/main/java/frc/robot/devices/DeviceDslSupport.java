package frc.robot.devices;

import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.ctre.diag.PdpStatusAttachment;
import frc.robot.manufacturers.rev.diag.PdhStatusAttachment;
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
  private static final String CHANNEL_PREFIX = "channel";
  private static final String CHANNEL_CURRENT_SUFFIX = "_current";
  private static final String CHANNEL_FAULT_SUFFIX = "_fault";
  private static final String CHANNEL_STICKY_FAULT_SUFFIX = "_sticky_fault";

  private DeviceDslSupport() {}

  public static Object readMotorSignal(DeviceUnit device, String signalName) {
    if (device == null || signalName == null) {
      return null;
    }
    if (isMotorPositionSignal(signalName)) {
      return device.getPositionRotations();
    }
    DeviceSnapshot snapshot = device.snapshot();
    RevMotorAttachment rev = snapshot.getAttachment(RevMotorAttachment.class);
    CtreMotorAttachment ctre = snapshot.getAttachment(CtreMotorAttachment.class);
    if (isMotorCurrentSignal(signalName)) {
      if (rev != null) {
        return rev.motorCurrentA;
      }
      if (ctre != null) {
        return ctre.motorCurrentA;
      }
    }
    if (isMotorTemperatureSignal(signalName)) {
      if (rev != null) {
        return rev.tempC;
      }
      if (ctre != null) {
        return ctre.tempC;
      }
    }
    if (isMotorVelocitySignal(signalName)) {
      if (rev != null) {
        return rev.velRpm;
      }
      if (ctre != null) {
        return ctre.velRpm;
      }
    }
    if (DslSignalRegistry.SIGNAL_OUTPUT_PERCENT_CMD.equals(signalName)) {
      if (rev != null) {
        return rev.cmdDuty;
      }
      if (ctre != null) {
        return ctre.cmdDuty;
      }
      return null;
    }
    if (DslSignalRegistry.SIGNAL_OUTPUT_PERCENT_APPLIED.equals(signalName)) {
      if (rev != null) {
        return rev.appliedDuty;
      }
      if (ctre != null) {
        return ctre.appliedDuty;
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
        || !isEncoderPositionSignal(signalName)) {
      return null;
    }
    return device.getPositionRotations();
  }

  public static Object readPowerDistributionSignal(DeviceUnit device, String signalName) {
    if (device == null || signalName == null) {
      return null;
    }
    DeviceSnapshot snapshot = device.snapshot();
    PdhStatusAttachment pdh = snapshot.getAttachment(PdhStatusAttachment.class);
    PdpStatusAttachment pdp = snapshot.getAttachment(PdpStatusAttachment.class);
    if (DslSignalRegistry.SIGNAL_VOLTAGE.equals(signalName)) {
      if (pdh != null) {
        return pdh.voltage;
      }
      if (pdp != null) {
        return pdp.voltage;
      }
    }
    if (DslSignalRegistry.SIGNAL_TOTAL_CURRENT.equals(signalName)) {
      if (pdh != null) {
        return pdh.totalCurrent;
      }
      if (pdp != null) {
        return pdp.totalCurrent;
      }
    }
    if (DslSignalRegistry.SIGNAL_TEMPERATURE.equals(signalName)) {
      if (pdh != null) {
        return pdh.temperature;
      }
      if (pdp != null) {
        return pdp.temperature;
      }
    }
    if (DslSignalRegistry.SIGNAL_SWITCHABLE_ENABLED.equals(signalName)) {
      if (pdh != null) {
        return pdh.switchableEnabled;
      }
      if (pdp != null) {
        return pdp.switchableEnabled;
      }
    }
    if (DslSignalRegistry.SIGNAL_BROWNOUT.equals(signalName)) {
      if (pdh != null) {
        return pdh.brownout;
      }
      if (pdp != null) {
        return pdp.brownout;
      }
    }
    if (DslSignalRegistry.SIGNAL_CAN_WARNING.equals(signalName)) {
      if (pdh != null) {
        return pdh.canWarning;
      }
      if (pdp != null) {
        return pdp.canWarning;
      }
    }
    if (DslSignalRegistry.SIGNAL_HARDWARE_FAULT.equals(signalName)) {
      if (pdh != null) {
        return pdh.hardwareFault;
      }
      if (pdp != null) {
        return pdp.hardwareFault;
      }
    }
    if (DslSignalRegistry.SIGNAL_STICKY_BROWNOUT.equals(signalName)) {
      if (pdh != null) {
        return pdh.stickyBrownout;
      }
      if (pdp != null) {
        return pdp.stickyBrownout;
      }
    }
    if (DslSignalRegistry.SIGNAL_STICKY_CAN_WARNING.equals(signalName)) {
      if (pdh != null) {
        return pdh.stickyCanWarning;
      }
      if (pdp != null) {
        return pdp.stickyCanWarning;
      }
    }
    if (DslSignalRegistry.SIGNAL_STICKY_CAN_BUS_OFF.equals(signalName)) {
      if (pdh != null) {
        return pdh.stickyCanBusOff;
      }
      if (pdp != null) {
        return pdp.stickyCanBusOff;
      }
    }
    if (DslSignalRegistry.SIGNAL_STICKY_HAS_RESET.equals(signalName)) {
      if (pdh != null) {
        return pdh.stickyHasReset;
      }
      if (pdp != null) {
        return pdp.stickyHasReset;
      }
    }
    Integer channelIndex = parsePowerChannelSignalIndex(signalName, CHANNEL_CURRENT_SUFFIX);
    if (channelIndex != null) {
      if (pdh != null && pdh.channelCurrentA != null && channelIndex < pdh.channelCurrentA.length) {
        return pdh.channelCurrentA[channelIndex];
      }
      if (pdp != null && pdp.channelCurrentA != null && channelIndex < pdp.channelCurrentA.length) {
        return pdp.channelCurrentA[channelIndex];
      }
      return null;
    }
    channelIndex = parsePowerChannelSignalIndex(signalName, CHANNEL_FAULT_SUFFIX);
    if (channelIndex != null) {
      if (pdh != null && pdh.channelFault != null && channelIndex < pdh.channelFault.length) {
        return pdh.channelFault[channelIndex];
      }
      if (pdp != null && pdp.channelFault != null && channelIndex < pdp.channelFault.length) {
        return pdp.channelFault[channelIndex];
      }
      return null;
    }
    channelIndex = parsePowerChannelSignalIndex(signalName, CHANNEL_STICKY_FAULT_SUFFIX);
    if (channelIndex != null) {
      if (pdh != null && pdh.channelStickyFault != null && channelIndex < pdh.channelStickyFault.length) {
        return pdh.channelStickyFault[channelIndex];
      }
      if (pdp != null && pdp.channelStickyFault != null && channelIndex < pdp.channelStickyFault.length) {
        return pdp.channelStickyFault[channelIndex];
      }
      return null;
    }
    return null;
  }

  public static boolean writeMotorSignal(DeviceUnit device, String signalName, double value) {
    if (device == null
        || signalName == null
        || !isMotorOutputSignal(signalName)) {
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
    if (isMotorOutputSignal(signalName)) {
      return value >= MOTOR_OUTPUT_MIN && value <= MOTOR_OUTPUT_MAX;
    }
    return true;
  }

  private static boolean isMotorOutputSignal(String signalName) {
    return DslSignalRegistry.SIGNAL_OUTPUT.equals(signalName)
        || DslSignalRegistry.SIGNAL_OUTPUT_PERCENT_CMD.equals(signalName);
  }

  private static boolean isMotorCurrentSignal(String signalName) {
    return DslSignalRegistry.SIGNAL_CURRENT.equals(signalName)
        || DslSignalRegistry.SIGNAL_CURRENT_ACTUAL.equals(signalName);
  }

  private static boolean isMotorTemperatureSignal(String signalName) {
    return DslSignalRegistry.SIGNAL_TEMPERATURE.equals(signalName)
        || DslSignalRegistry.SIGNAL_TEMPERATURE_ACTUAL.equals(signalName);
  }

  private static boolean isMotorVelocitySignal(String signalName) {
    return DslSignalRegistry.SIGNAL_VELOCITY.equals(signalName)
        || DslSignalRegistry.SIGNAL_VELOCITY_ACTUAL.equals(signalName);
  }

  private static boolean isMotorPositionSignal(String signalName) {
    return DslSignalRegistry.SIGNAL_POSITION.equals(signalName)
        || DslSignalRegistry.SIGNAL_POSITION_ACTUAL.equals(signalName)
        || DslSignalRegistry.SIGNAL_POSITION_DELTA.equals(signalName);
  }

  private static boolean isEncoderPositionSignal(String signalName) {
    return DslSignalRegistry.SIGNAL_POSITION.equals(signalName)
        || DslSignalRegistry.SIGNAL_POSITION_ACTUAL.equals(signalName)
        || DslSignalRegistry.SIGNAL_POSITION_DELTA.equals(signalName);
  }

  private static Integer parsePowerChannelSignalIndex(String signalName, String suffix) {
    if (signalName == null
        || suffix == null
        || !signalName.startsWith(CHANNEL_PREFIX)
        || !signalName.endsWith(suffix)) {
      return null;
    }
    String body = signalName.substring(CHANNEL_PREFIX.length(), signalName.length() - suffix.length());
    if (body.isBlank()) {
      return null;
    }
    try {
      int value = Integer.parseInt(body);
      return value >= 0 ? value : null;
    } catch (NumberFormatException ignored) {
      return null;
    }
  }
}
