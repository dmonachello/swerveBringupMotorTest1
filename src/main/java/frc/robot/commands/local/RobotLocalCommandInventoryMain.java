package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalCommandInventoryMain - Emit registry inventory JSON for tooling.
 */
public final class RobotLocalCommandInventoryMain {
  private RobotLocalCommandInventoryMain() {}

  public static void main(String[] args) {
    System.out.println(RobotLocalCommandRegistry.buildInventoryJson().toString());
  }
}
