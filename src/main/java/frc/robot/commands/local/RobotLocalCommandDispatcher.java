package frc.robot.commands.local;

import frc.robot.input.BindingsManager;

/**
 * NAME
 *   RobotLocalCommandDispatcher - Canonical dispatcher for robot-local bindings.
 *
 * DESCRIPTION
 *   Owns the single runtime dispatch path from binding state to command-family
 *   handlers. Callers provide a narrow context implementation for the current
 *   robot/runtime surface.
 */
public final class RobotLocalCommandDispatcher {
  /**
   * NAME
   *   CommonResult - Summary of binding-driven test actions.
   */
  public static final class CommonResult {
    public Boolean toggledTestEnabled = null;
    public boolean runTestPressed = false;
    public boolean runAllPressed = false;
  }

  private RobotLocalCommandDispatcher() {}

  /**
   * NAME
   *   dispatch - Apply all registered local commands for one loop.
   *
   * PARAMETERS
   *   bind - Current binding state.
   *   context - Narrow runtime action context.
   *
   * RETURNS
   *   Summary of test-run-related actions for caller-side safety handling.
   */
  public static CommonResult dispatch(
      BindingsManager.BindingState bind,
      RobotLocalCommandContext context) {
    CommonResult result = new CommonResult();
    boolean runHeld = bind.held(RobotLocalCommandRegistry.COMMAND_RUN_TEST);
    RobotLocalDeviceCommands.apply(bind, context);
    RobotLocalReportCommands.apply(bind, context, runHeld);
    RobotLocalTestCommands.apply(bind, context, result);
    RobotLocalUiCommands.apply(bind, context);
    context.updateReportsAndTests(runHeld || bind.held(RobotLocalCommandRegistry.COMMAND_RUN_TEST));
    return result;
  }
}
