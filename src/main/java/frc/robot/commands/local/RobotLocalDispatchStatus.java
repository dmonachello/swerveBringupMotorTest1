package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalDispatchStatus - Immediate outcome of submitting a command request.
 */
public enum RobotLocalDispatchStatus {
  ACCEPTED,
  QUEUED,
  REJECTED,
  INTERRUPTED_AND_ACCEPTED
}
