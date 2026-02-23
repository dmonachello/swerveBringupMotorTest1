package frc.robot;

import com.ctre.phoenix6.hardware.TalonFX;
import com.revrobotics.spark.SparkMax;
import edu.wpi.first.wpilibj.GenericHID;

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
  
  public enum CanProfile {
    ROBOT,
    DEMO_BOARD
  }

  private static final int[] ROBOT_NEO_CAN_IDS = { 10, 1, 7, 4 };
  private static final int[] ROBOT_KRAKEN_CAN_IDS = { 11, 2, 8, 5 };
  private static final int[] ROBOT_CANCODER_CAN_IDS = { 12, 3, 9, 6 };

  private static final int[] DEMO_NEO_CAN_IDS = { 25, 22, 10, -1 };
  private static final int[] DEMO_KRAKEN_CAN_IDS = { -1, -1, -1, -1 };
  private static final int[] DEMO_CANCODER_CAN_IDS = { -1, -1, -1, -1 };

  private static CanProfile activeProfile = CanProfile.ROBOT;

  public static int[] NEO_CAN_IDS = ROBOT_NEO_CAN_IDS;
  public static int[] KRAKEN_CAN_IDS = ROBOT_KRAKEN_CAN_IDS;
  public static int[] CANCODER_CAN_IDS = ROBOT_CANCODER_CAN_IDS;
  public static final int DISABLED_CAN_ID = -1;
  public static final double DEADBAND = 0.12;

  public static final class KeyboardKeys {
    private KeyboardKeys() {}

    // USB HID usage IDs used by the Driver Station Keyboard; adjust if DS mapping differs.
    public static final int A = 4;
    public static final int B = 5;
    public static final int H = 11;
    public static final int I = 12;
    public static final int K = 14;
    public static final int P = 19;
    public static final int R = 21;
    public static final int S = 22;
    public static final int W = 26;
    public static final int X = 27;
    public static final int Y = 28;
    public static final int ENTER = 40;
    public static final int SPACE = 44;

    public static boolean isPressed(GenericHID keyboard, int keyUsageId) {
      return keyboard.getRawButton(keyUsageId);
    }
  }

  public static void setActiveCanProfile(CanProfile profile) {
    activeProfile = profile;
    if (profile == CanProfile.ROBOT) {
      NEO_CAN_IDS = ROBOT_NEO_CAN_IDS;
      KRAKEN_CAN_IDS = ROBOT_KRAKEN_CAN_IDS;
      CANCODER_CAN_IDS = ROBOT_CANCODER_CAN_IDS;
    } else {
      NEO_CAN_IDS = DEMO_NEO_CAN_IDS;
      KRAKEN_CAN_IDS = DEMO_KRAKEN_CAN_IDS;
      CANCODER_CAN_IDS = DEMO_CANCODER_CAN_IDS;
    }
  }

  public static void toggleCanProfile() {
    setActiveCanProfile(activeProfile == CanProfile.DEMO_BOARD ? CanProfile.ROBOT : CanProfile.DEMO_BOARD);
  }

  public static CanProfile getActiveCanProfile() {
    return activeProfile;
  }

  public static String getActiveCanProfileLabel() {
    return activeProfile == CanProfile.ROBOT ? "Robot" : "Demo Board";
  }

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
