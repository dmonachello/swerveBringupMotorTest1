package frc.robot.commands.local;

import frc.robot.input.BindingsManager;

/**
 * NAME
 *   RobotLocalReportCommands - Report/diagnostic command family handlers.
 */
final class RobotLocalReportCommands {
  private RobotLocalReportCommands() {}

  static void apply(
      BindingsManager.BindingState bind,
      RobotLocalCommandContext context,
      boolean runHeld) {
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_PRINT_STATE)) {
      context.printState();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_PRINT_HEALTH)) {
      context.printHealth();
    }
    if (!runHeld && bind.pressed(RobotLocalCommandRegistry.COMMAND_PRINT_CANCODER)) {
      context.printCANCoder();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_PRINT_BINDINGS)) {
      context.printBindings();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_PRINT_TESTS_INFO)) {
      context.printTestsInfo();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_PRINT_TESTS_OVERVIEW)) {
      context.printTestsOverview();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_PRINT_NEXT_TEST)) {
      context.printNextTest();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_PRINT_NT_DIAG)) {
      context.printNtDiagnostics();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_PRINT_CAN_DIAG)) {
      context.printCanDiagnostics();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_DUMP_REPORT)) {
      context.dumpReport();
    }
    if (bind.pressed(RobotLocalCommandRegistry.COMMAND_PRINT_INPUTS)) {
      context.printInputs();
    }
  }
}
