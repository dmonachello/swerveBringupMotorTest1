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
      BringupPrinter.enqueue(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")");
    }
    prevSpeedPrint = speedPrintNow;

    boolean nudgeNow = controller.getLeftStickButton();
    if (nudgeNow && !prevNudge) {
      core.triggerNudge(0.2, 0.5);
      BringupPrinter.enqueue("Nudge: 0.2 for 0.5s (all motors)");
    }
    prevNudge = nudgeNow;

    core.setSpeeds(neoSpeed, krakenSpeed);
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  private void printStartupInfo() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Swerve Bringup ===");
    appendLine(sb, "A: add motor (alternates SPARK/CTRE)");
    appendLine(sb, "Start: add all motors + CANCoders");
    appendLine(sb, "B: print state");
    appendLine(sb, "X: print health status");
    appendLine(sb, "Back: toggle CAN profile");
    appendLine(sb, "Left Bumper: reprint bindings");
    appendLine(sb, "Right Stick: print speed inputs");
    appendLine(sb, "Left Stick: nudge motors (0.2 for 0.5s)");
    appendLine(sb, "Left Y: NEO/FLEX speed, Right Y: KRAKEN/FALCON speed");
    appendLine(sb, "Deadband: " + DEADBAND);
    appendLine(sb, "CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    appendLine(sb, "NEO CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO_CAN_IDS));
    appendLine(sb, "FLEX CAN IDs: " + BringupUtil.joinIds(BringupUtil.FLEX_CAN_IDS));
    appendLine(sb, "KRAKEN CAN IDs: " + BringupUtil.joinIds(BringupUtil.KRAKEN_CAN_IDS));
    appendLine(sb, "FALCON CAN IDs: " + BringupUtil.joinIds(BringupUtil.FALCON_CAN_IDS));
    appendLine(sb, "======================");
    BringupPrinter.enqueue(sb.toString());
  }

  private static void appendLine(StringBuilder sb, String line) {
    sb.append(line).append('\n');
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


