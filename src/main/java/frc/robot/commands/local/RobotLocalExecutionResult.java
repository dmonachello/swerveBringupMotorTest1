package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalExecutionResult - Per-step command execution result.
 */
public final class RobotLocalExecutionResult {
  private static final String TEXT_EMPTY = "";

  private final RobotLocalExecutionState state;
  private final boolean ok;
  private final String message;
  private final String outText;
  private final String outJson;

  private RobotLocalExecutionResult(
      RobotLocalExecutionState state,
      boolean ok,
      String message,
      String outText,
      String outJson) {
    this.state = state;
    this.ok = ok;
    this.message = message != null ? message : TEXT_EMPTY;
    this.outText = outText != null ? outText : this.message;
    this.outJson = outJson != null ? outJson : TEXT_EMPTY;
  }

  public static RobotLocalExecutionResult running() {
    return new RobotLocalExecutionResult(
        RobotLocalExecutionState.RUNNING,
        true,
        TEXT_EMPTY,
        TEXT_EMPTY,
        TEXT_EMPTY);
  }

  public static RobotLocalExecutionResult running(String message) {
    return new RobotLocalExecutionResult(
        RobotLocalExecutionState.RUNNING,
        true,
        message,
        message,
        TEXT_EMPTY);
  }

  public static RobotLocalExecutionResult complete(String message) {
    return new RobotLocalExecutionResult(
        RobotLocalExecutionState.COMPLETE,
        true,
        message,
        message,
        TEXT_EMPTY);
  }

  public static RobotLocalExecutionResult complete(String message, String outText, String outJson) {
    return new RobotLocalExecutionResult(
        RobotLocalExecutionState.COMPLETE,
        true,
        message,
        outText,
        outJson);
  }

  public static RobotLocalExecutionResult failed(String message) {
    return new RobotLocalExecutionResult(
        RobotLocalExecutionState.FAILED,
        false,
        message,
        message,
        TEXT_EMPTY);
  }

  public static RobotLocalExecutionResult interrupted(String message) {
    return new RobotLocalExecutionResult(
        RobotLocalExecutionState.INTERRUPTED,
        false,
        message,
        message,
        TEXT_EMPTY);
  }

  public static RobotLocalExecutionResult rejected(String message) {
    return new RobotLocalExecutionResult(
        RobotLocalExecutionState.REJECTED,
        false,
        message,
        message,
        TEXT_EMPTY);
  }

  public RobotLocalExecutionState state() {
    return state;
  }

  public boolean ok() {
    return ok;
  }

  public String message() {
    return message;
  }

  public String outText() {
    return outText;
  }

  public String outJson() {
    return outJson;
  }
}
