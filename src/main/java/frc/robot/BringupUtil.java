package frc.robot;

import com.ctre.phoenix6.SignalLogger;
import com.ctre.phoenix6.hardware.TalonFX;
import com.google.gson.Gson;
import com.google.gson.JsonParseException;
import com.google.gson.annotations.SerializedName;
import com.revrobotics.spark.SparkFlex;
import com.revrobotics.spark.SparkMax;
import com.revrobotics.util.StatusLogger;
import edu.wpi.first.wpilibj.GenericHID;
import edu.wpi.first.wpilibj.Filesystem;
import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * NAME
 *   BringupUtil - Shared CAN bringup utilities and profile handling.
 *
 * DESCRIPTION
 *   Loads CAN profiles, validates IDs, provides device helpers, and exposes
 *   constants used across the bringup system.
 */
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
  
  // Fallback profiles used when JSON is missing or invalid.
  private static final int[] FALLBACK_ROBOT_NEO_CAN_IDS = { 10, 1, 7, 4 };
  private static final int[] FALLBACK_ROBOT_KRAKEN_CAN_IDS = { 11, 2, 8, 5 };
  private static final int[] FALLBACK_ROBOT_CANCODER_CAN_IDS = { 12, 3, 9, 6 };

  private static final int[] FALLBACK_DEMO_NEO_CAN_IDS = { 25, 22, 10, -1 };
  private static final int[] FALLBACK_DEMO_KRAKEN_CAN_IDS = { -1, -1, -1, -1 };
  private static final int[] FALLBACK_DEMO_CANCODER_CAN_IDS = { -1, -1, -1, -1 };

  private static final int FALLBACK_PDH_CAN_ID = 1;
  private static final int FALLBACK_PIGEON_CAN_ID = 1;
  private static final int FALLBACK_ROBORIO_CAN_ID = 0;

  // Default profile names and file location.
  private static final String DEFAULT_PROFILE_NAME = "robot";
  private static final String DEFAULT_PROFILE_FILE = "bringup_profiles.json";
  private static final String MOTOR_SPECS_FILE = "motor_specs.json";
  private static final String CAN_MAPPINGS_FILE = "can_mappings.json";

  // JSON parser for bringup_profiles.json.
  private static final Gson GSON = new Gson();

  // Profile registry as loaded from JSON (or fallback).
  private static Map<String, CanProfileConfig> profiles = new LinkedHashMap<>();
  private static List<String> profileOrder = new ArrayList<>();
  private static String defaultProfile = DEFAULT_PROFILE_NAME;
  private static final Map<String, MotorSpec> MOTOR_SPECS = loadMotorSpecs();
  private static final CanMappings CAN_MAPPINGS = loadCanMappings();
  private static final Map<DeviceKey, List<DeviceConfig>> DEVICE_CONFIGS = new LinkedHashMap<>();

  // Currently active profile name.
  private static String activeProfile = DEFAULT_PROFILE_NAME;

  // Active CAN ID arrays used by BringupCore.
  public static int[] NEO_CAN_IDS = FALLBACK_ROBOT_NEO_CAN_IDS;
  public static int[] NEO550_CAN_IDS = new int[0];
  public static int[] FLEX_CAN_IDS = new int[0];
  public static int[] KRAKEN_CAN_IDS = FALLBACK_ROBOT_KRAKEN_CAN_IDS;
  public static int[] FALCON_CAN_IDS = new int[0];
  public static int[] CANCODER_CAN_IDS = FALLBACK_ROBOT_CANCODER_CAN_IDS;
  public static int[] CANDLE_CAN_IDS = new int[0];
  public static String[] NEO_LABELS = new String[0];
  public static String[] NEO550_LABELS = new String[0];
  public static String[] FLEX_LABELS = new String[0];
  public static String[] KRAKEN_LABELS = new String[0];
  public static String[] FALCON_LABELS = new String[0];
  public static String[] CANCODER_LABELS = new String[0];
  public static String[] CANDLE_LABELS = new String[0];
  public static String[] NEO_MOTOR_MODELS = new String[0];
  public static String[] NEO550_MOTOR_MODELS = new String[0];
  public static String[] FLEX_MOTOR_MODELS = new String[0];
  public static String[] KRAKEN_MOTOR_MODELS = new String[0];
  public static String[] FALCON_MOTOR_MODELS = new String[0];
  public static LimitConfig[] NEO_LIMITS = new LimitConfig[0];
  public static LimitConfig[] NEO550_LIMITS = new LimitConfig[0];
  public static LimitConfig[] FLEX_LIMITS = new LimitConfig[0];
  public static LimitConfig[] KRAKEN_LIMITS = new LimitConfig[0];
  public static LimitConfig[] FALCON_LIMITS = new LimitConfig[0];
  public static LimitConfig[] CANCODER_LIMITS = new LimitConfig[0];
  public static LimitConfig[] CANDLE_LIMITS = new LimitConfig[0];
  public static int PDH_CAN_ID = FALLBACK_PDH_CAN_ID;
  public static int PIGEON_CAN_ID = FALLBACK_PIGEON_CAN_ID;
  public static int ROBORIO_CAN_ID = FALLBACK_ROBORIO_CAN_ID;
  public static final int DISABLED_CAN_ID = -1;
  public static final double DEADBAND = 0.12;

  // Initialize logging suppression and load the profile JSON.
  static {
    disableVendorLogging();
    loadProfilesFromJson();
    setActiveCanProfile(activeProfile);
  }

  // Disable vendor auto-logging to avoid extra files on the roboRIO.
  private static void disableVendorLogging() {
    // Disable vendor auto-logging to avoid writing .revlog/.hoot files on the roboRIO.
    try {
      StatusLogger.disableAutoLogging();
      StatusLogger.stop();
    } catch (Throwable ignored) {
      // Ignore if REVLib is unavailable.
    }
    try {
      SignalLogger.enableAutoLogging(false);
      SignalLogger.stop();
    } catch (Throwable ignored) {
      // Ignore if Phoenix is unavailable.
    }
  }

  /**
   * NAME
   *   KeyboardKeys - Driver Station keyboard HID usage IDs.
   */
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

    /**
     * NAME
     *   isPressed - Check a keyboard key state by usage ID.
     *
     * PARAMETERS
     *   keyboard - GenericHID for the Driver Station keyboard.
     *   keyUsageId - USB HID usage ID.
     *
     * RETURNS
     *   True if the key is pressed.
     */
    public static boolean isPressed(GenericHID keyboard, int keyUsageId) {
      return keyboard.getRawButton(keyUsageId);
    }
  }

  /**
   * NAME
   *   setActiveCanProfile - Apply a named CAN profile.
   *
   * PARAMETERS
   *   profileName - Profile name to load.
   *
   * SIDE EFFECTS
   *   Updates static CAN ID arrays and label metadata.
   */
  public static void setActiveCanProfile(String profileName) {
    // Resolve profile name and apply its IDs to static arrays.
    if (profileName == null || profileName.isBlank()) {
      profileName = defaultProfile;
    }
    CanProfileConfig config = profiles.get(profileName);
    if (config == null) {
      System.out.println("Warning: unknown CAN profile '" + profileName + "'. Using default.");
      config = profiles.get(defaultProfile);
      profileName = defaultProfile;
    }
    if (config == null) {
      System.out.println("Warning: default CAN profile missing; using fallback IDs.");
      applyFallbackProfile();
      activeProfile = DEFAULT_PROFILE_NAME;
      return;
    }

    NEO_CAN_IDS = toIdArray(config.neos);
    NEO550_CAN_IDS = toIdArray(config.neo550s);
    FLEX_CAN_IDS = toIdArray(config.flexes);
    KRAKEN_CAN_IDS = toIdArray(config.krakens);
    FALCON_CAN_IDS = toIdArray(config.falcons);
    CANCODER_CAN_IDS = toIdArray(config.cancoders);
    CANDLE_CAN_IDS = toIdArray(config.candles);
    NEO_LABELS = toLabelArray(config.neos, "NEO");
    NEO550_LABELS = toLabelArray(config.neo550s, "NEO 550");
    FLEX_LABELS = toLabelArray(config.flexes, "FLEX");
    KRAKEN_LABELS = toLabelArray(config.krakens, "KRAKEN");
    FALCON_LABELS = toLabelArray(config.falcons, "FALCON");
    CANCODER_LABELS = toLabelArray(config.cancoders, "CANCoder");
    CANDLE_LABELS = toLabelArray(config.candles, "CANdle");
    NEO_MOTOR_MODELS = toMotorArray(config.neos);
    NEO550_MOTOR_MODELS = toMotorArray(config.neo550s);
    FLEX_MOTOR_MODELS = toMotorArray(config.flexes);
    KRAKEN_MOTOR_MODELS = toMotorArray(config.krakens);
    FALCON_MOTOR_MODELS = toMotorArray(config.falcons);
    NEO_LIMITS = toLimitArray(config.neos);
    NEO550_LIMITS = toLimitArray(config.neo550s);
    FLEX_LIMITS = toLimitArray(config.flexes);
    KRAKEN_LIMITS = toLimitArray(config.krakens);
    FALCON_LIMITS = toLimitArray(config.falcons);
    CANCODER_LIMITS = toLimitArray(config.cancoders);
    CANDLE_LIMITS = toLimitArray(config.candles);
    PDH_CAN_ID = config.pdh != null ? config.pdh.id : DISABLED_CAN_ID;
    PIGEON_CAN_ID = config.pigeon != null ? config.pigeon.id : DISABLED_CAN_ID;
    ROBORIO_CAN_ID = config.roborio != null ? config.roborio.id : DISABLED_CAN_ID;
    activeProfile = profileName;
    buildDeviceConfigs(config);
  }

  /**
   * NAME
   *   toggleCanProfile - Cycle to the next profile in order.
   */
  public static void toggleCanProfile() {
    // Cycle through profiles in a stable order.
    if (profileOrder.isEmpty()) {
      return;
    }
    int index = profileOrder.indexOf(activeProfile);
    int nextIndex = (index < 0 ? 0 : (index + 1) % profileOrder.size());
    setActiveCanProfile(profileOrder.get(nextIndex));
  }

  public static String getActiveCanProfile() {
    // Raw profile name (used in logs and reports).
    return activeProfile;
  }

  public static String getActiveCanProfileLabel() {
    // Label currently matches profile name, but can diverge later.
    return activeProfile;
  }

  /**
   * NAME
   *   setAllNeos - Apply a duty cycle to all SPARK MAX devices.
   *
   * PARAMETERS
   *   neos - Array of SparkMax devices.
   *   speed - Duty cycle (-1..1).
   */
  public static void setAllNeos(SparkMax[] neos, double speed) {
    // Apply output to all instantiated SPARK MAX devices.
    for (int i = 0; i < neos.length; i++) {
      if (neos[i] != null) {
        neos[i].set(speed);
      }
    }
  }

  /**
   * NAME
   *   setAllNeo550s - Apply a duty cycle to all NEO 550 devices.
   *
   * PARAMETERS
   *   neo550s - Array of SparkMax devices.
   *   speed - Duty cycle (-1..1).
   */
  public static void setAllNeo550s(SparkMax[] neo550s, double speed) {
    // Apply output to all instantiated NEO 550 SPARK MAX devices.
    for (int i = 0; i < neo550s.length; i++) {
      if (neo550s[i] != null) {
        neo550s[i].set(speed);
      }
    }
  }

  /**
   * NAME
   *   setAllFlexes - Apply a duty cycle to all SPARK FLEX devices.
   *
   * PARAMETERS
   *   flexes - Array of SparkFlex devices.
   *   speed - Duty cycle (-1..1).
   */
  public static void setAllFlexes(SparkFlex[] flexes, double speed) {
    // Apply output to all instantiated SPARK FLEX devices.
    for (int i = 0; i < flexes.length; i++) {
      if (flexes[i] != null) {
        flexes[i].set(speed);
      }
    }
  }

  /**
   * NAME
   *   setAllKrakens - Apply a duty cycle to all TalonFX devices.
   *
   * PARAMETERS
   *   krakens - Array of TalonFX devices.
   *   speed - Duty cycle (-1..1).
   */
  public static void setAllKrakens(TalonFX[] krakens, double speed) {
    // Apply output to all instantiated CTRE Krakens.
    for (int i = 0; i < krakens.length; i++) {
      if (krakens[i] != null) {
        krakens[i].set(speed);
      }
    }
  }

  /**
   * NAME
   *   setAllFalcons - Apply a duty cycle to all Falcon devices.
   *
   * PARAMETERS
   *   falcons - Array of TalonFX devices.
   *   speed - Duty cycle (-1..1).
   */
  public static void setAllFalcons(TalonFX[] falcons, double speed) {
    // Apply output to all instantiated CTRE Falcons.
    for (int i = 0; i < falcons.length; i++) {
      if (falcons[i] != null) {
        falcons[i].set(speed);
      }
    }
  }

  /**
   * NAME
   *   stopAll - Stop all device arrays by setting duty to zero.
   */
  public static void stopAll(
      SparkMax[] neos,
      SparkMax[] neo550s,
      SparkFlex[] flexes,
      TalonFX[] krakens,
      TalonFX[] falcons) {
    // Stop every output with a zero command.
    setAllNeos(neos, 0.0);
    setAllNeo550s(neo550s, 0.0);
    setAllFlexes(flexes, 0.0);
    setAllKrakens(krakens, 0.0);
    setAllFalcons(falcons, 0.0);
  }

  /**
   * NAME
   *   joinIds - Build a comma-separated list of enabled CAN IDs.
   *
   * PARAMETERS
   *   ids - CAN ID array.
   *
   * RETURNS
   *   String list or "(none)" when empty.
   */
  public static String joinIds(int[] ids) {
    // Join enabled IDs into a friendly comma-separated list.
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

  /**
   * NAME
   *   deadband - Zero small inputs below a threshold.
   *
   * PARAMETERS
   *   value - Input value.
   *   deadband - Threshold magnitude.
   *
   * RETURNS
   *   Zero when within deadband, otherwise the original value.
   */
  public static double deadband(double value, double deadband) {
    // Zero out small stick values to reduce noise.
    return Math.abs(value) < deadband ? 0.0 : value;
  }

  /**
   * NAME
   *   validateCanIds - Validate CAN ID groups without labels.
   */
  public static void validateCanIds(int[]... idGroups) {
    // Convenience overload without labels.
    validateCanIds(null, idGroups);
  }

  /**
   * NAME
   *   validateCanIds - Warn on duplicates and empty groups.
   *
   * PARAMETERS
   *   groupLabels - Optional labels for groups.
   *   idGroups - CAN ID groups to validate.
   */
  public static void validateCanIds(String[] groupLabels, int[]... idGroups) {
    // Warn on duplicates and empty groups to catch configuration issues early.
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

  /**
   * NAME
   *   filterCanIds - Remove disabled IDs while preserving order.
   *
   * PARAMETERS
   *   ids - CAN ID array.
   *
   * RETURNS
   *   Filtered array with only enabled IDs.
   */
  public static int[] filterCanIds(int[] ids) {
    // Drop disabled IDs while preserving order.
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

  /**
   * NAME
   *   countEnabledCanIds - Count enabled IDs in an array.
   */
  public static int countEnabledCanIds(int[] ids) {
    // Count IDs that are not DISABLED_CAN_ID.
    int count = 0;
    for (int id : ids) {
      if (isEnabledCanId(id)) {
        count++;
      }
    }
    return count;
  }

  /**
   * NAME
   *   isEnabledCanId - Check if an ID is not disabled.
   */
  public static boolean isEnabledCanId(int id) {
    // Convention: -1 means "disabled" in JSON and code.
    return id != DISABLED_CAN_ID;
  }

  /**
   * NAME
   *   closeIfPossible - Close a device if it implements AutoCloseable.
   */
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

  /**
   * NAME
   *   applyProfileFromArgs - Resolve and apply profile from CLI/env/system props.
   *
   * SIDE EFFECTS
   *   Updates active profile and logs selection.
   */
  public static void applyProfileFromArgs() {
    // Read profile name from JVM props, env var, or command-line flag.
    String profile = System.getProperty("bringup.profile");
    if (profile == null || profile.isBlank()) {
      profile = System.getenv("BRINGUP_PROFILE");
    }
    if (profile == null || profile.isBlank()) {
      profile = extractProfileFromCommand();
    }
    if (profile != null && !profile.isBlank()) {
      setActiveCanProfile(profile.trim());
    }
  }

  private static String extractProfileFromCommand() {
    // Parse --bringup-profile=... from the Java command line.
    String command = System.getProperty("sun.java.command");
    if (command == null || command.isBlank()) {
      return null;
    }
    String[] parts = command.split("\\s+");
    for (String part : parts) {
      if (part.startsWith("--bringup-profile=")) {
        return part.substring("--bringup-profile=".length());
      }
    }
    return null;
  }

  /**
   * NAME
   *   extractBringupTestsFromCommand - Parse bringup test path from JVM args.
   *
   * RETURNS
   *   Test path string or null when not present.
   */
  public static String extractBringupTestsFromCommand() {
    // Parse --bringup-tests=... from the Java command line.
    String command = System.getProperty("sun.java.command");
    if (command == null || command.isBlank()) {
      return null;
    }
    String[] parts = command.split("\\s+");
    for (String part : parts) {
      if (part.startsWith("--bringup-tests=")) {
        return part.substring("--bringup-tests=".length());
      }
    }
    return null;
  }

  /**
   * NAME
   *   loadProfilesFromJson - Load bringup_profiles.json into memory.
   */
  private static void loadProfilesFromJson() {
    // Load bringup_profiles.json from deploy or dev path.
    Path path = resolveProfilePath();
    if (path == null || !Files.exists(path)) {
      System.out.println("Warning: CAN profile JSON not found. Using fallback IDs.");
      applyFallbackProfile();
      return;
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      ProfileRoot root = GSON.fromJson(reader, ProfileRoot.class);
      if (root == null || root.profiles == null || root.profiles.isEmpty()) {
        throw new JsonParseException("No profiles found");
      }
      profiles = new LinkedHashMap<>(root.profiles);
      profileOrder = new ArrayList<>(profiles.keySet());
      defaultProfile = root.defaultProfile != null ? root.defaultProfile : DEFAULT_PROFILE_NAME;
      if (!profiles.containsKey(defaultProfile)) {
        System.out.println("Warning: default_profile not found in JSON. Using 'robot'.");
        defaultProfile = DEFAULT_PROFILE_NAME;
      }
      activeProfile = defaultProfile;
    } catch (IOException | JsonParseException ex) {
      System.out.println("Warning: failed to read CAN profile JSON: " + ex.getMessage());
      applyFallbackProfile();
    }
  }

  /**
   * NAME
   *   resolveProfilePath - Resolve the profile JSON path.
   */
  private static Path resolveProfilePath() {
    // Use deploy folder on roboRIO, fallback to repo-relative path.
    try {
      Path deployPath = Filesystem.getDeployDirectory().toPath().resolve(DEFAULT_PROFILE_FILE);
      if (Files.exists(deployPath)) {
        return deployPath;
      }
    } catch (Exception ex) {
      // Fall through to local dev path.
    }
    Path devPath = Paths.get("src", "main", "deploy", DEFAULT_PROFILE_FILE);
    if (Files.exists(devPath)) {
      return devPath;
    }
    return Paths.get(DEFAULT_PROFILE_FILE);
  }

  /**
   * NAME
   *   applyFallbackProfile - Populate built-in fallback profiles.
   */
  private static void applyFallbackProfile() {
    // Populate default profiles in-memory when JSON is unavailable.
    profiles = new LinkedHashMap<>();
    profiles.put("robot", new CanProfileConfig(
        toDevices(FALLBACK_ROBOT_NEO_CAN_IDS),
        Collections.emptyList(),
        Collections.emptyList(),
        toDevices(FALLBACK_ROBOT_KRAKEN_CAN_IDS),
        Collections.emptyList(),
        toDevices(FALLBACK_ROBOT_CANCODER_CAN_IDS),
        Collections.emptyList(),
        Collections.emptyList(),
        new DeviceRef(FALLBACK_PDH_CAN_ID),
        new DeviceRef(FALLBACK_PIGEON_CAN_ID),
        new DeviceRef(FALLBACK_ROBORIO_CAN_ID)));
    profiles.put("demo_club", new CanProfileConfig(
        toDevices(FALLBACK_DEMO_NEO_CAN_IDS),
        Collections.emptyList(),
        Collections.emptyList(),
        toDevices(FALLBACK_DEMO_KRAKEN_CAN_IDS),
        Collections.emptyList(),
        toDevices(FALLBACK_DEMO_CANCODER_CAN_IDS),
        Collections.emptyList(),
        Collections.emptyList(),
        null,
        null,
        new DeviceRef(FALLBACK_ROBORIO_CAN_ID)));
    profiles.put("demo_home", new CanProfileConfig(
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        null,
        null,
        new DeviceRef(FALLBACK_ROBORIO_CAN_ID)));
    profileOrder = new ArrayList<>(profiles.keySet());
    defaultProfile = DEFAULT_PROFILE_NAME;
    activeProfile = defaultProfile;
    NEO_CAN_IDS = FALLBACK_ROBOT_NEO_CAN_IDS;
    NEO550_CAN_IDS = new int[0];
    FLEX_CAN_IDS = new int[0];
    KRAKEN_CAN_IDS = FALLBACK_ROBOT_KRAKEN_CAN_IDS;
    FALCON_CAN_IDS = new int[0];
    CANCODER_CAN_IDS = FALLBACK_ROBOT_CANCODER_CAN_IDS;
    CANDLE_CAN_IDS = new int[0];
    NEO_LABELS = toLabelArray(toDevices(FALLBACK_ROBOT_NEO_CAN_IDS), "NEO");
    NEO550_LABELS = new String[0];
    FLEX_LABELS = new String[0];
    KRAKEN_LABELS = toLabelArray(toDevices(FALLBACK_ROBOT_KRAKEN_CAN_IDS), "KRAKEN");
    FALCON_LABELS = new String[0];
    CANCODER_LABELS = toLabelArray(toDevices(FALLBACK_ROBOT_CANCODER_CAN_IDS), "CANCoder");
    CANDLE_LABELS = new String[0];
    NEO_MOTOR_MODELS = new String[NEO_LABELS.length];
    NEO550_MOTOR_MODELS = new String[0];
    FLEX_MOTOR_MODELS = new String[0];
    KRAKEN_MOTOR_MODELS = new String[KRAKEN_LABELS.length];
    FALCON_MOTOR_MODELS = new String[0];
    NEO_LIMITS = toLimitArray(toDevices(FALLBACK_ROBOT_NEO_CAN_IDS));
    NEO550_LIMITS = new LimitConfig[0];
    FLEX_LIMITS = new LimitConfig[0];
    KRAKEN_LIMITS = toLimitArray(toDevices(FALLBACK_ROBOT_KRAKEN_CAN_IDS));
    FALCON_LIMITS = new LimitConfig[0];
    CANCODER_LIMITS = toLimitArray(toDevices(FALLBACK_ROBOT_CANCODER_CAN_IDS));
    CANDLE_LIMITS = new LimitConfig[0];
    PDH_CAN_ID = FALLBACK_PDH_CAN_ID;
    PIGEON_CAN_ID = FALLBACK_PIGEON_CAN_ID;
    ROBORIO_CAN_ID = FALLBACK_ROBORIO_CAN_ID;
    buildDeviceConfigs(profiles.get(DEFAULT_PROFILE_NAME));
  }

  /**
   * NAME
   *   getDeviceConfigs - Return device configs for a vendor/type.
   *
   * PARAMETERS
   *   vendor - Vendor name (e.g., REV, CTRE).
   *   deviceType - Device type label.
   *
   * RETURNS
   *   List of DeviceConfig entries or empty list.
   */
  public static List<DeviceConfig> getDeviceConfigs(String vendor, String deviceType) {
    if (vendor == null || deviceType == null) {
      return Collections.emptyList();
    }
    List<DeviceConfig> configs = DEVICE_CONFIGS.get(new DeviceKey(vendor, deviceType));
    return configs != null ? configs : Collections.emptyList();
  }

  /**
   * NAME
   *   buildDeviceConfigs - Build device config lookup tables.
   */
  private static void buildDeviceConfigs(CanProfileConfig config) {
    DEVICE_CONFIGS.clear();
    if (config == null) {
      return;
    }
    registerDeviceConfigs("REV", "NEO", config.neos, "NEO");
    registerDeviceConfigs("REV", "NEO 550", config.neo550s, "NEO 550");
    registerDeviceConfigs("REV", "FLEX", config.flexes, "FLEX");
    registerDeviceConfigs("CTRE", "KRAKEN", config.krakens, "KRAKEN");
    registerDeviceConfigs("CTRE", "FALCON", config.falcons, "FALCON");
    registerDeviceConfigs("CTRE", "CANCoder", config.cancoders, "CANCoder");
    registerDeviceConfigs("CTRE", "CANdle", config.candles, "CANdle");
    registerGenericDeviceConfigs(config.devices);
  }

  /**
   * NAME
   *   registerDeviceConfigs - Register device configs for a vendor/type.
   */
  private static void registerDeviceConfigs(
      String vendor,
      String deviceType,
      List<DeviceRef> refs,
      String defaultLabelPrefix) {
    List<DeviceConfig> configs = toDeviceConfigs(refs, defaultLabelPrefix);
    if (!configs.isEmpty()) {
      DEVICE_CONFIGS.put(new DeviceKey(vendor, deviceType), configs);
    }
  }

  /**
   * NAME
   *   registerGenericDeviceConfigs - Register generic device configs.
   */
  private static void registerGenericDeviceConfigs(List<DeviceRef> refs) {
    if (refs == null || refs.isEmpty()) {
      return;
    }
    for (DeviceRef ref : refs) {
      if (ref == null || ref.vendor == null || ref.type == null) {
        System.out.println("Warning: generic device entry missing vendor/type.");
        continue;
      }
      String vendor = ref.vendor.trim();
      String type = ref.type.trim();
      if (vendor.isBlank() || type.isBlank()) {
        System.out.println("Warning: generic device entry missing vendor/type.");
        continue;
      }
      DeviceConfig config = toDeviceConfig(ref, type + " " + ref.id);
      DeviceKey key = new DeviceKey(vendor, type);
      DEVICE_CONFIGS.computeIfAbsent(key, ignored -> new ArrayList<>()).add(config);
    }
  }

  /**
   * NAME
   *   toIdArray - Convert device refs to raw ID array.
   */
  private static int[] toIdArray(List<DeviceRef> refs) {
    // Convert JSON device objects into raw ID arrays.
    if (refs == null || refs.isEmpty()) {
      return new int[0];
    }
    int[] ids = new int[refs.size()];
    for (int i = 0; i < refs.size(); i++) {
      ids[i] = refs.get(i).id;
    }
    return ids;
  }

  /**
   * NAME
   *   toDevices - Convert raw IDs to device refs.
   */
  private static List<DeviceRef> toDevices(int[] ids) {
    // Convert raw IDs into JSON device objects for fallback profiles.
    List<DeviceRef> refs = new ArrayList<>();
    for (int id : ids) {
      if (isEnabledCanId(id)) {
        refs.add(new DeviceRef(id));
      }
    }
    return refs;
  }

  /**
   * NAME
   *   toLabelArray - Build label array with defaults.
   */
  private static String[] toLabelArray(List<DeviceRef> refs, String prefix) {
    if (refs == null || refs.isEmpty()) {
      return new String[0];
    }
    String[] labels = new String[refs.size()];
    for (int i = 0; i < refs.size(); i++) {
      DeviceRef ref = refs.get(i);
      String label = ref.label;
      if (label == null || label.isBlank()) {
        label = prefix + " " + ref.id;
      }
      labels[i] = label;
    }
    return labels;
  }

  /**
   * NAME
   *   toDeviceConfigs - Convert refs to DeviceConfig entries.
   */
  private static List<DeviceConfig> toDeviceConfigs(List<DeviceRef> refs, String defaultLabelPrefix) {
    if (refs == null || refs.isEmpty()) {
      return Collections.emptyList();
    }
    List<DeviceConfig> configs = new ArrayList<>(refs.size());
    for (DeviceRef ref : refs) {
      if (ref == null) {
        continue;
      }
      String label = ref.label;
      if (label == null || label.isBlank()) {
        label = defaultLabelPrefix + " " + ref.id;
      }
      configs.add(new DeviceConfig(ref.id, label, ref.motor, ref.limits));
    }
    return configs;
  }

  /**
   * NAME
   *   toDeviceConfig - Convert a single ref to DeviceConfig.
   */
  private static DeviceConfig toDeviceConfig(DeviceRef ref, String fallbackLabel) {
    String label = ref.label;
    if (label == null || label.isBlank()) {
      label = fallbackLabel;
    }
    return new DeviceConfig(ref.id, label, ref.motor, ref.limits);
  }

  /**
   * NAME
   *   toMotorArray - Build motor model array from refs.
   */
  private static String[] toMotorArray(List<DeviceRef> refs) {
    if (refs == null || refs.isEmpty()) {
      return new String[0];
    }
    String[] motors = new String[refs.size()];
    for (int i = 0; i < refs.size(); i++) {
      motors[i] = refs.get(i).motor;
    }
    return motors;
  }

  /**
   * NAME
   *   toLimitArray - Build limit config array from refs.
   */
  private static LimitConfig[] toLimitArray(List<DeviceRef> refs) {
    if (refs == null || refs.isEmpty()) {
      return new LimitConfig[0];
    }
    LimitConfig[] limits = new LimitConfig[refs.size()];
    for (int i = 0; i < refs.size(); i++) {
      DeviceRef ref = refs.get(i);
      limits[i] = ref.limits != null ? ref.limits : new LimitConfig();
    }
    return limits;
  }

  /**
   * NAME
   *   getNeoLabel - Return the label for a NEO at index.
   */
  public static String getNeoLabel(int index) {
    return labelForIndex(NEO_LABELS, NEO_CAN_IDS, index, "NEO");
  }

  /**
   * NAME
   *   getNeo550Label - Return the label for a NEO 550 at index.
   */
  public static String getNeo550Label(int index) {
    return labelForIndex(NEO550_LABELS, NEO550_CAN_IDS, index, "NEO 550");
  }

  /**
   * NAME
   *   getFlexLabel - Return the label for a FLEX at index.
   */
  public static String getFlexLabel(int index) {
    return labelForIndex(FLEX_LABELS, FLEX_CAN_IDS, index, "FLEX");
  }

  /**
   * NAME
   *   getKrakenLabel - Return the label for a Kraken at index.
   */
  public static String getKrakenLabel(int index) {
    return labelForIndex(KRAKEN_LABELS, KRAKEN_CAN_IDS, index, "KRAKEN");
  }

  /**
   * NAME
   *   getFalconLabel - Return the label for a Falcon at index.
   */
  public static String getFalconLabel(int index) {
    return labelForIndex(FALCON_LABELS, FALCON_CAN_IDS, index, "FALCON");
  }

  /**
   * NAME
   *   getCANCoderLabel - Return the label for a CANCoder at index.
   */
  public static String getCANCoderLabel(int index) {
    return labelForIndex(CANCODER_LABELS, CANCODER_CAN_IDS, index, "CANCoder");
  }

  /**
   * NAME
   *   getCandleLabel - Return the label for a CANdle at index.
   */
  public static String getCandleLabel(int index) {
    return labelForIndex(CANDLE_LABELS, CANDLE_CAN_IDS, index, "CANdle");
  }

  /**
   * NAME
   *   getNeoMotorModel - Return motor model override for NEO index.
   */
  public static String getNeoMotorModel(int index) {
    return motorForIndex(NEO_MOTOR_MODELS, index);
  }

  /**
   * NAME
   *   getNeo550MotorModel - Return motor model override for NEO 550 index.
   */
  public static String getNeo550MotorModel(int index) {
    return motorForIndex(NEO550_MOTOR_MODELS, index);
  }

  /**
   * NAME
   *   getFlexMotorModel - Return motor model override for FLEX index.
   */
  public static String getFlexMotorModel(int index) {
    return motorForIndex(FLEX_MOTOR_MODELS, index);
  }

  /**
   * NAME
   *   getKrakenMotorModel - Return motor model override for Kraken index.
   */
  public static String getKrakenMotorModel(int index) {
    return motorForIndex(KRAKEN_MOTOR_MODELS, index);
  }

  /**
   * NAME
   *   getFalconMotorModel - Return motor model override for Falcon index.
   */
  public static String getFalconMotorModel(int index) {
    return motorForIndex(FALCON_MOTOR_MODELS, index);
  }

  /**
   * NAME
   *   getNeoLimitConfig - Return limit config for NEO index.
   */
  public static LimitConfig getNeoLimitConfig(int index) {
    return limitForIndex(NEO_LIMITS, index);
  }

  /**
   * NAME
   *   getNeo550LimitConfig - Return limit config for NEO 550 index.
   */
  public static LimitConfig getNeo550LimitConfig(int index) {
    return limitForIndex(NEO550_LIMITS, index);
  }

  /**
   * NAME
   *   getFlexLimitConfig - Return limit config for FLEX index.
   */
  public static LimitConfig getFlexLimitConfig(int index) {
    return limitForIndex(FLEX_LIMITS, index);
  }

  /**
   * NAME
   *   getKrakenLimitConfig - Return limit config for Kraken index.
   */
  public static LimitConfig getKrakenLimitConfig(int index) {
    return limitForIndex(KRAKEN_LIMITS, index);
  }

  /**
   * NAME
   *   getFalconLimitConfig - Return limit config for Falcon index.
   */
  public static LimitConfig getFalconLimitConfig(int index) {
    return limitForIndex(FALCON_LIMITS, index);
  }

  /**
   * NAME
   *   getCANCoderLimitConfig - Return limit config for CANCoder index.
   */
  public static LimitConfig getCANCoderLimitConfig(int index) {
    return limitForIndex(CANCODER_LIMITS, index);
  }

  /**
   * NAME
   *   getCandleLimitConfig - Return limit config for CANdle index.
   */
  public static LimitConfig getCandleLimitConfig(int index) {
    return limitForIndex(CANDLE_LIMITS, index);
  }

  /**
   * NAME
   *   labelForIndex - Resolve label with bounds and fallback.
   */
  private static String labelForIndex(String[] labels, int[] ids, int index, String prefix) {
    if (labels == null || index < 0 || index >= labels.length) {
      return prefix + " " + (index >= 0 && index < ids.length ? ids[index] : "?");
    }
    return labels[index];
  }

  /**
   * NAME
   *   motorForIndex - Resolve motor model for an index.
   */
  private static String motorForIndex(String[] motors, int index) {
    if (motors == null || index < 0 || index >= motors.length) {
      return null;
    }
    String model = motors[index];
    return (model == null || model.isBlank()) ? null : model;
  }

  /**
   * NAME
   *   limitForIndex - Resolve limit config for an index.
   */
  private static LimitConfig limitForIndex(LimitConfig[] limits, int index) {
    if (limits == null || index < 0 || index >= limits.length) {
      return new LimitConfig();
    }
    return limits[index] != null ? limits[index] : new LimitConfig();
  }

  /**
   * NAME
   *   getMotorSpecForDevice - Resolve motor specs for a device label/model.
   *
   * PARAMETERS
   *   label - Device label.
   *   modelOverride - Optional explicit motor model name.
   *
   * RETURNS
   *   MotorSpec or null when unknown.
   */
  public static MotorSpec getMotorSpecForDevice(String label, String modelOverride) {
    String model = modelOverride;
    if (model == null || model.isBlank()) {
      model = inferMotorModelFromLabel(label);
    }
    if (model == null) {
      return null;
    }
    return MOTOR_SPECS.get(model);
  }

  /**
   * NAME
   *   getCanManufacturerName - Resolve manufacturer ID to name.
   */
  public static String getCanManufacturerName(int id) {
    if (CAN_MAPPINGS == null || CAN_MAPPINGS.manufacturers == null) {
      return null;
    }
    return CAN_MAPPINGS.manufacturers.get(String.valueOf(id));
  }

  /**
   * NAME
   *   getCanDeviceTypeName - Resolve device type ID to name.
   */
  public static String getCanDeviceTypeName(int id) {
    if (CAN_MAPPINGS == null || CAN_MAPPINGS.deviceTypes == null) {
      return null;
    }
    return CAN_MAPPINGS.deviceTypes.get(String.valueOf(id));
  }

  /**
   * NAME
   *   inferMotorModelFromLabel - Guess motor model from a label.
   */
  private static String inferMotorModelFromLabel(String label) {
    if (label == null) {
      return null;
    }
    String upper = label.toUpperCase();
    if (upper.contains("VORTEX")) {
      return "REV NEO Vortex";
    }
    if (upper.contains("NEO 550") || upper.contains("NEO550")) {
      return "REV NEO 550";
    }
    if (upper.contains("NEO 2.0") || upper.contains("NEO2")) {
      return "REV NEO 2.0";
    }
    if (upper.contains("NEO")) {
      return "REV NEO";
    }
    if (upper.contains("KRAKEN")) {
      return "CTRE Kraken X60";
    }
    if (upper.contains("FALCON")) {
      return "CTRE Falcon 500";
    }
    return null;
  }

  /**
   * NAME
   *   loadMotorSpecs - Load motor_specs.json from deploy.
   */
  private static Map<String, MotorSpec> loadMotorSpecs() {
    Map<String, MotorSpec> fallback = new LinkedHashMap<>();
    Path path = resolveDeployPath(MOTOR_SPECS_FILE);
    if (path == null || !Files.exists(path)) {
      return fallback;
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      MotorSpecRoot root = GSON.fromJson(reader, MotorSpecRoot.class);
      if (root == null || root.motors == null) {
        return fallback;
      }
      Map<String, MotorSpec> specs = new LinkedHashMap<>();
      for (MotorSpec spec : root.motors) {
        if (spec == null || spec.model == null || spec.model.isBlank()) {
          continue;
        }
        specs.put(spec.model, spec);
      }
      return specs;
    } catch (IOException | JsonParseException ex) {
      System.out.println("Warning: failed to load motor specs: " + ex.getMessage());
      return fallback;
    }
  }

  /**
   * NAME
   *   loadCanMappings - Load CAN manufacturer/type mappings.
   */
  private static CanMappings loadCanMappings() {
    Path path = resolveDeployPath(CAN_MAPPINGS_FILE);
    if (path == null || !Files.exists(path)) {
      return new CanMappings();
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      CanMappings mappings = GSON.fromJson(reader, CanMappings.class);
      return mappings != null ? mappings : new CanMappings();
    } catch (IOException | JsonParseException ex) {
      System.out.println("Warning: failed to load CAN mappings: " + ex.getMessage());
      return new CanMappings();
    }
  }

  /**
   * NAME
   *   resolveDeployPath - Resolve a deploy file path with dev fallback.
   */
  private static Path resolveDeployPath(String fileName) {
    try {
      Path deployPath = Filesystem.getDeployDirectory().toPath().resolve(fileName);
      if (Files.exists(deployPath)) {
        return deployPath;
      }
    } catch (Exception ex) {
      // Fall through to local dev path.
    }
    Path devPath = Paths.get("src", "main", "deploy", fileName);
    if (Files.exists(devPath)) {
      return devPath;
    }
    return Paths.get(fileName);
  }

  /**
   * NAME
   *   ProfileRoot - JSON root for bringup_profiles.json.
   */
  private static final class ProfileRoot {
    @SerializedName("default_profile")
    String defaultProfile;
    LinkedHashMap<String, CanProfileConfig> profiles;
  }

  /**
   * NAME
   *   CanProfileConfig - JSON profile entry for device lists.
   */
  private static final class CanProfileConfig {
    List<DeviceRef> neos = Collections.emptyList();
    List<DeviceRef> neo550s = Collections.emptyList();
    List<DeviceRef> flexes = Collections.emptyList();
    List<DeviceRef> krakens = Collections.emptyList();
    List<DeviceRef> falcons = Collections.emptyList();
    List<DeviceRef> cancoders = Collections.emptyList();
    List<DeviceRef> candles = Collections.emptyList();
    List<DeviceRef> devices = Collections.emptyList();
    DeviceRef pdh;
    DeviceRef pigeon;
    DeviceRef roborio;

    /**
     * NAME
     *   CanProfileConfig - Construct a profile entry with device lists.
     */
    CanProfileConfig(
        List<DeviceRef> neos,
        List<DeviceRef> neo550s,
        List<DeviceRef> flexes,
        List<DeviceRef> krakens,
        List<DeviceRef> falcons,
        List<DeviceRef> cancoders,
        List<DeviceRef> candles,
        List<DeviceRef> devices,
        DeviceRef pdh,
        DeviceRef pigeon,
        DeviceRef roborio) {
      this.neos = neos != null ? neos : Collections.emptyList();
      this.neo550s = neo550s != null ? neo550s : Collections.emptyList();
      this.flexes = flexes != null ? flexes : Collections.emptyList();
      this.krakens = krakens != null ? krakens : Collections.emptyList();
      this.falcons = falcons != null ? falcons : Collections.emptyList();
      this.cancoders = cancoders != null ? cancoders : Collections.emptyList();
      this.candles = candles != null ? candles : Collections.emptyList();
      this.devices = devices != null ? devices : Collections.emptyList();
      this.pdh = pdh;
      this.pigeon = pigeon;
      this.roborio = roborio;
    }
  }

  /**
   * NAME
   *   DeviceRef - JSON device reference entry.
   */
  private static final class DeviceRef {
    int id;
    String vendor;
    String type;
    String label;
    String motor;
    LimitConfig limits;

    /**
     * NAME
     *   DeviceRef - Construct a device ref with ID only.
     */
    DeviceRef(int id) {
      this.id = id;
    }
  }

  /**
   * NAME
   *   DeviceKey - Normalized key for vendor/type lookup.
   */
  public static final class DeviceKey {
    private final String vendor;
    private final String type;

    /**
     * NAME
     *   DeviceKey - Construct a normalized key.
     *
     * PARAMETERS
     *   vendor - Vendor name.
     *   type - Device type label.
     */
    public DeviceKey(String vendor, String type) {
      this.vendor = vendor == null ? "" : vendor.trim().toUpperCase();
      this.type = type == null ? "" : type.trim().toUpperCase();
    }

    /**
     * NAME
     *   equals - Compare vendor/type keys.
     */
    @Override
    public boolean equals(Object obj) {
      if (this == obj) {
        return true;
      }
      if (obj == null || getClass() != obj.getClass()) {
        return false;
      }
      DeviceKey other = (DeviceKey) obj;
      return vendor.equals(other.vendor) && type.equals(other.type);
    }

    /**
     * NAME
     *   hashCode - Hash vendor/type key.
     */
    @Override
    public int hashCode() {
      return 31 * vendor.hashCode() + type.hashCode();
    }
  }

  /**
   * NAME
   *   DeviceConfig - Resolved device configuration entry.
   */
  public static final class DeviceConfig {
    private final int id;
    private final String label;
    private final String motor;
    private final LimitConfig limits;

    /**
     * NAME
     *   DeviceConfig - Construct a device config entry.
     *
     * PARAMETERS
     *   id - CAN device ID.
     *   label - Display label.
     *   motor - Optional motor model override.
     *   limits - Optional limit config.
     */
    public DeviceConfig(int id, String label, String motor, LimitConfig limits) {
      this.id = id;
      this.label = label;
      this.motor = motor;
      this.limits = limits != null ? limits : new LimitConfig();
    }

    public int getId() {
      return id;
    }

    public String getLabel() {
      return label;
    }

    public String getMotor() {
      return motor;
    }

    public LimitConfig getLimits() {
      return limits;
    }
  }

  /**
   * NAME
   *   LimitConfig - Limit switch configuration for a device.
   */
  public static final class LimitConfig {
    @SerializedName("fwdDio")
    public int fwdDio = -1;
    @SerializedName("revDio")
    public int revDio = -1;
    @SerializedName("invert")
    public boolean invert = false;

    /**
     * NAME
     *   hasForward - Return true when a forward limit is configured.
     */
    public boolean hasForward() {
      return fwdDio >= 0;
    }

    /**
     * NAME
     *   hasReverse - Return true when a reverse limit is configured.
     */
    public boolean hasReverse() {
      return revDio >= 0;
    }
  }

  /**
   * NAME
   *   MotorSpecRoot - JSON root for motor specs.
   */
  private static final class MotorSpecRoot {
    List<MotorSpec> motors = Collections.emptyList();
  }

  /**
   * NAME
   *   CanMappings - JSON mapping of CAN IDs to names.
   */
  private static final class CanMappings {
    Map<String, String> manufacturers = Collections.emptyMap();
    @SerializedName("device_types")
    Map<String, String> deviceTypes = Collections.emptyMap();
  }

  /**
   * NAME
   *   MotorSpec - Motor specification data from JSON.
   */
  public static final class MotorSpec {
    public String model;
    public double nominalVoltage;
    public double freeCurrentA;
    public double stallCurrentA;
    public String source;
  }
}
