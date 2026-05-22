package frc.robot.commands.local;

import frc.robot.input.BindingsManager;

/**
 * NAME
 *   RobotLocalUiCommands - UI/profile toggle command family handlers.
 */
final class RobotLocalUiCommands {
  private RobotLocalUiCommands() {}

  static void apply(BindingsManager.BindingState bind, RobotLocalCommandContext context) {
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_PROFILE_TOGGLE)) {
      context.toggleProfile();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_TOGGLE_DASHBOARD)) {
      context.toggleDashboard();
    }
  }
}
