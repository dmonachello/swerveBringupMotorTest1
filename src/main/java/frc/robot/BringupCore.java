package frc.robot;

import edu.wpi.first.wpilibj.Timer;
import frc.robot.BringupUtil;
import frc.robot.devices.ctre.CtreCANCoderDevice;
import frc.robot.devices.ctre.CtreCANdleDevice;
import frc.robot.devices.ctre.CtreTalonFxDevice;
import frc.robot.devices.rev.RevFlexVortexDevice;
import frc.robot.devices.rev.RevSparkMaxNeoDevice;
import frc.robot.devices.rev.RevSparkMaxNeo550Device;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.manufacturers.CtreDeviceGroup;
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

  private boolean addNeoNext = true;
  private boolean addKrakenNext = true;

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

  public BringupCore() {
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
    revDevices.initLowCurrentTimers();

    addNeoNext = true;
    addKrakenNext = true;

    prevAdd = false;
    prevAddAll = false;
    prevPrint = false;
    prevHealth = false;
    prevCANCoder = false;

    BringupPrinter.enqueue("=== Bringup reset: no motors instantiated ===");
  }

  // Alternates between REV and CTRE motors to keep bringup balanced.
  private void addNextMotor() {
    if (addNeoNext) {
      int neoIndex = revDevices.addNextNeo();
      if (neoIndex >= 0) {
        RevSparkMaxNeoDevice[] neos = revDevices.getNeos();
        BringupPrinter.enqueue(
            "Added NEO index " + neoIndex +
            " (CAN " + neos[neoIndex].getCanId() + ")");
        addNeoNext = false;
        return;
      }

      int neo550Index = revDevices.addNextNeo550();
      if (neo550Index >= 0) {
        RevSparkMaxNeo550Device[] neo550s = revDevices.getNeo550s();
        BringupPrinter.enqueue(
            "Added NEO 550 index " + neo550Index +
            " (CAN " + neo550s[neo550Index].getCanId() + ")");
        addNeoNext = false;
        return;
      }

      int flexIndex = revDevices.addNextFlex();
      if (flexIndex >= 0) {
        RevFlexVortexDevice[] flexes = revDevices.getFlexes();
        BringupPrinter.enqueue(
            "Added FLEX index " + flexIndex +
            " (CAN " + flexes[flexIndex].getCanId() + ")");
        addNeoNext = false;
        return;
      }

      BringupPrinter.enqueue("No more SPARK motors to add");
      addNeoNext = false;
      return;
    }

    if (addKrakenNext) {
      int krakenIndex = ctreDevices.addNextKraken();
      if (krakenIndex >= 0) {
        CtreTalonFxDevice[] krakens = ctreDevices.getKrakens();
        BringupPrinter.enqueue(
            "Added KRAKEN index " + krakenIndex +
            " (CAN " + krakens[krakenIndex].getCanId() + ")");
        addKrakenNext = false;
        addNeoNext = true;
        return;
      }

      int falconIndex = ctreDevices.addNextFalcon();
      if (falconIndex >= 0) {
        CtreTalonFxDevice[] falcons = ctreDevices.getFalcons();
        BringupPrinter.enqueue(
            "Added FALCON index " + falconIndex +
            " (CAN " + falcons[falconIndex].getCanId() + ")");
        addKrakenNext = true;
        addNeoNext = true;
        return;
      }

      BringupPrinter.enqueue("No more CTRE motors to add");
      addNeoNext = true;
      return;
    }

    int falconIndex = ctreDevices.addNextFalcon();
    if (falconIndex >= 0) {
      CtreTalonFxDevice[] falcons = ctreDevices.getFalcons();
      BringupPrinter.enqueue(
          "Added FALCON index " + falconIndex +
          " (CAN " + falcons[falconIndex].getCanId() + ")");
      addKrakenNext = true;
      addNeoNext = true;
      return;
    }

    int krakenIndex = ctreDevices.addNextKraken();
    if (krakenIndex >= 0) {
      CtreTalonFxDevice[] krakens = ctreDevices.getKrakens();
      BringupPrinter.enqueue(
          "Added KRAKEN index " + krakenIndex +
          " (CAN " + krakens[krakenIndex].getCanId() + ")");
      addKrakenNext = false;
      addNeoNext = true;
      return;
    }

    BringupPrinter.enqueue("No more CTRE motors to add");
    addNeoNext = true;
  }

  // Instantiate all configured devices (motors + CANCoders + CANdles).
  private void addAllDevices() {
    revDevices.addAll();
    ctreDevices.addAll();
    addNeoNext = true;
    addKrakenNext = true;
    BringupPrinter.enqueue("Added all SPARKs, Krakens, Falcons, CANCoders, and CANdles.");
  }

  // Print a compact list of which devices are instantiated.
  private void printState() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Bringup State ===");

    RevSparkMaxNeoDevice[] neos = revDevices.getNeos();
    appendLine(sb, "NEOs:");
    for (int i = 0; i < neos.length; i++) {
      if (neos[i].isCreated()) {
        appendLine(sb, "  index " + i +
            " CAN " + neos[i].getCanId() + " ACTIVE");
      } else {
        appendLine(sb, "  index " + i +
            " CAN " + neos[i].getCanId() + " not added");
      }
    }

    RevSparkMaxNeo550Device[] neo550s = revDevices.getNeo550s();
    if (neo550s.length > 0) {
      appendLine(sb, "NEO 550:");
      for (int i = 0; i < neo550s.length; i++) {
        if (neo550s[i].isCreated()) {
          appendLine(sb, "  index " + i +
              " CAN " + neo550s[i].getCanId() + " ACTIVE");
        } else {
          appendLine(sb, "  index " + i +
              " CAN " + neo550s[i].getCanId() + " not added");
        }
      }
    }

    RevFlexVortexDevice[] flexes = revDevices.getFlexes();
    appendLine(sb, "FLEX:");
    for (int i = 0; i < flexes.length; i++) {
      if (flexes[i].isCreated()) {
        appendLine(sb, "  index " + i +
            " CAN " + flexes[i].getCanId() + " ACTIVE");
      } else {
        appendLine(sb, "  index " + i +
            " CAN " + flexes[i].getCanId() + " not added");
      }
    }

    CtreTalonFxDevice[] krakens = ctreDevices.getKrakens();
    appendLine(sb, "Krakens:");
    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i].isCreated()) {
        appendLine(sb, "  index " + i +
            " CAN " + krakens[i].getCanId() + " ACTIVE");
      } else {
        appendLine(sb, "  index " + i +
            " CAN " + krakens[i].getCanId() + " not added");
      }
    }

    CtreTalonFxDevice[] falcons = ctreDevices.getFalcons();
    appendLine(sb, "Falcons:");
    for (int i = 0; i < falcons.length; i++) {
      if (falcons[i].isCreated()) {
        appendLine(sb, "  index " + i +
            " CAN " + falcons[i].getCanId() + " ACTIVE");
      } else {
        appendLine(sb, "  index " + i +
            " CAN " + falcons[i].getCanId() + " not added");
      }
    }

    CtreCANdleDevice[] candles = ctreDevices.getCANdles();
    if (candles.length > 0) {
      appendLine(sb, "CANdles:");
      for (int i = 0; i < candles.length; i++) {
        if (candles[i].isCreated()) {
          appendLine(sb, "  index " + i +
              " CAN " + candles[i].getCanId() + " ACTIVE");
        } else {
          appendLine(sb, "  index " + i +
              " CAN " + candles[i].getCanId() + " not added");
        }
      }
    }

    appendLine(sb,
        "Next add will be: " +
        (addNeoNext ? "SPARK" : (addKrakenNext ? "KRAKEN" : "FALCON")));
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

    RevSparkMaxNeoDevice[] neos = revDevices.getNeos();
    for (int i = 0; i < neos.length; i++) {
      DeviceSnapshot snap = revDevices.snapshotNeo(i, nowSec);
      if (!snap.present) {
        appendLine(sb, "NEO index " + i +
            " CAN " + neos[i].getCanId() + " not added");
        continue;
      }
      appendLine(sb,
          "NEO index " + i +
          " CAN " + neos[i].getCanId() +
          formatRevFaultSummary(snap) +
          " lastErr=" + snap.lastError +
          snap.healthNote +
          snap.lowCurrentNote +
          formatMotorSpecNote(snap) +
          " busV=" + String.format("%.2f", safeDouble(snap.busV)) + "V" +
          " appliedDuty=" + String.format("%.2f", safeDouble(snap.appliedDuty)) + "dc" +
          " appliedV=" + String.format("%.2f", safeDouble(snap.appliedV)) + "V" +
          " motorCurrentA=" + String.format("%.4f", safeDouble(snap.motorCurrentA)) + "A" +
          " tempC=" + String.format("%.1f", safeDouble(snap.tempC)) + "C" +
          " cmdDuty=" + String.format("%.2f", safeDouble(snap.cmdDuty)) + "dc" +
          " follower=" + (snap.follower ? "Y" : "N"));
    }

    RevSparkMaxNeo550Device[] neo550s = revDevices.getNeo550s();
    for (int i = 0; i < neo550s.length; i++) {
      DeviceSnapshot snap = revDevices.snapshotNeo550(i, nowSec);
      if (!snap.present) {
        appendLine(sb, "NEO 550 index " + i +
            " CAN " + neo550s[i].getCanId() + " not added");
        continue;
      }
      appendLine(sb,
          "NEO 550 index " + i +
          " CAN " + neo550s[i].getCanId() +
          formatRevFaultSummary(snap) +
          " lastErr=" + snap.lastError +
          snap.healthNote +
          snap.lowCurrentNote +
          formatMotorSpecNote(snap) +
          " busV=" + String.format("%.2f", safeDouble(snap.busV)) + "V" +
          " appliedDuty=" + String.format("%.2f", safeDouble(snap.appliedDuty)) + "dc" +
          " appliedV=" + String.format("%.2f", safeDouble(snap.appliedV)) + "V" +
          " motorCurrentA=" + String.format("%.4f", safeDouble(snap.motorCurrentA)) + "A" +
          " tempC=" + String.format("%.1f", safeDouble(snap.tempC)) + "C" +
          " cmdDuty=" + String.format("%.2f", safeDouble(snap.cmdDuty)) + "dc" +
          " follower=" + (snap.follower ? "Y" : "N"));
    }

    RevFlexVortexDevice[] flexes = revDevices.getFlexes();
    for (int i = 0; i < flexes.length; i++) {
      DeviceSnapshot snap = revDevices.snapshotFlex(i, nowSec);
      if (!snap.present) {
        appendLine(sb, "FLEX index " + i +
            " CAN " + flexes[i].getCanId() + " not added");
        continue;
      }
      appendLine(sb,
          "FLEX index " + i +
          " CAN " + flexes[i].getCanId() +
          formatRevFaultSummary(snap) +
          " lastErr=" + snap.lastError +
          snap.healthNote +
          snap.lowCurrentNote +
          formatMotorSpecNote(snap) +
          " busV=" + String.format("%.2f", safeDouble(snap.busV)) + "V" +
          " appliedDuty=" + String.format("%.2f", safeDouble(snap.appliedDuty)) + "dc" +
          " appliedV=" + String.format("%.2f", safeDouble(snap.appliedV)) + "V" +
          " motorCurrentA=" + String.format("%.4f", safeDouble(snap.motorCurrentA)) + "A" +
          " tempC=" + String.format("%.1f", safeDouble(snap.tempC)) + "C" +
          " cmdDuty=" + String.format("%.2f", safeDouble(snap.cmdDuty)) + "dc" +
          " follower=" + (snap.follower ? "Y" : "N"));
    }

    CtreTalonFxDevice[] krakens = ctreDevices.getKrakens();
    for (int i = 0; i < krakens.length; i++) {
      DeviceSnapshot snap = ctreDevices.snapshotKraken(i);
      if (!snap.present) {
        appendLine(sb, "KRAKEN index " + i +
            " CAN " + krakens[i].getCanId() + " not added");
        continue;
      }
      appendLine(sb,
          "KRAKEN index " + i +
          " CAN " + krakens[i].getCanId() +
          formatCtreFaultSummary(snap) +
          formatMotorSpecNote(snap) +
          " busV=" + String.format("%.2f", safeDouble(snap.busV)) + "V" +
          " appliedDuty=" + String.format("%.2f", safeDouble(snap.appliedDuty)) + "dc" +
          " appliedV=" + String.format("%.2f", safeDouble(snap.appliedV)) + "V" +
          " motorCurrentA=" + String.format("%.4f", safeDouble(snap.motorCurrentA)) + "A" +
          " tempC=" + String.format("%.1f", safeDouble(snap.tempC)) + "C" +
          (snap.faultStatus.isBlank() && snap.stickyStatus.isBlank()
              ? ""
              : " status=" + snap.faultStatus + "/" + snap.stickyStatus));
    }

    CtreTalonFxDevice[] falcons = ctreDevices.getFalcons();
    for (int i = 0; i < falcons.length; i++) {
      DeviceSnapshot snap = ctreDevices.snapshotFalcon(i);
      if (!snap.present) {
        appendLine(sb, "FALCON index " + i +
            " CAN " + falcons[i].getCanId() + " not added");
        continue;
      }
      appendLine(sb,
          "FALCON index " + i +
          " CAN " + falcons[i].getCanId() +
          formatCtreFaultSummary(snap) +
          formatMotorSpecNote(snap) +
          " busV=" + String.format("%.2f", safeDouble(snap.busV)) + "V" +
          " appliedDuty=" + String.format("%.2f", safeDouble(snap.appliedDuty)) + "dc" +
          " appliedV=" + String.format("%.2f", safeDouble(snap.appliedV)) + "V" +
          " motorCurrentA=" + String.format("%.4f", safeDouble(snap.motorCurrentA)) + "A" +
          " tempC=" + String.format("%.1f", safeDouble(snap.tempC)) + "C" +
          (snap.faultStatus.isBlank() && snap.stickyStatus.isBlank()
              ? ""
              : " status=" + snap.faultStatus + "/" + snap.stickyStatus));
    }

    CtreCANdleDevice[] candles = ctreDevices.getCANdles();
    for (int i = 0; i < candles.length; i++) {
      DeviceSnapshot snap = ctreDevices.snapshotCANdle(i);
      if (!snap.present) {
        appendLine(sb, "CANdle index " + i +
            " CAN " + candles[i].getCanId() + " not added");
        continue;
      }
      appendLine(sb,
          "CANdle index " + i +
          " CAN " + candles[i].getCanId() +
          " present=YES");
    }

    appendVirtualDeviceHealth(sb);
    appendLine(sb, "======================");
    BringupPrinter.enqueueChunked(sb.toString(), 12);
  }

  // Print absolute positions for all CANCoders (instantiates if needed).
  private void printCANCoderStatus() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Bringup CANCoder ===");
    CtreCANCoderDevice[] cancoders = ctreDevices.getCANCoders();
    for (int i = 0; i < cancoders.length; i++) {
      cancoders[i].ensureCreated();
      DeviceSnapshot snap = ctreDevices.snapshotCANCoder(i);
      double degrees = safeDouble(snap.absDeg);
      double rotations = degrees / 360.0;
      appendLine(sb,
          "CANCoder index " + i +
          " CAN " + cancoders[i].getCanId() +
          " absRot=" + String.format("%.4f", rotations) +
          " absDeg=" + String.format("%.1f", degrees));
    }
    appendLine(sb, "=======================");
    BringupPrinter.enqueueChunked(sb.toString(), 12);
  }

  // Capture local device data into snapshot objects (no formatting here).
  public List<DeviceSnapshot> captureSnapshots() {
    List<DeviceSnapshot> devices = new ArrayList<>();
    double nowSec = Timer.getFPGATimestamp();
    devices.addAll(revDevices.captureSnapshots(nowSec));
    devices.addAll(ctreDevices.captureSnapshots());

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
    if (manufacturer == 5 && deviceType == 2) {
      return revDevices.isNeoInstantiated(deviceId)
          || revDevices.isNeo550Instantiated(deviceId)
          || revDevices.isFlexInstantiated(deviceId);
    }
    if (manufacturer == 4 && deviceType == 2) {
      return ctreDevices.isKrakenInstantiated(deviceId)
          || ctreDevices.isFalconInstantiated(deviceId);
    }
    if (manufacturer == 4 && deviceType == 7) {
      return ctreDevices.isCANCoderInstantiated(deviceId);
    }
    if (manufacturer == 4 && deviceType == 10) {
      return ctreDevices.isCANdleInstantiated(deviceId);
    }
    if (manufacturer == NI_MANUFACTURER && deviceType == TYPE_ROBOT_CONTROLLER) {
      return BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)
          && deviceId == BringupUtil.ROBORIO_CAN_ID;
    }
    return false;
  }

  private static String formatRevFaultSummary(DeviceSnapshot snap) {
    StringBuilder sb = new StringBuilder(128);
    sb.append(" faults=0x").append(Integer.toHexString(snap.faultsRaw));
    sb.append(formatFlagList(snap.faultFlags));
    sb.append(" sticky=0x").append(Integer.toHexString(snap.stickyFaultsRaw));
    sb.append(formatFlagList(snap.stickyFaultFlags));
    sb.append(" warnings=0x").append(Integer.toHexString(snap.warningsRaw));
    sb.append(formatFlagList(snap.warningFlags));
    sb.append(" stickyWarn=0x").append(Integer.toHexString(snap.stickyWarningsRaw));
    sb.append(formatFlagList(snap.stickyWarningFlags));
    return sb.toString();
  }

  private static String formatCtreFaultSummary(DeviceSnapshot snap) {
    StringBuilder sb = new StringBuilder(128);
    sb.append(" fault=0x").append(Integer.toHexString(snap.faultsRaw));
    sb.append(formatFlagList(snap.faultFlags));
    sb.append(" sticky=0x").append(Integer.toHexString(snap.stickyFaultsRaw));
    sb.append(formatFlagList(snap.stickyFaultFlags));
    return sb.toString();
  }

  private static String formatMotorSpecNote(DeviceSnapshot snap) {
    if (snap.specFreeA == null || snap.specStallA == null) {
      return "";
    }
    double free = snap.specFreeA;
    double stall = snap.specStallA;
    double current = snap.motorCurrentA != null ? snap.motorCurrentA : 0.0;
    String ratio = free > 0.0 ? String.format("%.2fx", current / free) : "?";
    return " specFree=" + String.format("%.1f", free) + "A" +
        " specStall=" + String.format("%.0f", stall) + "A" +
        " freeRatio=" + ratio;
  }

  private static String formatFlagList(List<String> flags) {
    if (flags == null || flags.isEmpty()) {
      return "";
    }
    return " [" + String.join(",", flags) + "]";
  }

  private static double safeDouble(Double value) {
    return value == null ? 0.0 : value;
  }

  private static void appendLine(StringBuilder sb, String line) {
    sb.append(line).append('\n');
  }
}

