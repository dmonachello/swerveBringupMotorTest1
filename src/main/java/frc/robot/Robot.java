package frc.robot;

import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import java.util.ArrayList;

// Legacy bringup robot program (simpler than RobotV2).
// Uses BringupCore to instantiate devices and print local health.
public class Robot extends TimedRobot {

  // Project repo: https://github.com/dmonachello/swerveBringupMotorTest1


  private static final double DEADBAND = BringupUtil.DEADBAND;
  // Driver Station controller input.
  private final XboxController controller = new XboxController(0);
  // Local bringup behaviors for device creation and health.
  private BringupCore core = new BringupCore();
  // Edge-detect state for one-shot actions.
  private final EdgeTrigger edge = new EdgeTrigger();

  @Override
  public void robotInit() {
    // Load profile before devices are created.
    BringupUtil.applyProfileFromArgs();
    printStartupInfo();
    validateCanIds();
  }

  @Override
  public void teleopInit() {
    // Reset local state whenever teleop starts.
    core.resetState();
    edge.reset();
  }

  @Override
  public void disabledInit() {
    // Keep behavior symmetric in disabled and teleop to avoid stale state.
    core.resetState();
    edge.reset();
  }

  @Override
  public void teleopPeriodic() {

    // --- Device instantiation / local prints ---
    core.handleAdd(controller.getAButton());
    core.handleAddAll(controller.getStartButton());
    core.handlePrint(controller.getBButton());
    core.handleHealth(controller.getXButton());

    // --- Profile switching ---
    if (edge.pressed("profileToggle", controller.getBackButton())) {
      BringupUtil.toggleCanProfile();
      core.resetState();
      core = new BringupCore();
      validateCanIds();
      printStartupInfo();
    }

    // --- Reprint bindings ---
    if (edge.pressed("bindings", controller.getLeftBumperButton())) {
      printStartupInfo();
    }

    // --- Analog input to motor outputs ---
    double neoSpeed = BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
    double krakenSpeed = BringupUtil.deadband(-controller.getRightY(), DEADBAND);

    // --- Print current stick inputs on demand ---
    if (edge.pressed("speedPrint", controller.getRightStickButton())) {
      BringupPrinter.enqueue(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")");
    }

    // --- Timed nudge for all motors ---
    if (edge.pressed("nudge", controller.getLeftStickButton())) {
      core.triggerNudge(0.2, 0.5);
      BringupPrinter.enqueue("Nudge: 0.2 for 0.5s (all motors)");
    }

    if (edge.pressed("clearFaults", controller.getRightBumperButton())) {
      core.clearAllFaults();
      BringupPrinter.enqueue("Cleared device faults (current + sticky).");
    }

    // Apply speeds after any nudge overrides.
    core.setSpeeds(neoSpeed, krakenSpeed);
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  // Print the control bindings and active CAN profile.
  private void printStartupInfo() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Swerve Bringup ===");
    appendLine(sb, "A: add motor (alternates SPARK/CTRE)");
    appendLine(sb, "Start: add all motors + CANCoders");
    appendLine(sb, "B: print state");
    appendLine(sb, "X: print health status");
    appendLine(sb, "Back: toggle CAN profile");
    appendLine(sb, "Left Bumper: reprint bindings");
    appendLine(sb, "Right Bumper: clear device faults");
    appendLine(sb, "Right Stick: print speed inputs");
    appendLine(sb, "Left Stick: nudge motors (0.2 for 0.5s)");
    appendLine(sb, "Left Y: NEO/FLEX speed, Right Y: KRAKEN/FALCON speed");
    appendLine(sb, "Deadband: " + DEADBAND);
    appendLine(sb, "CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    appendLine(sb, "NEO CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO_CAN_IDS));
    appendLine(sb, "NEO 550 CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO550_CAN_IDS));
    appendLine(sb, "FLEX CAN IDs: " + BringupUtil.joinIds(BringupUtil.FLEX_CAN_IDS));
    appendLine(sb, "KRAKEN CAN IDs: " + BringupUtil.joinIds(BringupUtil.KRAKEN_CAN_IDS));
    appendLine(sb, "FALCON CAN IDs: " + BringupUtil.joinIds(BringupUtil.FALCON_CAN_IDS));
    appendLine(sb, "======================");
    BringupPrinter.enqueue(sb.toString());
  }

  // Shared line-append helper to keep formatting consistent.
  private static void appendLine(StringBuilder sb, String line) {
    sb.append(line).append('\n');
  }

  // Validate CAN IDs for duplicates and disabled groups.
  private void validateCanIds() {
    ArrayList<String> labels = new ArrayList<>();
    ArrayList<int[]> groups = new ArrayList<>();

    labels.add("NEO");
    groups.add(BringupUtil.NEO_CAN_IDS);
    labels.add("NEO 550");
    groups.add(BringupUtil.NEO550_CAN_IDS);
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
