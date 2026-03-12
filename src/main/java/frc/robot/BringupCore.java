package frc.robot;

import edu.wpi.first.wpilibj.Timer;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.EncoderAttachment;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.diag.snapshots.MotorSpecAttachment;
import frc.robot.manufacturers.CtreDeviceGroup;
import frc.robot.manufacturers.DeviceAddResult;
import frc.robot.manufacturers.DeviceRole;
import frc.robot.manufacturers.DeviceTypeBucket;
import frc.robot.manufacturers.ManufacturerGroup;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
import frc.robot.manufacturers.RevDeviceGroup;
import frc.robot.tests.BringupTest;
import frc.robot.tests.BringupTestContext;
import frc.robot.tests.BringupTestRegistry;
import frc.robot.tests.BringupTestResult;
import frc.robot.tests.CompositeTest;
import frc.robot.tests.JoystickTest;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/**
 * NAME
 *   BringupCore - Core bringup logic and test coordination.
 *
 * DESCRIPTION
 *   Creates devices, commands outputs, manages bringup tests, and queues
 *   report output using robot-local vendor APIs only.
 */
public final class BringupCore {
  private static final int NI_MANUFACTURER = 1;
  private static final int TYPE_ROBOT_CONTROLLER = 1;
  private static final long MIN_PRINT_INTERVAL_MS = 1000;
  private static final int REPORT_BATCH = 2;

  private final RevDeviceGroup revDevices = new RevDeviceGroup();
  private final CtreDeviceGroup ctreDevices = new CtreDeviceGroup();

  private boolean addRevNext = true;

  private boolean prevAdd = false;
  private boolean prevAddAll = false;
  private boolean prevPrint = false;
  private boolean prevHealth = false;
  private boolean prevCANCoder = false;
  private long lastStatePrintMs = 0L;
  private long lastHealthPrintMs = 0L;
  private long lastCANCoderPrintMs = 0L;
  private final Deque<ReportJobBase> reportQueue = new ArrayDeque<>();
  private ReportJobBase activeReport = null;
  private final List<DeviceUnit> testDevices = new ArrayList<>();
  private int nextTestIndex = 0;
  private final List<BringupTest> bringupTests = new ArrayList<>();
  private final List<BringupTest> selectableTests = new ArrayList<>();
  private int nextBringupTestIndex = 0;
  private int selectedTestIndex = -1;
  private BringupTest activeTest = null;
  private boolean runAllActive = false;
  private final List<BringupTest> runAllQueue = new ArrayList<>();
  private int runAllIndex = 0;
  private final BringupTestContext testContext;
  private double primaryInput = 0.0;
  private double secondaryInput = 0.0;

  /**
   * NAME
   *   BringupCore - Construct and initialize bringup state.
   *
   * SIDE EFFECTS
   *   Loads bringup tests and initializes device groups.
   */
  public BringupCore() {
    List<ManufacturerGroup> groups = new ArrayList<>();
    groups.add(revDevices);
    groups.add(ctreDevices);
    testContext = new BringupTestContext(groups);
    bringupTests.addAll(BringupTestRegistry.loadTests());
    refreshSelectableTests();
    refreshTestDevices();
  }

  // Edge-triggered: add the next motor in the alternating sequence.
  /**
   * NAME
   *   handleAdd - Edge-triggered add-next-motor handler.
   *
   * PARAMETERS
   *   addNow - Current button state.
   */
  public void handleAdd(boolean addNow) {
    if (addNow && !prevAdd) {
      addNextMotor();
    }
    prevAdd = addNow;
  }

  // Edge-triggered: instantiate all configured devices at once.
  /**
   * NAME
   *   handleAddAll - Edge-triggered add-all-devices handler.
   *
   * PARAMETERS
   *   addAllNow - Current button state.
   */
  public void handleAddAll(boolean addAllNow) {
    if (addAllNow && !prevAddAll) {
      addAllDevices();
    }
    prevAddAll = addAllNow;
  }

  // Edge-triggered: print a concise state summary.
  /**
   * NAME
   *   handlePrint - Edge-triggered state report request.
   *
   * PARAMETERS
   *   printNow - Current button state.
   */
  public void handlePrint(boolean printNow) {
    if (printNow && !prevPrint) {
      long nowMs = System.currentTimeMillis();
      if (nowMs - lastStatePrintMs >= MIN_PRINT_INTERVAL_MS) {
        lastStatePrintMs = nowMs;
        requestStateReport();
      }
    }
    prevPrint = printNow;
  }

  // Edge-triggered: print local health for all instantiated devices.
  /**
   * NAME
   *   handleHealth - Edge-triggered health report request.
   *
   * PARAMETERS
   *   healthNow - Current button state.
   */
  public void handleHealth(boolean healthNow) {
    if (healthNow && !prevHealth) {
      long nowMs = System.currentTimeMillis();
      if (nowMs - lastHealthPrintMs >= MIN_PRINT_INTERVAL_MS) {
        lastHealthPrintMs = nowMs;
        requestHealthReport();
      }
    }
    prevHealth = healthNow;
  }

  // Edge-triggered: print CANCoder absolute position data.
  /**
   * NAME
   *   handleCANCoder - Edge-triggered CANCoder report request.
   *
   * PARAMETERS
   *   printNow - Current button state.
   */
  public void handleCANCoder(boolean printNow) {
    if (printNow && !prevCANCoder) {
      long nowMs = System.currentTimeMillis();
      if (nowMs - lastCANCoderPrintMs >= MIN_PRINT_INTERVAL_MS) {
        lastCANCoderPrintMs = nowMs;
        requestCANCoderReport();
      }
    }
    prevCANCoder = printNow;
  }

  // Apply requested speeds to all instantiated motors.
  /**
   * NAME
   *   setSpeeds - Apply output commands to motor groups.
   *
   * PARAMETERS
   *   neoSpeed - REV motor duty cycle (-1..1).
   *   krakenSpeed - CTRE motor duty cycle (-1..1).
   *
   * NOTES
   *   Suppressed while an active test is running.
   */
  public void setSpeeds(double neoSpeed, double krakenSpeed) {
    if (activeTest != null && activeTest.isRunning()) {
      return;
    }
    revDevices.setDuty(neoSpeed);
    ctreDevices.setDuty(krakenSpeed);
  }

  /**
   * NAME
   *   setTestInputs - Provide joystick inputs to test logic.
   *
   * PARAMETERS
   *   primary - Primary axis input.
   *   secondary - Secondary axis input.
   */
  public void setTestInputs(double primary, double secondary) {
    primaryInput = primary;
    secondaryInput = secondary;
    if (activeTest instanceof frc.robot.tests.JoystickTest joystick) {
      String axis = joystick.getInputAxis();
      double value = "secondary".equalsIgnoreCase(axis) ? secondaryInput : primaryInput;
      joystick.setInputValue(value);
    }
  }

  // Clear current and sticky faults on all instantiated devices where supported.
  /**
   * NAME
   *   clearAllFaults - Clear sticky and current faults where supported.
   */
  public void clearAllFaults() {
    revDevices.clearFaults();
    ctreDevices.clearFaults();
  }

  /**
   * NAME
   *   runCanPingSweep - Emit a local-vendor CAN presence sweep.
   *
   * SIDE EFFECTS
   *   Enqueues a report for console output.
   */
  public void runCanPingSweep() {
    StringBuilder sb = new StringBuilder(1024);
    appendLine(sb, "=== CAN Ping Sweep (Local Vendor API) ===");
    appendLine(sb, "Note: Devices must be added to be probed (use addAll).");
    appendLine(sb, "--- REV ---");
    appendSweepGroup(sb, revDevices);
    appendLine(sb, "--- CTRE ---");
    appendSweepGroup(sb, ctreDevices);
    appendLine(sb, "==============================");
    BringupPrinter.enqueueChunked(sb.toString(), 6);
  }

  // Stop all outputs, close devices, and reset internal state.
  /**
   * NAME
   *   resetState - Reset bringup state with a default reason.
   */
  public void resetState() {
    resetState("reset");
  }

  /**
   * NAME
   *   resetState - Reset bringup state and stop active tests.
   *
   * PARAMETERS
   *   reason - Label for the reset report.
   *
   * SIDE EFFECTS
   *   Stops tests, closes devices, and enqueues a reset report.
   */
  public void resetState(String reason) {
    if (activeTest != null && activeTest.isRunning()) {
      activeTest.stop(testContext);
    }
    activeTest = null;
    refreshSelectableTests();
    revDevices.stopAll();
    ctreDevices.stopAll();
    revDevices.closeAll();
    ctreDevices.closeAll();
    revDevices.resetLowCurrentTimers();

    addRevNext = true;

    prevAdd = false;
    prevAddAll = false;
    prevPrint = false;
    prevHealth = false;
    prevCANCoder = false;

    String label = reason != null && !reason.isBlank() ? reason : "reset";
    BringupPrinter.enqueue(
        "=== Bringup reset (" + label + " @ " + System.currentTimeMillis() + "): no motors instantiated ===");
  }

  /**
   * NAME
   *   runNextNonMotorTest - Run the next available non-motor device test.
   *
   * SIDE EFFECTS
   *   Starts a device test and enqueues a status message.
   */
  public void runNextNonMotorTest() {
    if (activeTest != null && activeTest.isRunning()) {
      BringupPrinter.enqueue("Test already running: " + activeTest.getName());
      return;
    }
    if (startNextBringupTest()) {
      return;
    }
    if (testDevices.isEmpty()) {
      BringupPrinter.enqueue("No non-motor test devices configured.");
      return;
    }
    int attempts = testDevices.size();
    while (attempts-- > 0) {
      DeviceUnit device = testDevices.get(nextTestIndex);
      nextTestIndex = (nextTestIndex + 1) % testDevices.size();
      if (!device.hasTest()) {
        continue;
      }
      device.runTest();
      String testName = device.getTestName();
      BringupPrinter.enqueue(
          "Test: " + device.getLabel() +
          " (" + device.getDeviceType() + ")" +
          (testName.isEmpty() ? "" : " [" + testName + "]"));
      return;
    }
    BringupPrinter.enqueue("No testable non-motor devices found.");
  }

  /**
   * NAME
   *   selectNextBringupTest - Advance selection through bringup tests.
   */
  public void selectNextBringupTest() {
    if (selectableTests.isEmpty()) {
      BringupPrinter.enqueue("No enabled bringup tests.");
      return;
    }
    if (selectedTestIndex < 0) {
      selectedTestIndex = 0;
    } else {
      selectedTestIndex = (selectedTestIndex + 1) % selectableTests.size();
    }
    BringupTest test = selectableTests.get(selectedTestIndex);
    BringupPrinter.enqueue("Selected test: " + test.getName());
  }

  /**
   * NAME
   *   selectPrevBringupTest - Move selection backward through bringup tests.
   */
  public void selectPrevBringupTest() {
    if (selectableTests.isEmpty()) {
      BringupPrinter.enqueue("No enabled bringup tests.");
      return;
    }
    if (selectedTestIndex < 0) {
      selectedTestIndex = selectableTests.size() - 1;
    } else {
      selectedTestIndex = (selectedTestIndex - 1 + selectableTests.size()) % selectableTests.size();
    }
    BringupTest test = selectableTests.get(selectedTestIndex);
    BringupPrinter.enqueue("Selected test: " + test.getName());
  }

  /**
   * NAME
   *   runSelectedBringupTest - Start the selected bringup test.
   *
   * SIDE EFFECTS
   *   Starts a test and enqueues a status message.
   */
  public void runSelectedBringupTest() {
    if (activeTest != null && activeTest.isRunning()) {
      BringupPrinter.enqueue("Test already running: " + activeTest.getName());
      return;
    }
    BringupTest test = getSelectedBringupTest();
    if (test == null) {
      runNextNonMotorTest();
      return;
    }
    if (!test.isEnabled()) {
      BringupPrinter.enqueue("Test disabled: " + test.getName());
      return;
    }
    runAllActive = false;
    boolean started = test.start(testContext, Timer.getFPGATimestamp());
    if (started) {
      activeTest = test;
      BringupPrinter.enqueue("Test: " + test.getName());
      return;
    }
    BringupPrinter.enqueue("Test skipped: " + test.getName() + " (" + test.getStatus() + ")");
  }

  /**
   * NAME
   *   updateTests - Advance the active test state machine.
   *
   * PARAMETERS
   *   holdSignal - Whether the hold-to-run signal is active.
   *
   * SIDE EFFECTS
   *   Updates test state and may enqueue completion messages.
   */
  public void updateTests(boolean holdSignal) {
    if (activeTest == null || !activeTest.isRunning()) {
      return;
    }
    activeTest.onHoldSignal(holdSignal);
    double now = Timer.getFPGATimestamp();
    activeTest.update(testContext, now);
    if (activeTest.isFinished()) {
      BringupTestResult result = activeTest.getResult();
      BringupPrinter.enqueue(
          "Test result: " + activeTest.getName() + " = " + result + " (" + activeTest.getStatus() + ")");
      activeTest = null;
      if (runAllActive) {
        if (!startNextRunAllTest()) {
          runAllActive = false;
          runAllQueue.clear();
          runAllIndex = 0;
          BringupPrinter.enqueue("Run-all complete.");
        }
      }
    }
  }

  /**
   * NAME
   *   updateTests - Update tests with no hold signal.
   */
  public void updateTests() {
    updateTests(false);
  }

  /**
   * NAME
   *   runAllBringupTests - Run enabled bringup tests sequentially.
   *
   * SIDE EFFECTS
   *   Starts tests and enqueues status updates.
   */
  public void runAllBringupTests() {
    if (activeTest != null && activeTest.isRunning()) {
      BringupPrinter.enqueue("Test already running: " + activeTest.getName());
      return;
    }
    buildRunAllQueue();
    if (runAllQueue.isEmpty()) {
      BringupPrinter.enqueue("No enabled bringup tests.");
      return;
    }
    runAllActive = true;
    if (!startNextRunAllTest()) {
      runAllActive = false;
      runAllQueue.clear();
      runAllIndex = 0;
      BringupPrinter.enqueue("No enabled bringup tests.");
    }
  }

  /**
   * NAME
   *   refreshTestDevices - Rebuild the list of non-motor test devices.
   */
  private void refreshTestDevices() {
    testDevices.clear();
    testDevices.addAll(ctreDevices.getTestDevices());
    testDevices.addAll(revDevices.getTestDevices());
    nextTestIndex = 0;
  }

  /**
   * NAME
   *   refreshSelectableTests - Rebuild the selectable test list.
   */
  private void refreshSelectableTests() {
    selectableTests.clear();
    for (BringupTest test : bringupTests) {
      if (test != null) {
        selectableTests.add(test);
      }
    }
    selectedTestIndex = selectableTests.isEmpty() ? -1 : 0;
  }

  /**
   * NAME
   *   getSelectedBringupTest - Return the currently selected test.
   *
   * RETURNS
   *   Selected BringupTest or null if none are available.
   */
  private BringupTest getSelectedBringupTest() {
    if (selectableTests.isEmpty() || selectedTestIndex < 0) {
      return null;
    }
    if (selectedTestIndex >= selectableTests.size()) {
      selectedTestIndex = 0;
    }
    return selectableTests.get(selectedTestIndex);
  }

  /**
   * NAME
   *   toggleSelectedBringupTestEnabled - Toggle enable state for selected test.
   *
   * SIDE EFFECTS
   *   Updates test metadata and attempts to persist to JSON.
   */
  public void toggleSelectedBringupTestEnabled() {
    BringupTest test = getSelectedBringupTest();
    if (test == null) {
      BringupPrinter.enqueue("No bringup tests available.");
      return;
    }
    boolean newValue = !test.isEnabled();
    test.setEnabled(newValue);
    BringupPrinter.enqueue(
        "Test " + (newValue ? "enabled: " : "disabled: ") + test.getName());
    boolean saved = BringupTestRegistry.saveTests(bringupTests);
    if (!saved) {
      BringupPrinter.enqueue("Warning: failed to persist bringup test enable state.");
    }
  }

  /**
   * NAME
   *   disableAllBringupTests - Disable all bringup tests.
   *
   * PARAMETERS
   *   persist - Whether to save changes to disk.
   *
   * SIDE EFFECTS
   *   Updates test enable flags and may write bringup_tests.json.
   */
  public void disableAllBringupTests(boolean persist) {
    if (bringupTests.isEmpty()) {
      BringupPrinter.enqueue("No bringup tests available.");
      return;
    }
    int changed = 0;
    for (BringupTest test : bringupTests) {
      if (test != null && test.isEnabled()) {
        test.setEnabled(false);
        changed++;
      }
    }
    BringupPrinter.enqueue("Disabled bringup tests: " + changed);
    if (persist) {
      boolean saved = BringupTestRegistry.saveTests(bringupTests);
      if (!saved) {
        BringupPrinter.enqueue("Warning: failed to persist bringup test enable state.");
      }
    }
  }

  /**
   * NAME
   *   buildTestsOverview - Build a snapshot of tests for display/publish.
   *
   * RETURNS
   *   TestsOverview with row entries and counts.
   */
  public TestsOverview buildTestsOverview() {
    TestsOverview overview = new TestsOverview();
    BringupTestRegistry.TestsInfo info = BringupTestRegistry.getTestsInfo();
    if (info != null) {
      overview.activeTestSet = info.activeTestSetName;
      overview.defaultTestSet = info.defaultTestSetName;
      overview.usingTestSets = info.usingTestSets;
    }
    overview.totalCount = bringupTests.size();
    int enabledCount = 0;
    for (int i = 0; i < bringupTests.size(); i++) {
      BringupTest test = bringupTests.get(i);
      if (test == null) {
        continue;
      }
      TestRow row = new TestRow();
      row.index = i;
      row.name = test.getDisplayName();
      row.enabled = test.isEnabled();
      row.selected = (i == selectedTestIndex);
      row.type = resolveTestType(test);
      row.status = test.getStatus();
      row.motors = test.getMotorKeys();
      if (row.enabled) {
        enabledCount++;
      }
      overview.rows.add(row);
    }
    overview.enabledCount = enabledCount;
    return overview;
  }

  /**
   * NAME
   *   formatTestsOverview - Render a tests overview as text.
   *
   * PARAMETERS
   *   overview - Snapshot to format.
   *
   * RETURNS
   *   Multiline string for console output.
   */
  public String formatTestsOverview(TestsOverview overview) {
    if (overview == null) {
      return "=== Bringup Tests ===\nNo tests loaded.\n=====================";
    }
    StringBuilder sb = new StringBuilder(1024);
    appendLine(sb, "=== Bringup Tests ===");
    if (overview.usingTestSets) {
      String active = overview.activeTestSet != null ? overview.activeTestSet : "(none)";
      String def = overview.defaultTestSet != null ? overview.defaultTestSet : "(none)";
      appendLine(sb, "Active set: " + active + " (default: " + def + ")");
    }
    appendLine(
        sb,
        "Total: " + overview.totalCount +
        " Enabled: " + overview.enabledCount);
    appendLine(sb, "Idx Sel En Type       Name                         Motors");
    for (TestRow row : overview.rows) {
      String sel = row.selected ? "*" : " ";
      String en = row.enabled ? "Y" : "N";
      String type = row.type != null ? row.type : "?";
      String name = row.name != null ? row.name : "(unnamed)";
      String motors = (row.motors == null || row.motors.isEmpty())
          ? "-"
          : String.join(", ", row.motors);
      appendLine(
          sb,
          String.format(
              "%3d  %s  %s  %-9s %-28s %s",
              row.index,
              sel,
              en,
              type,
              name,
              motors));
    }
    appendLine(sb, "=====================");
    return sb.toString();
  }

  /**
   * NAME
   *   resolveTestType - Resolve a human-readable test type name.
   */
  private static String resolveTestType(BringupTest test) {
    if (test instanceof CompositeTest) {
      return CompositeTest.TYPE;
    }
    if (test instanceof JoystickTest) {
      return JoystickTest.TYPE;
    }
    return test != null ? test.getClass().getSimpleName() : "?";
  }

  /**
   * NAME
   *   TestsOverview - Snapshot of bringup tests for UI/reporting.
   */
  public static final class TestsOverview {
    public String activeTestSet;
    public String defaultTestSet;
    public boolean usingTestSets;
    public int totalCount;
    public int enabledCount;
    public final List<TestRow> rows = new ArrayList<>();
  }

  /**
   * NAME
   *   TestRow - Single test row within a TestsOverview.
   */
  public static final class TestRow {
    public int index;
    public String name;
    public boolean enabled;
    public boolean selected;
    public String type;
    public String status;
    public List<String> motors = new ArrayList<>();
  }

  /**
   * NAME
   *   startNextRunAllTest - Start the next test in the run-all queue.
   *
   * RETURNS
   *   True when a test is started.
   */
  private boolean startNextRunAllTest() {
    if (runAllQueue.isEmpty()) {
      return false;
    }
    while (runAllIndex < runAllQueue.size()) {
      BringupTest test = runAllQueue.get(runAllIndex++);
      boolean started = test.start(testContext, Timer.getFPGATimestamp());
      if (started) {
        activeTest = test;
        BringupPrinter.enqueue("Test: " + test.getName());
        return true;
      }
      BringupPrinter.enqueue("Test skipped: " + test.getName() + " (" + test.getStatus() + ")");
    }
    return false;
  }

  /**
   * NAME
   *   buildRunAllQueue - Build the run-all queue from enabled tests.
   */
  private void buildRunAllQueue() {
    runAllQueue.clear();
    runAllIndex = 0;
    if (selectableTests.isEmpty()) {
      return;
    }
    int startIndex = selectedTestIndex < 0 ? 0 : selectedTestIndex;
    int attempts = selectableTests.size();
    int index = startIndex;
    while (attempts-- > 0) {
      BringupTest test = selectableTests.get(index);
      if (test != null && test.isEnabled()) {
        runAllQueue.add(test);
      }
      index = (index + 1) % selectableTests.size();
    }
  }

  /**
   * NAME
   *   startNextBringupTest - Start the next enabled bringup test.
   *
   * RETURNS
   *   True when a test is started.
   */
  private boolean startNextBringupTest() {
    if (bringupTests.isEmpty()) {
      return false;
    }
    int attempts = bringupTests.size();
    while (attempts-- > 0) {
      BringupTest test = bringupTests.get(nextBringupTestIndex);
      nextBringupTestIndex = (nextBringupTestIndex + 1) % bringupTests.size();
      if (!test.isEnabled()) {
        continue;
      }
      boolean started = test.start(testContext, Timer.getFPGATimestamp());
      if (started) {
        activeTest = test;
        BringupPrinter.enqueue("Test: " + test.getName());
        return true;
      }
      BringupPrinter.enqueue("Test skipped: " + test.getName() + " (" + test.getStatus() + ")");
    }
    BringupPrinter.enqueue("No enabled bringup tests.");
    return false;
  }

  // Alternates between REV and CTRE motors to keep bringup balanced.
  /**
   * NAME
   *   addNextMotor - Instantiate the next motor, alternating vendors.
   *
   * SIDE EFFECTS
   *   Creates devices and enqueues status messages.
   */
  private void addNextMotor() {
    if (addRevNext) {
      DeviceAddResult result = revDevices.addNextMotor();
      if (result != null) {
        BringupPrinter.enqueue(
            "Added " + result.registration().displayName() +
            " index " + result.index() +
            " (CAN " + result.device().getCanId() + ")");
        addRevNext = false;
        return;
      }
    }

    DeviceAddResult ctreResult = ctreDevices.addNextMotor();
    if (ctreResult != null) {
      BringupPrinter.enqueue(
          "Added " + ctreResult.registration().displayName() +
          " index " + ctreResult.index() +
          " (CAN " + ctreResult.device().getCanId() + ")");
      addRevNext = true;
      return;
    }

    DeviceAddResult revResult = revDevices.addNextMotor();
    if (revResult != null) {
      BringupPrinter.enqueue(
          "Added " + revResult.registration().displayName() +
          " index " + revResult.index() +
          " (CAN " + revResult.device().getCanId() + ")");
      addRevNext = false;
      return;
    }

    BringupPrinter.enqueue("No more motors to add");
    addRevNext = true;
  }

  /**
   * NAME
   *   addAllDevices - Instantiate all configured devices. (motors + sensors + misc).
   */
  private void addAllDevices() {
    revDevices.addAll();
    ctreDevices.addAll();
    addRevNext = true;
    BringupPrinter.enqueue("Added all REV and CTRE devices.");
  }

  // Print a compact list of which devices are instantiated.
  /**
   * NAME
   *   printState - Enqueue a compact state report of instantiated devices.
   */
  private void printState() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Bringup State ===");
    revDevices.appendState(sb);
    ctreDevices.appendState(sb);
    appendLine(sb, "Next add will be: " + (addRevNext ? "REV motor" : "CTRE motor"));
    appendVirtualDevices(sb);
    appendLine(sb, "=====================");
    BringupPrinter.enqueueChunked(sb.toString(), 4);
  }

  /**
   * NAME
   *   printHealthStatus - Enqueue a detailed local health report.
   *
   * NOTES
   *   Uses only robot-local vendor APIs (no PC sniffer data).
   */
  private void printHealthStatus() {
    requestHealthReport();
  }

  /**
   * NAME
   *   updateReports - Advance queued report printing.
   *
   * DESCRIPTION
   *   Processes one report chunk per call to avoid blocking the main loop.
   */
  public void updateReports() {
    if (activeReport == null) {
      activeReport = reportQueue.pollFirst();
      if (activeReport == null) {
        return;
      }
      activeReport.start();
    }
    if (activeReport.step(REPORT_BATCH)) {
      BringupPrinter.enqueueChunked(activeReport.getBuffer().toString(), activeReport.getChunkSize());
      activeReport = null;
    }
  }

  /**
   * NAME
   *   requestStateReport - Queue a state report.
   */
  public void requestStateReport() {
    reportQueue.addLast(buildStateReport());
  }

  /**
   * NAME
   *   requestHealthReport - Queue a health report.
   */
  public void requestHealthReport() {
    reportQueue.addLast(buildHealthReport());
  }

  /**
   * NAME
   *   requestCANCoderReport - Queue a CANCoder report.
   */
  public void requestCANCoderReport() {
    reportQueue.addLast(buildCANCoderReport());
  }

  /**
   * NAME
   *   requestSweepReport - Queue a CAN sweep report.
   */
  public void requestSweepReport() {
    reportQueue.addLast(buildSweepReport());
  }

  /**
   * NAME
   *   requestTextReport - Queue a raw text report.
   *
   * PARAMETERS
   *   text - Report content.
   *   chunkSize - Lines per print chunk.
   */
  public void requestTextReport(String text, int chunkSize) {
    if (text == null || text.isBlank()) {
      return;
    }
    reportQueue.addLast(new TextReportJob(text, chunkSize));
  }

  /**
   * NAME
   *   requestTextReportLines - Queue a report with header and footer.
   *
   * PARAMETERS
   *   header - Optional header line.
   *   lines - Body lines.
   *   footer - Optional footer line.
   *   chunkSize - Lines per print chunk.
   */
  public void requestTextReportLines(
      String header,
      List<String> lines,
      String footer,
      int chunkSize) {
    reportQueue.addLast(new TextReportJob(header, lines, footer, chunkSize));
  }

  /**
   * NAME
   *   collectHealthItems - Collect motor devices for health reporting.
   */
  private void collectHealthItems(List<DevicePrintItem> out, ManufacturerGroup group) {
    for (DeviceTypeBucket bucket : group.getDeviceBuckets()) {
      if (bucket.getRegistration().role() != DeviceRole.MOTOR) {
        continue;
      }
      List<DeviceUnit> bucketDevices = bucket.getDevices();
      for (int i = 0; i < bucketDevices.size(); i++) {
        out.add(new DevicePrintItem(bucket, bucketDevices.get(i), i));
      }
    }
  }

  /**
   * NAME
   *   appendHealthDevice - Append health status for a single device.
   */
  private void appendHealthDevice(StringBuilder sb, DevicePrintItem item, double nowSec) {
    DeviceTypeBucket bucket = item.bucket;
    DeviceUnit device = item.device;
    DeviceSnapshot snap = snapshotDevice(bucket, item.index, nowSec);
    if (!snap.present) {
      sb.append(bucket.getRegistration().displayName())
          .append(" index ").append(item.index)
          .append(" CAN ").append(device.getCanId())
          .append(" not added\n");
      return;
    }
    RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
    CtreMotorAttachment ctre = snap.getAttachment(CtreMotorAttachment.class);
    MotorSpecAttachment spec = snap.getAttachment(MotorSpecAttachment.class);
    LimitsAttachment limits = snap.getAttachment(LimitsAttachment.class);
    if (rev != null) {
      sb.append(bucket.getRegistration().displayName())
          .append(" index ").append(item.index)
          .append(" CAN ").append(device.getCanId())
          .append(BringupHealthFormat.formatRevFaultSummary(rev))
          .append(" lastErr=").append(BringupHealthFormat.safeText(rev.lastError))
          .append(BringupHealthFormat.safeText(rev.healthNote))
          .append(BringupHealthFormat.safeText(rev.lowCurrentNote))
          .append(BringupHealthFormat.formatMotorSpecNote(spec, rev.motorCurrentA))
          .append(BringupHealthFormat.formatLimitSummary(limits))
          .append(" busV=").append(String.format("%.2f", BringupHealthFormat.safeDouble(rev.busV))).append("V")
          .append(" appliedDuty=").append(String.format("%.2f", BringupHealthFormat.safeDouble(rev.appliedDuty))).append("dc")
          .append(" appliedV=").append(String.format("%.2f", BringupHealthFormat.safeDouble(rev.appliedV))).append("V")
          .append(" motorCurrentA=").append(String.format("%.4f", BringupHealthFormat.safeDouble(rev.motorCurrentA))).append("A")
          .append(" tempC=").append(String.format("%.1f", BringupHealthFormat.safeDouble(rev.tempC))).append("C")
          .append(" cmdDuty=").append(String.format("%.2f", BringupHealthFormat.safeDouble(rev.cmdDuty))).append("dc")
          .append(" follower=").append(rev.follower ? "Y" : "N")
          .append('\n');
      return;
    }
    if (ctre != null) {
      sb.append(bucket.getRegistration().displayName())
          .append(" index ").append(item.index)
          .append(" CAN ").append(device.getCanId())
          .append(BringupHealthFormat.formatCtreFaultSummary(ctre))
          .append(BringupHealthFormat.formatMotorSpecNote(spec, ctre.motorCurrentA))
          .append(BringupHealthFormat.formatLimitSummary(limits))
          .append(" busV=").append(String.format("%.2f", BringupHealthFormat.safeDouble(ctre.busV))).append("V")
          .append(" appliedDuty=").append(String.format("%.2f", BringupHealthFormat.safeDouble(ctre.appliedDuty))).append("dc")
          .append(" appliedV=").append(String.format("%.2f", BringupHealthFormat.safeDouble(ctre.appliedV))).append("V")
          .append(" motorCurrentA=").append(String.format("%.4f", BringupHealthFormat.safeDouble(ctre.motorCurrentA))).append("A")
          .append(" tempC=").append(String.format("%.1f", BringupHealthFormat.safeDouble(ctre.tempC))).append("C")
          .append(ctre.faultStatus.isBlank() && ctre.stickyStatus.isBlank()
              ? ""
              : " status=" + ctre.faultStatus + "/" + ctre.stickyStatus)
          .append('\n');
      return;
    }
    sb.append(bucket.getRegistration().displayName())
        .append(" index ").append(item.index)
        .append(" CAN ").append(device.getCanId())
        .append(" present=YES")
        .append(BringupHealthFormat.formatLimitSummary(limits))
        .append('\n');
  }

  /**
   * NAME
   *   appendStateDevice - Append state row for a single device.
   */
  private void appendStateDevice(StringBuilder sb, DevicePrintItem item) {
    DeviceTypeBucket bucket = item.bucket;
    if (item.firstInBucket) {
      sb.append(bucket.getRegistration().displayName()).append(":\n");
    }
    sb.append("  index ").append(item.index)
        .append(" CAN ").append(item.device.getCanId())
        .append(item.device.isCreated() ? " ACTIVE" : " not added")
        .append('\n');
  }

  /**
   * NAME
   *   appendSweepDevice - Append sweep status for a single device.
   */
  private void appendSweepDevice(StringBuilder sb, DevicePrintItem item, double nowSec) {
    DeviceTypeBucket bucket = item.bucket;
    if (item.firstInBucket) {
      sb.append(bucket.getRegistration().displayName()).append(":\n");
    }
    DeviceUnit device = item.device;
    if (!device.isCreated()) {
      sb.append("  index ").append(item.index)
          .append(" CAN ").append(device.getCanId())
          .append(" NOT_ADDED\n");
      return;
    }
    DeviceSnapshot snap = snapshotDevice(bucket, item.index, nowSec);
    sb.append("  index ").append(item.index)
        .append(" CAN ").append(device.getCanId())
        .append(" ").append(buildSweepStatus(snap))
        .append('\n');
  }

  /**
   * NAME
   *   appendCANCoderDevice - Append absolute position for a CANCoder device.
   */
  private void appendCANCoderDevice(StringBuilder sb, DevicePrintItem item) {
    DeviceUnit device = item.device;
    device.ensureCreated();
    DeviceSnapshot snap = device.snapshot();
    EncoderAttachment encoder = snap.getAttachment(EncoderAttachment.class);
    double degrees = BringupHealthFormat.safeDouble(encoder != null ? encoder.absDeg : null);
    double rotations = degrees / 360.0;
    sb.append(item.bucket.getRegistration().displayName())
        .append(" index ").append(item.index)
        .append(" CAN ").append(device.getCanId())
        .append(" absRot=").append(String.format("%.4f", rotations))
        .append(" absDeg=").append(String.format("%.1f", degrees))
        .append('\n');
  }

  /**
   * NAME
   *   snapshotDevice - Capture a snapshot with shared motor spec enrichment.
   *
   * PARAMETERS
   *   bucket - Device bucket containing the device.
   *   index - Index within the bucket.
   *   nowSec - Current time in seconds for timestamping.
   *
   * RETURNS
   *   Populated DeviceSnapshot for reporting.
   */
  private DeviceSnapshot snapshotDevice(DeviceTypeBucket bucket, int index, double nowSec) {
    DeviceUnit device = bucket.getDevices().get(index);
    DeviceSnapshot snap = device.snapshot();
    if (bucket.getRegistration().role() == DeviceRole.MOTOR) {
      fillSpecForMotor(snap, device.getLabel(), device.getMotorModelOverride());
      if ("REV".equalsIgnoreCase(bucket.getRegistration().vendor()) && snap.present) {
        RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
        if (rev != null) {
          rev.healthNote = buildRevHealthNote(
              rev.lastError,
              BringupHealthFormat.safeDouble(rev.busV));
          if (bucket.tracksLowCurrent()) {
            rev.lowCurrentNote = buildLowCurrentNote(
                bucket.getLowCurrentStartSec(),
                index,
                nowSec,
                BringupHealthFormat.safeDouble(rev.appliedV),
                BringupHealthFormat.safeDouble(rev.motorCurrentA));
          }
        }
      }
    }
    return snap;
  }

  /**
   * NAME
   *   fillSpecForMotor - Attach motor specification data to a snapshot.
   *
   * PARAMETERS
   *   snap - Snapshot to enrich.
   *   label - Device label used for spec lookup.
   *   modelOverride - Optional motor model override.
   */
  private void fillSpecForMotor(DeviceSnapshot snap, String label, String modelOverride) {
    snap.label = label;
    BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
    if (spec == null) {
      return;
    }
    MotorSpecAttachment motorSpec = new MotorSpecAttachment();
    motorSpec.model = spec.model;
    motorSpec.nominalV = spec.nominalVoltage;
    motorSpec.freeCurrentA = spec.freeCurrentA;
    motorSpec.stallCurrentA = spec.stallCurrentA;
    snap.addAttachment(motorSpec);
  }

  /**
   * NAME
   *   buildRevHealthNote - Produce a short REV health note.
   *
   * PARAMETERS
   *   lastError - Last reported REV error string.
   *   busVoltage - Current bus voltage.
   *
   * RETURNS
   *   Short note string or empty when no note applies.
   */
  private String buildRevHealthNote(String lastError, double busVoltage) {
    if (lastError == null || lastError.isBlank()) {
      return "";
    }
    if (!"kOk".equals(lastError) && busVoltage < 7.0) {
      return " lowBusV";
    }
    if (!"kOk".equals(lastError)) {
      return " lastErr=" + lastError;
    }
    return "";
  }

  /**
   * NAME
   *   buildLowCurrentNote - Detect sustained low-current behavior.
   *
   * PARAMETERS
   *   lowCurrentStart - Per-device start times for low-current tracking.
   *   index - Device index in the bucket.
   *   nowSec - Current time in seconds.
   *   appliedVolts - Applied motor voltage.
   *   currentA - Measured motor current.
   *
   * RETURNS
   *   Short note string or empty when no note applies.
   */
  private String buildLowCurrentNote(
      double[] lowCurrentStart,
      int index,
      double nowSec,
      double appliedVolts,
      double currentA) {
    final double lowCurrentAppliedVMin = 1.0;
    final double lowCurrentAMax = 0.05;
    final double lowCurrentMinSec = 1.0;
    boolean lowCurrentNow =
        Math.abs(appliedVolts) >= lowCurrentAppliedVMin && Math.abs(currentA) <= lowCurrentAMax;
    if (!lowCurrentNow) {
      lowCurrentStart[index] = -1.0;
      return "";
    }
    if (lowCurrentStart[index] < 0.0) {
      lowCurrentStart[index] = nowSec;
      return "";
    }
    if (nowSec - lowCurrentStart[index] < lowCurrentMinSec) {
      return "";
    }
    return " lowCurrent";
  }

  /**
   * NAME
   *   buildStateReport - Build a queued state report job.
   */
  private DeviceReportJob buildStateReport() {
    List<DevicePrintItem> items = collectDeviceItems();
    DeviceReportJob job = new DeviceReportJob(
        "=== Bringup State ===",
        "=====================",
        4,
        items,
        (sb, item) -> appendStateDevice(sb, item));
    job.onComplete = () -> {
      StringBuilder sb = job.buffer;
      appendLine(sb, "Next add will be: " + (addRevNext ? "REV motor" : "CTRE motor"));
      appendVirtualDevices(sb);
    };
    return job;
  }

  /**
   * NAME
   *   buildHealthReport - Build a queued health report job.
   */
  private DeviceReportJob buildHealthReport() {
    List<DevicePrintItem> items = new ArrayList<>();
    collectHealthItems(items, revDevices);
    collectHealthItems(items, ctreDevices);
    final DeviceReportJob[] jobRef = new DeviceReportJob[1];
    DeviceReportJob job = new DeviceReportJob(
        "=== Bringup Health (Local Robot Data) ===",
        "======================",
        4,
        items,
        (sb, item) -> appendHealthDevice(sb, item, jobRef[0].nowSec));
    jobRef[0] = job;
    job.onComplete = () -> appendVirtualDeviceHealth(job.buffer);
    return job;
  }

  /**
   * NAME
   *   buildCANCoderReport - Build a queued CANCoder report job.
   */
  private DeviceReportJob buildCANCoderReport() {
    List<DevicePrintItem> items = collectDeviceItems(DeviceRole.ENCODER);
    DeviceReportJob job = new DeviceReportJob(
        "=== Bringup CANCoder ===",
        "=======================",
        4,
        items,
        (sb, item) -> appendCANCoderDevice(sb, item));
    return job;
  }

  /**
   * NAME
   *   buildSweepReport - Build a queued sweep report job.
   */
  private DeviceReportJob buildSweepReport() {
    List<DevicePrintItem> items = collectDeviceItems();
    final DeviceReportJob[] jobRef = new DeviceReportJob[1];
    DeviceReportJob job = new DeviceReportJob(
        "=== CAN Ping Sweep (Local Vendor API) ===",
        "==============================",
        6,
        items,
        (sb, item) -> appendSweepDevice(sb, item, jobRef[0].nowSec));
    jobRef[0] = job;
    job.onComplete = () -> appendLine(job.buffer, "Note: Devices must be added to be probed (use addAll).");
    return job;
  }

  /**
   * NAME
   *   collectDeviceItems - Collect device items across all roles.
   */
  private List<DevicePrintItem> collectDeviceItems() {
    List<DevicePrintItem> items = new ArrayList<>();
    collectDeviceItems(items, revDevices, null);
    collectDeviceItems(items, ctreDevices, null);
    return items;
  }

  /**
   * NAME
   *   collectDeviceItems - Collect device items for a specific role.
   */
  private List<DevicePrintItem> collectDeviceItems(DeviceRole role) {
    List<DevicePrintItem> items = new ArrayList<>();
    collectDeviceItems(items, revDevices, role);
    collectDeviceItems(items, ctreDevices, role);
    return items;
  }

  /**
   * NAME
   *   collectDeviceItems - Add devices from a group, optionally filtered by role.
   */
  private void collectDeviceItems(List<DevicePrintItem> out, ManufacturerGroup group, DeviceRole role) {
    for (DeviceTypeBucket bucket : group.getDeviceBuckets()) {
      if (role != null && bucket.getRegistration().role() != role) {
        continue;
      }
      List<DeviceUnit> bucketDevices = bucket.getDevices();
      for (int i = 0; i < bucketDevices.size(); i++) {
        out.add(new DevicePrintItem(bucket, bucketDevices.get(i), i));
      }
    }
  }

  /**
   * NAME
   *   DevicePrintItem - Helper container for report rendering.
   */
  private static final class DevicePrintItem {
    private final DeviceTypeBucket bucket;
    private final DeviceUnit device;
    private final int index;
    private boolean firstInBucket;

    private DevicePrintItem(DeviceTypeBucket bucket, DeviceUnit device, int index) {
      this.bucket = bucket;
      this.device = device;
      this.index = index;
      this.firstInBucket = false;
    }
  }

  /**
   * NAME
   *   ReportJobBase - Interface for queued report jobs.
   */
  private interface ReportJobBase {
    void start();
    boolean step(int batch);
    int getChunkSize();
    StringBuilder getBuffer();
  }

  /**
   * NAME
   *   DeviceReportJob - Report job that iterates device items.
   */
  private static final class DeviceReportJob implements ReportJobBase {
    private final String header;
    private final String footer;
    private final int chunkSize;
    private final List<DevicePrintItem> items;
    private final java.util.function.BiConsumer<StringBuilder, DevicePrintItem> appender;
    private final StringBuilder buffer = new StringBuilder(768);
    private int index = 0;
    private double nowSec = 0.0;
    private Runnable onComplete = null;

    private DeviceReportJob(
        String header,
        String footer,
        int chunkSize,
        List<DevicePrintItem> items,
        java.util.function.BiConsumer<StringBuilder, DevicePrintItem> appender) {
      this.header = header;
      this.footer = footer;
      this.chunkSize = chunkSize;
      this.items = items;
      this.appender = appender;
    }

    /**
     * NAME
     *   start - Initialize the report buffer and timestamps.
     */
    public void start() {
      buffer.setLength(0);
      appendLine(buffer, header);
      nowSec = Timer.getFPGATimestamp();
      markFirstInBuckets();
    }

    /**
     * NAME
     *   step - Append up to batch items and indicate completion.
     */
    public boolean step(int batch) {
      int processed = 0;
      while (index < items.size() && processed < batch) {
        appender.accept(buffer, items.get(index++));
        processed++;
      }
      if (index < items.size()) {
        return false;
      }
      if (onComplete != null) {
        onComplete.run();
      }
      appendLine(buffer, footer);
      return true;
    }

    /**
     * NAME
     *   markFirstInBuckets - Flag the first item for each bucket.
     */
    private void markFirstInBuckets() {
      DeviceTypeBucket last = null;
      for (DevicePrintItem item : items) {
        if (item.bucket != last) {
          item.firstInBucket = true;
          last = item.bucket;
        }
      }
    }

    /**
     * NAME
     *   getChunkSize - Return preferred output chunk size.
     */
    public int getChunkSize() {
      return chunkSize;
    }

    /**
     * NAME
     *   getBuffer - Return the report buffer.
     */
    public StringBuilder getBuffer() {
      return buffer;
    }
  }

  /**
   * NAME
   *   TextReportJob - Report job for text-only output.
   */
  private static final class TextReportJob implements ReportJobBase {
    private final String header;
    private final String footer;
    private final int chunkSize;
    private final List<String> lines;
    private final StringBuilder buffer = new StringBuilder(512);
    private int index = 0;

    private TextReportJob(String text, int chunkSize) {
      this.header = null;
      this.footer = null;
      this.chunkSize = chunkSize;
      this.lines = splitLines(text);
    }

    private TextReportJob(String header, List<String> lines, String footer, int chunkSize) {
      this.header = header;
      this.footer = footer;
      this.chunkSize = chunkSize;
      this.lines = lines != null ? lines : List.of();
    }

    /**
     * NAME
     *   start - Initialize the text report buffer.
     */
    public void start() {
      buffer.setLength(0);
      index = 0;
      if (header != null && !header.isBlank()) {
        appendLine(buffer, header);
      }
    }

    /**
     * NAME
     *   step - Append up to batch lines and indicate completion.
     */
    public boolean step(int batch) {
      int processed = 0;
      while (index < lines.size() && processed < batch) {
        appendLine(buffer, lines.get(index++));
        processed++;
      }
      if (index < lines.size()) {
        return false;
      }
      if (footer != null && !footer.isBlank()) {
        appendLine(buffer, footer);
      }
      return true;
    }

    /**
     * NAME
     *   getChunkSize - Return preferred output chunk size.
     */
    public int getChunkSize() {
      return chunkSize;
    }

    /**
     * NAME
     *   getBuffer - Return the report buffer.
     */
    public StringBuilder getBuffer() {
      return buffer;
    }
  }

  /**
   * NAME
   *   splitLines - Split text into lines, trimming trailing blanks.
   */
  private static List<String> splitLines(String text) {
    if (text == null || text.isEmpty()) {
      return List.of();
    }
    String[] raw = text.split("\\R", -1);
    int end = raw.length;
    while (end > 0 && raw[end - 1].isEmpty()) {
      end--;
    }
    List<String> lines = new ArrayList<>(end);
    for (int i = 0; i < end; i++) {
      lines.add(raw[i]);
    }
    return lines;
  }

  /**
   * NAME
   *   printCANCoderStatus - Enqueue absolute position report for CANCoders.
   */
  private void printCANCoderStatus() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Bringup CANCoder ===");
    appendEncoderStatus(sb, revDevices);
    appendEncoderStatus(sb, ctreDevices);
    appendLine(sb, "=======================");
    BringupPrinter.enqueueChunked(sb.toString(), 4);
  }

  /**
   * NAME
   *   appendSweepGroup - Append sweep output for a manufacturer group.
   */
  private void appendSweepGroup(StringBuilder sb, ManufacturerGroup group) {
    for (DeviceTypeBucket bucket : group.getDeviceBuckets()) {
      List<DeviceUnit> devices = bucket.getDevices();
      if (devices.isEmpty()) {
        continue;
      }
      sb.append(bucket.getRegistration().displayName()).append(":\n");
      for (int i = 0; i < devices.size(); i++) {
        DeviceUnit device = devices.get(i);
        if (!device.isCreated()) {
          sb.append("  index ").append(i)
              .append(" CAN ").append(device.getCanId())
              .append(" NOT_ADDED\n");
          continue;
        }
        DeviceSnapshot snap = device.snapshot();
        sb.append("  index ").append(i)
            .append(" CAN ").append(device.getCanId())
            .append(" ").append(buildSweepStatus(snap))
            .append('\n');
      }
    }
  }

  /**
   * NAME
   *   buildSweepStatus - Build a short status string for sweep output.
   */
  private String buildSweepStatus(DeviceSnapshot snap) {
    if (snap == null) {
      return "NO_DATA";
    }
    RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
    if (rev != null) {
      String lastErr = BringupHealthFormat.safeText(rev.lastError);
      if (lastErr.isBlank() || "kOk".equals(lastErr)) {
        return "OK";
      }
      return "WARN lastErr=" + lastErr;
    }
    CtreMotorAttachment ctre = snap.getAttachment(CtreMotorAttachment.class);
    if (ctre != null) {
      String status = BringupHealthFormat.safeText(ctre.faultStatus);
      if (!status.isBlank() && status.toUpperCase().contains("OK")) {
        return "OK";
      }
      return status.isBlank() ? "WARN status=UNKNOWN" : "WARN status=" + status;
    }
    return snap.present ? "OK" : "NO_DATA";
  }

  /**
   * NAME
   *   appendEncoderStatus - Append absolute encoder positions for a group.
   */
  private void appendEncoderStatus(StringBuilder sb, ManufacturerGroup group) {
    for (DeviceTypeBucket bucket : group.getDeviceBuckets()) {
      if (bucket.getRegistration().role() != DeviceRole.ENCODER) {
        continue;
      }
      List<DeviceUnit> devices = bucket.getDevices();
      for (int i = 0; i < devices.size(); i++) {
        DeviceUnit device = devices.get(i);
        device.ensureCreated();
        DeviceSnapshot snap = device.snapshot();
        EncoderAttachment encoder = snap.getAttachment(EncoderAttachment.class);
        double degrees = BringupHealthFormat.safeDouble(encoder != null ? encoder.absDeg : null);
        double rotations = degrees / 360.0;
        appendLine(sb,
            bucket.getRegistration().displayName() + " index " + i +
            " CAN " + device.getCanId() +
            " absRot=" + String.format("%.4f", rotations) +
            " absDeg=" + String.format("%.1f", degrees));
      }
    }
  }

  /**
   * NAME
   *   captureSnapshots - Capture local device snapshots.
   *
   * RETURNS
   *   List of DeviceSnapshot objects for report generation.
   */
  public List<DeviceSnapshot> captureSnapshots() {
    List<DeviceSnapshot> devices = new ArrayList<>();
    double nowSec = Timer.getFPGATimestamp();
    devices.addAll(revDevices.captureSnapshots(nowSec));
    devices.addAll(ctreDevices.captureSnapshots(nowSec));

    if (BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)) {
      DeviceSnapshot snap = new DeviceSnapshot();
      snap.vendor = "NI";
      snap.deviceType = "roboRIO";
      snap.canId = BringupUtil.ROBORIO_CAN_ID;
      snap.present = true;
      snap.note = "virtual";
      devices.add(snap);
    }

    return devices;
  }

  /**
   * NAME
   *   appendVirtualDevices - Append virtual device entries to state output.
   */
  private void appendVirtualDevices(StringBuilder sb) {
    if (!BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)) {
      return;
    }
    appendLine(sb, "Virtual devices:");
    appendLine(sb, "  roboRIO CAN " + BringupUtil.ROBORIO_CAN_ID + " PRESENT (no local API)");
  }

  /**
   * NAME
   *   appendVirtualDeviceHealth - Append virtual device entries to health output.
   */
  private void appendVirtualDeviceHealth(StringBuilder sb) {
    if (!BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)) {
      return;
    }
    appendLine(sb, "  roboRIO CAN " + BringupUtil.ROBORIO_CAN_ID + ": present=YES (virtual, no API)");
  }

  /**
   * NAME
   *   isDeviceInstantiated - Check if a device is instantiated locally.
   *
   * PARAMETERS
   *   manufacturer - CAN manufacturer ID.
   *   deviceType - CAN device type ID.
   *   deviceId - CAN device ID.
   *
   * RETURNS
   *   True when the device is created in local vendor APIs.
   */
  public boolean isDeviceInstantiated(int manufacturer, int deviceType, int deviceId) {
    if (manufacturer == NI_MANUFACTURER && deviceType == TYPE_ROBOT_CONTROLLER) {
      return BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)
          && deviceId == BringupUtil.ROBORIO_CAN_ID;
    }

    String vendor = BringupUtil.getCanManufacturerName(manufacturer);
    String category = BringupUtil.getCanDeviceTypeName(deviceType);
    if (vendor == null || category == null) {
      return false;
    }

    DeviceRole role = mapRoleFromCategory(category);
    if (role == null) {
      return false;
    }

    if ("REV".equalsIgnoreCase(vendor)) {
      return isInstantiatedByRole(revDevices, role, deviceId);
    }
    if ("CTRE".equalsIgnoreCase(vendor)) {
      return isInstantiatedByRole(ctreDevices, role, deviceId);
    }
    return false;
  }

  /**
   * NAME
   *   isInstantiatedByRole - Check instantiation for a role within a group.
   */
  private boolean isInstantiatedByRole(ManufacturerGroup group, DeviceRole role, int deviceId) {
    for (DeviceTypeBucket bucket : group.getDeviceBuckets()) {
      if (bucket.getRegistration().role() != role) {
        continue;
      }
      for (DeviceUnit device : bucket.getDevices()) {
        if (device.getCanId() == deviceId) {
          return device.isCreated();
        }
      }
    }
    return false;
  }

  /**
   * NAME
   *   mapRoleFromCategory - Map CAN category strings to DeviceRole.
   */
  private DeviceRole mapRoleFromCategory(String category) {
    if ("MotorController".equalsIgnoreCase(category)) {
      return DeviceRole.MOTOR;
    }
    if ("Encoder".equalsIgnoreCase(category)) {
      return DeviceRole.ENCODER;
    }
    if ("Miscellaneous".equalsIgnoreCase(category)) {
      return DeviceRole.MISC;
    }
    return null;
  }

  /**
   * NAME
   *   appendLine - Append a line with newline termination.
   */
  private static void appendLine(StringBuilder sb, String line) {
    sb.append(line).append('\n');
  }
}
