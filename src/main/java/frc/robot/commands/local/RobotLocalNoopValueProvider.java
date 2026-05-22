package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalNoopValueProvider - Empty value provider for non-controller requests.
 */
public final class RobotLocalNoopValueProvider implements RobotLocalValueProvider {
  public static final RobotLocalNoopValueProvider INSTANCE = new RobotLocalNoopValueProvider();

  private RobotLocalNoopValueProvider() {}

  @Override
  public boolean isCommandActive(String commandName) {
    return false;
  }

  @Override
  public double axisValue(String commandName) {
    return 0.0;
  }
}
