package frc.robot;

import com.ctre.phoenix6.hardware.TalonFX;
import com.revrobotics.spark.SparkMax;

public final class BringupUtil {
  private BringupUtil() {}


  // CAN ID (6 bits) range - spark - 1 - 62, kracken 0 - 62
  // ---------------- CAN ID DEFINITIONS ----------------
  // front right neo - 10
  // front left neo  -  1
  // back right neo  -  7
  // back left neo   -  4

  // front right kraken - 11
  // front left kraken - 2
  // back right kraken - 8
  // back left kraken - 5

  // front right cancoder - 12
  // front left cancoder - 3 
  // back right cancoder - 9
  // back left cancoder - 6
  // ---------------------------------------------------
  
  // public static final int[] NEO_CAN_IDS = { 10, 1, 7, 4 };
  // public static final int[] KRAKEN_CAN_IDS = { 11, 2, 8, 5 };
  // public static final int[] CANCODER_CAN_IDS = { 12, 3, 9, 6 };

  public static final int[] NEO_CAN_IDS = { 25, 22, 10, -1 };
  public static final int[] KRAKEN_CAN_IDS = { -1, -1, -1, -1 };
  public static final int[] CANCODER_CAN_IDS = { -1, -1, -1, -1 };
  public static final int DISABLED_CAN_ID = -1;
  public static final double DEADBAND = 0.12;

  public static void setAllNeos(SparkMax[] neos, double speed) {
    for (int i = 0; i < neos.length; i++) {
      if (neos[i] != null) {
        neos[i].set(speed);
      }
    }
  }

  public static void setAllKrakens(TalonFX[] krakens, double speed) {
    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i] != null) {
        krakens[i].set(speed);
      }
    }
  }

  public static void stopAll(SparkMax[] neos, TalonFX[] krakens) {
    setAllNeos(neos, 0.0);
    setAllKrakens(krakens, 0.0);
  }

  public static String joinIds(int[] ids) {
    StringBuilder builder = new StringBuilder();
    int count = 0;
    for (int i = 0; i < ids.length; i++) {
      if (!isEnabledCanId(ids[i])) {
        continue;
      }
      if (count > 0) {
        builder.append(", ");
      }
      builder.append(ids[i]);
      count++;
    }
    if (count == 0) {
      return "(none)";
    }
    return builder.toString();
  }

  public static double deadband(double value, double deadband) {
    return Math.abs(value) < deadband ? 0.0 : value;
  }

  public static void validateCanIds(int[]... idGroups) {
    validateCanIds(null, idGroups);
  }

  public static void validateCanIds(String[] groupLabels, int[]... idGroups) {
    java.util.HashSet<Integer> seen = new java.util.HashSet<>();
    boolean hasDuplicate = false;

    for (int groupIndex = 0; groupIndex < idGroups.length; groupIndex++) {
      int[] ids = idGroups[groupIndex];
      int enabledCount = 0;
      for (int id : ids) {
        if (!isEnabledCanId(id)) {
          continue;
        }
        enabledCount++;
        if (!seen.add(id)) {
          System.out.println("Warning: duplicate CAN ID: " + id);
          hasDuplicate = true;
        }
      }
      if (enabledCount == 0) {
        String label = "group " + (groupIndex + 1);
        if (groupLabels != null && groupIndex < groupLabels.length) {
          label = groupLabels[groupIndex];
        }
        System.out.println("Warning: all CAN IDs disabled for " + label + ".");
      }
    }

    if (hasDuplicate) {
      System.out.println("Warning: duplicate CAN IDs can cause bringup confusion.");
    }
  }

  public static int[] filterCanIds(int[] ids) {
    int enabledCount = countEnabledCanIds(ids);
    int[] filtered = new int[enabledCount];
    int index = 0;
    for (int id : ids) {
      if (isEnabledCanId(id)) {
        filtered[index++] = id;
      }
    }
    return filtered;
  }

  public static int countEnabledCanIds(int[] ids) {
    int count = 0;
    for (int id : ids) {
      if (isEnabledCanId(id)) {
        count++;
      }
    }
    return count;
  }

  public static boolean isEnabledCanId(int id) {
    return id != DISABLED_CAN_ID;
  }

  public static void closeIfPossible(Object device) {
    // CTRE Phoenix 6 WPI TalonFX implements AutoCloseable (wpiapi-java 26.1.1+),
    // so this will clean up Sendables and sim resources when present.
    // REV SparkMax implements AutoCloseable via SparkLowLevel in REVLib 2025.0.2+;
    // close() releases the native handle and marks the instance closed (future use throws).
    if (device instanceof AutoCloseable closeable) {
      try {
        closeable.close();
      } catch (Exception e) {
        System.out.println("Warning: failed to close device: " + e.getMessage());
      }
    }
  }
}
