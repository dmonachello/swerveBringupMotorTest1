package frc.robot;

import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import java.util.ArrayList;

public class Robot extends TimedRobot {

  // Project repo: https://github.com/dmonachello/swerveBringupMotorTest1


  private static final double DEADBAND = BringupUtil.DEADBAND;
  private final XboxController controller = new XboxController(0);
  private BringupCore core = new BringupCore();
  private boolean prevBindings = false;
  private boolean prevProfileToggle = false;
  private boolean prevSpeedPrint = false;
  private boolean prevNudge = false;

  @Override
  public void robotInit() {
    BringupUtil.applyProfileFromArgs();
    printStartupInfo();
    validateCanIds();
  }

  @Override
  public void teleopInit() {
    core.resetState();
    prevBindings = false;
    prevProfileToggle = false;
    prevSpeedPrint = false;
    prevNudge = false;
  }

  @Override
  public void disabledInit() {
    core.resetState();
    prevBindings = false;
    prevProfileToggle = false;
    prevSpeedPrint = false;
    prevNudge = false;
  }

  @Override
  public void teleopPeriodic() {

    core.handleAdd(controller.getAButton());
    core.handleAddAll(controller.getStartButton());
    core.handlePrint(controller.getBButton());
    core.handleHealth(controller.getXButton());

    boolean profileToggleNow = controller.getBackButton();
    if (profileToggleNow && !prevProfileToggle) {
      BringupUtil.toggleCanProfile();
      core.resetState();
      core = new BringupCore();
      validateCanIds();
      printStartupInfo();
    }
    prevProfileToggle = profileToggleNow;

    boolean bindingsNow = controller.getLeftBumperButton();
    if (bindingsNow && !prevBindings) {
      printStartupInfo();
    }
    prevBindings = bindingsNow;

    double neoSpeed = BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
    double krakenSpeed = BringupUtil.deadband(-controller.getRightY(), DEADBAND);

    boolean speedPrintNow = controller.getRightStickButton();
    if (speedPrintNow && !prevSpeedPrint) {
      System.out.println(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")");
    }
    prevSpeedPrint = speedPrintNow;

    boolean nudgeNow = controller.getLeftStickButton();
    if (nudgeNow && !prevNudge) {
      core.triggerNudge(0.2, 0.5);
      System.out.println("Nudge: 0.2 for 0.5s (all motors)");
    }
    prevNudge = nudgeNow;

    core.setSpeeds(neoSpeed, krakenSpeed);
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  private void printStartupInfo() {
    System.out.println("=== Swerve Bringup ===");
    System.out.println("A: add motor (alternates SPARK/CTRE)");
    System.out.println("Start: add all motors + CANCoders");
    System.out.println("B: print state");
    System.out.println("X: print health status");
    System.out.println("Back: toggle CAN profile");
    System.out.println("Left Bumper: reprint bindings");
    System.out.println("Right Stick: print speed inputs");
    System.out.println("Left Stick: nudge motors (0.2 for 0.5s)");
    System.out.println("Left Y: NEO/FLEX speed, Right Y: KRAKEN/FALCON speed");
    System.out.println("Deadband: " + DEADBAND);
    System.out.println("CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    System.out.println("NEO CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO_CAN_IDS));
    System.out.println("FLEX CAN IDs: " + BringupUtil.joinIds(BringupUtil.FLEX_CAN_IDS));
    System.out.println("KRAKEN CAN IDs: " + BringupUtil.joinIds(BringupUtil.KRAKEN_CAN_IDS));
    System.out.println("FALCON CAN IDs: " + BringupUtil.joinIds(BringupUtil.FALCON_CAN_IDS));
    System.out.println("======================");
  }

  private void validateCanIds() {
    ArrayList<String> labels = new ArrayList<>();
    ArrayList<int[]> groups = new ArrayList<>();

    labels.add("NEO");
    groups.add(BringupUtil.NEO_CAN_IDS);
    labels.add("FLEX");
    groups.add(BringupUtil.FLEX_CAN_IDS);
    labels.add("KRAKEN");
    groups.add(BringupUtil.KRAKEN_CAN_IDS);
    labels.add("FALCON");
    groups.add(BringupUtil.FALCON_CAN_IDS);
    labels.add("CANCoder");
    groups.add(BringupUtil.CANCODER_CAN_IDS);
    if (BringupUtil.isEnabledCanId(BringupUtil.PDH_CAN_ID)) {
      labels.add("PDH");
      groups.add(new int[] { BringupUtil.PDH_CAN_ID });
    }
    if (BringupUtil.isEnabledCanId(BringupUtil.PIGEON_CAN_ID)) {
      labels.add("Pigeon");
      groups.add(new int[] { BringupUtil.PIGEON_CAN_ID });
    }

    BringupUtil.validateCanIds(
        labels.toArray(new String[0]),
        groups.toArray(new int[0][]));
  }
  // Shared behavior moved to BringupCore.
}


