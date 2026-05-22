package frc.robot.commands.local;

import com.google.gson.JsonObject;

/**
 * NAME
 *   RobotLocalValueProvider - Live input/value source used by active commands.
 */
public interface RobotLocalValueProvider {
  /**
   * NAME
   *   isCommandActive - Return whether the named trigger remains active.
   */
  boolean isCommandActive(String commandName);

  /**
   * NAME
   *   axisValue - Return the current value of a named axis binding.
   */
  double axisValue(String commandName);

  /**
   * NAME
   *   requestArgs - Return latest request args when available.
   */
  default JsonObject requestArgs() {
    return null;
  }
}
