package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalCommand - Standardized interface for robot-local commands.
 *
 * DESCRIPTION
 *   execute(...) is required. init(...), interrupt(...), finished(...), and
 *   isFinished(...) are optional lifecycle hooks, similar to the WPILib
 *   command-based model.
 */
public interface RobotLocalCommand {
  /**
   * NAME
   *   init - Optional setup hook before the first execute call.
   */
  default RobotLocalExecutionResult init(RobotLocalCommandParams params) {
    return RobotLocalExecutionResult.running();
  }

  /**
   * NAME
   *   execute - Advance the command for the current loop.
   */
  RobotLocalExecutionResult execute(RobotLocalCommandParams params);

  /**
   * NAME
   *   interrupt - Optional forced-stop hook.
   */
  default RobotLocalExecutionResult interrupt(RobotLocalCommandParams params, String reason) {
    return RobotLocalExecutionResult.interrupted(reason);
  }

  /**
   * NAME
   *   finished - Optional normal completion hook.
   */
  default void finished(RobotLocalCommandParams params, RobotLocalExecutionResult result) {}

  /**
   * NAME
   *   isFinished - Optional finish predicate checked after execute.
   */
  default boolean isFinished(RobotLocalCommandParams params) {
    return false;
  }
}
