package frc.robot.commands.local;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

/**
 * NAME
 *   RobotLocalHostVoidCommand - Generic command that invokes one no-arg host method.
 *
 * DESCRIPTION
 *   Used for the common case where a robot-local command only needs optional
 *   profile activation plus one no-argument call on RobotLocalCommandHost.
 *   This reduces the number of places that must change for simple commands.
 */
final class RobotLocalHostVoidCommand implements RobotLocalCommand {
  private final boolean ensureActiveProfile;
  private final String ensureReason;
  private final String inactiveProfileMessage;
  private final String hostMethodName;
  private final String successMessage;

  RobotLocalHostVoidCommand(
      boolean ensureActiveProfile,
      String ensureReason,
      String inactiveProfileMessage,
      String hostMethodName,
      String successMessage) {
    this.ensureActiveProfile = ensureActiveProfile;
    this.ensureReason = ensureReason;
    this.inactiveProfileMessage = inactiveProfileMessage;
    this.hostMethodName = hostMethodName;
    this.successMessage = successMessage;
  }

  @Override
  public RobotLocalExecutionResult execute(RobotLocalCommandParams params) {
    RobotLocalCommandHost host = params.host();
    if (ensureActiveProfile && !host.ensureActiveProfile(ensureReason)) {
      return RobotLocalExecutionResult.failed(inactiveProfileMessage);
    }
    try {
      Method method = host.getClass().getMethod(hostMethodName);
      method.invoke(host);
      return RobotLocalExecutionResult.complete(successMessage);
    } catch (NoSuchMethodException
        | IllegalAccessException
        | InvocationTargetException ex) {
      return RobotLocalExecutionResult.failed(
          "Host method failed: " + hostMethodName + " (" + ex.getClass().getSimpleName() + ")");
    }
  }
}
