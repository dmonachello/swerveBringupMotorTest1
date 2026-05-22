package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalExecutionState - Lifecycle state returned by command handlers.
 */
public enum RobotLocalExecutionState {
  RUNNING,
  COMPLETE,
  FAILED,
  INTERRUPTED,
  REJECTED
}
