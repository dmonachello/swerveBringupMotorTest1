package frc.robot;

import com.ctre.phoenix6.hardware.TalonFX;
import com.revrobotics.spark.SparkMax;

public final class BringupUtil {
  private BringupUtil() {}

  public static final int[] NEO_CAN_IDS = { 10, 1, 7, 4 };
  public static final int[] KRAKEN_CAN_IDS = { 11, 2, 8, 5 };
  public static final int[] CANCODER_CAN_IDS = { 12, 3, 9, 6 };
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
    for (int i = 0; i < ids.length; i++) {
      if (i > 0) {
        builder.append(", ");
      }
      builder.append(ids[i]);
    }
    return builder.toString();
  }

  public static double deadband(double value, double deadband) {
    return Math.abs(value) < deadband ? 0.0 : value;
  }

  public static void validateCanIds(int[]... idGroups) {
    java.util.HashSet<Integer> seen = new java.util.HashSet<>();
    boolean hasDuplicate = false;

    for (int[] ids : idGroups) {
      for (int id : ids) {
        if (!seen.add(id)) {
          System.out.println("Warning: duplicate CAN ID: " + id);
          hasDuplicate = true;
        }
      }
    }

    if (hasDuplicate) {
      System.out.println("Warning: duplicate CAN IDs can cause bringup confusion.");
    }
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
