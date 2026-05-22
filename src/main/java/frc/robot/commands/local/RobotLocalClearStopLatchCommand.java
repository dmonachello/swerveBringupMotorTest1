package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalClearStopLatchCommand - Clear the active safety stop latch.
 */
final class RobotLocalClearStopLatchCommand implements RobotLocalCommand {
  private static final String REASON_CLEAR_STOP_LATCH = "commandClearStopLatch";
  private static final String MESSAGE_STOP_LATCH_CLEARED = "Stop latch cleared.";
  private static final String MESSAGE_STOP_LATCH_NOT_ACTIVE = "Stop latch not active.";

  @Override
  public RobotLocalExecutionResult execute(RobotLocalCommandParams params) {
    return params.host().clearStopLatch(REASON_CLEAR_STOP_LATCH)
        ? RobotLocalExecutionResult.complete(MESSAGE_STOP_LATCH_CLEARED)
        : RobotLocalExecutionResult.complete(MESSAGE_STOP_LATCH_NOT_ACTIVE);
  }
}
