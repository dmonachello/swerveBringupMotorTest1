package frc.robot;

import com.ctre.phoenix6.BaseStatusSignal;
import com.ctre.phoenix6.hardware.CANcoder;
import com.ctre.phoenix6.hardware.TalonFX;
import edu.wpi.first.units.Units;
import com.revrobotics.spark.SparkMax;
import com.revrobotics.spark.SparkLowLevel.MotorType;

public final class BringupCore {
  private final int[] neoIds = BringupUtil.filterCanIds(BringupUtil.NEO_CAN_IDS);
  private final int[] krakenIds = BringupUtil.filterCanIds(BringupUtil.KRAKEN_CAN_IDS);
  private final int[] cancoderIds = BringupUtil.filterCanIds(BringupUtil.CANCODER_CAN_IDS);

  private final SparkMax[] neos = new SparkMax[neoIds.length];
  private final TalonFX[] krakens = new TalonFX[krakenIds.length];
  private final CANcoder[] cancoders = new CANcoder[cancoderIds.length];

  private int nextNeo = 0;
  private int nextKraken = 0;
  private boolean addNeoNext = true;

  private boolean prevAdd = false;
  private boolean prevAddAll = false;
  private boolean prevPrint = false;
  private boolean prevHealth = false;
  private boolean prevCANCoder = false;

  public void handleAdd(boolean addNow) {
    if (addNow && !prevAdd) {
      addNextMotor();
    }
    prevAdd = addNow;
  }

  public void handleAddAll(boolean addAllNow) {
    if (addAllNow && !prevAddAll) {
      addAllDevices();
    }
    prevAddAll = addAllNow;
  }

  public void handlePrint(boolean printNow) {
    if (printNow && !prevPrint) {
      printState();
    }
    prevPrint = printNow;
  }

  public void handleHealth(boolean healthNow) {
    if (healthNow && !prevHealth) {
      printHealthStatus();
    }
    prevHealth = healthNow;
  }

  public void handleCANCoder(boolean printNow) {
    if (printNow && !prevCANCoder) {
      printCANCoderStatus();
    }
    prevCANCoder = printNow;
  }

  public void setSpeeds(double neoSpeed, double krakenSpeed) {
    BringupUtil.setAllNeos(neos, neoSpeed);
    BringupUtil.setAllKrakens(krakens, krakenSpeed);
  }

  public void resetState() {
    BringupUtil.stopAll(neos, krakens);

    for (int i = 0; i < neos.length; i++) {
      BringupUtil.closeIfPossible(neos[i]);
      neos[i] = null;
    }
    for (int i = 0; i < krakens.length; i++) {
      BringupUtil.closeIfPossible(krakens[i]);
      krakens[i] = null;
    }
    for (int i = 0; i < cancoders.length; i++) {
      BringupUtil.closeIfPossible(cancoders[i]);
      cancoders[i] = null;
    }

    nextNeo = 0;
    nextKraken = 0;
    addNeoNext = true;

    prevAdd = false;
    prevAddAll = false;
    prevPrint = false;
    prevHealth = false;
    prevCANCoder = false;

    System.out.println("=== Bringup reset: no motors instantiated ===");
  }

  private void addNextMotor() {
    if (addNeoNext) {
      if (nextNeo < neos.length && neos[nextNeo] == null) {
        neos[nextNeo] = new SparkMax(neoIds[nextNeo], MotorType.kBrushless);

        System.out.println(
            "Added NEO index " + nextNeo +
            " (CAN " + neoIds[nextNeo] + ")");

        nextNeo++;
      } else {
        System.out.println("No more NEOs to add");
      }
      addNeoNext = false;
      return;
    }

    if (nextKraken < krakens.length && krakens[nextKraken] == null) {
      krakens[nextKraken] = new TalonFX(krakenIds[nextKraken]);

      System.out.println(
          "Added KRAKEN index " + nextKraken +
          " (CAN " + krakenIds[nextKraken] + ")");

      nextKraken++;
    } else {
      System.out.println("No more Krakens to add");
    }
    addNeoNext = true;
  }

  private void addAllDevices() {
    for (int i = 0; i < neos.length; i++) {
      if (neos[i] == null) {
        neos[i] = new SparkMax(neoIds[i], MotorType.kBrushless);
      }
    }
    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i] == null) {
        krakens[i] = new TalonFX(krakenIds[i]);
      }
    }
    for (int i = 0; i < cancoders.length; i++) {
      if (cancoders[i] == null) {
        cancoders[i] = new CANcoder(cancoderIds[i]);
      }
    }

    nextNeo = neos.length;
    nextKraken = krakens.length;
    addNeoNext = true;

    System.out.println("Added all NEOs, Krakens, and CANCoders.");
  }

  private void printState() {
    System.out.println("=== Bringup State ===");

    System.out.println("NEOs:");
    for (int i = 0; i < neos.length; i++) {
      if (neos[i] != null) {
        System.out.println("  index " + i +
            " CAN " + neoIds[i] + " ACTIVE");
      } else {
        System.out.println("  index " + i +
            " CAN " + neoIds[i] + " not added");
      }
    }

    System.out.println("Krakens:");
    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i] != null) {
        System.out.println("  index " + i +
            " CAN " + krakenIds[i] + " ACTIVE");
      } else {
        System.out.println("  index " + i +
            " CAN " + krakenIds[i] + " not added");
      }
    }

    System.out.println(
        "Next add will be: " +
        (addNeoNext ? "NEO" : "KRAKEN"));
    System.out.println("=====================");
  }

  private void printHealthStatus() {
    System.out.println("=== Bringup Health ===");
    for (int i = 0; i < neos.length; i++) {
      if (neos[i] == null) {
        System.out.println("NEO index " + i +
            " CAN " + neoIds[i] + " not added");
        continue;
      }
      var faults = neos[i].getFaults();
      var warnings = neos[i].getWarnings();
      System.out.println(
          "NEO index " + i +
          " CAN " + neoIds[i] +
          " faults=0x" + Integer.toHexString(faults.rawBits) +
          " warnings=0x" + Integer.toHexString(warnings.rawBits));
    }

    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i] == null) {
        System.out.println("KRAKEN index " + i +
            " CAN " + krakenIds[i] + " not added");
        continue;
      }
      var faultSignal = krakens[i].getFaultField();
      var stickySignal = krakens[i].getStickyFaultField();
      BaseStatusSignal.refreshAll(faultSignal, stickySignal);
      int faultField = faultSignal.getValue();
      int stickyField = stickySignal.getValue();
      boolean faultOk = faultSignal.getStatus().isOK();
      boolean stickyOk = stickySignal.getStatus().isOK();
      System.out.println(
          "KRAKEN index " + i +
          " CAN " + krakenIds[i] +
          " fault=0x" + Integer.toHexString(faultField) +
          " sticky=0x" + Integer.toHexString(stickyField) +
          (faultOk && stickyOk
              ? ""
              : " status=" + faultSignal.getStatus() + "/" + stickySignal.getStatus()));
    }
    System.out.println("======================");
  }

  private void printCANCoderStatus() {
    System.out.println("=== Bringup CANCoder ===");
    for (int i = 0; i < cancoders.length; i++) {
      if (cancoders[i] == null) {
        cancoders[i] = new CANcoder(cancoderIds[i]);
      }
      var absolute = cancoders[i].getAbsolutePosition();
      BaseStatusSignal.refreshAll(absolute);
      double rotations = absolute.getValue().in(Units.Rotations);
      double degrees = rotations * 360.0;
      System.out.println(
          "CANCoder index " + i +
          " CAN " + cancoderIds[i] +
          " absRot=" + String.format("%.4f", rotations) +
          " absDeg=" + String.format("%.1f", degrees));
    }
    System.out.println("=======================");
  }
}
