package frc.robot;

import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;

public class Robot extends TimedRobot {

  // Project repo: https://github.com/dmonachello/swerveBringupMotorTest1


  private static final double DEADBAND = BringupUtil.DEADBAND;

  private final XboxController controller = new XboxController(0);
  private final BringupCore core = new BringupCore();
  private boolean prevBindings = false;

  @Override
  public void robotInit() {
    printStartupInfo();
    BringupUtil.validateCanIds(
        new String[] { "NEO", "KRAKEN", "CANCoder" },
        BringupUtil.NEO_CAN_IDS,
        BringupUtil.KRAKEN_CAN_IDS,
        BringupUtil.CANCODER_CAN_IDS);
  }

  @Override
  public void teleopInit() {
    core.resetState();
    prevBindings = false;
  }

  @Override
  public void disabledInit() {
    core.resetState();
    prevBindings = false;
  }

  @Override
  public void teleopPeriodic() {

    core.handleAdd(controller.getAButton());
    core.handleAddAll(controller.getStartButton());
    core.handlePrint(controller.getBButton());
    core.handleHealth(controller.getXButton());

    boolean bindingsNow = controller.getBackButton();
    if (bindingsNow && !prevBindings) {
      printStartupInfo();
    }
    prevBindings = bindingsNow;

    double neoSpeed = BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
    double krakenSpeed = BringupUtil.deadband(-controller.getRightY(), DEADBAND);

    core.setSpeeds(neoSpeed, krakenSpeed);
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  private void printStartupInfo() {
    System.out.println("=== Swerve Bringup ===");
    System.out.println("A: add motor (alternates NEO/KRAKEN)");
    System.out.println("Start: add all motors + CANCoders");
    System.out.println("B: print state");
    System.out.println("X: print health status");
    System.out.println("Back: reprint bindings");
    System.out.println("Left Y: NEO speed, Right Y: KRAKEN speed");
    System.out.println("Deadband: " + DEADBAND);
    System.out.println("NEO CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO_CAN_IDS));
    System.out.println("KRAKEN CAN IDs: " + BringupUtil.joinIds(BringupUtil.KRAKEN_CAN_IDS));
    System.out.println("======================");
  }
  // Shared behavior moved to BringupCore.
}
