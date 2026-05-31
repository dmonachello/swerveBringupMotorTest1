package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalHostUiValueProvider - Value provider for host-UI hold commands.
 *
 * DESCRIPTION
 *   Host-UI commands do not stream controller hold state each robot loop.
 *   For host-originated HOLD commands, the REST/session layer owns lifecycle
 *   through explicit stop requests and command completion, so source-loss
 *   should not immediately cancel the command on the next executor step.
 */
public final class RobotLocalHostUiValueProvider implements RobotLocalValueProvider {
  public static final RobotLocalHostUiValueProvider INSTANCE =
      new RobotLocalHostUiValueProvider();

  private RobotLocalHostUiValueProvider() {}

  @Override
  public boolean isCommandActive(String commandName) {
    return true;
  }

  @Override
  public double axisValue(String commandName) {
    return 0.0;
  }
}
