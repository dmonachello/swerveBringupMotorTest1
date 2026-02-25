package frc.robot;

import com.ctre.phoenix6.BaseStatusSignal;
import com.ctre.phoenix6.StatusSignal;
import com.ctre.phoenix6.hardware.CANcoder;
import com.ctre.phoenix6.hardware.TalonFX;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import edu.wpi.first.units.Units;
import com.revrobotics.spark.SparkBase;
import com.revrobotics.spark.SparkFlex;
import com.revrobotics.spark.SparkMax;
import com.revrobotics.spark.SparkLowLevel.MotorType;
import com.revrobotics.spark.config.SparkFlexConfig;
import com.revrobotics.spark.config.SparkMaxConfig;
import com.revrobotics.ResetMode;
import com.revrobotics.PersistMode;
import com.revrobotics.REVLibError;
import edu.wpi.first.wpilibj.Timer;
import java.util.Arrays;

// Core bringup logic: creates devices, commands outputs, and prints local health.
// This class only uses robot-local vendor APIs (no PC sniffer data).
public final class BringupCore {
  private static final int NI_MANUFACTURER = 1;
  private static final int TYPE_ROBOT_CONTROLLER = 1;
  private final int[] neoIds = BringupUtil.filterCanIds(BringupUtil.NEO_CAN_IDS);
  private final int[] flexIds = BringupUtil.filterCanIds(BringupUtil.FLEX_CAN_IDS);
  private final int[] krakenIds = BringupUtil.filterCanIds(BringupUtil.KRAKEN_CAN_IDS);
  private final int[] falconIds = BringupUtil.filterCanIds(BringupUtil.FALCON_CAN_IDS);
  private final int[] cancoderIds = BringupUtil.filterCanIds(BringupUtil.CANCODER_CAN_IDS);

  private final SparkMax[] neos = new SparkMax[neoIds.length];
  private final SparkFlex[] flexes = new SparkFlex[flexIds.length];
  private final TalonFX[] krakens = new TalonFX[krakenIds.length];
  private final TalonFX[] falcons = new TalonFX[falconIds.length];
  private final CANcoder[] cancoders = new CANcoder[cancoderIds.length];
  private final double[] neoLowCurrentStartSec = new double[neoIds.length];
  private final double[] flexLowCurrentStartSec = new double[flexIds.length];

  private int nextNeo = 0;
  private int nextFlex = 0;
  private int nextKraken = 0;
  private int nextFalcon = 0;
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
  private static final long MIN_PRINT_INTERVAL_MS = 1000;
  private static final double LOW_CURRENT_APPLIED_V_MIN = 1.0;
  private static final double LOW_CURRENT_A_MAX = 0.05;
  private static final double LOW_CURRENT_MIN_SEC = 1.0;

  public BringupCore() {
    initLowCurrentTimers();
  }
  private long lastStatePrintMs = 0L;
  private long lastHealthPrintMs = 0L;
  private long lastCANCoderPrintMs = 0L;

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
    BringupUtil.setAllNeos(neos, neoSpeed);
    BringupUtil.setAllFlexes(flexes, neoSpeed);
    BringupUtil.setAllKrakens(krakens, krakenSpeed);
    BringupUtil.setAllFalcons(falcons, krakenSpeed);
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

  // Stop all outputs, close devices, and reset internal state.
  public void resetState() {
    BringupUtil.stopAll(neos, flexes, krakens, falcons);

    for (int i = 0; i < neos.length; i++) {
      BringupUtil.closeIfPossible(neos[i]);
      neos[i] = null;
    }
    for (int i = 0; i < flexes.length; i++) {
      BringupUtil.closeIfPossible(flexes[i]);
      flexes[i] = null;
    }
    for (int i = 0; i < krakens.length; i++) {
      BringupUtil.closeIfPossible(krakens[i]);
      krakens[i] = null;
    }
    for (int i = 0; i < falcons.length; i++) {
      BringupUtil.closeIfPossible(falcons[i]);
      falcons[i] = null;
    }
    for (int i = 0; i < cancoders.length; i++) {
      BringupUtil.closeIfPossible(cancoders[i]);
      cancoders[i] = null;
    }

    nextNeo = 0;
    nextFlex = 0;
    nextKraken = 0;
    nextFalcon = 0;
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
      if (!addNextNeo() && !addNextFlex()) {
        BringupPrinter.enqueue("No more SPARK motors to add");
      }
      addNeoNext = false;
      return;
    }

    if (addKrakenNext) {
      if (nextKraken < krakens.length && krakens[nextKraken] == null) {
        krakens[nextKraken] = new TalonFX(krakenIds[nextKraken]);
      BringupPrinter.enqueue(
          "Added KRAKEN index " + nextKraken +
          " (CAN " + krakenIds[nextKraken] + ")");
        nextKraken++;
        addKrakenNext = false;
      } else if (nextFalcon < falcons.length && falcons[nextFalcon] == null) {
        falcons[nextFalcon] = new TalonFX(falconIds[nextFalcon]);
      BringupPrinter.enqueue(
          "Added FALCON index " + nextFalcon +
          " (CAN " + falconIds[nextFalcon] + ")");
        nextFalcon++;
        addKrakenNext = true;
      } else {
        BringupPrinter.enqueue("No more CTRE motors to add");
      }
    } else {
      if (nextFalcon < falcons.length && falcons[nextFalcon] == null) {
        falcons[nextFalcon] = new TalonFX(falconIds[nextFalcon]);
        BringupPrinter.enqueue(
            "Added FALCON index " + nextFalcon +
            " (CAN " + falconIds[nextFalcon] + ")");
        nextFalcon++;
        addKrakenNext = true;
      } else if (nextKraken < krakens.length && krakens[nextKraken] == null) {
        krakens[nextKraken] = new TalonFX(krakenIds[nextKraken]);
        BringupPrinter.enqueue(
            "Added KRAKEN index " + nextKraken +
            " (CAN " + krakenIds[nextKraken] + ")");
        nextKraken++;
        addKrakenNext = false;
      } else {
        BringupPrinter.enqueue("No more CTRE motors to add");
      }
    }
    addNeoNext = true;
  }

  // Lazily instantiate the next available NEO.
  private boolean addNextNeo() {
    if (nextNeo < neos.length && neos[nextNeo] == null) {
      neos[nextNeo] = new SparkMax(neoIds[nextNeo], MotorType.kBrushless);
      neos[nextNeo].pauseFollowerModeAsync();
      neos[nextNeo].configureAsync(new SparkMaxConfig(), ResetMode.kResetSafeParameters, PersistMode.kNoPersistParameters);

      BringupPrinter.enqueue(
          "Added NEO index " + nextNeo +
          " (CAN " + neoIds[nextNeo] + ")");

      nextNeo++;
      return true;
    }
    return false;
  }

  // Lazily instantiate the next available FLEX/Vortex.
  private boolean addNextFlex() {
    if (nextFlex < flexes.length && flexes[nextFlex] == null) {
      flexes[nextFlex] = new SparkFlex(flexIds[nextFlex], MotorType.kBrushless);
      flexes[nextFlex].pauseFollowerModeAsync();
      flexes[nextFlex].configureAsync(new SparkFlexConfig(), ResetMode.kResetSafeParameters, PersistMode.kNoPersistParameters);

      BringupPrinter.enqueue(
          "Added FLEX index " + nextFlex +
          " (CAN " + flexIds[nextFlex] + ")");

      nextFlex++;
      return true;
    }
    return false;
  }

  // Instantiate all configured devices (motors + CANCoders).
  private void addAllDevices() {
    for (int i = 0; i < neos.length; i++) {
      if (neos[i] == null) {
        neos[i] = new SparkMax(neoIds[i], MotorType.kBrushless);
        neos[i].pauseFollowerModeAsync();
        neos[i].configureAsync(new SparkMaxConfig(), ResetMode.kResetSafeParameters, PersistMode.kNoPersistParameters);
      }
    }
    for (int i = 0; i < flexes.length; i++) {
      if (flexes[i] == null) {
        flexes[i] = new SparkFlex(flexIds[i], MotorType.kBrushless);
        flexes[i].pauseFollowerModeAsync();
        flexes[i].configureAsync(new SparkFlexConfig(), ResetMode.kResetSafeParameters, PersistMode.kNoPersistParameters);
      }
    }
    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i] == null) {
        krakens[i] = new TalonFX(krakenIds[i]);
      }
    }
    for (int i = 0; i < falcons.length; i++) {
      if (falcons[i] == null) {
        falcons[i] = new TalonFX(falconIds[i]);
      }
    }
    for (int i = 0; i < cancoders.length; i++) {
      if (cancoders[i] == null) {
        cancoders[i] = new CANcoder(cancoderIds[i]);
      }
    }

    nextNeo = neos.length;
    nextFlex = flexes.length;
    nextKraken = krakens.length;
    nextFalcon = falcons.length;
    addNeoNext = true;

    BringupPrinter.enqueue("Added all SPARKs, Krakens, Falcons, and CANCoders.");
  }

  // Print a compact list of which devices are instantiated.
  private void printState() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Bringup State ===");

    appendLine(sb, "NEOs:");
    for (int i = 0; i < neos.length; i++) {
      if (neos[i] != null) {
        appendLine(sb, "  index " + i +
            " CAN " + neoIds[i] + " ACTIVE");
      } else {
        appendLine(sb, "  index " + i +
            " CAN " + neoIds[i] + " not added");
      }
    }

    appendLine(sb, "FLEX:");
    for (int i = 0; i < flexes.length; i++) {
      if (flexes[i] != null) {
        appendLine(sb, "  index " + i +
            " CAN " + flexIds[i] + " ACTIVE");
      } else {
        appendLine(sb, "  index " + i +
            " CAN " + flexIds[i] + " not added");
      }
    }

    appendLine(sb, "Krakens:");
    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i] != null) {
        appendLine(sb, "  index " + i +
            " CAN " + krakenIds[i] + " ACTIVE");
      } else {
        appendLine(sb, "  index " + i +
            " CAN " + krakenIds[i] + " not added");
      }
    }

    appendLine(sb, "Falcons:");
    for (int i = 0; i < falcons.length; i++) {
      if (falcons[i] != null) {
        appendLine(sb, "  index " + i +
            " CAN " + falconIds[i] + " ACTIVE");
      } else {
        appendLine(sb, "  index " + i +
            " CAN " + falconIds[i] + " not added");
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
    // REV SPARK devices report their own faults, warnings, and telemetry.
    for (int i = 0; i < neos.length; i++) {
      if (neos[i] == null) {
        appendLine(sb, "NEO index " + i +
            " CAN " + neoIds[i] + " not added");
        continue;
      }
      var faults = neos[i].getFaults();
      var stickyFaults = neos[i].getStickyFaults();
      var warnings = neos[i].getWarnings();
      var stickyWarnings = neos[i].getStickyWarnings();
      REVLibError lastError = neos[i].getLastError();
      double busVoltage = neos[i].getBusVoltage();
      double appliedOutput = neos[i].getAppliedOutput();
      double appliedVolts = busVoltage * appliedOutput;
      double outputCurrent = neos[i].getOutputCurrent();
      double motorTemp = neos[i].getMotorTemperature();
      double setpoint = neos[i].get();
      boolean follower = neos[i].isFollower();
      String healthNote = buildRevHealthNote(lastError, busVoltage);
      String lowCurrentNote =
          buildLowCurrentNote(neoLowCurrentStartSec, i, nowSec, appliedVolts, outputCurrent);
      String label = BringupUtil.getNeoLabel(i);
      String modelOverride = BringupUtil.getNeoMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      String specNote = formatMotorSpecNote(spec, outputCurrent);
      appendLine(sb,
          "NEO index " + i +
          " CAN " + neoIds[i] +
          formatRevFaultSummary(faults, stickyFaults, warnings, stickyWarnings) +
          " lastErr=" + lastError +
          healthNote +
          lowCurrentNote +
          specNote +
          " busV=" + String.format("%.2f", busVoltage) + "V" +
          " appliedDuty=" + String.format("%.2f", appliedOutput) + "dc" +
          " appliedV=" + String.format("%.2f", appliedVolts) + "V" +
          " motorCurrentA=" + String.format("%.4f", outputCurrent) + "A" +
          " tempC=" + String.format("%.1f", motorTemp) + "C" +
          " cmdDuty=" + String.format("%.2f", setpoint) + "dc" +
          " follower=" + (follower ? "Y" : "N"));
    }

    // FLEX/Vortex uses the same REV SPARK API surface as NEOs.
    for (int i = 0; i < flexes.length; i++) {
      if (flexes[i] == null) {
        appendLine(sb, "FLEX index " + i +
            " CAN " + flexIds[i] + " not added");
        continue;
      }
      var faults = flexes[i].getFaults();
      var stickyFaults = flexes[i].getStickyFaults();
      var warnings = flexes[i].getWarnings();
      var stickyWarnings = flexes[i].getStickyWarnings();
      REVLibError lastError = flexes[i].getLastError();
      double busVoltage = flexes[i].getBusVoltage();
      double appliedOutput = flexes[i].getAppliedOutput();
      double appliedVolts = busVoltage * appliedOutput;
      double outputCurrent = flexes[i].getOutputCurrent();
      double motorTemp = flexes[i].getMotorTemperature();
      double setpoint = flexes[i].get();
      boolean follower = flexes[i].isFollower();
      String healthNote = buildRevHealthNote(lastError, busVoltage);
      String lowCurrentNote =
          buildLowCurrentNote(flexLowCurrentStartSec, i, nowSec, appliedVolts, outputCurrent);
      String label = BringupUtil.getFlexLabel(i);
      String modelOverride = BringupUtil.getFlexMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      String specNote = formatMotorSpecNote(spec, outputCurrent);
      appendLine(sb,
          "FLEX index " + i +
          " CAN " + flexIds[i] +
          formatRevFaultSummary(faults, stickyFaults, warnings, stickyWarnings) +
          " lastErr=" + lastError +
          healthNote +
          lowCurrentNote +
          specNote +
          " busV=" + String.format("%.2f", busVoltage) + "V" +
          " appliedDuty=" + String.format("%.2f", appliedOutput) + "dc" +
          " appliedV=" + String.format("%.2f", appliedVolts) + "V" +
          " motorCurrentA=" + String.format("%.4f", outputCurrent) + "A" +
          " tempC=" + String.format("%.1f", motorTemp) + "C" +
          " cmdDuty=" + String.format("%.2f", setpoint) + "dc" +
          " follower=" + (follower ? "Y" : "N"));
    }

    // CTRE devices are read via Phoenix status signals. Refresh before reading.
    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i] == null) {
        appendLine(sb, "KRAKEN index " + i +
            " CAN " + krakenIds[i] + " not added");
        continue;
      }
      var faultSignal = krakens[i].getFaultField();
      var stickySignal = krakens[i].getStickyFaultField();
      var supplyVoltage = krakens[i].getSupplyVoltage();
      var dutyCycle = krakens[i].getDutyCycle();
      var supplyCurrent = krakens[i].getSupplyCurrent();
      var deviceTemp = krakens[i].getDeviceTemp();
      var motorVoltage = krakens[i].getMotorVoltage();
      BaseStatusSignal.refreshAll(
          faultSignal,
          stickySignal,
          supplyVoltage,
          dutyCycle,
          supplyCurrent,
          deviceTemp,
          motorVoltage);
      int faultField = faultSignal.getValue();
      int stickyField = stickySignal.getValue();
      boolean faultOk = faultSignal.getStatus().isOK();
      boolean stickyOk = stickySignal.getStatus().isOK();
      double busVoltage = supplyVoltage.getValue().in(Units.Volts);
      double applied = dutyCycle.getValue();
      double outputCurrent = supplyCurrent.getValue().in(Units.Amps);
      double motorTemp = deviceTemp.getValue().in(Units.Celsius);
      double motorVolts = motorVoltage.getValue().in(Units.Volts);
      String label = BringupUtil.getKrakenLabel(i);
      String modelOverride = BringupUtil.getKrakenMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      String specNote = formatMotorSpecNote(spec, outputCurrent);
      appendLine(sb,
          "KRAKEN index " + i +
          " CAN " + krakenIds[i] +
          " fault=0x" + Integer.toHexString(faultField) +
          formatCtreFaults(krakens[i]) +
          " sticky=0x" + Integer.toHexString(stickyField) +
          formatCtreStickyFaults(krakens[i]) +
          specNote +
          " busV=" + String.format("%.2f", busVoltage) + "V" +
          " appliedDuty=" + String.format("%.2f", applied) + "dc" +
          " appliedV=" + String.format("%.2f", motorVolts) + "V" +
          " motorCurrentA=" + String.format("%.4f", outputCurrent) + "A" +
          " tempC=" + String.format("%.1f", motorTemp) + "C" +
          (faultOk && stickyOk
              ? ""
              : " status=" + faultSignal.getStatus() + "/" + stickySignal.getStatus()));
    }
    for (int i = 0; i < falcons.length; i++) {
      if (falcons[i] == null) {
        appendLine(sb, "FALCON index " + i +
            " CAN " + falconIds[i] + " not added");
        continue;
      }
      var faultSignal = falcons[i].getFaultField();
      var stickySignal = falcons[i].getStickyFaultField();
      var supplyVoltage = falcons[i].getSupplyVoltage();
      var dutyCycle = falcons[i].getDutyCycle();
      var supplyCurrent = falcons[i].getSupplyCurrent();
      var deviceTemp = falcons[i].getDeviceTemp();
      var motorVoltage = falcons[i].getMotorVoltage();
      BaseStatusSignal.refreshAll(
          faultSignal,
          stickySignal,
          supplyVoltage,
          dutyCycle,
          supplyCurrent,
          deviceTemp,
          motorVoltage);
      int faultField = faultSignal.getValue();
      int stickyField = stickySignal.getValue();
      boolean faultOk = faultSignal.getStatus().isOK();
      boolean stickyOk = stickySignal.getStatus().isOK();
      double busVoltage = supplyVoltage.getValue().in(Units.Volts);
      double applied = dutyCycle.getValue();
      double outputCurrent = supplyCurrent.getValue().in(Units.Amps);
      double motorTemp = deviceTemp.getValue().in(Units.Celsius);
      double motorVolts = motorVoltage.getValue().in(Units.Volts);
      String label = BringupUtil.getFalconLabel(i);
      String modelOverride = BringupUtil.getFalconMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      String specNote = formatMotorSpecNote(spec, outputCurrent);
      appendLine(sb,
          "FALCON index " + i +
          " CAN " + falconIds[i] +
          " fault=0x" + Integer.toHexString(faultField) +
          formatCtreFaults(falcons[i]) +
          " sticky=0x" + Integer.toHexString(stickyField) +
          formatCtreStickyFaults(falcons[i]) +
          specNote +
          " busV=" + String.format("%.2f", busVoltage) + "V" +
          " appliedDuty=" + String.format("%.2f", applied) + "dc" +
          " appliedV=" + String.format("%.2f", motorVolts) + "V" +
          " motorCurrentA=" + String.format("%.4f", outputCurrent) + "A" +
          " tempC=" + String.format("%.1f", motorTemp) + "C" +
          (faultOk && stickyOk
              ? ""
              : " status=" + faultSignal.getStatus() + "/" + stickySignal.getStatus()));
    }
    appendVirtualDeviceHealth(sb);
    appendLine(sb, "======================");
    BringupPrinter.enqueueChunked(sb.toString(), 12);
  }

  private static String buildRevHealthNote(REVLibError lastError, double busVoltage) {
    boolean timeout = lastError == REVLibError.kTimeout;
    boolean noPower = busVoltage < 1.0;
    if (!timeout && !noPower) {
      return "";
    }
    StringBuilder sb = new StringBuilder();
    sb.append(" !!");
    if (timeout) {
      sb.append(" TIMEOUT");
    }
    if (noPower) {
      if (timeout) {
        sb.append("/");
      }
      sb.append("LOW_VBUS");
    }
    sb.append(" (check CAN ID/profile/power)");
    return sb.toString();
  }

  private void initLowCurrentTimers() {
    Arrays.fill(neoLowCurrentStartSec, -1.0);
    Arrays.fill(flexLowCurrentStartSec, -1.0);
  }

  private String buildLowCurrentNote(
      double[] startTimes,
      int index,
      double nowSec,
      double appliedVolts,
      double outputCurrent) {
    boolean lowCurrent = appliedVolts >= LOW_CURRENT_APPLIED_V_MIN
        && outputCurrent <= LOW_CURRENT_A_MAX;
    double start = startTimes[index];
    if (!lowCurrent) {
      startTimes[index] = -1.0;
      return "";
    }
    if (start < 0.0) {
      startTimes[index] = nowSec;
      return "";
    }
    if (nowSec - start < LOW_CURRENT_MIN_SEC) {
      return "";
    }
    return " !! LOW_CURRENT (check load/wiring)";
  }

  private static String formatMotorSpecNote(BringupUtil.MotorSpec spec, double outputCurrent) {
    if (spec == null) {
      return "";
    }
    double free = spec.freeCurrentA;
    double stall = spec.stallCurrentA;
    String ratio = free > 0.0 ? String.format("%.2fx", outputCurrent / free) : "?";
    return " specFree=" + String.format("%.1f", free) + "A" +
        " specStall=" + String.format("%.0f", stall) + "A" +
        " freeRatio=" + ratio;
  }

  // Print absolute positions for all CANCoders (instantiates if needed).
  private void printCANCoderStatus() {
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Bringup CANCoder ===");
    // CANCoder absolute position is useful for verifying sensor wiring.
    for (int i = 0; i < cancoders.length; i++) {
      if (cancoders[i] == null) {
        cancoders[i] = new CANcoder(cancoderIds[i]);
      }
      var absolute = cancoders[i].getAbsolutePosition();
      BaseStatusSignal.refreshAll(absolute);
      double rotations = absolute.getValue().in(Units.Rotations);
      double degrees = rotations * 360.0;
      appendLine(sb,
          "CANCoder index " + i +
          " CAN " + cancoderIds[i] +
          " absRot=" + String.format("%.4f", rotations) +
          " absDeg=" + String.format("%.1f", degrees));
    }
    appendLine(sb, "=======================");
    BringupPrinter.enqueueChunked(sb.toString(), 12);
  }

  // Append local device health lines to a shared report buffer.
  public void appendDeviceDiagnosticsReport(StringBuilder sb) {
    appendLine(sb, "Device Health (local API):");

    // REV devices first, then CTRE, then sensors, then virtuals.
    for (int i = 0; i < neos.length; i++) {
      if (neos[i] == null) {
        appendLine(sb, "  NEO CAN " + neoIds[i] + ": present=NO (not added)");
        continue;
      }
      var faults = neos[i].getFaults();
      var stickyFaults = neos[i].getStickyFaults();
      var warnings = neos[i].getWarnings();
      var stickyWarnings = neos[i].getStickyWarnings();
      REVLibError lastError = neos[i].getLastError();
      double busVoltage = neos[i].getBusVoltage();
      double appliedDuty = neos[i].getAppliedOutput();
      double appliedVolts = busVoltage * appliedDuty;
      double outputCurrent = neos[i].getOutputCurrent();
      double motorTemp = neos[i].getMotorTemperature();
      boolean resetFlag = warnings.hasReset || stickyWarnings.hasReset;
      String label = BringupUtil.getNeoLabel(i);
      String modelOverride = BringupUtil.getNeoMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      String specNote = formatMotorSpecNote(spec, outputCurrent);
      appendLine(sb,
          "  NEO CAN " + neoIds[i] +
          ": present=YES" + formatRevFaultSummary(faults, stickyFaults, warnings, stickyWarnings) +
          " lastErr=" + lastError +
          " reset=" + (resetFlag ? "YES" : "NO") +
          specNote +
          " busV=" + String.format("%.2f", busVoltage) + "V" +
          " appliedV=" + String.format("%.2f", appliedVolts) + "V" +
          " motorCurrentA=" + String.format("%.4f", outputCurrent) + "A" +
          " tempC=" + String.format("%.1f", motorTemp) + "C");
    }

    for (int i = 0; i < flexes.length; i++) {
      if (flexes[i] == null) {
        appendLine(sb, "  FLEX CAN " + flexIds[i] + ": present=NO (not added)");
        continue;
      }
      var faults = flexes[i].getFaults();
      var stickyFaults = flexes[i].getStickyFaults();
      var warnings = flexes[i].getWarnings();
      var stickyWarnings = flexes[i].getStickyWarnings();
      REVLibError lastError = flexes[i].getLastError();
      double busVoltage = flexes[i].getBusVoltage();
      double appliedDuty = flexes[i].getAppliedOutput();
      double appliedVolts = busVoltage * appliedDuty;
      double outputCurrent = flexes[i].getOutputCurrent();
      double motorTemp = flexes[i].getMotorTemperature();
      boolean resetFlag = warnings.hasReset || stickyWarnings.hasReset;
      String label = BringupUtil.getFlexLabel(i);
      String modelOverride = BringupUtil.getFlexMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      String specNote = formatMotorSpecNote(spec, outputCurrent);
      appendLine(sb,
          "  FLEX CAN " + flexIds[i] +
          ": present=YES" + formatRevFaultSummary(faults, stickyFaults, warnings, stickyWarnings) +
          " lastErr=" + lastError +
          " reset=" + (resetFlag ? "YES" : "NO") +
          specNote +
          " busV=" + String.format("%.2f", busVoltage) + "V" +
          " appliedV=" + String.format("%.2f", appliedVolts) + "V" +
          " motorCurrentA=" + String.format("%.4f", outputCurrent) + "A" +
          " tempC=" + String.format("%.1f", motorTemp) + "C");
    }

    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i] == null) {
        appendLine(sb, "  KRAKEN CAN " + krakenIds[i] + ": present=NO (not added)");
        continue;
      }
      var faultSignal = krakens[i].getFaultField();
      var stickySignal = krakens[i].getStickyFaultField();
      var supplyVoltage = krakens[i].getSupplyVoltage();
      var dutyCycle = krakens[i].getDutyCycle();
      var supplyCurrent = krakens[i].getSupplyCurrent();
      var deviceTemp = krakens[i].getDeviceTemp();
      var motorVoltage = krakens[i].getMotorVoltage();
      BaseStatusSignal.refreshAll(
          faultSignal,
          stickySignal,
          supplyVoltage,
          dutyCycle,
          supplyCurrent,
          deviceTemp,
          motorVoltage);
      int faultField = faultSignal.getValue();
      int stickyField = stickySignal.getValue();
      boolean faultOk = faultSignal.getStatus().isOK();
      boolean stickyOk = stickySignal.getStatus().isOK();
      double busVoltage = supplyVoltage.getValue().in(Units.Volts);
      double applied = dutyCycle.getValue();
      double outputCurrent = supplyCurrent.getValue().in(Units.Amps);
      double motorTemp = deviceTemp.getValue().in(Units.Celsius);
      double motorVolts = motorVoltage.getValue().in(Units.Volts);
      String label = BringupUtil.getKrakenLabel(i);
      String modelOverride = BringupUtil.getKrakenMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      String specNote = formatMotorSpecNote(spec, outputCurrent);
      appendLine(sb,
          "  KRAKEN CAN " + krakenIds[i] +
          ": present=YES fault=0x" + Integer.toHexString(faultField) +
          formatCtreFaults(krakens[i]) +
          " sticky=0x" + Integer.toHexString(stickyField) +
          formatCtreStickyFaults(krakens[i]) +
          " lastErr=" + faultSignal.getStatus() +
          specNote +
          " busV=" + String.format("%.2f", busVoltage) + "V" +
          " appliedDuty=" + String.format("%.2f", applied) + "dc" +
          " appliedV=" + String.format("%.2f", motorVolts) + "V" +
          " motorCurrentA=" + String.format("%.4f", outputCurrent) + "A" +
          " tempC=" + String.format("%.1f", motorTemp) + "C" +
          (faultOk && stickyOk
              ? ""
              : " status=" + faultSignal.getStatus() + "/" + stickySignal.getStatus()));
    }

    for (int i = 0; i < falcons.length; i++) {
      if (falcons[i] == null) {
        appendLine(sb, "  FALCON CAN " + falconIds[i] + ": present=NO (not added)");
        continue;
      }
      var faultSignal = falcons[i].getFaultField();
      var stickySignal = falcons[i].getStickyFaultField();
      var supplyVoltage = falcons[i].getSupplyVoltage();
      var dutyCycle = falcons[i].getDutyCycle();
      var supplyCurrent = falcons[i].getSupplyCurrent();
      var deviceTemp = falcons[i].getDeviceTemp();
      var motorVoltage = falcons[i].getMotorVoltage();
      BaseStatusSignal.refreshAll(
          faultSignal,
          stickySignal,
          supplyVoltage,
          dutyCycle,
          supplyCurrent,
          deviceTemp,
          motorVoltage);
      int faultField = faultSignal.getValue();
      int stickyField = stickySignal.getValue();
      boolean faultOk = faultSignal.getStatus().isOK();
      boolean stickyOk = stickySignal.getStatus().isOK();
      double busVoltage = supplyVoltage.getValue().in(Units.Volts);
      double applied = dutyCycle.getValue();
      double outputCurrent = supplyCurrent.getValue().in(Units.Amps);
      double motorTemp = deviceTemp.getValue().in(Units.Celsius);
      double motorVolts = motorVoltage.getValue().in(Units.Volts);
      String label = BringupUtil.getFalconLabel(i);
      String modelOverride = BringupUtil.getFalconMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      String specNote = formatMotorSpecNote(spec, outputCurrent);
      appendLine(sb,
          "  FALCON CAN " + falconIds[i] +
          ": present=YES fault=0x" + Integer.toHexString(faultField) +
          formatCtreFaults(falcons[i]) +
          " sticky=0x" + Integer.toHexString(stickyField) +
          formatCtreStickyFaults(falcons[i]) +
          " lastErr=" + faultSignal.getStatus() +
          specNote +
          " busV=" + String.format("%.2f", busVoltage) + "V" +
          " appliedDuty=" + String.format("%.2f", applied) + "dc" +
          " appliedV=" + String.format("%.2f", motorVolts) + "V" +
          " motorCurrentA=" + String.format("%.4f", outputCurrent) + "A" +
          " tempC=" + String.format("%.1f", motorTemp) + "C" +
          (faultOk && stickyOk
              ? ""
              : " status=" + faultSignal.getStatus() + "/" + stickySignal.getStatus()));
    }

    for (int i = 0; i < cancoders.length; i++) {
      if (cancoders[i] == null) {
        appendLine(sb, "  CANCoder CAN " + cancoderIds[i] + ": present=NO (not added)");
        continue;
      }
      var absolute = cancoders[i].getAbsolutePosition();
      BaseStatusSignal.refreshAll(absolute);
      double rotations = absolute.getValue().in(Units.Rotations);
      double degrees = rotations * 360.0;
      appendLine(sb,
          "  CANCoder CAN " + cancoderIds[i] +
          ": present=YES absDeg=" + String.format("%.1f", degrees) +
          " lastErr=" + absolute.getStatus());
    }
    appendVirtualDeviceHealth(sb);
  }

  // Append local device health into a JSON array for reports and AI analysis.
  public void appendDeviceDiagnosticsJson(JsonArray devices) {
    if (devices == null) {
      return;
    }
    // Preserve device order for stable diffs between snapshots.
    for (int i = 0; i < neos.length; i++) {
      JsonObject entry = baseDeviceJson("NEO", neoIds[i]);
      if (neos[i] == null) {
        entry.addProperty("present", false);
        entry.addProperty("note", "not added");
        devices.add(entry);
        continue;
      }
      var faults = neos[i].getFaults();
      var stickyFaults = neos[i].getStickyFaults();
      var warnings = neos[i].getWarnings();
      var stickyWarnings = neos[i].getStickyWarnings();
      REVLibError lastError = neos[i].getLastError();
      double busVoltage = neos[i].getBusVoltage();
      double appliedDuty = neos[i].getAppliedOutput();
      double appliedVolts = busVoltage * appliedDuty;
      double outputCurrent = neos[i].getOutputCurrent();
      double motorTemp = neos[i].getMotorTemperature();
      boolean resetFlag = warnings.hasReset || stickyWarnings.hasReset;
      String label = BringupUtil.getNeoLabel(i);
      String modelOverride = BringupUtil.getNeoMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      entry.addProperty("present", true);
      entry.addProperty("faultsRaw", faults.rawBits);
      entry.addProperty("stickyFaultsRaw", stickyFaults.rawBits);
      entry.addProperty("warningsRaw", warnings.rawBits);
      entry.addProperty("stickyWarningsRaw", stickyWarnings.rawBits);
      entry.addProperty("lastError", String.valueOf(lastError));
      entry.addProperty("reset", resetFlag);
      if (spec != null) {
        entry.addProperty("specModel", spec.model);
        entry.addProperty("specNominalV", spec.nominalVoltage);
        entry.addProperty("specFreeA", spec.freeCurrentA);
        entry.addProperty("specStallA", spec.stallCurrentA);
      }
      entry.addProperty("busV", busVoltage);
      entry.addProperty("appliedV", appliedVolts);
      entry.addProperty("motorCurrentA", outputCurrent);
      entry.addProperty("tempC", motorTemp);
      entry.addProperty("cmdDuty", neos[i].get());
      entry.addProperty("appliedDuty", neos[i].getAppliedOutput());
      devices.add(entry);
    }

    for (int i = 0; i < flexes.length; i++) {
      JsonObject entry = baseDeviceJson("FLEX", flexIds[i]);
      if (flexes[i] == null) {
        entry.addProperty("present", false);
        entry.addProperty("note", "not added");
        devices.add(entry);
        continue;
      }
      var faults = flexes[i].getFaults();
      var stickyFaults = flexes[i].getStickyFaults();
      var warnings = flexes[i].getWarnings();
      var stickyWarnings = flexes[i].getStickyWarnings();
      REVLibError lastError = flexes[i].getLastError();
      double busVoltage = flexes[i].getBusVoltage();
      double appliedDuty = flexes[i].getAppliedOutput();
      double appliedVolts = busVoltage * appliedDuty;
      double outputCurrent = flexes[i].getOutputCurrent();
      double motorTemp = flexes[i].getMotorTemperature();
      boolean resetFlag = warnings.hasReset || stickyWarnings.hasReset;
      String label = BringupUtil.getFlexLabel(i);
      String modelOverride = BringupUtil.getFlexMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      entry.addProperty("present", true);
      entry.addProperty("faultsRaw", faults.rawBits);
      entry.addProperty("stickyFaultsRaw", stickyFaults.rawBits);
      entry.addProperty("warningsRaw", warnings.rawBits);
      entry.addProperty("stickyWarningsRaw", stickyWarnings.rawBits);
      entry.addProperty("lastError", String.valueOf(lastError));
      entry.addProperty("reset", resetFlag);
      if (spec != null) {
        entry.addProperty("specModel", spec.model);
        entry.addProperty("specNominalV", spec.nominalVoltage);
        entry.addProperty("specFreeA", spec.freeCurrentA);
        entry.addProperty("specStallA", spec.stallCurrentA);
      }
      entry.addProperty("busV", busVoltage);
      entry.addProperty("appliedV", appliedVolts);
      entry.addProperty("motorCurrentA", outputCurrent);
      entry.addProperty("tempC", motorTemp);
      entry.addProperty("cmdDuty", flexes[i].get());
      entry.addProperty("appliedDuty", flexes[i].getAppliedOutput());
      devices.add(entry);
    }

    for (int i = 0; i < krakens.length; i++) {
      JsonObject entry = baseDeviceJson("KRAKEN", krakenIds[i]);
      if (krakens[i] == null) {
        entry.addProperty("present", false);
        entry.addProperty("note", "not added");
        devices.add(entry);
        continue;
      }
      var faultSignal = krakens[i].getFaultField();
      var stickySignal = krakens[i].getStickyFaultField();
      var supplyVoltage = krakens[i].getSupplyVoltage();
      var dutyCycle = krakens[i].getDutyCycle();
      var supplyCurrent = krakens[i].getSupplyCurrent();
      var deviceTemp = krakens[i].getDeviceTemp();
      var motorVoltage = krakens[i].getMotorVoltage();
      BaseStatusSignal.refreshAll(
          faultSignal,
          stickySignal,
          supplyVoltage,
          dutyCycle,
          supplyCurrent,
          deviceTemp,
          motorVoltage);
      int faultField = faultSignal.getValue();
      int stickyField = stickySignal.getValue();
      double busVoltage = supplyVoltage.getValue().in(Units.Volts);
      double applied = dutyCycle.getValue();
      double outputCurrent = supplyCurrent.getValue().in(Units.Amps);
      double motorTemp = deviceTemp.getValue().in(Units.Celsius);
      double motorVolts = motorVoltage.getValue().in(Units.Volts);
      String label = BringupUtil.getKrakenLabel(i);
      String modelOverride = BringupUtil.getKrakenMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      entry.addProperty("present", true);
      entry.addProperty("faultsRaw", faultField);
      entry.addProperty("stickyFaultsRaw", stickyField);
      entry.addProperty("faultStatus", String.valueOf(faultSignal.getStatus()));
      entry.addProperty("stickyStatus", String.valueOf(stickySignal.getStatus()));
      if (spec != null) {
        entry.addProperty("specModel", spec.model);
        entry.addProperty("specNominalV", spec.nominalVoltage);
        entry.addProperty("specFreeA", spec.freeCurrentA);
        entry.addProperty("specStallA", spec.stallCurrentA);
      }
      entry.addProperty("busV", busVoltage);
      entry.addProperty("appliedDuty", applied);
      entry.addProperty("appliedV", motorVolts);
      entry.addProperty("motorCurrentA", outputCurrent);
      entry.addProperty("tempC", motorTemp);
      entry.addProperty("motorV", motorVolts);
      devices.add(entry);
    }

    for (int i = 0; i < falcons.length; i++) {
      JsonObject entry = baseDeviceJson("FALCON", falconIds[i]);
      if (falcons[i] == null) {
        entry.addProperty("present", false);
        entry.addProperty("note", "not added");
        devices.add(entry);
        continue;
      }
      var faultSignal = falcons[i].getFaultField();
      var stickySignal = falcons[i].getStickyFaultField();
      var supplyVoltage = falcons[i].getSupplyVoltage();
      var dutyCycle = falcons[i].getDutyCycle();
      var supplyCurrent = falcons[i].getSupplyCurrent();
      var deviceTemp = falcons[i].getDeviceTemp();
      var motorVoltage = falcons[i].getMotorVoltage();
      BaseStatusSignal.refreshAll(
          faultSignal,
          stickySignal,
          supplyVoltage,
          dutyCycle,
          supplyCurrent,
          deviceTemp,
          motorVoltage);
      int faultField = faultSignal.getValue();
      int stickyField = stickySignal.getValue();
      double busVoltage = supplyVoltage.getValue().in(Units.Volts);
      double applied = dutyCycle.getValue();
      double outputCurrent = supplyCurrent.getValue().in(Units.Amps);
      double motorTemp = deviceTemp.getValue().in(Units.Celsius);
      double motorVolts = motorVoltage.getValue().in(Units.Volts);
      String label = BringupUtil.getFalconLabel(i);
      String modelOverride = BringupUtil.getFalconMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      entry.addProperty("present", true);
      entry.addProperty("faultsRaw", faultField);
      entry.addProperty("stickyFaultsRaw", stickyField);
      entry.addProperty("faultStatus", String.valueOf(faultSignal.getStatus()));
      entry.addProperty("stickyStatus", String.valueOf(stickySignal.getStatus()));
      if (spec != null) {
        entry.addProperty("specModel", spec.model);
        entry.addProperty("specNominalV", spec.nominalVoltage);
        entry.addProperty("specFreeA", spec.freeCurrentA);
        entry.addProperty("specStallA", spec.stallCurrentA);
      }
      entry.addProperty("busV", busVoltage);
      entry.addProperty("appliedDuty", applied);
      entry.addProperty("appliedV", motorVolts);
      entry.addProperty("motorCurrentA", outputCurrent);
      entry.addProperty("tempC", motorTemp);
      entry.addProperty("motorV", motorVolts);
      devices.add(entry);
    }

    for (int i = 0; i < cancoders.length; i++) {
      JsonObject entry = baseDeviceJson("CANCoder", cancoderIds[i]);
      if (cancoders[i] == null) {
        entry.addProperty("present", false);
        entry.addProperty("note", "not added");
        devices.add(entry);
        continue;
      }
      var absolute = cancoders[i].getAbsolutePosition();
      BaseStatusSignal.refreshAll(absolute);
      double rotations = absolute.getValue().in(Units.Rotations);
      double degrees = rotations * 360.0;
      entry.addProperty("present", true);
      entry.addProperty("absDeg", degrees);
      entry.addProperty("lastError", String.valueOf(absolute.getStatus()));
      devices.add(entry);
    }

    if (BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)) {
      JsonObject entry = baseDeviceJson("roboRIO", BringupUtil.ROBORIO_CAN_ID);
      entry.addProperty("present", true);
      entry.addProperty("note", "virtual");
      devices.add(entry);
    }
  }

  // Create the minimal JSON object for a device entry.
  private static JsonObject baseDeviceJson(String type, int id) {
    JsonObject entry = new JsonObject();
    entry.addProperty("type", type);
    entry.addProperty("id", id);
    return entry;
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

  // Format REV fault bits into a compact list for console output.
  private static String formatRevFaults(SparkBase.Faults faults) {
    StringBuilder sb = new StringBuilder(64);
    appendFlag(sb, "other", faults.other);
    appendFlag(sb, "motorType", faults.motorType);
    appendFlag(sb, "sensor", faults.sensor);
    appendFlag(sb, "can", faults.can);
    appendFlag(sb, "temperature", faults.temperature);
    appendFlag(sb, "gateDriver", faults.gateDriver);
    appendFlag(sb, "escEeprom", faults.escEeprom);
    appendFlag(sb, "firmware", faults.firmware);
    return formatFlagList(sb);
  }

  // Format REV warnings into a compact list for console output.
  private static String formatRevWarnings(SparkBase.Warnings warnings) {
    StringBuilder sb = new StringBuilder(64);
    appendFlag(sb, "brownout", warnings.brownout);
    appendFlag(sb, "overcurrent", warnings.overcurrent);
    appendFlag(sb, "escEeprom", warnings.escEeprom);
    appendFlag(sb, "extEeprom", warnings.extEeprom);
    appendFlag(sb, "sensor", warnings.sensor);
    appendFlag(sb, "stall", warnings.stall);
    appendFlag(sb, "hasReset", warnings.hasReset);
    appendFlag(sb, "other", warnings.other);
    return formatFlagList(sb);
  }

  // Expand CTRE fault StatusSignals into a readable list.
  private static String formatCtreFaults(TalonFX talon) {
    var bootDuringEnable = talon.getFault_BootDuringEnable();
    var bridgeBrownout = talon.getFault_BridgeBrownout();
    var deviceTemp = talon.getFault_DeviceTemp();
    var forwardHardLimit = talon.getFault_ForwardHardLimit();
    var forwardSoftLimit = talon.getFault_ForwardSoftLimit();
    var fusedSensorOutOfSync = talon.getFault_FusedSensorOutOfSync();
    var hardware = talon.getFault_Hardware();
    var missingDifferentialFx = talon.getFault_MissingDifferentialFX();
    var missingHardLimitRemote = talon.getFault_MissingHardLimitRemote();
    var missingSoftLimitRemote = talon.getFault_MissingSoftLimitRemote();
    var overSupplyV = talon.getFault_OverSupplyV();
    var procTemp = talon.getFault_ProcTemp();
    var remoteSensorDataInvalid = talon.getFault_RemoteSensorDataInvalid();
    var remoteSensorPosOverflow = talon.getFault_RemoteSensorPosOverflow();
    var remoteSensorReset = talon.getFault_RemoteSensorReset();
    var reverseHardLimit = talon.getFault_ReverseHardLimit();
    var reverseSoftLimit = talon.getFault_ReverseSoftLimit();
    var staticBrakeDisabled = talon.getFault_StaticBrakeDisabled();
    var statorCurrLimit = talon.getFault_StatorCurrLimit();
    var supplyCurrLimit = talon.getFault_SupplyCurrLimit();
    var undervoltage = talon.getFault_Undervoltage();
    var unlicensedFeatureInUse = talon.getFault_UnlicensedFeatureInUse();
    var unstableSupplyV = talon.getFault_UnstableSupplyV();
    var usingFusedCancoderUnlicensed = talon.getFault_UsingFusedCANcoderWhileUnlicensed();
    BaseStatusSignal.refreshAll(
        bootDuringEnable,
        bridgeBrownout,
        deviceTemp,
        forwardHardLimit,
        forwardSoftLimit,
        fusedSensorOutOfSync,
        hardware,
        missingDifferentialFx,
        missingHardLimitRemote,
        missingSoftLimitRemote,
        overSupplyV,
        procTemp,
        remoteSensorDataInvalid,
        remoteSensorPosOverflow,
        remoteSensorReset,
        reverseHardLimit,
        reverseSoftLimit,
        staticBrakeDisabled,
        statorCurrLimit,
        supplyCurrLimit,
        undervoltage,
        unlicensedFeatureInUse,
        unstableSupplyV,
        usingFusedCancoderUnlicensed);
    StringBuilder sb = new StringBuilder(128);
    appendFlag(sb, "BootDuringEnable", isTrue(bootDuringEnable));
    appendFlag(sb, "BridgeBrownout", isTrue(bridgeBrownout));
    appendFlag(sb, "DeviceTemp", isTrue(deviceTemp));
    appendFlag(sb, "ForwardHardLimit", isTrue(forwardHardLimit));
    appendFlag(sb, "ForwardSoftLimit", isTrue(forwardSoftLimit));
    appendFlag(sb, "FusedSensorOutOfSync", isTrue(fusedSensorOutOfSync));
    appendFlag(sb, "Hardware", isTrue(hardware));
    appendFlag(sb, "MissingDifferentialFX", isTrue(missingDifferentialFx));
    appendFlag(sb, "MissingHardLimitRemote", isTrue(missingHardLimitRemote));
    appendFlag(sb, "MissingSoftLimitRemote", isTrue(missingSoftLimitRemote));
    appendFlag(sb, "OverSupplyV", isTrue(overSupplyV));
    appendFlag(sb, "ProcTemp", isTrue(procTemp));
    appendFlag(sb, "RemoteSensorDataInvalid", isTrue(remoteSensorDataInvalid));
    appendFlag(sb, "RemoteSensorPosOverflow", isTrue(remoteSensorPosOverflow));
    appendFlag(sb, "RemoteSensorReset", isTrue(remoteSensorReset));
    appendFlag(sb, "ReverseHardLimit", isTrue(reverseHardLimit));
    appendFlag(sb, "ReverseSoftLimit", isTrue(reverseSoftLimit));
    appendFlag(sb, "StaticBrakeDisabled", isTrue(staticBrakeDisabled));
    appendFlag(sb, "StatorCurrLimit", isTrue(statorCurrLimit));
    appendFlag(sb, "SupplyCurrLimit", isTrue(supplyCurrLimit));
    appendFlag(sb, "Undervoltage", isTrue(undervoltage));
    appendFlag(sb, "UnlicensedFeatureInUse", isTrue(unlicensedFeatureInUse));
    appendFlag(sb, "UnstableSupplyV", isTrue(unstableSupplyV));
    appendFlag(sb, "UsingFusedCANcoderWhileUnlicensed", isTrue(usingFusedCancoderUnlicensed));
    return formatFlagList(sb);
  }

  // Expand CTRE sticky fault StatusSignals into a readable list.
  private static String formatCtreStickyFaults(TalonFX talon) {
    var bootDuringEnable = talon.getStickyFault_BootDuringEnable();
    var bridgeBrownout = talon.getStickyFault_BridgeBrownout();
    var deviceTemp = talon.getStickyFault_DeviceTemp();
    var forwardHardLimit = talon.getStickyFault_ForwardHardLimit();
    var forwardSoftLimit = talon.getStickyFault_ForwardSoftLimit();
    var fusedSensorOutOfSync = talon.getStickyFault_FusedSensorOutOfSync();
    var hardware = talon.getStickyFault_Hardware();
    var missingDifferentialFx = talon.getStickyFault_MissingDifferentialFX();
    var missingHardLimitRemote = talon.getStickyFault_MissingHardLimitRemote();
    var missingSoftLimitRemote = talon.getStickyFault_MissingSoftLimitRemote();
    var overSupplyV = talon.getStickyFault_OverSupplyV();
    var procTemp = talon.getStickyFault_ProcTemp();
    var remoteSensorDataInvalid = talon.getStickyFault_RemoteSensorDataInvalid();
    var remoteSensorPosOverflow = talon.getStickyFault_RemoteSensorPosOverflow();
    var remoteSensorReset = talon.getStickyFault_RemoteSensorReset();
    var reverseHardLimit = talon.getStickyFault_ReverseHardLimit();
    var reverseSoftLimit = talon.getStickyFault_ReverseSoftLimit();
    var staticBrakeDisabled = talon.getStickyFault_StaticBrakeDisabled();
    var statorCurrLimit = talon.getStickyFault_StatorCurrLimit();
    var supplyCurrLimit = talon.getStickyFault_SupplyCurrLimit();
    var undervoltage = talon.getStickyFault_Undervoltage();
    var unlicensedFeatureInUse = talon.getStickyFault_UnlicensedFeatureInUse();
    var unstableSupplyV = talon.getStickyFault_UnstableSupplyV();
    var usingFusedCancoderUnlicensed = talon.getStickyFault_UsingFusedCANcoderWhileUnlicensed();
    BaseStatusSignal.refreshAll(
        bootDuringEnable,
        bridgeBrownout,
        deviceTemp,
        forwardHardLimit,
        forwardSoftLimit,
        fusedSensorOutOfSync,
        hardware,
        missingDifferentialFx,
        missingHardLimitRemote,
        missingSoftLimitRemote,
        overSupplyV,
        procTemp,
        remoteSensorDataInvalid,
        remoteSensorPosOverflow,
        remoteSensorReset,
        reverseHardLimit,
        reverseSoftLimit,
        staticBrakeDisabled,
        statorCurrLimit,
        supplyCurrLimit,
        undervoltage,
        unlicensedFeatureInUse,
        unstableSupplyV,
        usingFusedCancoderUnlicensed);
    StringBuilder sb = new StringBuilder(128);
    appendFlag(sb, "BootDuringEnable", isTrue(bootDuringEnable));
    appendFlag(sb, "BridgeBrownout", isTrue(bridgeBrownout));
    appendFlag(sb, "DeviceTemp", isTrue(deviceTemp));
    appendFlag(sb, "ForwardHardLimit", isTrue(forwardHardLimit));
    appendFlag(sb, "ForwardSoftLimit", isTrue(forwardSoftLimit));
    appendFlag(sb, "FusedSensorOutOfSync", isTrue(fusedSensorOutOfSync));
    appendFlag(sb, "Hardware", isTrue(hardware));
    appendFlag(sb, "MissingDifferentialFX", isTrue(missingDifferentialFx));
    appendFlag(sb, "MissingHardLimitRemote", isTrue(missingHardLimitRemote));
    appendFlag(sb, "MissingSoftLimitRemote", isTrue(missingSoftLimitRemote));
    appendFlag(sb, "OverSupplyV", isTrue(overSupplyV));
    appendFlag(sb, "ProcTemp", isTrue(procTemp));
    appendFlag(sb, "RemoteSensorDataInvalid", isTrue(remoteSensorDataInvalid));
    appendFlag(sb, "RemoteSensorPosOverflow", isTrue(remoteSensorPosOverflow));
    appendFlag(sb, "RemoteSensorReset", isTrue(remoteSensorReset));
    appendFlag(sb, "ReverseHardLimit", isTrue(reverseHardLimit));
    appendFlag(sb, "ReverseSoftLimit", isTrue(reverseSoftLimit));
    appendFlag(sb, "StaticBrakeDisabled", isTrue(staticBrakeDisabled));
    appendFlag(sb, "StatorCurrLimit", isTrue(statorCurrLimit));
    appendFlag(sb, "SupplyCurrLimit", isTrue(supplyCurrLimit));
    appendFlag(sb, "Undervoltage", isTrue(undervoltage));
    appendFlag(sb, "UnlicensedFeatureInUse", isTrue(unlicensedFeatureInUse));
    appendFlag(sb, "UnstableSupplyV", isTrue(unstableSupplyV));
    appendFlag(sb, "UsingFusedCANcoderWhileUnlicensed", isTrue(usingFusedCancoderUnlicensed));
    return formatFlagList(sb);
  }

  // Phoenix signals wrap Boolean values; normalize null to false.
  private static boolean isTrue(StatusSignal<Boolean> signal) {
    return Boolean.TRUE.equals(signal.getValue());
  }

  // Append a flag name if its status is active.
  private static void appendFlag(StringBuilder sb, String name, boolean active) {
    if (!active) {
      return;
    }
    if (sb.length() > 0) {
      sb.append(',');
    }
    sb.append(name);
  }

  // Format a comma-separated list in square brackets, or empty if none.
  private static String formatFlagList(StringBuilder sb) {
    if (sb.length() == 0) {
      return "";
    }
    return " [" + sb + "]";
  }

  // Shared line-append helper to keep formatting consistent.
  private static void appendLine(StringBuilder sb, String line) {
    sb.append(line).append('\n');
  }

  // Report whether a device is instantiated based on CAN metadata.
  public boolean isDeviceInstantiated(int manufacturer, int deviceType, int deviceId) {
    if (manufacturer == 5 && deviceType == 2) {
      for (int i = 0; i < neoIds.length; i++) {
        if (neoIds[i] == deviceId) {
          return neos[i] != null;
        }
      }
      for (int i = 0; i < flexIds.length; i++) {
        if (flexIds[i] == deviceId) {
          return flexes[i] != null;
        }
      }
      return false;
    }
    if (manufacturer == 4 && deviceType == 2) {
      for (int i = 0; i < krakenIds.length; i++) {
        if (krakenIds[i] == deviceId) {
          return krakens[i] != null;
        }
      }
      for (int i = 0; i < falconIds.length; i++) {
        if (falconIds[i] == deviceId) {
          return falcons[i] != null;
        }
      }
      return false;
    }
    if (manufacturer == 4 && deviceType == 7) {
      for (int i = 0; i < cancoderIds.length; i++) {
        if (cancoderIds[i] == deviceId) {
          return cancoders[i] != null;
        }
      }
    }
    if (manufacturer == NI_MANUFACTURER && deviceType == TYPE_ROBOT_CONTROLLER) {
      return BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)
          && deviceId == BringupUtil.ROBORIO_CAN_ID;
    }
    return false;
  }

  // Summary line with raw bitfields + decoded REV flags.
  private static String formatRevFaultSummary(
      SparkBase.Faults faults,
      SparkBase.Faults stickyFaults,
      SparkBase.Warnings warnings,
      SparkBase.Warnings stickyWarnings) {
    StringBuilder sb = new StringBuilder(128);
    sb.append(" faults=0x").append(Integer.toHexString(faults.rawBits));
    sb.append(formatRevFaults(faults));
    sb.append(" sticky=0x").append(Integer.toHexString(stickyFaults.rawBits));
    sb.append(formatRevFaults(stickyFaults));
    sb.append(" warnings=0x").append(Integer.toHexString(warnings.rawBits));
    sb.append(formatRevWarnings(warnings));
    sb.append(" stickyWarn=0x").append(Integer.toHexString(stickyWarnings.rawBits));
    sb.append(formatRevWarnings(stickyWarnings));
    return sb.toString();
  }
}
