package frc.robot;

import edu.wpi.first.cameraserver.CameraServer;
import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import frc.robot.input.BindingsManager;
import frc.robot.input.ControllerManager;
import frc.robot.manufacturers.microsoft.XboxControllerDevice;
import frc.robot.tests.BringupTestRegistry;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * NAME
 *   Robot - Legacy bringup robot program.
 *
 * DESCRIPTION
 *   Provides a simplified bringup loop that drives BringupCore without the
 *   extended diagnostics in RobotV2.
 *
 * SIDE EFFECTS
 *   Instantiates devices and drives motors via vendor APIs.
 */
public class Robot extends TimedRobot {

  // Project repo: https://github.com/dmonachello/swerveBringupMotorTest1


  private static final double DEADBAND = BringupUtil.DEADBAND;
  private static final String TEXT_TESTS_INFO_PROFILE = "Profile: ";
  private static final String TEXT_TESTS_INFO_SOURCE = "Source: ";
  // Driver Station controller input.
  private final ControllerManager controllers = new ControllerManager();
  private final java.util.Map<String, XboxController> controllerMap = controllers.getXboxControllers();
  private final XboxController controller0 = controllerMap.get("controller0");
  private final BindingsManager bindings = new BindingsManager();
  // Local bringup behaviors for device creation and health.
  private BringupCore core;
  // Edge-detect state for one-shot actions.
  private final EdgeTrigger edge = new EdgeTrigger();
  private final BringupCommandRouter.AddAllHandler addAllHandler = new AddAllHandlerImpl();
  private final BringupCommandRouter.AddMotorHandler addMotorHandler = new AddMotorHandlerImpl();

  /**
   * NAME
   *   robotInit - One-time robot initialization.
   *
   * DESCRIPTION
   *   Loads the active profile, creates BringupCore, and prints startup info.
   */
  @Override
  public void robotInit() {
    // Load profile before devices are created.
    BringupUtil.applyProfileFromArgs();
    core = new BringupCore();
    printStartupInfo();
    validateCanIds();
    CameraServer.startAutomaticCapture();

  }

  /**
   * NAME
   *   teleopInit - Teleop mode entry hook.
   *
   * DESCRIPTION
   *   Resets bringup state and edge-trigger state for teleop.
   */
  @Override
  public void teleopInit() {
    // Reset local state whenever teleop starts.
    core.resetState("teleopInit");
    edge.reset();
  }

  /**
   * NAME
   *   disabledInit - Disabled mode entry hook.
   *
   * DESCRIPTION
   *   Disables tests and clears state for safety in disabled mode.
   */
  @Override
  public void disabledInit() {
    // Keep behavior symmetric in disabled and teleop to avoid stale state.
    core.disableAllBringupTests(true);
    core.resetState("disabledInit");
    edge.reset();
  }

  /**
   * NAME
   *   teleopPeriodic - Teleop periodic loop.
   *
   * DESCRIPTION
   *   Processes controller bindings, updates bringup commands, and applies
   *   motor outputs within the 20ms loop.
   */
  @Override
  public void teleopPeriodic() {

    // --- Device instantiation / local prints ---
    if (controller0 == null) {
      return;
    }
    BindingsManager.BindingState bind = bindings.sample(controllerMap, edge);

    BringupCommandRouter.applyCommon(
        bind,
        core,
        null,
        new StartupInfoPrinter(),
        new TestsInfoPrinter(),
        new TestsOverviewPrinter(),
        bind.held("runTest"),
        addAllHandler,
        addMotorHandler);

    // --- Profile switching ---
    if (bind.pressed("profileToggle")) {
      BringupUtil.selectNextProfile();
      printProfileInfo();
    }

    // --- Analog input to motor outputs ---
    double neoSpeed = bind.hasAxis("leftDrive")
        ? bind.axis("leftDrive")
        : BringupUtil.deadband(-controller0.getLeftY(), DEADBAND);
    double krakenSpeed = bind.hasAxis("rightDrive")
        ? bind.axis("rightDrive")
        : BringupUtil.deadband(-controller0.getRightY(), DEADBAND);

    // --- Print current stick inputs on demand ---
    if (bind.pressed("printInputs")) {
      core.requestTextReport(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")",
          4);
    }

    // core update handled by BringupCommandRouter

    // Feed test inputs (used by joystick-mode tests).
    core.setTestInputs(XboxControllerDevice.buildControllerInputs(controllerMap, neoSpeed, krakenSpeed));

    // Apply speeds after inputs are processed.
    core.setSpeeds(neoSpeed, krakenSpeed);
  }

  /**
   * NAME
   *   AddAllHandlerImpl - Activate profile before add-all.
   */
  private final class AddAllHandlerImpl implements BringupCommandRouter.AddAllHandler {
    @Override
    public void handleAddAll(boolean addAllNow) {
      if (addAllNow && !BringupUtil.isProfileActive()) {
        BringupUtil.prepareActivationForSelectedProfile();
        BringupUtil.activateSelectedProfile();
        if (BringupUtil.isProfileActive()) {
          core.resetState("profileActivate");
          core = new BringupCore();
          validateCanIds();
          printProfileInfo();
        }
      }
      if (core != null) {
        core.handleAddAll(addAllNow);
      }
    }
  }

  /**
   * NAME
   *   AddMotorHandlerImpl - Activate profile before add-next.
   */
  private final class AddMotorHandlerImpl implements BringupCommandRouter.AddMotorHandler {
    @Override
    public void handleAddMotor(boolean addMotorNow) {
      if (addMotorNow && !BringupUtil.isProfileActive()) {
        BringupUtil.prepareActivationForSelectedProfile();
        BringupUtil.activateSelectedProfile();
        if (BringupUtil.isProfileActive()) {
          core.resetState("profileActivate");
          core = new BringupCore();
          validateCanIds();
          printProfileInfo();
        }
      }
      if (core != null) {
        core.handleAdd(addMotorNow);
      }
    }
  }

  /**
   * NAME
   *   StartupInfoPrinter - Delegate for startup info printing.
   */
  private final class StartupInfoPrinter implements Runnable {
    @Override
    public void run() {
      printStartupInfo();
    }
  }

  /**
   * NAME
   *   TestsInfoPrinter - Delegate for tests info printing.
   */
  private final class TestsInfoPrinter implements Runnable {
    @Override
    public void run() {
      printTestsInfo();
    }
  }

  /**
   * NAME
   *   TestsOverviewPrinter - Delegate for tests overview printing.
   */
  private final class TestsOverviewPrinter implements Runnable {
    @Override
    public void run() {
      printTestsOverview();
    }
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  /**
   * NAME
   *   printStartupInfo - Emit bindings and profile diagnostics.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
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
    appendDeviceSummary(sb);
    appendLine(sb, "======================");
    core.requestTextReport(sb.toString(), 4);
  }

  /**
   * NAME
   *   printProfileInfo - Emit CAN profile details after a switch.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  private void printProfileInfo() {
    StringBuilder sb = new StringBuilder(256);
    appendLine(sb, "=== Profile Updated ===");
    appendLine(sb, "CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    appendDeviceSummary(sb);
    appendLine(sb, "======================");
    core.requestTextReport(sb.toString(), 4);
  }

  /**
   * NAME
   *   printTestsInfo - Emit bringup tests diagnostics.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  private void printTestsInfo() {
    BringupTestRegistry.TestsInfo info = BringupTestRegistry.getTestsInfo();
    StringBuilder sb = new StringBuilder(256);
    appendLine(sb, "=== Bringup Tests Info ===");
    appendLine(sb, "Resolved path: " + (info.path != null ? info.path.toString() : "(none)"));
    appendLine(sb, TEXT_TESTS_INFO_PROFILE + (info.profileName != null ? info.profileName : "(none)"));
    appendLine(sb, TEXT_TESTS_INFO_SOURCE + (info.source != null ? info.source : "(none)"));
    appendLine(sb, "Exists: " + info.exists);
    if (info.exists) {
      if (info.sizeBytes > 0) {
        appendLine(sb, "Size: " + info.sizeBytes + " bytes");
      }
      if (info.lastModifiedMs > 0) {
        appendLine(sb, "Last modified: " + Instant.ofEpochMilli(info.lastModifiedMs));
      }
      if (info.sha256 != null && !info.sha256.isBlank()) {
        appendLine(sb, "SHA-256: " + info.sha256);
      }
      if (info.readError != null) {
        appendLine(sb, "Read warning: " + info.readError);
      }
      if (info.usingTestSets) {
        String active = info.activeTestSetName != null ? info.activeTestSetName : "(none)";
        String def = info.defaultTestSetName != null ? info.defaultTestSetName : "(none)";
        appendLine(
            sb,
            "Test sets: yes (active=" + active + ", default=" + def + ", count=" + info.testSetCount + ")");
      } else {
        appendLine(sb, "Test sets: no");
      }
      if (info.testCount > 0) {
        appendLine(sb, "Test count: " + info.testCount);
      }
    }
    appendLine(sb, "==========================");
    core.requestTextReport(sb.toString(), 4);
  }

  /**
   * NAME
   *   printTestsOverview - Emit a tests overview snapshot.
   *
   * SIDE EFFECTS
   *   Enqueues a text report for throttled console output.
   */
  private void printTestsOverview() {
    BringupCore.TestsOverview overview = core.buildTestsOverview();
    String text = core.formatTestsOverview(overview);
    core.requestTextReport(text, 6);
  }

  /**
   * NAME
   *   appendDeviceSummary - Append active devices grouped by vendor/type.
   *
   * PARAMETERS
   *   sb - Target StringBuilder.
   */
  private void appendDeviceSummary(StringBuilder sb) {
    List<BringupUtil.DeviceEntry> devices = BringupUtil.getActiveDevicesSorted();
    if (devices.isEmpty()) {
      appendLine(sb, "Devices: (none)");
      return;
    }
    Map<String, List<Integer>> groups = new java.util.LinkedHashMap<>();
    for (BringupUtil.DeviceEntry entry : devices) {
      if (entry == null || !BringupUtil.isEnabledCanId(entry.id)) {
        continue;
      }
      String vendor = entry.vendor != null ? entry.vendor.trim() : "";
      String type = entry.type != null ? entry.type.trim() : "";
      String key = (vendor.isEmpty() ? "UNKNOWN" : vendor) + " " + (type.isEmpty() ? "Device" : type);
      groups.computeIfAbsent(key, ignored -> new ArrayList<>()).add(entry.id);
    }
    for (Map.Entry<String, List<Integer>> entry : groups.entrySet()) {
      List<Integer> ids = entry.getValue();
      if (ids.isEmpty()) {
        continue;
      }
      StringBuilder line = new StringBuilder();
      for (int i = 0; i < ids.size(); i++) {
        if (i > 0) {
          line.append(", ");
        }
        line.append(ids.get(i));
      }
      appendLine(sb, entry.getKey() + " CAN IDs: " + line);
    }
  }

  /**
   * NAME
   *   appendLine - Append a line with newline termination.
   *
   * PARAMETERS
   *   sb - Target StringBuilder.
   *   line - Line content to append.
   */
  private static void appendLine(StringBuilder sb, String line) {
    sb.append(line).append('\n');
  }

  /**
   * NAME
   *   validateCanIds - Check for duplicate or invalid CAN IDs.
   *
   * DESCRIPTION
   *   Builds labeled groups for clearer warning output from BringupUtil.
   */
  private void validateCanIds() {
    BringupUtil.validateCanIds(BringupUtil.getActiveDevices());
  }
  // Shared behavior moved to BringupCore.
}
