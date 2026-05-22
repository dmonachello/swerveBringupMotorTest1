package frc.robot.commands.local;

import frc.robot.input.BindingsManager;

/**
 * NAME
 *   RobotLocalTestCommands - Bringup-test command family handlers.
 */
final class RobotLocalTestCommands {
  private static final String MESSAGE_COMMAND_PREFIX = "Command: ";

  private RobotLocalTestCommands() {}

  static void apply(
      BindingsManager.BindingState bind,
      RobotLocalCommandContext context,
      RobotLocalCommandDispatcher.CommonResult result) {
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_SELECT_TEST_PREV)) {
      context.selectPreviousTest();
      context.printTestsOverview();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_SELECT_TEST_NEXT)) {
      context.selectNextTest();
      context.printTestsOverview();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_TOGGLE_TEST)) {
      result.toggledTestEnabled = context.toggleSelectedTestEnabled();
      context.printTestsOverview();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_RUN_TEST)) {
      context.enqueuePrint(MESSAGE_COMMAND_PREFIX + RobotLocalCommandRegistry.COMMAND_RUN_TEST);
      context.runSelectedTest();
      result.runTestPressed = true;
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_RUN_ALL_TESTS)) {
      context.enqueuePrint(MESSAGE_COMMAND_PREFIX + RobotLocalCommandRegistry.COMMAND_RUN_ALL_TESTS);
      context.runAllTests();
      result.runAllPressed = true;
    }
  }
}
