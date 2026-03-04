package frc.robot;

import edu.wpi.first.cameraserver.CameraServer;
import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import frc.robot.input.BindingsManager;
import frc.robot.input.ControllerManager;
import java.util.ArrayList;

// Legacy bringup robot program (simpler than RobotV2).
// Uses BringupCore to instantiate devices and print local health.
public class Robot extends TimedRobot {

  // Project repo: https://github.com/dmonachello/swerveBringupMotorTest1


  private static final double DEADBAND = BringupUtil.DEADBAND;
  // Driver Station controller input.
  private final ControllerManager controllers = new ControllerManager();
  private final XboxController controller = controllers.getXbox(0);
  private final BindingsManager bindings = new BindingsManager();
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
    CameraServer.startAutomaticCapture();

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
    if (controller == null) {
      return;
    }
    BindingsManager.BindingState bind = bindings.sample(controller, null, edge);

    BringupCommandRouter.applyCommon(
        bind,
        core,
        null,
        this::printStartupInfo,
        bind.held("runTest"));

    // --- Profile switching ---
    if (bind.pressed("profileToggle")) {
      BringupUtil.toggleCanProfile();
      core.resetState();
      core = new BringupCore();
      validateCanIds();
      printStartupInfo();
    }

    // --- Analog input to motor outputs ---
    double neoSpeed = bind.hasAxis("leftDrive")
        ? bind.axis("leftDrive")
        : BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
    double krakenSpeed = bind.hasAxis("rightDrive")
        ? bind.axis("rightDrive")
        : BringupUtil.deadband(-controller.getRightY(), DEADBAND);

    // --- Print current stick inputs on demand ---
    if (bind.pressed("printInputs")) {
      BringupPrinter.enqueue(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")");
    }

    // core update handled by BringupCommandRouter

    // Feed test inputs (used by joystick-mode tests).
    core.setTestInputs(neoSpeed, krakenSpeed);

    // Apply speeds after inputs are processed.
    core.setSpeeds(neoSpeed, krakenSpeed);
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  // Print the control bindings and active CAN profile.
  private void printStartupInfo() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Swerve Bringup ===");
    appendLine(sb, "Bindings (from bringup_bindings.json):");
    for (String line : bindings.describeBindings()) {
      appendLine(sb, "  " + line);
    }
    for (String line : bindings.describeAxes()) {
      appendLine(sb, "  " + line);
    }
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
