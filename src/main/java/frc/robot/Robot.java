package frc.robot;

import edu.wpi.first.wpilibj.GenericHID;
import edu.wpi.first.wpilibj.TimedRobot;

public class Robot extends TimedRobot {

  // Project repo: https://github.com/dmonachello/swerveBringupMotorTest1


  private static final double DEADBAND = BringupUtil.DEADBAND;
  private static final double KEYBOARD_SPEED = 0.4;

  private final GenericHID keyboard = new GenericHID(0);
  private BringupCore core = new BringupCore();
  private boolean prevBindings = false;
  private boolean prevProfileToggle = false;

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
    prevProfileToggle = false;
  }

  @Override
  public void disabledInit() {
    core.resetState();
    prevBindings = false;
    prevProfileToggle = false;
  }

  @Override
  public void teleopPeriodic() {

    core.handleAdd(BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.A));
    core.handleAddAll(BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.ENTER));
    core.handlePrint(BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.B));
    core.handleHealth(BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.X));

    boolean profileToggleNow = BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.P);
    if (profileToggleNow && !prevProfileToggle) {
      BringupUtil.toggleCanProfile();
      core.resetState();
      core = new BringupCore();
      BringupUtil.validateCanIds(
          new String[] { "NEO", "KRAKEN", "CANCoder" },
          BringupUtil.NEO_CAN_IDS,
          BringupUtil.KRAKEN_CAN_IDS,
          BringupUtil.CANCODER_CAN_IDS);
      printStartupInfo();
    }
    prevProfileToggle = profileToggleNow;

    boolean bindingsNow = BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.H);
    if (bindingsNow && !prevBindings) {
      printStartupInfo();
    }
    prevBindings = bindingsNow;

    double neoInput = 0.0;
    if (BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.W)) {
      neoInput += 1.0;
    }
    if (BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.S)) {
      neoInput -= 1.0;
    }
    double krakenInput = 0.0;
    if (BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.I)) {
      krakenInput += 1.0;
    }
    if (BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.K)) {
      krakenInput -= 1.0;
    }
    double neoSpeed = neoInput * KEYBOARD_SPEED;
    double krakenSpeed = krakenInput * KEYBOARD_SPEED;
    if (BringupUtil.KeyboardKeys.isPressed(keyboard, BringupUtil.KeyboardKeys.SPACE)) {
      neoSpeed = 0.0;
      krakenSpeed = 0.0;
    }

    core.setSpeeds(neoSpeed, krakenSpeed);
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  private void printStartupInfo() {
    System.out.println("=== Swerve Bringup ===");
    System.out.println("A: add motor (alternates NEO/KRAKEN)");
    System.out.println("Enter: add all motors + CANCoders");
    System.out.println("B: print state");
    System.out.println("X: print health status");
    System.out.println("P: toggle CAN profile");
    System.out.println("H: reprint bindings");
    System.out.println("W/S: NEO speed, I/K: KRAKEN speed, Space: stop");
    System.out.println("Deadband (unused on keyboard): " + DEADBAND);
    System.out.println("CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    System.out.println("NEO CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO_CAN_IDS));
    System.out.println("KRAKEN CAN IDs: " + BringupUtil.joinIds(BringupUtil.KRAKEN_CAN_IDS));
    System.out.println("======================");
  }
  // Shared behavior moved to BringupCore.
}
