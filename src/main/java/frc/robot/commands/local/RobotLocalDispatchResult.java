package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalDispatchResult - Immediate result of submitting a request.
 */
public final class RobotLocalDispatchResult {
  private final RobotLocalDispatchStatus status;
  private final String message;
  private final RobotLocalExecutionResult executionResult;

  private RobotLocalDispatchResult(
      RobotLocalDispatchStatus status,
      String message,
      RobotLocalExecutionResult executionResult) {
    this.status = status;
    this.message = message;
    this.executionResult = executionResult;
  }

  public static RobotLocalDispatchResult accepted(
      RobotLocalDispatchStatus status,
      String message,
      RobotLocalExecutionResult executionResult) {
    return new RobotLocalDispatchResult(status, message, executionResult);
  }

  public static RobotLocalDispatchResult rejected(String message) {
    return new RobotLocalDispatchResult(
        RobotLocalDispatchStatus.REJECTED,
        message,
        RobotLocalExecutionResult.rejected(message));
  }

  public RobotLocalDispatchStatus status() {
    return status;
  }

  public String message() {
    return message;
  }

  public RobotLocalExecutionResult executionResult() {
    return executionResult;
  }
}
