package frc.robot;

import edu.wpi.first.wpilibj.Timer;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.EncoderAttachment;
import frc.robot.manufacturers.CtreDeviceGroup;
import frc.robot.manufacturers.DeviceAddResult;
import frc.robot.manufacturers.DeviceRole;
import frc.robot.manufacturers.DeviceTypeBucket;
import frc.robot.manufacturers.ManufacturerGroup;
import frc.robot.manufacturers.RevDeviceGroup;
import frc.robot.tests.BringupTest;
import frc.robot.tests.BringupTestContext;
import frc.robot.tests.BringupTestRegistry;
import frc.robot.tests.BringupTestResult;
import frc.robot.tests.CompositeTest;
import frc.robot.tests.JoystickTest;
import java.util.ArrayList;
import java.util.List;

// Core bringup logic: creates devices, commands outputs, and prints local health.
// This class only uses robot-local vendor APIs (no PC sniffer data).
public final class BringupCore {
  private static final int NI_MANUFACTURER = 1;
  private static final int TYPE_ROBOT_CONTROLLER = 1;
  private static final long MIN_PRINT_INTERVAL_MS = 1000;

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
  public void handleAdd(boolean addNow) {
    if (addNow && !prevAdd) {
      addNextMotor();
    }
    prevAdd = addNow;
  }

  // Edge-triggered: instantiate all configured devices at once.
  public void handleAddAll(boolean addAllNow) {
    if (addAllNow && !prevAddAll) {
      addAllDevices();
    }
    prevAddAll = addAllNow;
  }

  // Edge-triggered: print a concise state summary.
  public void handlePrint(boolean printNow) {
    if (printNow && !prevPrint) {
      long nowMs = System.currentTimeMillis();
      if (nowMs - lastStatePrintMs >= MIN_PRINT_INTERVAL_MS) {
        lastStatePrintMs = nowMs;
        printState();
      }
    }
    prevPrint = printNow;
  }

  // Edge-triggered: print local health for all instantiated devices.
  public void handleHealth(boolean healthNow) {
    if (healthNow && !prevHealth) {
      long nowMs = System.currentTimeMillis();
      if (nowMs - lastHealthPrintMs >= MIN_PRINT_INTERVAL_MS) {
        lastHealthPrintMs = nowMs;
        printHealthStatus();
      }
    }
    prevHealth = healthNow;
  }

  // Edge-triggered: print CANCoder absolute position data.
  public void handleCANCoder(boolean printNow) {
    if (printNow && !prevCANCoder) {
      long nowMs = System.currentTimeMillis();
      if (nowMs - lastCANCoderPrintMs >= MIN_PRINT_INTERVAL_MS) {
        lastCANCoderPrintMs = nowMs;
        printCANCoderStatus();
      }
    }
    prevCANCoder = printNow;
  }

  // Apply requested speeds to all instantiated motors.
  public void setSpeeds(double neoSpeed, double krakenSpeed) {
    if (activeTest != null && activeTest.isRunning()) {
      return;
    }
    revDevices.setDuty(neoSpeed);
    ctreDevices.setDuty(krakenSpeed);
  }

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
  public void clearAllFaults() {
    revDevices.clearFaults();
    ctreDevices.clearFaults();
  }

  // Stop all outputs, close devices, and reset internal state.
  public void resetState() {
    resetState("reset");
  }

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

  public void updateTests() {
    updateTests(false);
  }

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

  private void refreshTestDevices() {
    testDevices.clear();
    testDevices.addAll(ctreDevices.getTestDevices());
    testDevices.addAll(revDevices.getTestDevices());
    nextTestIndex = 0;
  }

  private void refreshSelectableTests() {
    selectableTests.clear();
    for (BringupTest test : bringupTests) {
      if (test != null) {
        selectableTests.add(test);
      }
    }
    selectedTestIndex = selectableTests.isEmpty() ? -1 : 0;
  }

  private BringupTest getSelectedBringupTest() {
    if (selectableTests.isEmpty() || selectedTestIndex < 0) {
      return null;
    }
    if (selectedTestIndex >= selectableTests.size()) {
      selectedTestIndex = 0;
    }
    return selectableTests.get(selectedTestIndex);
  }

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

  private static String resolveTestType(BringupTest test) {
    if (test instanceof CompositeTest) {
      return CompositeTest.TYPE;
    }
    if (test instanceof JoystickTest) {
      return JoystickTest.TYPE;
    }
    return test != null ? test.getClass().getSimpleName() : "?";
  }

  public static final class TestsOverview {
    public String activeTestSet;
    public String defaultTestSet;
    public boolean usingTestSets;
    public int totalCount;
    public int enabledCount;
    public final List<TestRow> rows = new ArrayList<>();
  }

  public static final class TestRow {
    public int index;
    public String name;
    public boolean enabled;
    public boolean selected;
    public String type;
    public String status;
    public List<String> motors = new ArrayList<>();
  }

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

  // Instantiate all configured devices (motors + sensors + misc).
  private void addAllDevices() {
    revDevices.addAll();
    ctreDevices.addAll();
    addRevNext = true;
    BringupPrinter.enqueue("Added all REV and CTRE devices.");
  }

  // Print a compact list of which devices are instantiated.
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

  // Print detailed local health with faults, warnings, and key telemetry.
  // Uses only local vendor APIs; no PC sniffer data is involved here.
  private void printHealthStatus() {
    StringBuilder sb = new StringBuilder(768);
    appendLine(sb, "=== Bringup Health (Local Robot Data) ===");
    double nowSec = Timer.getFPGATimestamp();
    revDevices.appendHealth(sb, nowSec);
    ctreDevices.appendHealth(sb, nowSec);
    appendVirtualDeviceHealth(sb);
    appendLine(sb, "======================");
    BringupPrinter.enqueueChunked(sb.toString(), 4);
  }

  // Print absolute positions for all CANCoders (instantiates if needed).
  private void printCANCoderStatus() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Bringup CANCoder ===");
    appendEncoderStatus(sb, revDevices);
    appendEncoderStatus(sb, ctreDevices);
    appendLine(sb, "=======================");
    BringupPrinter.enqueueChunked(sb.toString(), 4);
  }

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

  // Capture local device data into snapshot objects (no formatting here).
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

  // Append virtual device presence (currently the roboRIO) to state output.
  private void appendVirtualDevices(StringBuilder sb) {
    if (!BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)) {
      return;
    }
    appendLine(sb, "Virtual devices:");
    appendLine(sb, "  roboRIO CAN " + BringupUtil.ROBORIO_CAN_ID + " PRESENT (no local API)");
  }

  // Append virtual device presence to health output.
  private void appendVirtualDeviceHealth(StringBuilder sb) {
    if (!BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)) {
      return;
    }
    appendLine(sb, "  roboRIO CAN " + BringupUtil.ROBORIO_CAN_ID + ": present=YES (virtual, no API)");
  }

  // Report whether a device is instantiated based on CAN metadata.
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

  private static void appendLine(StringBuilder sb, String line) {
    sb.append(line).append('\n');
  }
}
