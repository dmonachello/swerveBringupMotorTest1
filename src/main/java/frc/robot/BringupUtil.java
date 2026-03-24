package frc.robot;

import com.ctre.phoenix6.SignalLogger;
import com.ctre.phoenix6.hardware.TalonFX;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import com.google.gson.annotations.SerializedName;
import com.revrobotics.spark.SparkFlex;
import com.revrobotics.spark.SparkMax;
import com.revrobotics.util.StatusLogger;
import edu.wpi.first.wpilibj.DigitalInput;
import edu.wpi.first.wpilibj.Filesystem;
import edu.wpi.first.wpilibj.GenericHID;
import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
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
  private static final String DEFAULT_PROFILE_FILE = "bringup_system.json";
  // LEGACY (remove after v3 unified file adoption).
  private static final String LEGACY_PROFILE_FILE = "bringup_profiles.json";
  private static final int PROFILE_SCHEMA_VERSION = 3;
  private static final String MOTOR_SPECS_FILE = "motor_specs.json";
  private static final String CAN_MAPPINGS_FILE = "can_mappings.json";

  // JSON parser for bringup_system.json.
  private static final Gson GSON = new Gson();
  private static final Gson CANONICAL_GSON = new GsonBuilder().disableHtmlEscaping().create();

  // Profile registry as loaded from JSON (or fallback).
  private static Map<String, CanProfileConfig> profiles = new LinkedHashMap<>();
  private static List<String> profileOrder = new ArrayList<>();
  private static String defaultProfile = DEFAULT_PROFILE_NAME;
  private static final Map<String, MotorSpec> MOTOR_SPECS = loadMotorSpecs();
  private static final CanMappings CAN_MAPPINGS = loadCanMappings();
  private static final Map<String, Integer> MANUFACTURER_NAME_TO_ID = buildManufacturerNameToId();
  private static final Map<String, Integer> DEVICE_TYPE_NAME_TO_ID = buildDeviceTypeNameToId();
  private static final Map<DeviceKey, List<DeviceConfig>> DEVICE_CONFIGS = new LinkedHashMap<>();

  // Currently active profile name.
  private static String activeProfile = DEFAULT_PROFILE_NAME;

  // Active device list built from the selected profile.
  private static final List<DeviceEntry> ACTIVE_DEVICES = new ArrayList<>();
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

    List<DeviceRef> merged = mergeDevices(config);
    buildDeviceConfigs(merged);
    PDH_CAN_ID = resolveSingletonId(merged, "REV", "PDH", config.pdh);
    PIGEON_CAN_ID = resolveSingletonId(merged, "CTRE", "Pigeon", config.pigeon);
    ROBORIO_CAN_ID = resolveSingletonId(merged, "NI", "roboRIO", config.roborio);
    activeProfile = profileName;
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
   *   getActiveDevices - Return the active device list.
   *
   * RETURNS
   *   Unmodifiable list of active device entries.
   */
  public static List<DeviceEntry> getActiveDevices() {
    return Collections.unmodifiableList(ACTIVE_DEVICES);
  }

  /**
   * NAME
   *   getActiveDevicesSorted - Return active devices sorted by vendor/type/id.
   */
  public static List<DeviceEntry> getActiveDevicesSorted() {
    List<DeviceEntry> devices = new ArrayList<>(ACTIVE_DEVICES);
    devices.sort((a, b) -> {
      int vendor = safeText(a.vendor).compareToIgnoreCase(safeText(b.vendor));
      if (vendor != 0) {
        return vendor;
      }
      int type = safeText(a.type).compareToIgnoreCase(safeText(b.type));
      if (type != 0) {
        return type;
      }
      return Integer.compare(a.id, b.id);
    });
    return devices;
  }

  /**
   * NAME
   *   validateCanIds - Warn on duplicate CAN IDs.
   *
   * PARAMETERS
   *   devices - Active device entries.
   */
  public static void validateCanIds(List<DeviceEntry> devices) {
    java.util.HashSet<Integer> seen = new java.util.HashSet<>();
    boolean hasDuplicate = false;
    if (devices != null) {
      for (DeviceEntry entry : devices) {
        if (entry == null || !isEnabledCanId(entry.id)) {
          continue;
        }
        if (!seen.add(entry.id)) {
          System.out.println("Warning: duplicate CAN ID: " + entry.id);
          hasDuplicate = true;
        }
      }
    }
    if (hasDuplicate) {
      System.out.println("Warning: duplicate CAN IDs can cause bringup confusion.");
    }
  }

  /**
   * NAME
   *   getExpectedDevices - Return expected devices with CAN identity data.
   *
   * RETURNS
   *   List of ExpectedDevice entries for diagnostics reporting.
   */
  public static List<ExpectedDevice> getExpectedDevices() {
    List<ExpectedDevice> devices = new ArrayList<>();
    for (DeviceEntry entry : ACTIVE_DEVICES) {
      if (entry == null || !isEnabledCanId(entry.id)) {
        continue;
      }
      int manufacturer = resolveCanManufacturerId(entry.vendor);
      int deviceType = resolveCanDeviceTypeId(entry.type);
      if (manufacturer < 0 || deviceType < 0) {
        System.out.println(
            "Warning: unable to map device to CAN identity (vendor="
                + entry.vendor + ", type=" + entry.type + ", id=" + entry.id + ").");
        continue;
      }
      devices.add(new ExpectedDevice(entry.label, manufacturer, deviceType, entry.id));
    }
    return devices;
  }

  private static int resolveCanManufacturerId(String vendor) {
    String key = normalizeKey(vendor);
    if (key.isEmpty()) {
      return -1;
    }
    Integer id = MANUFACTURER_NAME_TO_ID.get(key);
    if (id != null) {
      return id;
    }
    try {
      return Integer.parseInt(vendor.trim());
    } catch (NumberFormatException ignored) {
      return -1;
    }
  }

  private static int resolveCanDeviceTypeId(String type) {
    String key = normalizeKey(type);
    if (key.isEmpty()) {
      return -1;
    }
    if (key.equals("NEO") || key.equals("NEO550") || key.equals("NEO550S")
        || key.equals("FLEX") || key.equals("KRAKEN") || key.equals("FALCON")) {
      return 2; // MotorController
    }
    if (key.equals("CANCODER") || key.equals("ENCODER")) {
      return 7; // Encoder
    }
    if (key.equals("CANDLE")) {
      return 10; // Miscellaneous
    }
    if (key.equals("PDH") || key.equals("PDP") || key.equals("PDM")
        || key.equals("POWERDISTRIBUTIONMODULE")) {
      return 8; // PowerDistributionModule
    }
    if (key.equals("PIGEON") || key.equals("IMU") || key.equals("GYROSENSOR")) {
      return 4; // GyroSensor
    }
    if (key.equals("ROBORIO") || key.equals("ROBOTCONTROLLER")) {
      return 1; // RobotController
    }
    Integer id = DEVICE_TYPE_NAME_TO_ID.get(key);
    return id != null ? id : -1;
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
   *   loadProfilesFromJson - Load bringup_system.json into memory.
   */
  private static void loadProfilesFromJson() {
    // Load bringup_system.json from deploy or dev path.
    Path path = resolveProfilePath();
    if (path == null || !Files.exists(path)) {
      System.out.println("Warning: CAN profile JSON not found. Using fallback IDs.");
      applyFallbackProfile();
      return;
    }
    try {
      String rawJson = Files.readString(path, StandardCharsets.UTF_8);
      ProfileRoot root = GSON.fromJson(rawJson, ProfileRoot.class);
      if (root == null || root.profiles == null || root.profiles.isEmpty()) {
        throw new JsonParseException("No profiles found");
      }
      if (root.schemaVersion != PROFILE_SCHEMA_VERSION && root.schemaVersion != 2) {
        throw new JsonParseException(
            "schema_version mismatch: expected "
                + PROFILE_SCHEMA_VERSION
                + " or 2, got "
                + root.schemaVersion);
      }
      if (root.dataVersion == null || root.dataVersion.isBlank()) {
        throw new JsonParseException("data_version missing or empty");
      }
      if (root.dataHash == null || root.dataHash.isBlank()) {
        throw new JsonParseException("data_hash missing or empty");
      }
      String computedHash = computeDataHash(rawJson);
      if (!root.dataHash.equals(computedHash)) {
        throw new JsonParseException("data_hash mismatch (run tools/sync_profiles.py)");
      }
      profiles = new LinkedHashMap<>(root.profiles);
      for (Map.Entry<String, CanProfileConfig> entry : profiles.entrySet()) {
        validateProfileCanIdsStrict(entry.getKey(), entry.getValue());
      }
      profileOrder = new ArrayList<>(profiles.keySet());
      defaultProfile = root.defaultProfile != null ? root.defaultProfile : DEFAULT_PROFILE_NAME;
      if (!profiles.containsKey(defaultProfile)) {
        System.out.println("Warning: default_profile not found in JSON. Using 'robot'.");
        defaultProfile = DEFAULT_PROFILE_NAME;
      }
      activeProfile = defaultProfile;
    } catch (IOException | JsonParseException ex) {
      System.out.println("ERROR: bringup_system.json invalid: " + ex.getMessage());
      System.out.println("ERROR: Redeploy required. Robot code will stop.");
      throw new RuntimeException("Invalid bringup_system.json", ex);
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
      // LEGACY (remove after v3 unified file adoption).
      Path legacyDeploy = Filesystem.getDeployDirectory().toPath().resolve(LEGACY_PROFILE_FILE);
      if (Files.exists(legacyDeploy)) {
        return legacyDeploy;
      }
    } catch (Exception ex) {
      // Fall through to local dev path.
    }
    Path dataPath = Paths.get("data", DEFAULT_PROFILE_FILE);
    if (Files.exists(dataPath)) {
      return dataPath;
    }
    // LEGACY (remove after v3 unified file adoption).
    Path legacyDataPath = Paths.get("data", LEGACY_PROFILE_FILE);
    if (Files.exists(legacyDataPath)) {
      return legacyDataPath;
    }
    Path devPath = Paths.get("src", "main", "deploy", DEFAULT_PROFILE_FILE);
    if (Files.exists(devPath)) {
      return devPath;
    }
    // LEGACY (remove after v3 unified file adoption).
    Path legacyDevPath = Paths.get("src", "main", "deploy", LEGACY_PROFILE_FILE);
    if (Files.exists(legacyDevPath)) {
      return legacyDevPath;
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
    List<DeviceRef> robotDevices = new ArrayList<>();
    robotDevices.addAll(toDevices(FALLBACK_ROBOT_NEO_CAN_IDS, "REV", "NEO"));
    robotDevices.addAll(toDevices(FALLBACK_ROBOT_KRAKEN_CAN_IDS, "CTRE", "KRAKEN"));
    robotDevices.addAll(toDevices(FALLBACK_ROBOT_CANCODER_CAN_IDS, "CTRE", "CANCoder"));
    robotDevices.add(new DeviceRef(FALLBACK_PDH_CAN_ID, "REV", "PDH"));
    robotDevices.add(new DeviceRef(FALLBACK_PIGEON_CAN_ID, "CTRE", "Pigeon"));
    robotDevices.add(new DeviceRef(FALLBACK_ROBORIO_CAN_ID, "NI", "roboRIO"));
    profiles.put("robot", new CanProfileConfig(
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        robotDevices,
        new DeviceRef(FALLBACK_PDH_CAN_ID, "REV", "PDH"),
        null,
        new DeviceRef(FALLBACK_PIGEON_CAN_ID, "CTRE", "Pigeon"),
        new DeviceRef(FALLBACK_ROBORIO_CAN_ID, "NI", "roboRIO")));
    List<DeviceRef> demoDevices = new ArrayList<>();
    demoDevices.addAll(toDevices(FALLBACK_DEMO_NEO_CAN_IDS, "REV", "NEO"));
    demoDevices.addAll(toDevices(FALLBACK_DEMO_KRAKEN_CAN_IDS, "CTRE", "KRAKEN"));
    demoDevices.addAll(toDevices(FALLBACK_DEMO_CANCODER_CAN_IDS, "CTRE", "CANCoder"));
    demoDevices.add(new DeviceRef(FALLBACK_ROBORIO_CAN_ID, "NI", "roboRIO"));
    profiles.put("demo_club", new CanProfileConfig(
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        demoDevices,
        null,
        null,
        null,
        new DeviceRef(FALLBACK_ROBORIO_CAN_ID, "NI", "roboRIO")));
    List<DeviceRef> homeDevices = new ArrayList<>();
    homeDevices.add(new DeviceRef(FALLBACK_ROBORIO_CAN_ID, "NI", "roboRIO"));
    profiles.put("demo_home", new CanProfileConfig(
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        homeDevices,
        null,
        null,
        null,
        new DeviceRef(FALLBACK_ROBORIO_CAN_ID, "NI", "roboRIO")));
    profileOrder = new ArrayList<>(profiles.keySet());
    defaultProfile = DEFAULT_PROFILE_NAME;
    activeProfile = defaultProfile;
    List<DeviceRef> merged = mergeDevices(profiles.get(DEFAULT_PROFILE_NAME));
    buildDeviceConfigs(merged);
    PDH_CAN_ID = resolveSingletonId(merged, "REV", "PDH", new DeviceRef(FALLBACK_PDH_CAN_ID, "REV", "PDH"));
    PIGEON_CAN_ID = resolveSingletonId(merged, "CTRE", "Pigeon", new DeviceRef(FALLBACK_PIGEON_CAN_ID, "CTRE", "Pigeon"));
    ROBORIO_CAN_ID = resolveSingletonId(merged, "NI", "roboRIO", new DeviceRef(FALLBACK_ROBORIO_CAN_ID, "NI", "roboRIO"));
  }

  /**
   * NAME
   *   validateProfileCanIdsStrict - Fail fast on duplicate CAN IDs in a profile.
   *
   * PARAMETERS
   *   profileName - Profile key being validated.
   *   config - Profile configuration entry.
   *
   * ERRORS
   *   Throws JsonParseException when duplicates are found.
   */
  private static void validateProfileCanIdsStrict(String profileName, CanProfileConfig config) {
    if (config == null) {
      return;
    }
    Map<Integer, List<String>> seen = new LinkedHashMap<>();
    addDeviceRefIds(seen, config.neos, "NEO");
    addDeviceRefIds(seen, config.neo550s, "NEO 550");
    addDeviceRefIds(seen, config.flexes, "FLEX");
    addDeviceRefIds(seen, config.krakens, "KRAKEN");
    addDeviceRefIds(seen, config.falcons, "FALCON");
    addDeviceRefIds(seen, config.cancoders, "CANCoder");
    addDeviceRefIds(seen, config.candles, "CANdle");
    addDeviceRefIds(seen, config.devices, "Device");
    addDeviceRefId(seen, config.pdh, "PDH");
    addDeviceRefId(seen, config.pdp, "PDP");
    addDeviceRefId(seen, config.pigeon, "Pigeon");
    addDeviceRefId(seen, config.roborio, "roboRIO");

    for (Map.Entry<Integer, List<String>> entry : seen.entrySet()) {
      if (entry.getValue().size() > 1) {
        throw new JsonParseException(
            "Profile '"
                + profileName
                + "' duplicate CAN ID "
                + entry.getKey()
                + " ("
                + String.join(", ", entry.getValue())
                + ")");
      }
    }
  }

  private static void addDeviceRefIds(
      Map<Integer, List<String>> seen,
      List<DeviceRef> refs,
      String fallbackLabel) {
    if (refs == null) {
      return;
    }
    for (DeviceRef ref : refs) {
      addDeviceRefId(seen, ref, fallbackLabel);
    }
  }

  private static void addDeviceRefId(
      Map<Integer, List<String>> seen,
      DeviceRef ref,
      String fallbackLabel) {
    if (ref == null || !isEnabledCanId(ref.id)) {
      return;
    }
    String label = ref.label;
    if (label == null || label.isBlank()) {
      label = fallbackLabel + " " + ref.id;
    }
    List<String> labels = seen.computeIfAbsent(ref.id, ignored -> new ArrayList<>());
    labels.add(label);
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
  private static void buildDeviceConfigs(List<DeviceRef> refs) {
    DEVICE_CONFIGS.clear();
    ACTIVE_DEVICES.clear();
    if (refs == null || refs.isEmpty()) {
      return;
    }
    for (DeviceRef ref : refs) {
      if (ref == null) {
        continue;
      }
      String vendor = safeText(ref.vendor);
      String type = safeText(ref.type);
      String label = safeText(ref.label);
      if (label.isEmpty()) {
        String fallback = !type.isEmpty() ? type : "Device";
        label = fallback + " " + ref.id;
      }
      DeviceEntry entry = new DeviceEntry(
          ref.id,
          vendor,
          type,
          label,
          safeText(ref.motor),
          ref.limits,
          ref.tags,
          ref.terminator);
      ACTIVE_DEVICES.add(entry);
      if (vendor.isEmpty() || type.isEmpty()) {
        System.out.println("Warning: device entry missing vendor/type for CAN ID " + ref.id);
        continue;
      }
      DeviceKey key = new DeviceKey(vendor, type);
      DeviceConfig config = new DeviceConfig(ref.id, label, ref.motor, ref.limits);
      DEVICE_CONFIGS.computeIfAbsent(key, ignored -> new ArrayList<>()).add(config);
    }
  }

  /**
   * NAME
   *   mergeDevices - Build a merged device list from legacy and new schema.
   *
   * DESCRIPTION
   *   Prefers explicit devices[] entries when both schemas are present.
   */
  private static List<DeviceRef> mergeDevices(CanProfileConfig config) {
    if (config == null) {
      return Collections.emptyList();
    }
    LinkedHashMap<String, DeviceRef> merged = new LinkedHashMap<>();
    addDeviceRefs(merged, config.devices);
    addLegacyDeviceRefs(merged, "REV", "NEO", config.neos);
    addLegacyDeviceRefs(merged, "REV", "NEO 550", config.neo550s);
    addLegacyDeviceRefs(merged, "REV", "FLEX", config.flexes);
    addLegacyDeviceRefs(merged, "CTRE", "KRAKEN", config.krakens);
    addLegacyDeviceRefs(merged, "CTRE", "FALCON", config.falcons);
    addLegacyDeviceRefs(merged, "CTRE", "CANCoder", config.cancoders);
    addLegacyDeviceRefs(merged, "CTRE", "CANdle", config.candles);
    addSingletonRef(merged, "REV", "PDH", config.pdh);
    addSingletonRef(merged, "CTRE", "PDP", config.pdp);
    addSingletonRef(merged, "CTRE", "Pigeon", config.pigeon);
    addSingletonRef(merged, "NI", "roboRIO", config.roborio);
    return new ArrayList<>(merged.values());
  }

  private static void addDeviceRefs(Map<String, DeviceRef> merged, List<DeviceRef> refs) {
    if (refs == null || refs.isEmpty()) {
      return;
    }
    for (DeviceRef ref : refs) {
      if (ref == null) {
        continue;
      }
      String key = deviceKey(ref.vendor, ref.type, ref.id);
      if (!merged.containsKey(key)) {
        merged.put(key, normalizeRef(ref));
      }
    }
  }

  private static void addLegacyDeviceRefs(
      Map<String, DeviceRef> merged,
      String vendor,
      String type,
      List<DeviceRef> refs) {
    if (refs == null || refs.isEmpty()) {
      return;
    }
    for (DeviceRef ref : refs) {
      if (ref == null) {
        continue;
      }
      DeviceRef copy = normalizeRef(ref);
      copy.vendor = vendor;
      copy.type = type;
      String key = deviceKey(copy.vendor, copy.type, copy.id);
      merged.putIfAbsent(key, copy);
    }
  }

  private static void addSingletonRef(
      Map<String, DeviceRef> merged,
      String vendor,
      String type,
      DeviceRef ref) {
    if (ref == null) {
      return;
    }
    DeviceRef copy = normalizeRef(ref);
    copy.vendor = vendor;
    copy.type = type;
    String key = deviceKey(copy.vendor, copy.type, copy.id);
    merged.putIfAbsent(key, copy);
  }

  private static DeviceRef normalizeRef(DeviceRef ref) {
    DeviceRef copy = new DeviceRef(ref.id, ref.vendor, ref.type);
    copy.label = ref.label;
    copy.motor = ref.motor;
    copy.limits = ref.limits;
    copy.tags = ref.tags;
    copy.terminator = ref.terminator;
    return copy;
  }

  private static String deviceKey(String vendor, String type, int id) {
    String v = safeText(vendor).toUpperCase();
    String t = safeText(type).toUpperCase();
    return v + "|" + t + "|" + id;
  }

  private static int resolveSingletonId(
      List<DeviceRef> refs,
      String vendor,
      String type,
      DeviceRef fallback) {
    if (refs != null) {
      for (DeviceRef ref : refs) {
        if (ref == null) {
          continue;
        }
        String v = safeText(ref.vendor);
        String t = safeText(ref.type);
        if (v.equalsIgnoreCase(vendor) && t.equalsIgnoreCase(type) && isEnabledCanId(ref.id)) {
          return ref.id;
        }
      }
    }
    if (fallback != null && isEnabledCanId(fallback.id)) {
      return fallback.id;
    }
    return DISABLED_CAN_ID;
  }

  private static String safeText(String value) {
    return value == null ? "" : value.trim();
  }

  /**
   * NAME
   *   toDevices - Convert raw IDs to device refs.
   */
  private static List<DeviceRef> toDevices(int[] ids, String vendor, String type) {
    // Convert raw IDs into JSON device objects for fallback profiles.
    List<DeviceRef> refs = new ArrayList<>();
    for (int id : ids) {
      if (isEnabledCanId(id)) {
        refs.add(new DeviceRef(id, vendor, type));
      }
    }
    return refs;
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
   *   ProfileRoot - JSON root for bringup_system.json.
   */
  private static final class ProfileRoot {
    @SerializedName("default_profile")
    String defaultProfile;
    @SerializedName("schema_version")
    int schemaVersion;
    @SerializedName("data_version")
    String dataVersion;
    @SerializedName("data_hash")
    String dataHash;
    LinkedHashMap<String, CanProfileConfig> profiles;
  }

  private static String computeDataHash(String rawJson) {
    JsonElement parsed = JsonParser.parseString(rawJson);
    if (!parsed.isJsonObject()) {
      throw new JsonParseException("profiles JSON root is not an object");
    }
    JsonObject root = parsed.getAsJsonObject();
    root.addProperty("data_hash", "");
    if (root.has("bridgeConfig")) {
      root.remove("bridgeConfig");
    }
    String canonical = canonicalizeJson(root);
    return sha256Hex(canonical);
  }

  private static String canonicalizeJson(JsonElement element) {
    if (element == null || element instanceof JsonNull || element.isJsonNull()) {
      return "null";
    }
    if (element.isJsonPrimitive()) {
      JsonPrimitive prim = element.getAsJsonPrimitive();
      return CANONICAL_GSON.toJson(prim);
    }
    if (element.isJsonArray()) {
      JsonArray array = element.getAsJsonArray();
      StringBuilder builder = new StringBuilder();
      builder.append("[");
      boolean first = true;
      for (JsonElement item : array) {
        if (!first) {
          builder.append(",");
        }
        builder.append(canonicalizeJson(item));
        first = false;
      }
      builder.append("]");
      return builder.toString();
    }
    if (element.isJsonObject()) {
      JsonObject obj = element.getAsJsonObject();
      List<String> keys = new ArrayList<>(obj.keySet());
      Collections.sort(keys);
      StringBuilder builder = new StringBuilder();
      builder.append("{");
      boolean first = true;
      for (String key : keys) {
        if (!first) {
          builder.append(",");
        }
        builder.append(CANONICAL_GSON.toJson(key));
        builder.append(":");
        builder.append(canonicalizeJson(obj.get(key)));
        first = false;
      }
      builder.append("}");
      return builder.toString();
    }
    return "null";
  }

  private static String sha256Hex(String input) {
    try {
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
      StringBuilder hex = new StringBuilder();
      for (byte b : hash) {
        String h = Integer.toHexString(0xff & b);
        if (h.length() == 1) {
          hex.append('0');
        }
        hex.append(h);
      }
      return hex.toString();
    } catch (NoSuchAlgorithmException ex) {
      throw new RuntimeException("SHA-256 unavailable", ex);
    }
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
    DeviceRef pdp;
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
        DeviceRef pdp,
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
      this.pdp = pdp;
      this.pigeon = pigeon;
      this.roborio = roborio;
    }
  }

  private static Map<String, Integer> buildManufacturerNameToId() {
    Map<String, Integer> map = new LinkedHashMap<>();
    if (CAN_MAPPINGS != null && CAN_MAPPINGS.manufacturers != null) {
      for (Map.Entry<String, String> entry : CAN_MAPPINGS.manufacturers.entrySet()) {
        String name = normalizeKey(entry.getValue());
        if (name.isEmpty()) {
          continue;
        }
        try {
          int id = Integer.parseInt(entry.getKey());
          map.put(name, id);
        } catch (NumberFormatException ignored) {
          // skip invalid id
        }
      }
    }
    map.putIfAbsent("NI", 1);
    map.putIfAbsent("CTRE", 4);
    map.putIfAbsent("REV", 5);
    return map;
  }

  private static Map<String, Integer> buildDeviceTypeNameToId() {
    Map<String, Integer> map = new LinkedHashMap<>();
    if (CAN_MAPPINGS != null && CAN_MAPPINGS.deviceTypes != null) {
      for (Map.Entry<String, String> entry : CAN_MAPPINGS.deviceTypes.entrySet()) {
        String name = normalizeKey(entry.getValue());
        if (name.isEmpty()) {
          continue;
        }
        try {
          int id = Integer.parseInt(entry.getKey());
          map.put(name, id);
        } catch (NumberFormatException ignored) {
          // skip invalid id
        }
      }
    }
    return map;
  }

  private static String normalizeKey(String value) {
    if (value == null) {
      return "";
    }
    return value.trim().toUpperCase().replaceAll("[^A-Z0-9]+", "");
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
    List<String> tags;
    Boolean terminator;

    /**
     * NAME
     *   DeviceRef - Construct a device ref with ID only.
     */
    DeviceRef(int id) {
      this.id = id;
    }

    DeviceRef(int id, String vendor, String type) {
      this.id = id;
      this.vendor = vendor;
      this.type = type;
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
   *   DeviceEntry - Active device entry loaded from profiles.
   */
  public static final class DeviceEntry {
    public final int id;
    public final String vendor;
    public final String type;
    public final String label;
    public final String motor;
    public final LimitConfig limits;
    public final List<String> tags;
    public final Boolean terminator;

    public DeviceEntry(
        int id,
        String vendor,
        String type,
        String label,
        String motor,
        LimitConfig limits,
        List<String> tags,
        Boolean terminator) {
      this.id = id;
      this.vendor = vendor;
      this.type = type;
      this.label = label;
      this.motor = motor;
      this.limits = limits != null ? limits : new LimitConfig();
      this.tags = tags != null ? tags : Collections.emptyList();
      this.terminator = terminator;
    }
  }

  /**
   * NAME
   *   ExpectedDevice - CAN identity view for diagnostics.
   */
  public static final class ExpectedDevice {
    public final String label;
    public final int manufacturer;
    public final int deviceType;
    public final int deviceId;

    public ExpectedDevice(String label, int manufacturer, int deviceType, int deviceId) {
      this.label = label;
      this.manufacturer = manufacturer;
      this.deviceType = deviceType;
      this.deviceId = deviceId;
    }
  }

  /**
   * NAME
   *   ensureDioInput - Lazily create a DigitalInput for a DIO channel.
   *
   * PARAMETERS
   *   input - Current DigitalInput (may be null).
   *   channel - DIO channel number (>=0 to create).
   *
   * RETURNS
   *   Existing input or a newly created DigitalInput when configured.
   *
   * SIDE EFFECTS
   *   Allocates a DigitalInput when the channel is valid.
   */
  public static DigitalInput ensureDioInput(DigitalInput input, int channel) {
    if (channel < 0) {
      return input;
    }
    if (input != null) {
      return input;
    }
    return new DigitalInput(channel);
  }

  /**
   * NAME
   *   readLimitInput - Read a DIO input with optional inversion.
   *
   * PARAMETERS
   *   input - DigitalInput to sample (may be null).
   *   invert - Whether to invert the raw signal.
   *
   * RETURNS
   *   True if closed, false if open, or null when input is absent.
   */
  public static Boolean readLimitInput(DigitalInput input, boolean invert) {
    if (input == null) {
      return null;
    }
    boolean raw = input.get();
    return invert ? !raw : raw;
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
