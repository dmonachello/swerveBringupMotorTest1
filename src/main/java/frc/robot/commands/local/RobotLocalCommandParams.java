package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalCommandParams - Standardized params object passed to commands.
 */
public final class RobotLocalCommandParams {
  private final RobotLocalCommandDefinition definition;
  private final RobotLocalCommandRequest request;
  private final RobotLocalCommandHost host;

  public RobotLocalCommandParams(
      RobotLocalCommandDefinition definition,
      RobotLocalCommandRequest request,
      RobotLocalCommandHost host) {
    this.definition = definition;
    this.request = request;
    this.host = host;
  }

  public RobotLocalCommandDefinition definition() {
    return definition;
  }

  public RobotLocalCommandRequest request() {
    return request;
  }

  public RobotLocalCommandHost host() {
    return host;
  }

  public RobotLocalValueProvider valueProvider() {
    return request.valueProvider();
  }
}
