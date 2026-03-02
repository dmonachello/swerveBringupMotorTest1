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
  private boolean nudgeActive = false;
  private double nudgeEndSec = 0.0;
  private double nudgeSpeed = 0.2;

  private long lastStatePrintMs = 0L;
  private long lastHealthPrintMs = 0L;
  private long lastCANCoderPrintMs = 0L;
  private final List<DeviceUnit> testDevices = new ArrayList<>();
  private int nextTestIndex = 0;

  public BringupCore() {
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

  // Apply requested speeds to all instantiated motors (with optional nudge override).
  public void setSpeeds(double neoSpeed, double krakenSpeed) {
    if (nudgeActive) {
      double now = Timer.getFPGATimestamp();
      if (now < nudgeEndSec) {
        neoSpeed = nudgeSpeed;
        krakenSpeed = nudgeSpeed;
      } else {
        nudgeActive = false;
      }
    }
    revDevices.setDuty(neoSpeed);
    ctreDevices.setDuty(krakenSpeed);
  }

  // Force a brief output at a fixed duty cycle for all motors.
  public void triggerNudge(double speed, double seconds) {
    if (seconds <= 0.0) {
      return;
    }
    nudgeSpeed = Math.max(-1.0, Math.min(1.0, speed));
    nudgeEndSec = Timer.getFPGATimestamp() + seconds;
    nudgeActive = true;
  }

  // Clear current and sticky faults on all instantiated devices where supported.
  public void clearAllFaults() {
    revDevices.clearFaults();
    ctreDevices.clearFaults();
  }

  // Stop all outputs, close devices, and reset internal state.
  public void resetState() {
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

    BringupPrinter.enqueue("=== Bringup reset: no motors instantiated ===");
  }

  public void runNextNonMotorTest() {
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

  private void refreshTestDevices() {
    testDevices.clear();
    testDevices.addAll(ctreDevices.getTestDevices());
    testDevices.addAll(revDevices.getTestDevices());
    nextTestIndex = 0;
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
    BringupPrinter.enqueueChunked(sb.toString(), 12);
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
    BringupPrinter.enqueueChunked(sb.toString(), 12);
  }

  // Print absolute positions for all CANCoders (instantiates if needed).
  private void printCANCoderStatus() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Bringup CANCoder ===");
    appendEncoderStatus(sb, revDevices);
    appendEncoderStatus(sb, ctreDevices);
    appendLine(sb, "=======================");
    BringupPrinter.enqueueChunked(sb.toString(), 12);
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
