package frc.robot.commands.local;

import frc.robot.input.BindingsManager;

/**
 * NAME
 *   RobotLocalDeviceCommands - Device/runtime command family handlers.
 */
final class RobotLocalDeviceCommands {
  private static final String MESSAGE_COMMAND_PREFIX = "Command: ";
  private static final String MESSAGE_CLEAR_FAULTS = "Cleared device faults (current + sticky).";

  private RobotLocalDeviceCommands() {}

  static void apply(BindingsManager.BindingState bind, RobotLocalCommandContext context) {
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_ADD_MOTOR)) {
      context.enqueuePrint(MESSAGE_COMMAND_PREFIX + RobotLocalCommandRegistry.COMMAND_ADD_MOTOR);
      context.handleAddMotor(true);
    } else {
      context.handleAddMotor(false);
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_ADD_ALL)) {
      context.enqueuePrint(MESSAGE_COMMAND_PREFIX + RobotLocalCommandRegistry.COMMAND_ADD_ALL);
      context.handleAddAll(true);
    } else {
      context.handleAddAll(false);
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_GENERIC_CMD)) {
      context.enqueuePrint(MESSAGE_COMMAND_PREFIX + RobotLocalCommandRegistry.COMMAND_GENERIC_CMD);
      context.handleGenericCmd(true);
    } else {
      context.handleGenericCmd(false);
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_CLEAR_FAULTS)) {
      context.enqueuePrint(MESSAGE_COMMAND_PREFIX + RobotLocalCommandRegistry.COMMAND_CLEAR_FAULTS);
      context.clearAllFaults();
      context.enqueuePrint(MESSAGE_CLEAR_FAULTS);
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_CAN_SWEEP)) {
      context.enqueuePrint(MESSAGE_COMMAND_PREFIX + RobotLocalCommandRegistry.COMMAND_CAN_SWEEP);
      context.runCanSweep();
    }
  }
}
