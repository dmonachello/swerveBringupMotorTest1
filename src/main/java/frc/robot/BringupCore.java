package frc.robot;

import com.ctre.phoenix6.BaseStatusSignal;
import com.ctre.phoenix6.StatusSignal;
import com.ctre.phoenix6.hardware.CANcoder;
import com.ctre.phoenix6.hardware.CANdle;
import com.ctre.phoenix6.hardware.TalonFX;
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
import java.util.ArrayList;
import java.util.List;
import frc.robot.diag.readers.CtreCANCoderReader;
import frc.robot.diag.readers.CtreCandleReader;
import frc.robot.diag.readers.CtreTalonFxReader;
import frc.robot.diag.readers.RevSparkFlexReader;
import frc.robot.diag.readers.RevSparkMaxReader;
import frc.robot.diag.snapshots.DeviceSnapshot;

// Core bringup logic: creates devices, commands outputs, and prints local health.
// This class only uses robot-local vendor APIs (no PC sniffer data).
public final class BringupCore {
  private static final int NI_MANUFACTURER = 1;
  private static final int TYPE_ROBOT_CONTROLLER = 1;
  private final int[] neoIds = BringupUtil.filterCanIds(BringupUtil.NEO_CAN_IDS);
  private final int[] neo550Ids = BringupUtil.filterCanIds(BringupUtil.NEO550_CAN_IDS);
  private final int[] flexIds = BringupUtil.filterCanIds(BringupUtil.FLEX_CAN_IDS);
  private final int[] krakenIds = BringupUtil.filterCanIds(BringupUtil.KRAKEN_CAN_IDS);
  private final int[] falconIds = BringupUtil.filterCanIds(BringupUtil.FALCON_CAN_IDS);
  private final int[] cancoderIds = BringupUtil.filterCanIds(BringupUtil.CANCODER_CAN_IDS);
  private final int[] candleIds = BringupUtil.filterCanIds(BringupUtil.CANDLE_CAN_IDS);

  private final SparkMax[] neos = new SparkMax[neoIds.length];
  private final SparkMax[] neo550s = new SparkMax[neo550Ids.length];
  private final SparkFlex[] flexes = new SparkFlex[flexIds.length];
  private final TalonFX[] krakens = new TalonFX[krakenIds.length];
  private final TalonFX[] falcons = new TalonFX[falconIds.length];
  private final CANcoder[] cancoders = new CANcoder[cancoderIds.length];
  private final CANdle[] candles = new CANdle[candleIds.length];
  private final double[] neoLowCurrentStartSec = new double[neoIds.length];
  private final double[] neo550LowCurrentStartSec = new double[neo550Ids.length];
  private final double[] flexLowCurrentStartSec = new double[flexIds.length];

  private int nextNeo = 0;
  private int nextNeo550 = 0;
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
    BringupUtil.setAllNeo550s(neo550s, neoSpeed);
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

  // Clear current and sticky faults on all instantiated devices where supported.
  public void clearAllFaults() {
    for (SparkMax neo : neos) {
      if (neo != null) {
        neo.clearFaults();
      }
    }
    for (SparkMax neo550 : neo550s) {
      if (neo550 != null) {
        neo550.clearFaults();
      }
    }
    for (SparkFlex flex : flexes) {
      if (flex != null) {
        flex.clearFaults();
      }
    }
    for (TalonFX kraken : krakens) {
      if (kraken != null) {
        kraken.clearStickyFaults();
      }
    }
    for (TalonFX falcon : falcons) {
      if (falcon != null) {
        falcon.clearStickyFaults();
      }
    }
    for (CANcoder cancoder : cancoders) {
      if (cancoder != null) {
        cancoder.clearStickyFaults();
      }
    }
    for (CANdle candle : candles) {
      if (candle != null) {
        candle.clearStickyFaults();
      }
    }
  }

  // Stop all outputs, close devices, and reset internal state.
  public void resetState() {
    BringupUtil.stopAll(neos, neo550s, flexes, krakens, falcons);

    for (int i = 0; i < neos.length; i++) {
      BringupUtil.closeIfPossible(neos[i]);
      neos[i] = null;
    }
    for (int i = 0; i < neo550s.length; i++) {
      BringupUtil.closeIfPossible(neo550s[i]);
      neo550s[i] = null;
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
    for (int i = 0; i < candles.length; i++) {
      BringupUtil.closeIfPossible(candles[i]);
      candles[i] = null;
    }

    nextNeo = 0;
    nextNeo550 = 0;
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
      if (!addNextNeo() && !addNextNeo550() && !addNextFlex()) {
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

  // Lazily instantiate the next available NEO 550.
  private boolean addNextNeo550() {
    if (nextNeo550 < neo550s.length && neo550s[nextNeo550] == null) {
      neo550s[nextNeo550] = new SparkMax(neo550Ids[nextNeo550], MotorType.kBrushless);
      neo550s[nextNeo550].pauseFollowerModeAsync();
      neo550s[nextNeo550].configureAsync(
          new SparkMaxConfig(),
          ResetMode.kResetSafeParameters,
          PersistMode.kNoPersistParameters);

      BringupPrinter.enqueue(
          "Added NEO 550 index " + nextNeo550 +
          " (CAN " + neo550Ids[nextNeo550] + ")");

      nextNeo550++;
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
    for (int i = 0; i < neo550s.length; i++) {
      if (neo550s[i] == null) {
        neo550s[i] = new SparkMax(neo550Ids[i], MotorType.kBrushless);
        neo550s[i].pauseFollowerModeAsync();
        neo550s[i].configureAsync(
            new SparkMaxConfig(),
            ResetMode.kResetSafeParameters,
            PersistMode.kNoPersistParameters);
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
    for (int i = 0; i < candles.length; i++) {
      if (candles[i] == null) {
        candles[i] = new CANdle(candleIds[i]);
      }
    }

    nextNeo = neos.length;
    nextNeo550 = neo550s.length;
    nextFlex = flexes.length;
    nextKraken = krakens.length;
    nextFalcon = falcons.length;
    addNeoNext = true;

    BringupPrinter.enqueue("Added all SPARKs, Krakens, Falcons, CANCoders, and CANdles.");
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

    if (neo550s.length > 0) {
      appendLine(sb, "NEO 550:");
      for (int i = 0; i < neo550s.length; i++) {
        if (neo550s[i] != null) {
          appendLine(sb, "  index " + i +
              " CAN " + neo550Ids[i] + " ACTIVE");
        } else {
          appendLine(sb, "  index " + i +
              " CAN " + neo550Ids[i] + " not added");
        }
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

    if (candles.length > 0) {
      appendLine(sb, "CANdles:");
      for (int i = 0; i < candles.length; i++) {
        if (candles[i] != null) {
          appendLine(sb, "  index " + i +
              " CAN " + candleIds[i] + " ACTIVE");
        } else {
          appendLine(sb, "  index " + i +
              " CAN " + candleIds[i] + " not added");
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

    for (int i = 0; i < neo550s.length; i++) {
      if (neo550s[i] == null) {
        appendLine(sb, "NEO 550 index " + i +
            " CAN " + neo550Ids[i] + " not added");
        continue;
      }
      var faults = neo550s[i].getFaults();
      var stickyFaults = neo550s[i].getStickyFaults();
      var warnings = neo550s[i].getWarnings();
      var stickyWarnings = neo550s[i].getStickyWarnings();
      REVLibError lastError = neo550s[i].getLastError();
      double busVoltage = neo550s[i].getBusVoltage();
      double appliedOutput = neo550s[i].getAppliedOutput();
      double appliedVolts = busVoltage * appliedOutput;
      double outputCurrent = neo550s[i].getOutputCurrent();
      double motorTemp = neo550s[i].getMotorTemperature();
      double setpoint = neo550s[i].get();
      boolean follower = neo550s[i].isFollower();
      String healthNote = buildRevHealthNote(lastError, busVoltage);
      String lowCurrentNote =
          buildLowCurrentNote(neo550LowCurrentStartSec, i, nowSec, appliedVolts, outputCurrent);
      String label = BringupUtil.getNeo550Label(i);
      String modelOverride = BringupUtil.getNeo550MotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      String specNote = formatMotorSpecNote(spec, outputCurrent);
      appendLine(sb,
          "NEO 550 index " + i +
          " CAN " + neo550Ids[i] +
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
    for (int i = 0; i < candles.length; i++) {
      if (candles[i] == null) {
        appendLine(sb, "CANdle index " + i +
            " CAN " + candleIds[i] + " not added");
        continue;
      }
      appendLine(sb,
          "CANdle index " + i +
          " CAN " + candleIds[i] +
          " present=YES");
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

  private static String buildRevHealthNote(String lastError, double busVoltage) {
    boolean timeout = "kTimeout".equals(lastError);
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
    Arrays.fill(neo550LowCurrentStartSec, -1.0);
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

  // Capture local device data into snapshot objects (no formatting here).
  public List<DeviceSnapshot> captureSnapshots() {
    List<DeviceSnapshot> devices = new ArrayList<>();
    double nowSec = Timer.getFPGATimestamp();

    for (int i = 0; i < neos.length; i++) {
      if (neos[i] == null) {
        DeviceSnapshot snap = new DeviceSnapshot();
        snap.vendor = "REV";
        snap.deviceType = "NEO";
        snap.canId = neoIds[i];
        snap.present = false;
        snap.note = "not added";
        devices.add(snap);
        continue;
      }
      DeviceSnapshot snap = RevSparkMaxReader.read(neos[i], neoIds[i]);
      String label = BringupUtil.getNeoLabel(i);
      String modelOverride = BringupUtil.getNeoMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      snap.label = label;
      if (spec != null) {
        snap.model = spec.model;
        snap.specNominalV = spec.nominalVoltage;
        snap.specFreeA = spec.freeCurrentA;
        snap.specStallA = spec.stallCurrentA;
      }
      snap.healthNote = buildRevHealthNote(snap.lastError, snap.busV != null ? snap.busV : 0.0);
      snap.lowCurrentNote = buildLowCurrentNote(
          neoLowCurrentStartSec,
          i,
          nowSec,
          snap.appliedV != null ? snap.appliedV : 0.0,
          snap.motorCurrentA != null ? snap.motorCurrentA : 0.0);
      devices.add(snap);
    }

    for (int i = 0; i < neo550s.length; i++) {
      if (neo550s[i] == null) {
        DeviceSnapshot snap = new DeviceSnapshot();
        snap.vendor = "REV";
        snap.deviceType = "NEO 550";
        snap.canId = neo550Ids[i];
        snap.present = false;
        snap.note = "not added";
        devices.add(snap);
        continue;
      }
      DeviceSnapshot snap = RevSparkMaxReader.read(neo550s[i], neo550Ids[i]);
      String label = BringupUtil.getNeo550Label(i);
      String modelOverride = BringupUtil.getNeo550MotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      snap.label = label;
      if (spec != null) {
        snap.model = spec.model;
        snap.specNominalV = spec.nominalVoltage;
        snap.specFreeA = spec.freeCurrentA;
        snap.specStallA = spec.stallCurrentA;
      }
      snap.healthNote = buildRevHealthNote(snap.lastError, snap.busV != null ? snap.busV : 0.0);
      snap.lowCurrentNote = buildLowCurrentNote(
          neo550LowCurrentStartSec,
          i,
          nowSec,
          snap.appliedV != null ? snap.appliedV : 0.0,
          snap.motorCurrentA != null ? snap.motorCurrentA : 0.0);
      devices.add(snap);
    }

    for (int i = 0; i < flexes.length; i++) {
      if (flexes[i] == null) {
        DeviceSnapshot snap = new DeviceSnapshot();
        snap.vendor = "REV";
        snap.deviceType = "FLEX";
        snap.canId = flexIds[i];
        snap.present = false;
        snap.note = "not added";
        devices.add(snap);
        continue;
      }
      DeviceSnapshot snap = RevSparkFlexReader.read(flexes[i], flexIds[i]);
      String label = BringupUtil.getFlexLabel(i);
      String modelOverride = BringupUtil.getFlexMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      snap.label = label;
      if (spec != null) {
        snap.model = spec.model;
        snap.specNominalV = spec.nominalVoltage;
        snap.specFreeA = spec.freeCurrentA;
        snap.specStallA = spec.stallCurrentA;
      }
      snap.healthNote = buildRevHealthNote(snap.lastError, snap.busV != null ? snap.busV : 0.0);
      snap.lowCurrentNote = buildLowCurrentNote(
          flexLowCurrentStartSec,
          i,
          nowSec,
          snap.appliedV != null ? snap.appliedV : 0.0,
          snap.motorCurrentA != null ? snap.motorCurrentA : 0.0);
      devices.add(snap);
    }

    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i] == null) {
        DeviceSnapshot snap = new DeviceSnapshot();
        snap.vendor = "CTRE";
        snap.deviceType = "KRAKEN";
        snap.canId = krakenIds[i];
        snap.present = false;
        snap.note = "not added";
        devices.add(snap);
        continue;
      }
      DeviceSnapshot snap = CtreTalonFxReader.read(krakens[i], "KRAKEN", krakenIds[i]);
      String label = BringupUtil.getKrakenLabel(i);
      String modelOverride = BringupUtil.getKrakenMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      snap.label = label;
      if (spec != null) {
        snap.model = spec.model;
        snap.specNominalV = spec.nominalVoltage;
        snap.specFreeA = spec.freeCurrentA;
        snap.specStallA = spec.stallCurrentA;
      }
      devices.add(snap);
    }

    for (int i = 0; i < falcons.length; i++) {
      if (falcons[i] == null) {
        DeviceSnapshot snap = new DeviceSnapshot();
        snap.vendor = "CTRE";
        snap.deviceType = "FALCON";
        snap.canId = falconIds[i];
        snap.present = false;
        snap.note = "not added";
        devices.add(snap);
        continue;
      }
      DeviceSnapshot snap = CtreTalonFxReader.read(falcons[i], "FALCON", falconIds[i]);
      String label = BringupUtil.getFalconLabel(i);
      String modelOverride = BringupUtil.getFalconMotorModel(i);
      BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
      snap.label = label;
      if (spec != null) {
        snap.model = spec.model;
        snap.specNominalV = spec.nominalVoltage;
        snap.specFreeA = spec.freeCurrentA;
        snap.specStallA = spec.stallCurrentA;
      }
      devices.add(snap);
    }

    for (int i = 0; i < cancoders.length; i++) {
      if (cancoders[i] == null) {
        DeviceSnapshot snap = new DeviceSnapshot();
        snap.vendor = "CTRE";
        snap.deviceType = "CANCoder";
        snap.canId = cancoderIds[i];
        snap.present = false;
        snap.note = "not added";
        devices.add(snap);
        continue;
      }
      DeviceSnapshot snap = CtreCANCoderReader.read(cancoders[i], cancoderIds[i]);
      devices.add(snap);
    }

    for (int i = 0; i < candles.length; i++) {
      if (candles[i] == null) {
        DeviceSnapshot snap = new DeviceSnapshot();
        snap.vendor = "CTRE";
        snap.deviceType = "CANdle";
        snap.canId = candleIds[i];
        snap.present = false;
        snap.note = "not added";
        devices.add(snap);
        continue;
      }
      DeviceSnapshot snap = CtreCandleReader.read(candles[i], candleIds[i]);
      snap.label = BringupUtil.getCandleLabel(i);
      devices.add(snap);
    }

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
      for (int i = 0; i < neo550Ids.length; i++) {
        if (neo550Ids[i] == deviceId) {
          return neo550s[i] != null;
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
    if (manufacturer == 4 && deviceType == 10) {
      for (int i = 0; i < candleIds.length; i++) {
        if (candleIds[i] == deviceId) {
          return candles[i] != null;
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
