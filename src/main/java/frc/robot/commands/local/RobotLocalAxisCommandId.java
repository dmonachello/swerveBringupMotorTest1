package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalAxisCommandId - Canonical axis command identifiers.
 */
public enum RobotLocalAxisCommandId {
  LEFT_DRIVE("leftDrive"),
  RIGHT_DRIVE("rightDrive");

  private final String wireName;

  RobotLocalAxisCommandId(String wireName) {
    this.wireName = wireName;
  }

  /**
   * NAME
   *   wireName - Return the config-visible axis command name.
   */
  public String wireName() {
    return wireName;
  }
}
