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
import frc.robot.devices.DeviceLifecycleOwnership;
import frc.robot.devices.DeviceUnit;
import frc.robot.registry.RegistrationHeader;
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
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Supplier;

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
  // Default profile names and file location.
  private static final String DEFAULT_PROFILE_FILE = "bringup_system.json";
  // LEGACY (remove after v3 unified file adoption).
  private static final String LEGACY_PROFILE_FILE = "bringup_profiles.json";
  private static final String KEY_BRIDGE_CONFIG = "bridgeConfig";
  private static final String KEY_BRIDGE_BY_PROFILE = "byProfile";
  private static final String KEY_BRIDGE_GROUPS = "groups";
  private static final String KEY_BRIDGE_SELECTED_DEVICE = "selectedDevice";
  private static final String KEY_BRIDGE_BINDINGS = "bindings";
  private static final String KEY_BRIDGE_TESTS = "tests";
  private static final String KEY_DSL_TESTS = "dslTests";
  private static final String KEY_DSL_TEST_SET = "dslTestSet";
  private static final String KEY_LIFECYCLE = "lifecycle";
  private static final String KEY_DISCOVER_THRESHOLD = "discoverThreshold";
  private static final String KEY_LOST_PRESENCE_THRESHOLD = "lostPresenceThreshold";
  private static final String KEY_INPUT_ALIASES = "inputAliases";
  private static final String KEY_LABEL = "label";
  private static final String KEY_DEVICE = "device";
  private static final String KEY_ENABLED = "enabled";
  private static final String KEY_INPUT = "input";
  private static final String KEY_KIND = "kind";
  private static final String KEY_MEMBERS = "members";
  private static final String KEY_NAME = "name";
  private static final String KEY_VALUE = "value";
  private static final String LABEL_UNKNOWN = "UNKNOWN";
  private static final String NT_LABEL_EMPTY = "";
  public static final long REGISTRY_BYTES_UNKNOWN = -1L;
  private static final int DIO_REFCOUNT_ZERO = 0;
  private static final int DIO_REFCOUNT_ONE = 1;
  private static final int DIO_REFCOUNT_INCREMENT = 1;
  private static final Object DIO_INPUT_LOCK = new Object();
  private static final Map<Integer, DigitalInput> DIO_INPUTS = new HashMap<>();
  private static final Map<DigitalInput, Integer> DIO_INPUT_CHANNELS = new IdentityHashMap<>();
  private static final Map<Integer, Integer> DIO_INPUT_REFCOUNT = new HashMap<>();
  private static final int ASCII_0 = 48;
  private static final int ASCII_9 = 57;
  private static final int ASCII_A = 65;
  private static final int ASCII_F = 70;
  private static final int ASCII_Z = 90;
  private static final int ASCII_a = 97;
  private static final int ASCII_f = 102;
  private static final int ASCII_z = 122;
  private static final String MESSAGE_DUPLICATE_LABEL =
      "Profile '%s' duplicate label '%s' used by %s";
  private static final String MESSAGE_UNKNOWN_DEVICE =
      "Profile '%s' references unknown device '%s'";
  private static final String MESSAGE_EMPTY_DEVICE_REGISTRY =
      "No devices found";
  private static final String MESSAGE_REGISTRY_JSON_MISSING =
      "Registry JSON missing.";
  private static final String MESSAGE_REGISTRY_JSON_PARSE =
      "Registry JSON parse failed: %s";
  private static final String MESSAGE_REGISTRY_ROOT_NOT_OBJECT =
      "Registry JSON root is not an object.";
  private static final String MESSAGE_REGISTRY_SCHEMA_MISMATCH =
      "schema_version mismatch: expected %s, got %s";
  private static final String MESSAGE_REGISTRY_DATA_VERSION_MISSING =
      "data_version missing or empty";
  private static final String MESSAGE_REGISTRY_DATA_HASH_MISSING =
      "data_hash missing or empty";
  private static final String MESSAGE_REGISTRY_DATA_HASH_MISMATCH =
      "data_hash mismatch";
  private static final String MESSAGE_REGISTRY_DEVICES_MISSING =
      "devices missing or empty";
  private static final String MESSAGE_REGISTRY_DEVICE_LABEL_MISSING =
      "device label missing";
  private static final String MESSAGE_REGISTRY_PERSIST_FAILED =
      "Failed to persist bringup_system.json to runtime path: %s";
  private static final String MESSAGE_REGISTRY_PERSIST_FAILED_BOTH =
      "Failed to persist bringup_system.json to runtime path: %s; fallback: %s";
  private static final String MESSAGE_REGISTRY_PERSIST_FALLBACK =
      "Warning: failed to persist bringup_system.json to runtime path (%s). Wrote to %s instead.";
  private static final String MESSAGE_REGISTRY_PERSIST_PATH_MISSING =
      "Runtime path unavailable; cannot persist bringup_system.json.";
  private static final boolean REGISTRY_PERSIST_ON_APPLY = true;
  private static final boolean REGISTRY_PERSIST_FALLBACK_ON_FAIL = true;
  private static final String MESSAGE_REGISTRY_DEVICE_LABEL_DUP =
      "duplicate device label: %s";
  private static final String MESSAGE_REGISTRY_PROFILES_MISSING =
      "profiles missing or empty";
  private static final String MESSAGE_REGISTRY_PROFILE_DEVICES_MISSING =
      "profile devices missing: %s";
  private static final String MESSAGE_REGISTRY_PROFILE_DEVICE_DUP =
      "profile duplicate device label: %s/%s";
  private static final String MESSAGE_REGISTRY_PROFILE_DEVICE_UNKNOWN =
      "profile unknown device label: %s/%s";
  private static final String MESSAGE_REGISTRY_ACTIVATE_UNKNOWN =
      "activate profile not found: %s";
  private static final String MESSAGE_REGISTRY_ACTIVATE_MISSING =
      "activate profile missing";
  private static final String MESSAGE_REGISTRY_ACTIVATE_FAILED =
      "activate profile failed";
  private static final String MESSAGE_REGISTRY_ACTIVE_UNKNOWN =
      "active profile not found: %s";
  private static final String MESSAGE_REGISTRY_APPLY_FAILED =
      "registry apply failed: %s";
  private static final String MESSAGE_REGISTRY_POST_APPLY_FAILED =
      "post-apply check failed: %s";
  private static final String MESSAGE_UNKNOWN_CAN_IDENTITY =
      "Warning: unable to map device to CAN identity (label=%s, id=%s).";
  private static final String MESSAGE_RELOAD_FAILED = "profiles reload failed";
  private static final String MESSAGE_APP_SINGLETON_TYPE_MISMATCH =
      "App singleton service type mismatch for %s/%s/%s";
  private static final String MESSAGE_SAFE_MODE_APPLIED =
      "Warning: no valid bringup profiles loaded. Entering empty safe mode.";
  private static final String MESSAGE_REGISTRY_DEFAULT_PROFILE_MISSING =
      "Warning: default_profile not found in JSON. Using first available profile.";
  private static final String MESSAGE_UNKNOWN_PROFILE_DEFAULT =
      "Warning: unknown CAN profile '%s'. Using default.";
  private static final String MESSAGE_DEFAULT_PROFILE_MISSING =
      "Warning: default CAN profile missing. Entering empty safe mode.";
  private static final String TEXT_PROFILE_INACTIVE_SUFFIX = " (inactive)";
  private static final String TEXT_NONE = "(none)";
  private static final String MESSAGE_NO_PROFILE_SELECTED = "No profile selected.";
  private static final String MESSAGE_SELECTED_PROFILE_STAGE_FAILED =
      "selected profile stage failed";
  private static final String MESSAGE_SELECTED_PROFILE_STAGE_UNKNOWN =
      "selected profile not found: %s";
  private static final int PROFILE_SCHEMA_VERSION = 5;
  private static final String MOTOR_SPECS_FILE = "motor_specs.json";
  private static final String CAN_MAPPINGS_FILE = "can_mappings.json";
  private static final String INTERFACE_CAN = "CAN";
  private static final String INTERFACE_DIO = "DIO";
  private static final String INTERFACE_PWM = "PWM";
  private static final String INTERFACE_ANALOG = "ANALOG";
  private static final String INTERFACE_INTERNAL = "INTERNAL";
  private static final String INTERFACE_USB = "USB";
  private static final String TEXT_ADDRESS_CAN = "CAN";
  private static final String TEXT_ADDRESS_DIO_CHANNEL = "DIO channel";
  private static final String TEXT_ADDRESS_PWM_CHANNEL = "PWM channel";
  private static final String TEXT_ADDRESS_ANALOG_CHANNEL = "Analog channel";
  private static final String TEXT_ADDRESS_USB_PORT = "USB port";
  private static final String TEXT_ADDRESS_INTERNAL_ID = "Internal ID";
  private static final String TEXT_ADDRESS_ADDRESS = "address";
  private static final String TEXT_SUMMARY_CAN_IDS = "CAN IDs";
  private static final String TEXT_SUMMARY_DIO_CHANNELS = "DIO channels";
  private static final String TEXT_SUMMARY_PWM_CHANNELS = "PWM channels";
  private static final String TEXT_SUMMARY_ANALOG_CHANNELS = "Analog channels";
  private static final String TEXT_SUMMARY_USB_PORTS = "USB ports";
  private static final String TEXT_SUMMARY_INTERNAL_IDS = "Internal IDs";
  private static final String TEXT_SUMMARY_ADDRESSES = "addresses";
  private static final String DEVICE_TYPE_MOTOR = "motor";
  private static final String DEVICE_TYPE_LIMIT_SWITCH = "limitSwitch";
  private static final String DEVICE_TYPE_ENCODER_EXTERNAL = "encoderExternal";
  private static final String DEVICE_TYPE_XBOX_CONTROLLER = "xboxController";
  private static final String DEVICE_VENDOR_NI = "NI";
  private static final String DEVICE_VENDOR_CTRE = "CTRE";
  private static final String DEVICE_VENDOR_REV = "REV";
  private static final String DEVICE_VENDOR_MICROSOFT = "Microsoft";
  private static final String DEVICE_TYPE_ROBORIO = "roboRIO";
  private static final String DEVICE_TYPE_PDH = "PDH";
  private static final String DEVICE_TYPE_PDP = "PDP";
  private static final String DEVICE_TYPE_PIGEON = "Pigeon";
  private static final String DEVICE_TYPE_CANCODER = "CANCoder";
  private static final String DEVICE_TYPE_CANDLE = "CANdle";
  private static final String DEVICE_TYPE_NEO = "NEO";
  private static final String DEVICE_TYPE_NEO_550 = "NEO 550";
  private static final String DEVICE_TYPE_FLEX = "FLEX";
  private static final String DEVICE_TYPE_KRAKEN = "KRAKEN";
  private static final String DEVICE_TYPE_FALCON = "FALCON";
  private static final String MODEL_NEO = "NEO";
  private static final String MODEL_NEO_550 = "NEO 550";
  private static final String MODEL_FLEX = "VORTEX";
  private static final String MODEL_KRAKEN = "KRAKEN";
  private static final String MODEL_FALCON = "FALCON";
  private static final String MOTOR_SPEC_REV_NEO = "REV NEO";
  private static final String MOTOR_SPEC_REV_NEO_550 = "REV NEO 550";
  private static final String MOTOR_SPEC_REV_NEO_2 = "REV NEO 2.0";
  private static final String MOTOR_SPEC_REV_VORTEX = "REV NEO Vortex";
  private static final String MOTOR_SPEC_CTRE_FALCON_500 = "CTRE Falcon 500";
  private static final String MOTOR_SPEC_CTRE_KRAKEN_X60 = "CTRE Kraken X60";
  private static final int MFG_NI_ID = 1;
  private static final int MFG_CTRE_ID = 4;
  private static final int MFG_REV_ID = 5;
  private static final int DEVTYPE_ROBORIO_ID = 1;
  private static final int DEVTYPE_GYRO_ID = 4;
  private static final int DEVTYPE_MOTOR_ID = 2;
  private static final int DEVTYPE_ENCODER_ID = 7;
  private static final int DEVTYPE_POWER_ID = 8;
  private static final int DEVTYPE_MISC_ID = 10;
  private static final int INDEX_ZERO = 0;
  private static final long PROFILE_CONFIG_GENERATION_INITIAL = 0L;
  private static final long PROFILE_CONFIG_GENERATION_INCREMENT = 1L;
  private static final String PROP_AUTO_SELECT_DEFAULT_PROFILE =
      "bringup.autoSelectDefaultProfile";
  private static final String ENV_AUTO_SELECT_DEFAULT_PROFILE =
      "BRINGUP_AUTO_SELECT_DEFAULT_PROFILE";
  public static final double DEFAULT_DISCOVER_THRESHOLD = 0.80;
  public static final double DEFAULT_LOST_PRESENCE_THRESHOLD = 0.60;

  /**
   * NAME
   *   getProfileSchemaVersion - Return the shared bringup schema version.
   */
  public static int getProfileSchemaVersion() {
    return PROFILE_SCHEMA_VERSION;
  }

  // JSON parser for bringup_system.json.
  private static final Gson GSON = new Gson();
  private static final Gson CANONICAL_GSON = new GsonBuilder().disableHtmlEscaping().create();

  // Profile registry as loaded from JSON (or fallback).
  private static Map<String, ProfileConfig> profiles = new LinkedHashMap<>();
  private static List<String> profileOrder = new ArrayList<>();
  private static final Map<String, JsonElement> PROFILE_TESTS = new LinkedHashMap<>();
  private static final Map<String, BridgeProfileRuntimeConfig> PROFILE_BRIDGE_CONFIGS =
      new LinkedHashMap<>();
  private static JsonObject dslTestsRoot = null;
  private static String defaultProfile = NT_LABEL_EMPTY;
  private static String selectedProfile = NT_LABEL_EMPTY;
  private static String currentDataVersion = NT_LABEL_EMPTY;
  private static boolean activeProfileApplied = false;
  private static final Map<String, MotorSpec> MOTOR_SPECS = loadMotorSpecs();
  private static final CanMappings CAN_MAPPINGS = loadCanMappings();
  private static final Map<DeviceKey, List<DeviceConfig>> DEVICE_CONFIGS = new LinkedHashMap<>();
  private static final Map<String, DeviceDefinition> DEVICE_REGISTRY = new LinkedHashMap<>();
  private static final Map<DeviceInstanceKey, Object> DEVICE_INSTANCE_REGISTRY = new LinkedHashMap<>();
  private static final Map<DeviceInstanceKey, Object> APP_SINGLETON_SERVICE_REGISTRY =
      new LinkedHashMap<>();
  private static final Object APP_SINGLETON_MARKER = new Object();
  private static long activeProfileGeneration = PROFILE_CONFIG_GENERATION_INITIAL;

  // Currently active profile name.
  private static String activeProfile = NT_LABEL_EMPTY;

  // Active device list built from the selected profile.
  private static final List<DeviceEntry> ACTIVE_DEVICES = new ArrayList<>();
  public static final int DISABLED_CAN_ID = -1;
  public static int PDH_CAN_ID = DISABLED_CAN_ID;
  public static int PDP_CAN_ID = DISABLED_CAN_ID;
  public static int PIGEON_CAN_ID = DISABLED_CAN_ID;
  public static int ROBORIO_CAN_ID = DISABLED_CAN_ID;
  public static final double DEADBAND = 0.12;

  // Initialize logging suppression and load the profile JSON.
  static {
    disableVendorLogging();
    try {
      loadProfilesFromJson();
    } catch (RuntimeException ex) {
      applyEmptySafeMode();
    }
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
    ProfileConfig config = profiles.get(profileName);
    if (config == null) {
      BringupPrinter.enqueue(String.format(MESSAGE_UNKNOWN_PROFILE_DEFAULT, profileName));
      config = profiles.get(defaultProfile);
      profileName = defaultProfile;
    }
    if (config == null) {
      BringupPrinter.enqueue(MESSAGE_DEFAULT_PROFILE_MISSING);
      applyEmptySafeMode();
      return;
    }
    try {
      validateProfileCanIdsStrict(profileName, config);
      validateProfileLabelsStrict(profileName, config);
    } catch (JsonParseException ex) {
      BringupPrinter.enqueue("ERROR: cannot activate profile '" + profileName + "': " + ex.getMessage());
      BringupPrinter.enqueue("ERROR: Profile activation aborted. Staying on '" + activeProfile + "'.");
      return;
    }

    List<DeviceDefinition> profileDevices = resolveProfileDevices(config);
    buildDeviceConfigs(profileDevices);
    PDH_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_REV_ID, DEVTYPE_POWER_ID);
    PDP_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_CTRE_ID, DEVTYPE_POWER_ID);
    PIGEON_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_CTRE_ID, DEVTYPE_GYRO_ID);
    ROBORIO_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_NI_ID, DEVTYPE_ROBORIO_ID);
    activeProfile = profileName;
    selectedProfile = profileName;
    activeProfileApplied = true;
    bumpActiveProfileGeneration();
  }

  /**
   * NAME
   *   getActiveProfileGeneration - Return active profile registry generation.
   *
   * RETURNS
   *   Monotonic generation incremented when profile-derived runtime config changes.
   */
  public static long getActiveProfileGeneration() {
    return activeProfileGeneration;
  }

  /**
   * NAME
   *   bumpActiveProfileGeneration - Mark profile-derived runtime config dirty.
   */
  private static void bumpActiveProfileGeneration() {
    activeProfileGeneration += PROFILE_CONFIG_GENERATION_INCREMENT;
  }

  /**
   * NAME
   *   selectCanProfile - Select a profile without activating it.
   *
   * PARAMETERS
   *   profileName - Profile name to select.
   *
   * SIDE EFFECTS
   *   Updates the selected profile label only.
   */
  public static void selectCanProfile(String profileName) {
    if (profileName == null || profileName.isBlank()) {
      selectedProfile = NT_LABEL_EMPTY;
      return;
    }
    if (!profiles.containsKey(profileName)) {
      BringupPrinter.enqueue("Warning: unknown CAN profile '" + profileName + "'.");
      selectedProfile = NT_LABEL_EMPTY;
      return;
    }
    selectedProfile = profileName;
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
    selectNextProfile();
  }

  public static String getActiveCanProfile() {
    // Raw profile name (used in logs and reports).
    return activeProfile;
  }

  public static String getActiveCanProfileLabel() {
    // Label currently matches profile name, but can diverge later.
    String label = activeProfileApplied ? activeProfile : getSelectedCanProfileLabel();
    if (!activeProfileApplied) {
      return label + TEXT_PROFILE_INACTIVE_SUFFIX;
    }
    return label;
  }

  /**
   * NAME
   *   isProfileActive - Check whether a profile is currently active.
   */
  public static boolean isProfileActive() {
    return activeProfileApplied;
  }

  /**
   * NAME
   *   getSelectedCanProfile - Return the currently selected profile name.
   */
  public static String getSelectedCanProfile() {
    return selectedProfile;
  }

  /**
   * NAME
   *   getSelectedCanProfileLabel - Return the selected profile label with default fallback.
   */
  public static String getSelectedCanProfileLabel() {
    String label = selectedProfile;
    if (label == null || label.isBlank()) {
      return TEXT_NONE;
    }
    return label;
  }

  /**
   * NAME
   *   getActiveRuntimeProfileLabel - Return the active runtime profile label.
   *
   * RETURNS
   *   Active runtime profile name, or empty string when runtime is inactive.
   */
  public static String getActiveRuntimeProfileLabel() {
    if (!activeProfileApplied) {
      return NT_LABEL_EMPTY;
    }
    return activeProfile == null ? NT_LABEL_EMPTY : activeProfile;
  }

  /**
   * NAME
   *   getConfiguredDeviceTypeByLabel - Return the configured logical device type for a label.
   *
   * PARAMETERS
   *   label - Device label from bringup_system.json.
   *
   * RETURNS
   *   Configured logical type such as motor or limitSwitch, or empty string when unknown.
   */
  public static String getConfiguredDeviceTypeByLabel(String label) {
    if (label == null || label.isBlank()) {
      return "";
    }
    DeviceDefinition def = DEVICE_REGISTRY.get(normalizeKey(label));
    if (def == null) {
      return "";
    }
    if (def.type != null && !def.type.isBlank()) {
      return def.type;
    }
    String inferred = resolveDeviceTypeLabel(def);
    return inferred != null && !LABEL_UNKNOWN.equalsIgnoreCase(inferred) ? inferred : "";
  }

  /**
   * NAME
   *   getConfiguredDeviceEntryByLabel - Return one runtime-capable configured device entry by label.
   *
   * PARAMETERS
   *   label - Device label from bringup_system.json.
   *
   * RETURNS
   *   DeviceEntry built from the loaded registry, or null when the label is unknown
   *   or not runtime-addressable.
   */
  public static DeviceEntry getConfiguredDeviceEntryByLabel(String label) {
    if (label == null || label.isBlank()) {
      return null;
    }
    DeviceDefinition def = DEVICE_REGISTRY.get(normalizeKey(label));
    if (def == null || !isRuntimeDevice(def)) {
      return null;
    }
    return buildDeviceEntry(def);
  }

  /**
   * NAME
   *   getSelectedDslTestSetForProfile - Return the DSL test set referenced by a profile.
   *
   * PARAMETERS
   *   profileName - Profile name from bringup_system.json.
   *
   * RETURNS
   *   Referenced set name or empty string when unset.
   */
  public static String getSelectedDslTestSetForProfile(String profileName) {
    if (profileName == null || profileName.isBlank()) {
      return "";
    }
    ProfileConfig config = profiles.get(profileName);
    if (config == null || config.dslTestSet == null) {
      return "";
    }
    return config.dslTestSet;
  }

  /**
   * NAME
   *   readDslTestsRoot - Read the top-level DSL tests payload from bringup_system.json.
   *
   * RETURNS
   *   JSON object for the DSL tests root, or null when missing.
   */
  public static JsonObject readDslTestsRoot() {
    if (dslTestsRoot != null) {
      return dslTestsRoot.deepCopy();
    }
    Path path = getProfilePath();
    if (path == null || !Files.exists(path)) {
      return null;
    }
    try {
      String rawJson = Files.readString(path, StandardCharsets.UTF_8);
      JsonElement parsed = JsonParser.parseString(rawJson);
      if (parsed == null || !parsed.isJsonObject()) {
        return null;
      }
      JsonObject root = parsed.getAsJsonObject();
      JsonElement dslElement = root.get(KEY_DSL_TESTS);
      if (dslElement == null || !dslElement.isJsonObject()) {
        return null;
      }
      return dslElement.getAsJsonObject().deepCopy();
    } catch (IOException | JsonParseException ex) {
      BringupPrinter.enqueue("Warning: failed to read dslTests: " + ex.getMessage());
      return null;
    }
  }

  /**
   * NAME
   *   getDefaultCanProfile - Return the configured default profile name.
   */
  public static String getDefaultCanProfile() {
    return defaultProfile;
  }

  /**
   * NAME
   *   selectNextProfile - Advance selected profile without activating.
   */
  public static void selectNextProfile() {
    if (profileOrder.isEmpty()) {
      return;
    }
    int index = profileOrder.indexOf(selectedProfile);
    int nextIndex = (index < 0 ? 0 : (index + 1) % profileOrder.size());
    selectedProfile = profileOrder.get(nextIndex);
  }

  /**
   * NAME
   *   activateSelectedProfile - Activate the currently selected profile.
   */
  public static void activateSelectedProfile() {
    if (selectedProfile == null || selectedProfile.isBlank()) {
      return;
    }
    setActiveCanProfile(selectedProfile);
  }

  /**
   * NAME
   *   prepareActivationForSelectedProfile - Deactivate active profile when switching.
   *
   * DESCRIPTION
   *   Ensures the previously active profile is deactivated once per switch
   *   before the selected profile is activated.
   */
  public static void prepareActivationForSelectedProfile() {
    if (!activeProfileApplied) {
      return;
    }
    if (activeProfile == null || selectedProfile == null) {
      return;
    }
    if (activeProfile.equals(selectedProfile)) {
      return;
    }
    deactivateActiveProfile();
  }

  /**
   * NAME
   *   deactivateActiveProfile - Clear active profile state without selecting a new one.
   *
   * SIDE EFFECTS
   *   Clears active device configs and marks the profile inactive.
   */
  public static void deactivateActiveProfile() {
    if (!activeProfileApplied) {
      return;
    }
    ACTIVE_DEVICES.clear();
    DEVICE_CONFIGS.clear();
    PDH_CAN_ID = DISABLED_CAN_ID;
    PDP_CAN_ID = DISABLED_CAN_ID;
    PIGEON_CAN_ID = DISABLED_CAN_ID;
    ROBORIO_CAN_ID = DISABLED_CAN_ID;
    activeProfileApplied = false;
    bumpActiveProfileGeneration();
  }

  /**
   * NAME
   *   stageSelectedProfileForBringup - Load selected profile device configs without full activation.
   *
   * RETURNS
   *   Empty string on success, or an error message when staging fails.
   *
   * SIDE EFFECTS
   *   Rebuilds runtime device configs and active-device inventory from the
   *   selected profile while keeping the runtime profile inactive.
   */
  public static String stageSelectedProfileForBringup() {
    String resolved = selectedProfile;
    if (resolved == null || resolved.isBlank()) {
      return MESSAGE_NO_PROFILE_SELECTED;
    }
    ProfileConfig config = profiles.get(resolved);
    if (config == null) {
      return String.format(MESSAGE_SELECTED_PROFILE_STAGE_UNKNOWN, resolved);
    }
    try {
      validateProfileCanIdsStrict(resolved, config);
      validateProfileLabelsStrict(resolved, config);
    } catch (JsonParseException ex) {
      return ex.getMessage();
    }
    List<DeviceDefinition> profileDevices = resolveProfileDevices(config);
    buildDeviceConfigs(profileDevices);
    PDH_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_REV_ID, DEVTYPE_POWER_ID);
    PDP_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_CTRE_ID, DEVTYPE_POWER_ID);
    PIGEON_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_CTRE_ID, DEVTYPE_GYRO_ID);
    ROBORIO_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_NI_ID, DEVTYPE_ROBORIO_ID);
    selectedProfile = resolved;
    activeProfile = NT_LABEL_EMPTY;
    activeProfileApplied = false;
    bumpActiveProfileGeneration();
    return NT_LABEL_EMPTY;
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
   *   getRegistryDeviceCount - Return number of registry devices.
   */
  public static int getRegistryDeviceCount() {
    return DEVICE_REGISTRY.size();
  }

  /**
   * NAME
   *   getProfileCount - Return number of profiles in the registry.
   */
  public static int getProfileCount() {
    return profiles.size();
  }

  /**
   * NAME
   *   getProfileNames - Return profile names in registry order.
   *
   * RETURNS
   *   Unmodifiable list of profile names.
   */
  public static List<String> getProfileNames() {
    return Collections.unmodifiableList(profileOrder);
  }

  /**
   * NAME
   *   getProfileInputAliases - Return input aliases for a profile.
   *
   * RETURNS
   *   Unmodifiable map of alias->canonical entries.
   */
  public static Map<String, String> getProfileInputAliases(String profileName) {
    String name = resolveProfileNameOrActive(profileName);
    ProfileConfig config = profiles.get(name);
    if (config == null || config.inputAliases == null) {
      return Collections.emptyMap();
    }
    return Collections.unmodifiableMap(config.inputAliases);
  }

  /**
   * NAME
   *   getProfileDiscoverThreshold - Return lifecycle discover threshold for one profile.
   *
   * PARAMETERS
   *   profileName - Profile name or empty for active/selected fallback.
   *
   * RETURNS
   *   Threshold in [0, 1] used to promote presence to present.
   */
  public static double getProfileDiscoverThreshold(String profileName) {
    String name = resolveProfileNameOrActive(profileName);
    ProfileConfig config = profiles.get(name);
    double configured = config != null && config.lifecycle != null
        ? config.lifecycle.discoverThreshold
        : DEFAULT_DISCOVER_THRESHOLD;
    return clampLifecycleThreshold(configured, DEFAULT_DISCOVER_THRESHOLD);
  }

  /**
   * NAME
   *   getProfileLostPresenceThreshold - Return lifecycle stale threshold for one profile.
   *
   * PARAMETERS
   *   profileName - Profile name or empty for active/selected fallback.
   *
   * RETURNS
   *   Threshold in [0, 1] used to demote presence to stale.
   */
  public static double getProfileLostPresenceThreshold(String profileName) {
    String name = resolveProfileNameOrActive(profileName);
    ProfileConfig config = profiles.get(name);
    double configured = config != null && config.lifecycle != null
        ? config.lifecycle.lostPresenceThreshold
        : DEFAULT_LOST_PRESENCE_THRESHOLD;
    return clampLifecycleThreshold(configured, DEFAULT_LOST_PRESENCE_THRESHOLD);
  }

  private static double clampLifecycleThreshold(double value, double fallback) {
    if (Double.isNaN(value) || Double.isInfinite(value)) {
      return fallback;
    }
    if (value < 0.0) {
      return 0.0;
    }
    if (value > 1.0) {
      return 1.0;
    }
    return value;
  }

  /**
   * NAME
   *   getProfileBridgeConfig - Return runtime bridgeConfig state for a profile.
   *
   * RETURNS
   *   Immutable bridgeConfig snapshot for the resolved profile.
   */
  public static BridgeProfileRuntimeConfig getProfileBridgeConfig(String profileName) {
    String name = resolveProfileNameOrActive(profileName);
    BridgeProfileRuntimeConfig config = PROFILE_BRIDGE_CONFIGS.get(name);
    if (config == null) {
      return BridgeProfileRuntimeConfig.empty();
    }
    return config;
  }

  /**
   * NAME
   *   getProfileTestsPayload - Return tests payload for a profile.
   */
  public static JsonElement getProfileTestsPayload(String profileName) {
    String name = resolveProfileNameOrActive(profileName);
    return PROFILE_TESTS.get(name);
  }

  /**
   * NAME
   *   updateProfileTests - Update cached tests payload for a profile.
   */
  public static void updateProfileTests(String profileName, JsonElement payload) {
    String name = safeText(profileName);
    if (name.isBlank() || payload == null) {
      return;
    }
    PROFILE_TESTS.put(name, payload);
  }

  /**
   * NAME
   *   getProfilePath - Resolve bringup_system.json path.
   */
  public static Path getProfilePath() {
    return resolveProfilePath();
  }

  /**
   * NAME
   *   readCurrentProfilesJson - Read the current bringup_system.json payload from disk.
   *
   * RETURNS
   *   Parsed JSON object for the currently resolved profile path, or null on read/parse failure.
   */
  public static JsonObject readCurrentProfilesJson() {
    Path path = resolveProfilePath();
    if (path == null) {
      return null;
    }
    try {
      String rawJson = Files.readString(path, StandardCharsets.UTF_8);
      JsonElement parsed = JsonParser.parseString(rawJson);
      return parsed != null && parsed.isJsonObject() ? parsed.getAsJsonObject() : null;
    } catch (IOException | JsonParseException ex) {
      return null;
    }
  }

  /**
   * NAME
   *   buildCurrentProfilesJson - Build the loaded in-memory bringup_system.json payload.
   *
   * RETURNS
   *   JSON object representing the robot's authoritative loaded registry state.
   */
  public static JsonObject buildCurrentProfilesJson() {
    JsonObject root = new JsonObject();
    root.addProperty("schema_version", PROFILE_SCHEMA_VERSION);
    root.addProperty("data_version", currentDataVersion != null ? currentDataVersion : NT_LABEL_EMPTY);
    root.add("devices", GSON.toJsonTree(new ArrayList<>(DEVICE_REGISTRY.values())));
    root.add("profiles", GSON.toJsonTree(profiles));
    root.addProperty("default_profile", defaultProfile != null ? defaultProfile : NT_LABEL_EMPTY);
    if (dslTestsRoot != null) {
      root.add(KEY_DSL_TESTS, dslTestsRoot.deepCopy());
    }
    JsonObject bridgeConfig = buildBridgeConfigJson();
    if (bridgeConfig.size() > 0) {
      root.add(KEY_BRIDGE_CONFIG, bridgeConfig);
    }
    root.addProperty("data_hash", NT_LABEL_EMPTY);
    root.addProperty("data_hash", sha256Hex(canonicalizeJson(root)));
    return root;
  }

  private static String resolveProfileNameOrActive(String profileName) {
    String name = safeText(profileName);
    if (name.isBlank()) {
      name = safeText(activeProfile);
    }
    if (name.isBlank()) {
      name = safeText(defaultProfile);
    }
    return name;
  }

  /**
   * NAME
   *   computeRawRegistryHash - Compute SHA-256 for raw registry JSON.
   *
   * PARAMETERS
   *   rawJson - Registry JSON string.
   *
   * RETURNS
   *   Hex-encoded SHA-256 digest or empty string on missing input.
   */
  public static String computeRawRegistryHash(String rawJson) {
    if (rawJson == null) {
      return NT_LABEL_EMPTY;
    }
    return sha256Hex(rawJson);
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
   *   claimDeviceInstance - Enforce single-instance ownership per vendor/type/id.
   *
   * PARAMETERS
   *   device - DeviceUnit requesting ownership.
   *
   * RETURNS
   *   True if ownership is granted or already held by the same instance.
   */
  public static synchronized boolean claimDeviceInstance(DeviceUnit device) {
    if (device == null) {
      return false;
    }
    RegistrationHeader header = device.getHeader();
    String vendor = header != null ? header.vendor() : "";
    String type = header != null ? header.deviceType() : device.getDeviceType();
    int id = device.getCanId();
    DeviceInstanceKey key = new DeviceInstanceKey(vendor, type, id);
    Object existing = DEVICE_INSTANCE_REGISTRY.get(key);
    if (existing == device) {
      return true;
    }
    if (existing != null) {
      BringupPrinter.enqueue(
          "ERROR: duplicate device instance for "
              + safeText(vendor) + " " + safeText(type) + " CAN " + id
              + " (" + safeText(device.getLabel()) + ").");
      return false;
    }
    DEVICE_INSTANCE_REGISTRY.put(key, device);
    return true;
  }

  /**
   * NAME
   *   releaseDeviceInstance - Release a claimed device instance.
   *
   * PARAMETERS
   *   device - DeviceUnit releasing ownership.
   */
  public static synchronized void releaseDeviceInstance(DeviceUnit device) {
    if (device == null) {
      return;
    }
    RegistrationHeader header = device.getHeader();
    String vendor = header != null ? header.vendor() : "";
    String type = header != null ? header.deviceType() : device.getDeviceType();
    int id = device.getCanId();
    DeviceInstanceKey key = new DeviceInstanceKey(vendor, type, id);
    Object existing = DEVICE_INSTANCE_REGISTRY.get(key);
    if (existing == device) {
      DEVICE_INSTANCE_REGISTRY.remove(key);
    }
  }

  /**
   * NAME
   *   clearDeviceInstanceRegistry - Clear all claimed device instances.
   */
  public static synchronized void clearDeviceInstanceRegistry() {
    DEVICE_INSTANCE_REGISTRY.clear();
  }

  /**
   * NAME
   *   clearRuntimeOwnedDeviceInstanceRegistry - Clear claims for runtime-owned devices only.
   *
   * DESCRIPTION
   *   App-owned singleton-service devices do not participate in the runtime
   *   claim registry. This method preserves that future separation by removing
   *   only claims owned by runtime-recreatable devices.
   */
  public static synchronized void clearRuntimeOwnedDeviceInstanceRegistry() {
    DEVICE_INSTANCE_REGISTRY.entrySet().removeIf(
        entry -> isRuntimeOwnedDeviceInstance(entry.getValue()));
  }

  /**
   * NAME
   *   acquireAppSingletonService - Create or reuse an app-lifetime singleton.
   *
   * PARAMETERS
   *   device - Device wrapper requesting the singleton-backed service.
   *   serviceClass - Expected singleton implementation type.
   *   factory - Factory used only for the first allocation.
   *
   * RETURNS
   *   Existing or newly created singleton service instance.
   *
   * ERRORS
   *   Throws IllegalStateException if the stored singleton type does not match
   *   the requested type for the same vendor/type/id key.
   */
  public static synchronized <T> T acquireAppSingletonService(
      DeviceUnit device,
      Class<T> serviceClass,
      Supplier<T> factory) {
    if (device == null || serviceClass == null || factory == null) {
      return null;
    }
    RegistrationHeader header = device.getHeader();
    String vendor = header != null ? header.vendor() : "";
    String type = header != null ? header.deviceType() : device.getDeviceType();
    int id = device.getCanId();
    DeviceInstanceKey key = new DeviceInstanceKey(vendor, type, id);
    Object existing = APP_SINGLETON_SERVICE_REGISTRY.get(key);
    if (existing == null) {
      T created = factory.get();
      APP_SINGLETON_SERVICE_REGISTRY.put(key, created);
      return created;
    }
    if (!serviceClass.isInstance(existing)) {
      throw new IllegalStateException(
          String.format(MESSAGE_APP_SINGLETON_TYPE_MISMATCH, safeText(vendor), safeText(type), id));
    }
    return serviceClass.cast(existing);
  }

  /**
   * NAME
   *   peekAppSingletonService - Return an already-allocated app singleton without creating it.
   *
   * PARAMETERS
   *   device - Device wrapper requesting the singleton-backed service.
   *   serviceClass - Expected singleton implementation type.
   *
   * RETURNS
   *   Existing singleton service instance, or null when none has been allocated yet.
   *
   * ERRORS
   *   Throws IllegalStateException if the stored singleton type does not match
   *   the requested type for the same vendor/type/id key.
   */
  public static synchronized <T> T peekAppSingletonService(
      DeviceUnit device,
      Class<T> serviceClass) {
    if (device == null || serviceClass == null) {
      return null;
    }
    RegistrationHeader header = device.getHeader();
    String vendor = header != null ? header.vendor() : "";
    String type = header != null ? header.deviceType() : device.getDeviceType();
    int id = device.getCanId();
    DeviceInstanceKey key = new DeviceInstanceKey(vendor, type, id);
    Object existing = APP_SINGLETON_SERVICE_REGISTRY.get(key);
    if (existing == null) {
      return null;
    }
    if (!serviceClass.isInstance(existing)) {
      throw new IllegalStateException(
          String.format(MESSAGE_APP_SINGLETON_TYPE_MISMATCH, safeText(vendor), safeText(type), id));
    }
    return serviceClass.cast(existing);
  }

  /**
   * NAME
   *   hasAppSingletonService - Report whether one app-owned singleton has been allocated.
   *
   * PARAMETERS
   *   device - Device wrapper identity to query.
   *
   * RETURNS
   *   True when one app-owned singleton allocation exists for the wrapper key.
   */
  public static synchronized boolean hasAppSingletonService(DeviceUnit device) {
    if (device == null) {
      return false;
    }
    RegistrationHeader header = device.getHeader();
    String vendor = header != null ? header.vendor() : "";
    String type = header != null ? header.deviceType() : device.getDeviceType();
    int id = device.getCanId();
    DeviceInstanceKey key = new DeviceInstanceKey(vendor, type, id);
    return APP_SINGLETON_SERVICE_REGISTRY.containsKey(key);
  }

  /**
   * NAME
   *   hasAppSingletonService - Report whether one app-owned singleton has been allocated.
   *
   * PARAMETERS
   *   deviceEntry - Profile/device-entry identity to query.
   *
   * RETURNS
   *   True when one app-owned singleton allocation exists for the vendor/type/id key.
   */
  public static synchronized boolean hasAppSingletonService(DeviceEntry deviceEntry) {
    if (deviceEntry == null) {
      return false;
    }
    String vendor = deviceEntry.vendor != null ? deviceEntry.vendor : "";
    String type = deviceEntry.type != null ? deviceEntry.type : "";
    DeviceInstanceKey key = new DeviceInstanceKey(vendor, type, deviceEntry.id);
    return APP_SINGLETON_SERVICE_REGISTRY.containsKey(key);
  }

  /**
   * NAME
   *   markAppSingletonAllocated - Record one app-owned singleton allocation marker.
   *
   * PARAMETERS
   *   device - Device wrapper identity to mark allocated.
   *
   * SIDE EFFECTS
   *   Persists a process-lifetime marker used by lightweight virtual singleton
   *   wrappers that do not own a richer vendor service object.
   */
  public static synchronized void markAppSingletonAllocated(DeviceUnit device) {
    if (device == null) {
      return;
    }
    RegistrationHeader header = device.getHeader();
    String vendor = header != null ? header.vendor() : "";
    String type = header != null ? header.deviceType() : device.getDeviceType();
    int id = device.getCanId();
    DeviceInstanceKey key = new DeviceInstanceKey(vendor, type, id);
    APP_SINGLETON_SERVICE_REGISTRY.putIfAbsent(key, APP_SINGLETON_MARKER);
  }

  /**
   * NAME
   *   isRuntimeOwnedDeviceInstance - Report whether an instance claim is runtime-owned.
   *
   * PARAMETERS
   *   instance - Claimed object from the device instance registry.
   *
   * RETURNS
   *   True when the claim belongs to a runtime-owned recreatable device.
   */
  public static boolean isRuntimeOwnedDeviceInstance(Object instance) {
    if (!(instance instanceof DeviceUnit device)) {
      return true;
    }
    return device.getLifecycleOwnership() == DeviceLifecycleOwnership.RUNTIME_OWNED_RECREATABLE;
  }

  /**
   * NAME
   *   getSelectedDevicesSorted - Return selected profile devices sorted by vendor/type/id.
   */
  public static List<DeviceEntry> getSelectedDevicesSorted() {
    return getProfileDevicesSorted(selectedProfile);
  }

  /**
   * NAME
   *   getProfileDevicesSorted - Return devices for a profile without activating it.
   *
   * PARAMETERS
   *   profileName - Profile to inspect.
   *
   * RETURNS
   *   Sorted list of device entries.
   */
  public static List<DeviceEntry> getProfileDevicesSorted(String profileName) {
    if (profileName == null || profileName.isBlank()) {
      return Collections.emptyList();
    }
    ProfileConfig config = profiles.get(profileName);
    if (config == null) {
      return Collections.emptyList();
    }
    List<DeviceEntry> devices = buildDeviceEntries(resolveProfileDevices(config));
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
          BringupPrinter.enqueue("Warning: duplicate CAN ID: " + entry.id);
          hasDuplicate = true;
        }
      }
    }
    if (hasDuplicate) {
      BringupPrinter.enqueue("Warning: duplicate CAN IDs can cause bringup confusion.");
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
      if (entry.manufacturer < 0 || entry.deviceType < 0) {
        BringupPrinter.enqueue(
            String.format(MESSAGE_UNKNOWN_CAN_IDENTITY, entry.label, entry.id));
        continue;
      }
      devices.add(new ExpectedDevice(entry.label, entry.manufacturer, entry.deviceType, entry.id));
    }
    return devices;
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
          BringupPrinter.enqueue("Warning: duplicate CAN ID: " + id);
          hasDuplicate = true;
        }
      }
      if (enabledCount == 0) {
        String label = "group " + (groupIndex + 1);
        if (groupLabels != null && groupIndex < groupLabels.length) {
          label = groupLabels[groupIndex];
        }
        BringupPrinter.enqueue("Warning: all CAN IDs disabled for " + label + ".");
      }
    }

    if (hasDuplicate) {
      BringupPrinter.enqueue("Warning: duplicate CAN IDs can cause bringup confusion.");
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
   *   isEnabledDeviceAddress - Check whether an interface-specific address is enabled.
   */
  public static boolean isEnabledDeviceAddress(int address) {
    return address != DISABLED_CAN_ID;
  }

  /**
   * NAME
   *   summaryAddressLabelForInterface - Return the summary label for an interface address.
   */
  public static String summaryAddressLabelForInterface(String deviceInterface) {
    String value = safeText(deviceInterface);
    if (INTERFACE_CAN.equalsIgnoreCase(value)) {
      return TEXT_SUMMARY_CAN_IDS;
    }
    if (INTERFACE_DIO.equalsIgnoreCase(value)) {
      return TEXT_SUMMARY_DIO_CHANNELS;
    }
    if (INTERFACE_PWM.equalsIgnoreCase(value)) {
      return TEXT_SUMMARY_PWM_CHANNELS;
    }
    if (INTERFACE_ANALOG.equalsIgnoreCase(value)) {
      return TEXT_SUMMARY_ANALOG_CHANNELS;
    }
    if (INTERFACE_USB.equalsIgnoreCase(value)) {
      return TEXT_SUMMARY_USB_PORTS;
    }
    if (INTERFACE_INTERNAL.equalsIgnoreCase(value)) {
      return TEXT_SUMMARY_INTERNAL_IDS;
    }
    return TEXT_SUMMARY_ADDRESSES;
  }

  /**
   * NAME
   *   creationAddressTextForLabel - Format an interface-specific address for device creation logs.
   */
  public static String creationAddressTextForLabel(String label, int address) {
    String deviceInterface = deviceInterfaceForLabel(label);
    String addressLabel = creationAddressLabelForInterface(deviceInterface);
    return addressLabel + " " + address;
  }

  private static String deviceInterfaceForLabel(String label) {
    String lookup = normalizeKey(label);
    if (lookup.isEmpty()) {
      return "";
    }
    for (DeviceEntry entry : ACTIVE_DEVICES) {
      if (entry == null) {
        continue;
      }
      if (lookup.equals(normalizeKey(entry.label))) {
        return safeText(entry.deviceInterface);
      }
    }
    return "";
  }

  private static String creationAddressLabelForInterface(String deviceInterface) {
    String value = safeText(deviceInterface);
    if (INTERFACE_CAN.equalsIgnoreCase(value)) {
      return TEXT_ADDRESS_CAN;
    }
    if (INTERFACE_DIO.equalsIgnoreCase(value)) {
      return TEXT_ADDRESS_DIO_CHANNEL;
    }
    if (INTERFACE_PWM.equalsIgnoreCase(value)) {
      return TEXT_ADDRESS_PWM_CHANNEL;
    }
    if (INTERFACE_ANALOG.equalsIgnoreCase(value)) {
      return TEXT_ADDRESS_ANALOG_CHANNEL;
    }
    if (INTERFACE_USB.equalsIgnoreCase(value)) {
      return TEXT_ADDRESS_USB_PORT;
    }
    if (INTERFACE_INTERNAL.equalsIgnoreCase(value)) {
      return TEXT_ADDRESS_INTERNAL_ID;
    }
    return TEXT_ADDRESS_ADDRESS;
  }

  private static final String WARNING_CLOSE_FAILED_PREFIX =
      "Warning: failed to close device: ";

  /**
   * NAME
   *   closeIfPossible - Close a device if it implements AutoCloseable.
   *
   * RETURNS
   *   True when the handle was closed successfully or did not need closing.
   *   False when close() threw and ownership should be preserved.
   */
  public static boolean closeIfPossible(Object device) {
    return closeIfPossible(device, WARNING_CLOSE_FAILED_PREFIX);
  }

  /**
   * NAME
   *   closeIfPossible - Close a device if it implements AutoCloseable with one warning prefix.
   *
   * PARAMETERS
   *   device - Candidate vendor/app handle.
   *   warningPrefix - Prefix used when close() throws.
   *
   * RETURNS
   *   True when the handle was closed successfully or did not need closing.
   *   False when close() threw and ownership should be preserved.
   */
  public static boolean closeIfPossible(Object device, String warningPrefix) {
    // CTRE Phoenix 6 WPI TalonFX implements AutoCloseable (wpiapi-java 26.1.1+),
    // so this will clean up Sendables and sim resources when present.
    // REV SparkMax implements AutoCloseable via SparkLowLevel in REVLib 2025.0.2+;
    // close() releases the native handle and marks the instance closed (future use throws).
    if (device instanceof AutoCloseable closeable) {
      try {
        closeable.close();
        return true;
      } catch (Exception e) {
        BringupPrinter.enqueue(safeText(warningPrefix) + safeText(e.getMessage()));
        return false;
      }
    }
    return true;
  }

  /**
   * NAME
   *   applyProfileFromArgs - Resolve and select profile from CLI/env/system props.
   *
   * SIDE EFFECTS
   *   Updates selected profile for later activation.
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
      selectCanProfile(profile.trim());
    }
  }

  private static boolean autoSelectDefaultProfileOnStartup() {
    String prop = System.getProperty(PROP_AUTO_SELECT_DEFAULT_PROFILE);
    if (prop != null && !prop.isBlank()) {
      return Boolean.parseBoolean(prop.trim());
    }
    String env = System.getenv(ENV_AUTO_SELECT_DEFAULT_PROFILE);
    if (env != null && !env.isBlank()) {
      return Boolean.parseBoolean(env.trim());
    }
    return false;
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
      BringupPrinter.enqueue(MESSAGE_REGISTRY_JSON_MISSING);
      throw new RuntimeException(MESSAGE_REGISTRY_JSON_MISSING);
    }
    try {
      String rawJson = Files.readString(path, StandardCharsets.UTF_8);
      JsonElement parsed = JsonParser.parseString(rawJson);
      setProfileTests(extractProfileTests(parsed));
      setProfileBridgeConfigs(extractProfileBridgeConfigs(parsed));
      dslTestsRoot = extractDslTestsRoot(parsed);
      ProfileRoot root = GSON.fromJson(rawJson, ProfileRoot.class);
      if (root == null || root.profiles == null || root.profiles.isEmpty()) {
        throw new JsonParseException("No profiles found");
      }
      if (root.schemaVersion != PROFILE_SCHEMA_VERSION) {
        throw new JsonParseException(
            "schema_version mismatch: expected "
                + PROFILE_SCHEMA_VERSION
                + ", got "
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
      validateDeviceRegistryStrict(root.devices);
      if (DEVICE_REGISTRY.isEmpty()) {
        throw new JsonParseException(MESSAGE_EMPTY_DEVICE_REGISTRY);
      }
      profiles = new LinkedHashMap<>(root.profiles);
      profileOrder = new ArrayList<>(profiles.keySet());
      currentDataVersion = root.dataVersion != null ? root.dataVersion : NT_LABEL_EMPTY;
      defaultProfile =
          root.defaultProfile != null ? root.defaultProfile : NT_LABEL_EMPTY;
      if (!profiles.containsKey(defaultProfile)) {
        BringupPrinter.enqueue(MESSAGE_REGISTRY_DEFAULT_PROFILE_MISSING);
        defaultProfile = profileOrder.isEmpty() ? NT_LABEL_EMPTY : profileOrder.get(INDEX_ZERO);
      }
      selectedProfile = autoSelectDefaultProfileOnStartup() ? defaultProfile : NT_LABEL_EMPTY;
      activeProfile = NT_LABEL_EMPTY;
      activeProfileApplied = false;
      bumpActiveProfileGeneration();
    } catch (IOException | JsonParseException ex) {
      BringupPrinter.enqueue("ERROR: bringup_system.json invalid: " + ex.getMessage());
      BringupPrinter.enqueue("ERROR: Redeploy required. Robot code will stop.");
      throw new RuntimeException("Invalid bringup_system.json", ex);
    }
  }

  /**
   * NAME
   *   reloadProfilesFromJson - Reload bringup_system.json from disk.
   *
   * RETURNS
   *   Empty string when reload succeeds, otherwise a human-readable error.
   *
   * SIDE EFFECTS
   *   Clears active profile state and device instances before reloading.
   */
  public static String reloadProfilesFromJson() {
    deactivateActiveProfile();
    clearDeviceInstanceRegistry();
    try {
      loadProfilesFromJson();
      return NT_LABEL_EMPTY;
    } catch (RuntimeException ex) {
      String error = safeText(ex.getMessage());
      if (error.isBlank()) {
        return MESSAGE_RELOAD_FAILED;
      }
      return error;
    }
  }

  /**
   * NAME
   *   resolveProfilePath - Resolve the profile JSON path.
   */
  private static Path resolveProfilePath() {
    // Use deploy folder on roboRIO, fallback to repo-relative path.
    try {
      Path runtimePath = Filesystem.getOperatingDirectory().toPath().resolve(DEFAULT_PROFILE_FILE);
      if (Files.exists(runtimePath)) {
        return runtimePath;
      }
      Path legacyRuntime = Filesystem.getOperatingDirectory().toPath().resolve(LEGACY_PROFILE_FILE);
      if (Files.exists(legacyRuntime)) {
        return legacyRuntime;
      }
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
   *   resolveProfilePersistPath - Resolve the profile JSON runtime path for writes.
   *
   * RETURNS
   *   Runtime-owned path for bringup_system.json when available, otherwise a local path.
   */
  private static Path resolveProfilePersistPath() {
    try {
      return Filesystem.getOperatingDirectory().toPath().resolve(DEFAULT_PROFILE_FILE);
    } catch (Exception ex) {
      return Paths.get(DEFAULT_PROFILE_FILE);
    }
  }

  /**
   * NAME
   *   resolveProfilePersistFallbackPath - Resolve fallback path for profile JSON writes.
   *
   * RETURNS
   *   Deploy path for bringup_system.json when available.
   */
  private static Path resolveProfilePersistFallbackPath() {
    try {
      return Filesystem.getDeployDirectory().toPath().resolve(DEFAULT_PROFILE_FILE);
    } catch (Exception ex) {
      return Paths.get(DEFAULT_PROFILE_FILE);
    }
  }

  /**
   * NAME
   *   applyEmptySafeMode - Clear profile state when no valid JSON config exists.
   */
  private static void applyEmptySafeMode() {
    profiles = new LinkedHashMap<>();
    profileOrder = new ArrayList<>();
    DEVICE_REGISTRY.clear();
    DEVICE_CONFIGS.clear();
    ACTIVE_DEVICES.clear();
    setProfileTests(new LinkedHashMap<>());
    setProfileBridgeConfigs(new LinkedHashMap<>());
    dslTestsRoot = null;
    currentDataVersion = NT_LABEL_EMPTY;
    defaultProfile = NT_LABEL_EMPTY;
    selectedProfile = NT_LABEL_EMPTY;
    activeProfile = NT_LABEL_EMPTY;
    activeProfileApplied = false;
    PDH_CAN_ID = DISABLED_CAN_ID;
    PDP_CAN_ID = DISABLED_CAN_ID;
    PIGEON_CAN_ID = DISABLED_CAN_ID;
    ROBORIO_CAN_ID = DISABLED_CAN_ID;
    BringupPrinter.enqueue(MESSAGE_SAFE_MODE_APPLIED);
    bumpActiveProfileGeneration();
  }

  /**
   * NAME
   *   RegistryStageResult - Stage result for registry apply workflow.
   *
   * DESCRIPTION
   *   Captures per-stage success and message text for UI reporting.
   */
  public static final class RegistryStageResult {
    public boolean ok = false;
    public String message = NT_LABEL_EMPTY;
    public String expectedHash = NT_LABEL_EMPTY;
    public String computedHash = NT_LABEL_EMPTY;
    public long expectedBytes = REGISTRY_BYTES_UNKNOWN;
    public long computedBytes = REGISTRY_BYTES_UNKNOWN;
  }

  /**
   * NAME
   *   RegistryApplyReport - Registry apply report for UI commands.
   *
   * DESCRIPTION
   *   Bundles stage results plus final active profile metadata.
   */
  public static final class RegistryApplyReport {
    public final RegistryStageResult contentValidation = new RegistryStageResult();
    public final RegistryStageResult apply = new RegistryStageResult();
    public final RegistryStageResult postApplyCheck = new RegistryStageResult();
    public boolean overallOk = false;
    public String activeProfile = NT_LABEL_EMPTY;
    public boolean activated = false;
  }

  /**
   * NAME
   *   applyRegistryJson - Validate and apply a registry JSON payload.
   *
   * PARAMETERS
   *   rawJson - Full bringup_system.json payload.
   *   activateProfile - Optional profile name to activate.
   *
   * RETURNS
   *   RegistryApplyReport with per-stage status.
   */
  public static RegistryApplyReport applyRegistryJson(String rawJson, String activateProfile) {
    RegistryApplyReport report = new RegistryApplyReport();
    RegistryPayload payload = validateRegistryPayload(rawJson, activateProfile, report);
    if (payload == null) {
      return report;
    }
    report.contentValidation.ok = true;
    boolean applied = applyRegistryPayload(payload, activateProfile, report);
    if (!applied) {
      return report;
    }
    boolean verified = verifyRegistryApply(activateProfile, report);
    if (!verified) {
      return report;
    }
    if (REGISTRY_PERSIST_ON_APPLY) {
      boolean persisted = persistRegistryJson(rawJson, report);
      if (!persisted) {
        return report;
      }
    }
    report.overallOk = true;
    report.activeProfile = safeText(activeProfile);
    report.activated = activateProfile != null
        && !activateProfile.isBlank()
        && safeText(activeProfile).equals(activateProfile)
        && activeProfileApplied;
    return report;
  }

  /**
   * NAME
   *   RegistryPayload - Parsed registry payload with a validated registry map.
   */
  private static final class RegistryPayload {
    private final ProfileRoot root;
    private final Map<String, DeviceDefinition> registry;
    private final Map<String, JsonElement> testsByProfile;
    private final Map<String, BridgeProfileRuntimeConfig> bridgeConfigsByProfile;
    private final JsonObject dslTestsRoot;

    private RegistryPayload(
        ProfileRoot root,
        Map<String, DeviceDefinition> registry,
        Map<String, JsonElement> testsByProfile,
        Map<String, BridgeProfileRuntimeConfig> bridgeConfigsByProfile,
        JsonObject dslTestsRoot) {
      this.root = root;
      this.registry = registry;
      this.testsByProfile = testsByProfile;
      this.bridgeConfigsByProfile = bridgeConfigsByProfile;
      this.dslTestsRoot = dslTestsRoot;
    }
  }

  /**
   * NAME
   *   BridgeProfileMemberConfig - Immutable group member snapshot.
   */
  public static final class BridgeProfileMemberConfig {
    public final String label;
    public final boolean enabled;

    public BridgeProfileMemberConfig(String label, boolean enabled) {
      this.label = safeText(label);
      this.enabled = enabled;
    }
  }

  /**
   * NAME
   *   BridgeProfileBindingConfig - Immutable group binding snapshot.
   */
  public static final class BridgeProfileBindingConfig {
    public final String input;
    public final String kind;
    public final boolean hasValue;
    public final double value;

    public BridgeProfileBindingConfig(String input, String kind, boolean hasValue, double value) {
      this.input = safeText(input);
      this.kind = safeText(kind);
      this.hasValue = hasValue;
      this.value = value;
    }
  }

  /**
   * NAME
   *   BridgeProfileGroupConfig - Immutable bridge group snapshot.
   */
  public static final class BridgeProfileGroupConfig {
    public final String name;
    public final boolean enabled;
    public final List<BridgeProfileMemberConfig> members;
    public final List<BridgeProfileBindingConfig> bindings;

    public BridgeProfileGroupConfig(
        String name,
        boolean enabled,
        List<BridgeProfileMemberConfig> members,
        List<BridgeProfileBindingConfig> bindings) {
      this.name = safeText(name);
      this.enabled = enabled;
      this.members = Collections.unmodifiableList(new ArrayList<>(members));
      this.bindings = Collections.unmodifiableList(new ArrayList<>(bindings));
    }
  }

  /**
   * NAME
   *   BridgeProfileSelectedDeviceConfig - Immutable selected-device snapshot.
   */
  public static final class BridgeProfileSelectedDeviceConfig {
    public final String device;
    public final boolean enabled;

    public BridgeProfileSelectedDeviceConfig(String device, boolean enabled) {
      this.device = safeText(device);
      this.enabled = enabled;
    }
  }

  /**
   * NAME
   *   BridgeProfileRuntimeConfig - Immutable per-profile bridge runtime config.
   */
  public static final class BridgeProfileRuntimeConfig {
    private static final BridgeProfileRuntimeConfig EMPTY =
        new BridgeProfileRuntimeConfig(
            Collections.emptyList(),
            new BridgeProfileSelectedDeviceConfig(NT_LABEL_EMPTY, false));

    public final List<BridgeProfileGroupConfig> groups;
    public final BridgeProfileSelectedDeviceConfig selectedDevice;

    public BridgeProfileRuntimeConfig(
        List<BridgeProfileGroupConfig> groups,
        BridgeProfileSelectedDeviceConfig selectedDevice) {
      this.groups = Collections.unmodifiableList(new ArrayList<>(groups));
      this.selectedDevice = selectedDevice != null
          ? selectedDevice
          : new BridgeProfileSelectedDeviceConfig(NT_LABEL_EMPTY, false);
    }

    public static BridgeProfileRuntimeConfig empty() {
      return EMPTY;
    }
  }

  private static String readJsonString(JsonObject object, String key) {
    if (object == null || key == null || !object.has(key) || object.get(key).isJsonNull()) {
      return NT_LABEL_EMPTY;
    }
    try {
      return object.get(key).getAsString();
    } catch (Exception ex) {
      return NT_LABEL_EMPTY;
    }
  }

  private static boolean readJsonBoolean(JsonObject object, String key, boolean defaultValue) {
    if (object == null || key == null || !object.has(key) || object.get(key).isJsonNull()) {
      return defaultValue;
    }
    try {
      return object.get(key).getAsBoolean();
    } catch (Exception ex) {
      return defaultValue;
    }
  }

  private static double readJsonDouble(JsonObject object, String key, double defaultValue) {
    if (object == null || key == null || !object.has(key) || object.get(key).isJsonNull()) {
      return defaultValue;
    }
    try {
      return object.get(key).getAsDouble();
    } catch (Exception ex) {
      return defaultValue;
    }
  }

  /**
   * NAME
   *   validateRegistryPayload - Validate registry JSON without mutating state.
   */
  private static RegistryPayload validateRegistryPayload(
      String rawJson,
      String activateProfile,
      RegistryApplyReport report) {
    if (rawJson == null || rawJson.isBlank()) {
      report.contentValidation.message = MESSAGE_REGISTRY_JSON_MISSING;
      return null;
    }
    JsonElement parsed;
    try {
      parsed = JsonParser.parseString(rawJson);
    } catch (JsonParseException ex) {
      report.contentValidation.message = String.format(MESSAGE_REGISTRY_JSON_PARSE, ex.getMessage());
      return null;
    }
    if (parsed == null || !parsed.isJsonObject()) {
      report.contentValidation.message = MESSAGE_REGISTRY_ROOT_NOT_OBJECT;
      return null;
    }
    ProfileRoot root;
    try {
      root = GSON.fromJson(parsed, ProfileRoot.class);
    } catch (JsonParseException ex) {
      report.contentValidation.message = String.format(MESSAGE_REGISTRY_JSON_PARSE, ex.getMessage());
      return null;
    }
    if (root == null) {
      report.contentValidation.message = MESSAGE_REGISTRY_JSON_MISSING;
      return null;
    }
    if (root.schemaVersion != PROFILE_SCHEMA_VERSION) {
      report.contentValidation.message =
          String.format(MESSAGE_REGISTRY_SCHEMA_MISMATCH, PROFILE_SCHEMA_VERSION, root.schemaVersion);
      return null;
    }
    if (root.dataVersion == null || root.dataVersion.isBlank()) {
      report.contentValidation.message = MESSAGE_REGISTRY_DATA_VERSION_MISSING;
      return null;
    }
    if (root.dataHash == null || root.dataHash.isBlank()) {
      report.contentValidation.message = MESSAGE_REGISTRY_DATA_HASH_MISSING;
      return null;
    }
    String computedHash;
    try {
      computedHash = computeDataHash(rawJson);
    } catch (JsonParseException ex) {
      report.contentValidation.message = ex.getMessage();
      return null;
    }
    if (!root.dataHash.equals(computedHash)) {
      report.contentValidation.message = MESSAGE_REGISTRY_DATA_HASH_MISMATCH;
      return null;
    }
    if (root.devices == null || root.devices.isEmpty()) {
      report.contentValidation.message = MESSAGE_REGISTRY_DEVICES_MISSING;
      return null;
    }
    Map<String, DeviceDefinition> registry = buildRegistryMap(root.devices, report);
    if (registry == null) {
      return null;
    }
    if (root.profiles == null || root.profiles.isEmpty()) {
      report.contentValidation.message = MESSAGE_REGISTRY_PROFILES_MISSING;
      return null;
    }
    if (activateProfile != null && !activateProfile.isBlank()
        && !root.profiles.containsKey(activateProfile)) {
      report.contentValidation.message =
          String.format(MESSAGE_REGISTRY_ACTIVATE_UNKNOWN, activateProfile);
      return null;
    }
    for (Map.Entry<String, ProfileConfig> entry : root.profiles.entrySet()) {
      String profileName = entry.getKey();
      ProfileConfig config = entry.getValue();
      List<String> labels = config != null ? config.devices : null;
      if (labels == null) {
        report.contentValidation.message =
            String.format(MESSAGE_REGISTRY_PROFILE_DEVICES_MISSING, profileName);
        return null;
      }
      Set<String> seen = new java.util.HashSet<>();
      for (String label : labels) {
        String display = safeText(label);
        if (display.isEmpty()) {
          continue;
        }
        String normalized = normalizeKey(display);
        if (normalized.isEmpty()) {
          continue;
        }
        if (seen.contains(normalized)) {
          report.contentValidation.message =
              String.format(MESSAGE_REGISTRY_PROFILE_DEVICE_DUP, profileName, display);
          return null;
        }
        seen.add(normalized);
        if (!registry.containsKey(normalized)) {
          report.contentValidation.message =
              String.format(MESSAGE_REGISTRY_PROFILE_DEVICE_UNKNOWN, profileName, display);
          return null;
        }
      }
    }
    Map<String, JsonElement> testsByProfile = extractProfileTests(parsed);
    Map<String, BridgeProfileRuntimeConfig> bridgeConfigsByProfile =
        extractProfileBridgeConfigs(parsed);
    JsonObject nextDslTestsRoot = extractDslTestsRoot(parsed);
    return new RegistryPayload(
        root,
        registry,
        testsByProfile,
        bridgeConfigsByProfile,
        nextDslTestsRoot);
  }

  /**
   * NAME
   *   buildRegistryMap - Build a validated device registry map.
   */
  private static Map<String, DeviceDefinition> buildRegistryMap(
      List<DeviceDefinition> devices,
      RegistryApplyReport report) {
    Map<String, DeviceDefinition> registry = new LinkedHashMap<>();
    for (DeviceDefinition def : devices) {
      if (def == null) {
        continue;
      }
      String label = safeText(def.label);
      if (label.isEmpty()) {
        report.contentValidation.message = MESSAGE_REGISTRY_DEVICE_LABEL_MISSING;
        return null;
      }
      String lookup = normalizeKey(label);
      if (lookup.isEmpty()) {
        report.contentValidation.message = MESSAGE_REGISTRY_DEVICE_LABEL_MISSING;
        return null;
      }
      if (registry.containsKey(lookup)) {
        report.contentValidation.message =
            String.format(MESSAGE_REGISTRY_DEVICE_LABEL_DUP, label);
        return null;
      }
      registry.put(lookup, def);
    }
    return registry;
  }

  /**
   * NAME
   *   extractProfileTests - Extract per-profile tests payloads from JSON.
   */
  private static Map<String, JsonElement> extractProfileTests(JsonElement parsed) {
    Map<String, JsonElement> testsByProfile = new LinkedHashMap<>();
    if (parsed == null || !parsed.isJsonObject()) {
      return testsByProfile;
    }
    JsonObject root = parsed.getAsJsonObject();
    JsonElement bridgeElement = root.get(KEY_BRIDGE_CONFIG);
    if (bridgeElement == null || !bridgeElement.isJsonObject()) {
      return testsByProfile;
    }
    JsonObject bridge = bridgeElement.getAsJsonObject();
    JsonElement byProfileElement = bridge.get(KEY_BRIDGE_BY_PROFILE);
    if (byProfileElement == null || !byProfileElement.isJsonObject()) {
      return testsByProfile;
    }
    JsonObject byProfile = byProfileElement.getAsJsonObject();
    for (Map.Entry<String, JsonElement> entry : byProfile.entrySet()) {
      String profileName = entry.getKey();
      JsonElement profileElement = entry.getValue();
      if (profileElement == null || !profileElement.isJsonObject()) {
        continue;
      }
      JsonObject profile = profileElement.getAsJsonObject();
      JsonElement testsElement = profile.get(KEY_BRIDGE_TESTS);
      if (testsElement != null && testsElement.isJsonObject()) {
        testsByProfile.put(profileName, testsElement);
      }
    }
    return testsByProfile;
  }

  /**
   * NAME
   *   extractProfileBridgeConfigs - Extract per-profile bridgeConfig payloads.
   */
  private static Map<String, BridgeProfileRuntimeConfig> extractProfileBridgeConfigs(
      JsonElement parsed) {
    Map<String, BridgeProfileRuntimeConfig> configs = new LinkedHashMap<>();
    if (parsed == null || !parsed.isJsonObject()) {
      return configs;
    }
    JsonObject root = parsed.getAsJsonObject();
    JsonElement bridgeElement = root.get(KEY_BRIDGE_CONFIG);
    if (bridgeElement == null || !bridgeElement.isJsonObject()) {
      return configs;
    }
    JsonObject bridge = bridgeElement.getAsJsonObject();
    JsonElement byProfileElement = bridge.get(KEY_BRIDGE_BY_PROFILE);
    if (byProfileElement == null || !byProfileElement.isJsonObject()) {
      return configs;
    }
    JsonObject byProfile = byProfileElement.getAsJsonObject();
    for (Map.Entry<String, JsonElement> entry : byProfile.entrySet()) {
      JsonElement profileElement = entry.getValue();
      if (profileElement == null || !profileElement.isJsonObject()) {
        continue;
      }
      configs.put(entry.getKey(), parseBridgeProfileRuntimeConfig(profileElement.getAsJsonObject()));
    }
    return configs;
  }

  private static BridgeProfileRuntimeConfig parseBridgeProfileRuntimeConfig(JsonObject profile) {
    List<BridgeProfileGroupConfig> groups = new ArrayList<>();
    JsonElement groupsElement = profile.get(KEY_BRIDGE_GROUPS);
    if (groupsElement != null && groupsElement.isJsonArray()) {
      for (JsonElement groupElement : groupsElement.getAsJsonArray()) {
        if (groupElement == null || !groupElement.isJsonObject()) {
          continue;
        }
        JsonObject group = groupElement.getAsJsonObject();
        String name = safeText(readJsonString(group, KEY_NAME));
        if (name.isBlank()) {
          continue;
        }
        boolean enabled = readJsonBoolean(group, KEY_ENABLED, true);
        List<BridgeProfileMemberConfig> members = new ArrayList<>();
        JsonElement membersElement = group.get(KEY_MEMBERS);
        if (membersElement != null && membersElement.isJsonArray()) {
          for (JsonElement memberElement : membersElement.getAsJsonArray()) {
            if (memberElement == null) {
              continue;
            }
            if (memberElement.isJsonPrimitive()) {
              String label = safeText(memberElement.getAsString());
              if (!label.isBlank()) {
                members.add(new BridgeProfileMemberConfig(label, true));
              }
              continue;
            }
            if (!memberElement.isJsonObject()) {
              continue;
            }
            JsonObject member = memberElement.getAsJsonObject();
            String label = safeText(readJsonString(member, KEY_LABEL));
            if (label.isBlank()) {
              label = safeText(readJsonString(member, KEY_DEVICE));
            }
            if (label.isBlank()) {
              continue;
            }
            members.add(
                new BridgeProfileMemberConfig(label, readJsonBoolean(member, KEY_ENABLED, true)));
          }
        }
        List<BridgeProfileBindingConfig> bindings = new ArrayList<>();
        JsonElement bindingsElement = group.get(KEY_BRIDGE_BINDINGS);
        if (bindingsElement != null && bindingsElement.isJsonArray()) {
          for (JsonElement bindingElement : bindingsElement.getAsJsonArray()) {
            if (bindingElement == null || !bindingElement.isJsonObject()) {
              continue;
            }
            JsonObject binding = bindingElement.getAsJsonObject();
            String input = safeText(readJsonString(binding, KEY_INPUT));
            String kind = safeText(readJsonString(binding, KEY_KIND));
            if (input.isBlank() || kind.isBlank()) {
              continue;
            }
            boolean hasValue = binding.has(KEY_VALUE) && !binding.get(KEY_VALUE).isJsonNull();
            double value = hasValue ? readJsonDouble(binding, KEY_VALUE, 0.0) : 0.0;
            bindings.add(new BridgeProfileBindingConfig(input, kind, hasValue, value));
          }
        }
        groups.add(new BridgeProfileGroupConfig(name, enabled, members, bindings));
      }
    }
    JsonObject selected = profile.has(KEY_BRIDGE_SELECTED_DEVICE)
        && profile.get(KEY_BRIDGE_SELECTED_DEVICE).isJsonObject()
            ? profile.getAsJsonObject(KEY_BRIDGE_SELECTED_DEVICE)
            : null;
    String device = selected != null ? safeText(readJsonString(selected, KEY_DEVICE)) : NT_LABEL_EMPTY;
    boolean enabled = selected != null && readJsonBoolean(selected, KEY_ENABLED, false);
    return new BridgeProfileRuntimeConfig(
        groups,
        new BridgeProfileSelectedDeviceConfig(device, enabled));
  }

  /**
   * NAME
   *   extractDslTestsRoot - Extract top-level DSL tests root from JSON.
   */
  private static JsonObject extractDslTestsRoot(JsonElement parsed) {
    if (parsed == null || !parsed.isJsonObject()) {
      return null;
    }
    JsonObject root = parsed.getAsJsonObject();
    JsonElement dslElement = root.get(KEY_DSL_TESTS);
    return dslElement != null && dslElement.isJsonObject() ? dslElement.getAsJsonObject().deepCopy() : null;
  }

  /**
   * NAME
   *   setProfileTests - Replace profile tests cache.
   */
  private static void setProfileTests(Map<String, JsonElement> testsByProfile) {
    PROFILE_TESTS.clear();
    if (testsByProfile == null || testsByProfile.isEmpty()) {
      return;
    }
    PROFILE_TESTS.putAll(testsByProfile);
  }

  /**
   * NAME
   *   setProfileBridgeConfigs - Replace bridgeConfig cache.
   */
  private static void setProfileBridgeConfigs(
      Map<String, BridgeProfileRuntimeConfig> configsByProfile) {
    PROFILE_BRIDGE_CONFIGS.clear();
    if (configsByProfile == null || configsByProfile.isEmpty()) {
      return;
    }
    PROFILE_BRIDGE_CONFIGS.putAll(configsByProfile);
  }

  private static JsonObject buildBridgeConfigJson() {
    JsonObject byProfile = new JsonObject();
    for (String profileName : profileOrder) {
      JsonObject profile = buildBridgeProfileJson(profileName);
      if (profile.size() > 0) {
        byProfile.add(profileName, profile);
      }
    }
    if (byProfile.size() <= 0) {
      return new JsonObject();
    }
    JsonObject bridge = new JsonObject();
    bridge.add(KEY_BRIDGE_BY_PROFILE, byProfile);
    return bridge;
  }

  private static JsonObject buildBridgeProfileJson(String profileName) {
    JsonObject profile = new JsonObject();
    JsonElement testsPayload = PROFILE_TESTS.get(profileName);
    if (testsPayload != null && !testsPayload.isJsonNull()) {
      profile.add(KEY_BRIDGE_TESTS, testsPayload.deepCopy());
    }
    BridgeProfileRuntimeConfig runtimeConfig = PROFILE_BRIDGE_CONFIGS.get(profileName);
    if (runtimeConfig == null) {
      return profile;
    }
    JsonArray groups = new JsonArray();
    for (BridgeProfileGroupConfig group : runtimeConfig.groups) {
      if (group == null || group.name == null || group.name.isBlank()) {
        continue;
      }
      JsonObject groupObject = new JsonObject();
      groupObject.addProperty(KEY_NAME, group.name);
      groupObject.addProperty(KEY_ENABLED, group.enabled);
      JsonArray members = new JsonArray();
      for (BridgeProfileMemberConfig member : group.members) {
        if (member == null || member.label == null || member.label.isBlank()) {
          continue;
        }
        JsonObject memberObject = new JsonObject();
        memberObject.addProperty(KEY_LABEL, member.label);
        memberObject.addProperty(KEY_ENABLED, member.enabled);
        members.add(memberObject);
      }
      groupObject.add(KEY_MEMBERS, members);
      JsonArray bindings = new JsonArray();
      for (BridgeProfileBindingConfig binding : group.bindings) {
        if (binding == null
            || binding.input == null
            || binding.input.isBlank()
            || binding.kind == null
            || binding.kind.isBlank()) {
          continue;
        }
        JsonObject bindingObject = new JsonObject();
        bindingObject.addProperty(KEY_INPUT, binding.input);
        bindingObject.addProperty(KEY_KIND, binding.kind);
        if (binding.hasValue) {
          bindingObject.addProperty(KEY_VALUE, binding.value);
        }
        bindings.add(bindingObject);
      }
      groupObject.add(KEY_BRIDGE_BINDINGS, bindings);
      groups.add(groupObject);
    }
    if (groups.size() > 0) {
      profile.add(KEY_BRIDGE_GROUPS, groups);
    }
    if (runtimeConfig.selectedDevice != null
        && runtimeConfig.selectedDevice.device != null
        && !runtimeConfig.selectedDevice.device.isBlank()) {
      JsonObject selectedDevice = new JsonObject();
      selectedDevice.addProperty(KEY_DEVICE, runtimeConfig.selectedDevice.device);
      selectedDevice.addProperty(KEY_ENABLED, runtimeConfig.selectedDevice.enabled);
      profile.add(KEY_BRIDGE_SELECTED_DEVICE, selectedDevice);
    }
    return profile;
  }

  /**
   * NAME
   *   applyRegistryPayload - Replace in-memory registry from payload data.
   */
  private static boolean applyRegistryPayload(
      RegistryPayload payload,
      String activateProfile,
      RegistryApplyReport report) {
    try {
      profiles = new LinkedHashMap<>(payload.root.profiles);
      profileOrder = new ArrayList<>(profiles.keySet());
      currentDataVersion = payload.root.dataVersion != null ? payload.root.dataVersion : NT_LABEL_EMPTY;
      String nextDefault = safeText(payload.root.defaultProfile);
      if (nextDefault.isBlank() || !profiles.containsKey(nextDefault)) {
        nextDefault = profiles.isEmpty() ? NT_LABEL_EMPTY : profileOrder.get(INDEX_ZERO);
      }
      defaultProfile = nextDefault;
      if (selectedProfile == null || selectedProfile.isBlank() || !profiles.containsKey(selectedProfile)) {
        selectedProfile = autoSelectDefaultProfileOnStartup() ? defaultProfile : NT_LABEL_EMPTY;
      }
      if ((activateProfile == null || activateProfile.isBlank())
          && (activeProfile == null || activeProfile.isBlank() || !profiles.containsKey(activeProfile))) {
        activeProfile = NT_LABEL_EMPTY;
        activeProfileApplied = false;
      }
      DEVICE_REGISTRY.clear();
      DEVICE_REGISTRY.putAll(payload.registry);
      setProfileTests(payload.testsByProfile);
      setProfileBridgeConfigs(payload.bridgeConfigsByProfile);
      dslTestsRoot = payload.dslTestsRoot != null ? payload.dslTestsRoot.deepCopy() : null;
      clearDeviceInstanceRegistry();
      bumpActiveProfileGeneration();
      if (activateProfile != null && !activateProfile.isBlank()) {
        String error = applyActiveProfileStrict(activateProfile);
        if (!error.isBlank()) {
          report.apply.message = error;
          return false;
        }
      }
      report.apply.ok = true;
      return true;
    } catch (Exception ex) {
      report.apply.message = String.format(MESSAGE_REGISTRY_APPLY_FAILED, ex.getMessage());
      return false;
    }
  }

  /**
   * NAME
   *   verifyRegistryApply - Verify registry consistency after apply.
   */
  private static boolean verifyRegistryApply(
      String activateProfile,
      RegistryApplyReport report) {
    if (profiles == null || profiles.isEmpty()) {
      report.postApplyCheck.message =
          String.format(MESSAGE_REGISTRY_POST_APPLY_FAILED, MESSAGE_REGISTRY_PROFILES_MISSING);
      return false;
    }
    if (DEVICE_REGISTRY.isEmpty()) {
      report.postApplyCheck.message =
          String.format(MESSAGE_REGISTRY_POST_APPLY_FAILED, MESSAGE_REGISTRY_DEVICES_MISSING);
      return false;
    }
    String active = safeText(activeProfile);
    if (!active.isBlank() && !profiles.containsKey(active)) {
      report.postApplyCheck.message =
          String.format(MESSAGE_REGISTRY_POST_APPLY_FAILED, String.format(MESSAGE_REGISTRY_ACTIVE_UNKNOWN, active));
      return false;
    }
    if (activateProfile != null && !activateProfile.isBlank()) {
      if (!activeProfileApplied || !safeText(activeProfile).equals(activateProfile)) {
        report.postApplyCheck.message =
            String.format(MESSAGE_REGISTRY_POST_APPLY_FAILED, MESSAGE_REGISTRY_ACTIVATE_FAILED);
        return false;
      }
    }
    report.postApplyCheck.ok = true;
    return true;
  }

  /**
   * NAME
   *   persistRegistryJson - Persist registry JSON to the deploy path.
   *
   * PARAMETERS
   *   rawJson - Full bringup_system.json payload.
   *   report - Registry apply report to update on failure.
   *
   * RETURNS
   *   True when persisted, false when an error is reported.
   */
  private static boolean persistRegistryJson(String rawJson, RegistryApplyReport report) {
    Path path = resolveProfilePersistPath();
    if (path == null) {
      report.postApplyCheck.ok = false;
      report.postApplyCheck.message = MESSAGE_REGISTRY_PERSIST_PATH_MISSING;
      return false;
    }
    try {
      Files.writeString(path, rawJson, StandardCharsets.UTF_8);
      report.postApplyCheck.ok = true;
      return true;
    } catch (IOException ex) {
      String primaryError = safeText(ex.getMessage());
      if (REGISTRY_PERSIST_FALLBACK_ON_FAIL) {
        Path fallbackPath = resolveProfilePersistFallbackPath();
        if (fallbackPath != null) {
          try {
            Files.writeString(fallbackPath, rawJson, StandardCharsets.UTF_8);
            BringupPrinter.enqueue(
                String.format(MESSAGE_REGISTRY_PERSIST_FALLBACK, primaryError, fallbackPath));
            report.postApplyCheck.ok = true;
            return true;
          } catch (IOException fallbackEx) {
            String fallbackError = safeText(fallbackEx.getMessage());
            report.postApplyCheck.ok = false;
            report.postApplyCheck.message =
                String.format(MESSAGE_REGISTRY_PERSIST_FAILED_BOTH, primaryError, fallbackError);
            return false;
          }
        }
      }
      report.postApplyCheck.ok = false;
      report.postApplyCheck.message = String.format(MESSAGE_REGISTRY_PERSIST_FAILED, primaryError);
      return false;
    }
  }

  /**
   * NAME
   *   applyActiveProfileStrict - Activate a profile with strict validation.
   */
  private static String applyActiveProfileStrict(String profileName) {
    String resolved = safeText(profileName);
    if (resolved.isBlank()) {
      return MESSAGE_REGISTRY_ACTIVATE_MISSING;
    }
    ProfileConfig config = profiles.get(resolved);
    if (config == null) {
      return String.format(MESSAGE_REGISTRY_ACTIVATE_UNKNOWN, resolved);
    }
    try {
      validateProfileCanIdsStrict(resolved, config);
      validateProfileLabelsStrict(resolved, config);
    } catch (JsonParseException ex) {
      return ex.getMessage();
    }
    List<DeviceDefinition> profileDevices = resolveProfileDevices(config);
    buildDeviceConfigs(profileDevices);
    PDH_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_REV_ID, DEVTYPE_POWER_ID);
    PDP_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_CTRE_ID, DEVTYPE_POWER_ID);
    PIGEON_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_CTRE_ID, DEVTYPE_GYRO_ID);
    ROBORIO_CAN_ID = resolveSingletonIdByMfgType(profileDevices, MFG_NI_ID, DEVTYPE_ROBORIO_ID);
    activeProfile = resolved;
    selectedProfile = resolved;
    activeProfileApplied = true;
    return NT_LABEL_EMPTY;
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
  private static void validateProfileCanIdsStrict(String profileName, ProfileConfig config) {
    if (config == null || config.devices == null) {
      return;
    }
    Map<String, List<String>> seen = new LinkedHashMap<>();
    Map<Integer, List<String>> seenById = new LinkedHashMap<>();
    for (String label : config.devices) {
      String lookup = normalizeKey(label);
      String display = safeText(label);
      if (lookup.isEmpty()) {
        continue;
      }
      DeviceDefinition def = DEVICE_REGISTRY.get(lookup);
      if (def == null) {
        throw new JsonParseException(String.format(MESSAGE_UNKNOWN_DEVICE, profileName, display));
      }
      if (!isCanDevice(def)) {
        continue;
      }
      int canId = def.id != null ? def.id : DISABLED_CAN_ID;
      if (!isEnabledCanId(canId)) {
        continue;
      }
      String vendor = resolveVendorName(def);
      String type = resolveDeviceTypeLabel(def);
      String key = deviceKey(vendor, type, canId);
      addSeenLabel(seen, key, display);
      addSeenLabelById(seenById, canId, display);
    }

    for (Map.Entry<String, List<String>> entry : seen.entrySet()) {
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

    for (Map.Entry<Integer, List<String>> entry : seenById.entrySet()) {
      if (entry.getValue().size() > 1) {
        BringupPrinter.enqueue(
            "Warning: profile '" + profileName + "' uses CAN ID " + entry.getKey()
                + " across multiple vendor/types ("
                + String.join(", ", entry.getValue())
                + "). This violates the bringup conventions but is allowed.");
      }
    }
  }

  /**
   * NAME
   *   validateProfileLabelsStrict - Fail fast on duplicate labels in a profile.
   *
   * PARAMETERS
   *   profileName - Profile key being validated.
   *   config - Profile configuration entry.
   *
   * ERRORS
   *   Throws JsonParseException when duplicates are found.
   */
  private static void validateProfileLabelsStrict(String profileName, ProfileConfig config) {
    if (config == null || config.devices == null) {
      return;
    }
    Map<String, List<String>> seen = new LinkedHashMap<>();
    for (String label : config.devices) {
      String normalized = safeText(label);
      if (normalized.isEmpty()) {
        continue;
      }
      List<String> labels = getOrCreateLabelList(seen, normalized);
      labels.add(normalized);
    }
    for (Map.Entry<String, List<String>> entry : seen.entrySet()) {
      if (entry.getValue().size() > 1) {
        throw new JsonParseException(
            String.format(
                MESSAGE_DUPLICATE_LABEL,
                profileName,
                entry.getKey(),
                String.join(", ", entry.getValue())));
      }
    }
  }

  private static void validateDeviceRegistryStrict(List<DeviceDefinition> devices) {
    DEVICE_REGISTRY.clear();
    if (devices == null || devices.isEmpty()) {
      return;
    }
    for (DeviceDefinition def : devices) {
      if (def == null) {
        continue;
      }
      String label = normalizeKey(def.label);
      if (label.isEmpty()) {
        throw new JsonParseException("Device registry contains entry with empty label.");
      }
      if (DEVICE_REGISTRY.containsKey(label)) {
        throw new JsonParseException("Duplicate device label in registry: " + label);
      }
      DEVICE_REGISTRY.put(label, def);
    }
  }

  private static void addSeenLabel(Map<String, List<String>> seen, String key, String label) {
    if (key == null) {
      return;
    }
    List<String> labels = getOrCreateLabelList(seen, key);
    labels.add(label);
  }

  private static void addSeenLabelById(Map<Integer, List<String>> seen, int id, String label) {
    List<String> labels = getOrCreateLabelList(seen, id);
    labels.add(label);
  }

  private static <K> List<String> getOrCreateLabelList(Map<K, List<String>> map, K key) {
    List<String> labels = map.get(key);
    if (labels == null) {
      labels = new ArrayList<>();
      map.put(key, labels);
    }
    return labels;
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
  private static void buildDeviceConfigs(List<DeviceDefinition> defs) {
    DEVICE_CONFIGS.clear();
    ACTIVE_DEVICES.clear();
    if (defs == null || defs.isEmpty()) {
      return;
    }
    for (DeviceDefinition def : defs) {
      if (def == null || !isRuntimeDevice(def)) {
        continue;
      }
      DeviceEntry entry = buildDeviceEntry(def);
      ACTIVE_DEVICES.add(entry);
      if (entry.vendor.isEmpty() || entry.type.isEmpty()) {
        BringupPrinter.enqueue("Warning: device entry missing vendor/type for CAN ID " + entry.id);
        continue;
      }
      DeviceKey key = new DeviceKey(entry.vendor, entry.type);
      DeviceConfig config = new DeviceConfig(entry.id, entry.label, entry.motor, entry.limits, def.invert);
      DEVICE_CONFIGS.computeIfAbsent(key, ignored -> new ArrayList<>()).add(config);
    }
  }

  private static List<DeviceEntry> buildDeviceEntries(List<DeviceDefinition> defs) {
    List<DeviceEntry> entries = new ArrayList<>();
    if (defs == null || defs.isEmpty()) {
      return entries;
    }
    for (DeviceDefinition def : defs) {
      if (def == null || !isRuntimeDevice(def)) {
        continue;
      }
      entries.add(buildDeviceEntry(def));
    }
    return entries;
  }

  private static DeviceEntry buildDeviceEntry(DeviceDefinition def) {
    String label = safeText(def.label);
    int canId = def.id != null ? def.id : DISABLED_CAN_ID;
    String deviceInterface = safeText(def.deviceInterface);
    String vendor = resolveVendorName(def);
    String type = resolveDeviceTypeLabel(def);
    String motor = resolveMotorModel(def);
    LimitConfig limits = buildLimitConfig(def);
    int manufacturer = def.manufacturer != null ? def.manufacturer : DISABLED_CAN_ID;
    int deviceType = def.deviceType != null ? def.deviceType : DISABLED_CAN_ID;
    return new DeviceEntry(
        canId,
        manufacturer,
        deviceType,
        deviceInterface,
        vendor,
        type,
        label,
        motor,
        limits,
        def.tags,
        def.terminator);
  }

  private static List<DeviceDefinition> resolveProfileDevices(ProfileConfig config) {
    if (config == null) {
      return Collections.emptyList();
    }
    return resolveProfileDevices(config.devices);
  }

  private static List<DeviceDefinition> resolveProfileDevices(List<String> labels) {
    if (labels == null || labels.isEmpty()) {
      return Collections.emptyList();
    }
    List<DeviceDefinition> devices = new ArrayList<>();
    for (String label : labels) {
      String lookup = normalizeKey(label);
      if (lookup.isEmpty()) {
        continue;
      }
      DeviceDefinition def = DEVICE_REGISTRY.get(lookup);
      if (def != null) {
        devices.add(def);
      }
    }
    return devices;
  }

  private static boolean isRuntimeDevice(DeviceDefinition def) {
    return isCanDevice(def) || isXboxControllerDevice(def) || isLimitSwitch(def);
  }

  private static boolean isCanDevice(DeviceDefinition def) {
    if (def == null || def.deviceInterface == null) {
      return false;
    }
    return INTERFACE_CAN.equalsIgnoreCase(def.deviceInterface);
  }

  private static boolean isXboxControllerDevice(DeviceDefinition def) {
    if (def == null || def.deviceInterface == null) {
      return false;
    }
    return INTERFACE_USB.equalsIgnoreCase(def.deviceInterface)
        && DEVICE_TYPE_XBOX_CONTROLLER.equalsIgnoreCase(safeText(def.type));
  }

  private static boolean isLimitSwitch(DeviceDefinition def) {
    if (def == null || def.deviceInterface == null) {
      return false;
    }
    if (!INTERFACE_DIO.equalsIgnoreCase(def.deviceInterface)) {
      return false;
    }
    return DEVICE_TYPE_LIMIT_SWITCH.equalsIgnoreCase(safeText(def.type));
  }

  private static LimitConfig buildLimitConfig(DeviceDefinition def) {
    List<LimitSwitchConfig> switches = resolveLimitSwitches(def);
    return new LimitConfig(switches);
  }

  private static List<LimitSwitchConfig> resolveLimitSwitches(DeviceDefinition def) {
    if (def == null || def.attachments == null || def.attachments.isEmpty()) {
      return Collections.emptyList();
    }
    List<LimitSwitchConfig> switches = new ArrayList<>();
    for (String label : def.attachments) {
      String lookup = normalizeKey(label);
      if (lookup.isEmpty()) {
        continue;
      }
      DeviceDefinition attachment = DEVICE_REGISTRY.get(lookup);
      if (attachment == null || !isLimitSwitch(attachment)) {
        continue;
      }
      int dio = attachment.id != null ? attachment.id : DISABLED_CAN_ID;
      boolean invert = attachment.invert != null ? attachment.invert : false;
      switches.add(new LimitSwitchConfig(safeText(attachment.label), dio, invert));
    }
    return switches;
  }

  private static String resolveVendorName(DeviceDefinition def) {
    if (isXboxControllerDevice(def)) {
      return DEVICE_VENDOR_MICROSOFT;
    }
    if (isLimitSwitch(def)) {
      return DEVICE_VENDOR_NI;
    }
    if (def == null || def.manufacturer == null) {
      return LABEL_UNKNOWN;
    }
    String name = getCanManufacturerName(def.manufacturer);
    if (name != null && !name.isBlank()) {
      return name;
    }
    if (def.manufacturer == MFG_NI_ID) {
      return DEVICE_VENDOR_NI;
    }
    if (def.manufacturer == MFG_CTRE_ID) {
      return DEVICE_VENDOR_CTRE;
    }
    if (def.manufacturer == MFG_REV_ID) {
      return DEVICE_VENDOR_REV;
    }
    return LABEL_UNKNOWN;
  }

  private static String resolveDeviceTypeLabel(DeviceDefinition def) {
    if (def == null) {
      return LABEL_UNKNOWN;
    }
    if (isXboxControllerDevice(def)) {
      return DEVICE_TYPE_XBOX_CONTROLLER;
    }
    if (isLimitSwitch(def)) {
      return DEVICE_TYPE_LIMIT_SWITCH;
    }
    int manufacturer = def.manufacturer != null ? def.manufacturer : DISABLED_CAN_ID;
    int devType = def.deviceType != null ? def.deviceType : DISABLED_CAN_ID;
    String model = safeText(def.model).toUpperCase();
    if (manufacturer == MFG_REV_ID && devType == DEVTYPE_MOTOR_ID) {
      if (model.contains(MODEL_NEO_550)) {
        return DEVICE_TYPE_NEO_550;
      }
      if (model.contains(MODEL_FLEX)) {
        return DEVICE_TYPE_FLEX;
      }
      return DEVICE_TYPE_NEO;
    }
    if (manufacturer == MFG_CTRE_ID && devType == DEVTYPE_MOTOR_ID) {
      if (model.contains(MODEL_FALCON)) {
        return DEVICE_TYPE_FALCON;
      }
      if (model.contains(MODEL_KRAKEN)) {
        return DEVICE_TYPE_KRAKEN;
      }
      return DEVICE_TYPE_KRAKEN;
    }
    if (devType == DEVTYPE_ENCODER_ID) {
      return DEVICE_TYPE_CANCODER;
    }
    if (devType == DEVTYPE_MISC_ID) {
      return DEVICE_TYPE_CANDLE;
    }
    if (devType == DEVTYPE_POWER_ID) {
      return manufacturer == MFG_CTRE_ID ? DEVICE_TYPE_PDP : DEVICE_TYPE_PDH;
    }
    if (devType == DEVTYPE_GYRO_ID) {
      return DEVICE_TYPE_PIGEON;
    }
    if (devType == DEVTYPE_ROBORIO_ID) {
      return DEVICE_TYPE_ROBORIO;
    }
    String name = def.deviceType != null ? getCanDeviceTypeName(def.deviceType) : null;
    return name != null && !name.isBlank() ? name : LABEL_UNKNOWN;
  }

  private static String resolveMotorModel(DeviceDefinition def) {
    if (def == null) {
      return "";
    }
    return safeText(def.model);
  }

  private static String deviceKey(String vendor, String type, int id) {
    String v = safeText(vendor).toUpperCase();
    String t = safeText(type).toUpperCase();
    return v + "|" + t + "|" + id;
  }

  private static int resolveSingletonIdByMfgType(
      List<DeviceDefinition> defs,
      int manufacturer,
      int deviceType) {
    if (defs != null) {
      for (DeviceDefinition def : defs) {
        if (def == null || !isCanDevice(def)) {
          continue;
        }
        int mfg = def.manufacturer != null ? def.manufacturer : DISABLED_CAN_ID;
        int dtype = def.deviceType != null ? def.deviceType : DISABLED_CAN_ID;
        int id = def.id != null ? def.id : DISABLED_CAN_ID;
        if (mfg == manufacturer && dtype == deviceType && isEnabledCanId(id)) {
          return id;
        }
      }
    }
    return DISABLED_CAN_ID;
  }

  private static String safeText(String value) {
    return value == null ? "" : value.trim();
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
    MotorSpec exact = MOTOR_SPECS.get(model);
    if (exact != null) {
      return exact;
    }
    String normalizedModel = normalizeMotorSpecModel(model);
    if (normalizedModel == null || normalizedModel.isBlank()) {
      return null;
    }
    return MOTOR_SPECS.get(normalizedModel);
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
      return MOTOR_SPEC_REV_VORTEX;
    }
    if (upper.contains("NEO 550") || upper.contains("NEO550")) {
      return MOTOR_SPEC_REV_NEO_550;
    }
    if (upper.contains("NEO 2.0") || upper.contains("NEO2")) {
      return MOTOR_SPEC_REV_NEO_2;
    }
    if (upper.contains("NEO")) {
      return MOTOR_SPEC_REV_NEO;
    }
    if (upper.contains("KRAKEN")) {
      return MOTOR_SPEC_CTRE_KRAKEN_X60;
    }
    if (upper.contains("FALCON")) {
      return MOTOR_SPEC_CTRE_FALCON_500;
    }
    return null;
  }

  /**
   * NAME
   *   normalizeMotorSpecModel - Canonicalize one configured motor-model alias for spec lookup.
   *
   * PARAMETERS
   *   modelName - Raw configured or vendor-reported motor model text.
   *
   * RETURNS
   *   Canonical motor-spec model key when recognized, otherwise the original text.
   */
  private static String normalizeMotorSpecModel(String modelName) {
    if (modelName == null) {
      return null;
    }
    String exact = modelName.trim();
    if (exact.isBlank()) {
      return null;
    }
    String inferred = inferMotorModelFromLabel(exact);
    if (inferred != null && !inferred.isBlank()) {
      return inferred;
    }
    return exact;
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
      BringupPrinter.enqueue("Warning: failed to load motor specs: " + ex.getMessage());
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
      BringupPrinter.enqueue("Warning: failed to load CAN mappings: " + ex.getMessage());
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
    List<DeviceDefinition> devices = Collections.emptyList();
    LinkedHashMap<String, ProfileConfig> profiles;
  }

  private static String computeDataHash(String rawJson) {
    JsonElement parsed = JsonParser.parseString(rawJson);
    if (!parsed.isJsonObject()) {
      throw new JsonParseException("profiles JSON root is not an object");
    }
    JsonObject root = parsed.getAsJsonObject();
    root.addProperty("data_hash", "");
    if (root.has(KEY_BRIDGE_CONFIG)) {
      root.remove(KEY_BRIDGE_CONFIG);
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
   *   ProfileConfig - JSON profile entry for device label lists.
   */
  private static final class ProfileConfig {
    List<String> devices = Collections.emptyList();
    @SerializedName(KEY_INPUT_ALIASES)
    Map<String, String> inputAliases = Collections.emptyMap();
    @SerializedName(KEY_DSL_TEST_SET)
    String dslTestSet = "";
    @SerializedName(KEY_LIFECYCLE)
    LifecycleConfig lifecycle = new LifecycleConfig();
  }

  /**
   * NAME
   *   LifecycleConfig - Optional per-profile lifecycle threshold settings.
   */
  private static final class LifecycleConfig {
    @SerializedName(KEY_DISCOVER_THRESHOLD)
    double discoverThreshold = DEFAULT_DISCOVER_THRESHOLD;
    @SerializedName(KEY_LOST_PRESENCE_THRESHOLD)
    double lostPresenceThreshold = DEFAULT_LOST_PRESENCE_THRESHOLD;
  }

  /**
   * NAME
   *   DeviceDefinition - Central device registry entry.
   */
  private static final class DeviceDefinition {
    String label;
    @SerializedName(value = "deviceInterface", alternate = {"interface"})
    String deviceInterface;
    Integer manufacturer;
    Integer deviceType;
    Integer id;
    String model;
    String type;
    Boolean invert;
    List<String> attachments = Collections.emptyList();
    List<String> tags = Collections.emptyList();
    Boolean terminator;
  }

  private static String normalizeKey(String value) {
    if (value == null) {
      return "";
    }
    return value.trim().toUpperCase().replaceAll("[^A-Z0-9]+", "");
  }

  /**
   * NAME
   *   LimitSwitchConfig - Limit switch attachment configuration.
   */
  public static final class LimitSwitchConfig {
    public final String label;
    public final int dio;
    public final boolean invert;

    /**
     * NAME
     *   LimitSwitchConfig - Construct a limit switch config.
     *
     * PARAMETERS
     *   label - Attachment label.
     *   dio - DIO channel.
     *   invert - Whether to invert the raw signal.
     */
    public LimitSwitchConfig(String label, int dio, boolean invert) {
      this.label = label;
      this.dio = dio;
      this.invert = invert;
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
   *   DeviceInstanceKey - Normalized key for runtime device instances.
   */
  private static final class DeviceInstanceKey {
    private final String vendor;
    private final String type;
    private final int id;

    DeviceInstanceKey(String vendor, String type, int id) {
      this.vendor = vendor == null ? "" : vendor.trim().toUpperCase();
      this.type = type == null ? "" : type.trim().toUpperCase();
      this.id = id;
    }

    @Override
    public boolean equals(Object obj) {
      if (this == obj) {
        return true;
      }
      if (obj == null || getClass() != obj.getClass()) {
        return false;
      }
      DeviceInstanceKey other = (DeviceInstanceKey) obj;
      return id == other.id && vendor.equals(other.vendor) && type.equals(other.type);
    }

    @Override
    public int hashCode() {
      int result = vendor.hashCode();
      result = 31 * result + type.hashCode();
      result = 31 * result + id;
      return result;
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
    private final boolean invert;

    /**
     * NAME
     *   DeviceConfig - Construct a device config entry.
     *
     * PARAMETERS
     *   id - CAN device ID.
     *   label - Display label.
     *   motor - Optional motor model override.
     *   limits - Optional limit config.
     *   invert - Optional standalone inversion flag.
     */
    public DeviceConfig(int id, String label, String motor, LimitConfig limits, Boolean invert) {
      this.id = id;
      this.label = label;
      this.motor = motor;
      this.limits = limits != null ? limits : new LimitConfig();
      this.invert = invert != null ? invert.booleanValue() : false;
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

    public boolean isInvert() {
      return invert;
    }
  }

  /**
   * NAME
   *   LimitConfig - Limit switch configuration for a device.
   */
  public static final class LimitConfig {
    public final List<LimitSwitchConfig> switches;

    /**
     * NAME
     *   LimitConfig - Construct with optional limit switches.
     *
     * PARAMETERS
     *   switches - List of configured limit switches.
     */
    public LimitConfig(List<LimitSwitchConfig> switches) {
      this.switches = switches != null ? switches : Collections.emptyList();
    }

    /**
     * NAME
     *   LimitConfig - Construct empty limit config.
     */
    public LimitConfig() {
      this.switches = Collections.emptyList();
    }

    /**
     * NAME
     *   hasSwitches - Return true when any limit switch is configured.
     */
    public boolean hasSwitches() {
      return switches != null && !switches.isEmpty();
    }
  }

  /**
   * NAME
   *   DeviceEntry - Active device entry loaded from profiles.
   */
  public static final class DeviceEntry {
    public final int id;
    public final int manufacturer;
    public final int deviceType;
    public final String deviceInterface;
    public final String vendor;
    public final String type;
    public final String label;
    public final String motor;
    public final LimitConfig limits;
    public final List<String> tags;
    public final Boolean terminator;

    public DeviceEntry(
        int id,
        int manufacturer,
        int deviceType,
        String deviceInterface,
        String vendor,
        String type,
        String label,
        String motor,
        LimitConfig limits,
        List<String> tags,
        Boolean terminator) {
      this.id = id;
      this.manufacturer = manufacturer;
      this.deviceType = deviceType;
      this.deviceInterface = deviceInterface;
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
    return acquireDioInput(channel);
  }

  /**
   * NAME
   *   ensureDioInputs - Ensure DIO inputs exist for configured limit switches.
   *
   * PARAMETERS
   *   inputs - Existing DIO inputs list (may be empty).
   *   switches - Configured limit switch list.
   *
   * RETURNS
   *   The updated input list sized to match the switch count.
   *
   * SIDE EFFECTS
   *   Allocates new DigitalInput instances as needed.
   */
  public static List<DigitalInput> ensureDioInputs(
      List<DigitalInput> inputs,
      List<LimitSwitchConfig> switches) {
    List<DigitalInput> resolved = inputs != null ? inputs : new ArrayList<>();
    if (switches == null) {
      return resolved;
    }
    while (resolved.size() < switches.size()) {
      resolved.add(null);
    }
    for (int i = 0; i < switches.size(); i++) {
      LimitSwitchConfig spec = switches.get(i);
      int channel = spec != null ? spec.dio : DISABLED_CAN_ID;
      DigitalInput existing = resolved.get(i);
      if (channel < 0) {
        if (existing != null) {
          releaseDioInput(existing);
          resolved.set(i, null);
        }
        continue;
      }
      Integer currentChannel = channelForDioInput(existing);
      if (currentChannel != null && currentChannel != channel) {
        releaseDioInput(existing);
        existing = null;
      }
      resolved.set(i, ensureDioInput(existing, channel));
    }
    if (resolved.size() > switches.size()) {
      for (int i = switches.size(); i < resolved.size(); i++) {
        releaseDioInput(resolved.get(i));
      }
      resolved.subList(switches.size(), resolved.size()).clear();
    }
    return resolved;
  }

  /**
   * NAME
   *   closeInputs - Close and clear a list of DIO inputs.
   *
   * PARAMETERS
   *   inputs - Input list to close (may be null).
   */
  public static void closeInputs(List<DigitalInput> inputs) {
    if (inputs == null) {
      return;
    }
    for (DigitalInput input : inputs) {
      releaseDioInput(input);
    }
    inputs.clear();
  }

  /**
   * NAME
   *   acquireDioInput - Get a shared DigitalInput for a DIO channel.
   *
   * PARAMETERS
   *   channel - DIO channel number (>=0).
   *
   * RETURNS
   *   Shared DigitalInput instance for the channel.
   *
   * SIDE EFFECTS
   *   Allocates and reference-counts the DIO input.
   */
  private static DigitalInput acquireDioInput(int channel) {
    synchronized (DIO_INPUT_LOCK) {
      DigitalInput input = DIO_INPUTS.get(channel);
      if (input == null) {
        input = new DigitalInput(channel);
        DIO_INPUTS.put(channel, input);
        DIO_INPUT_CHANNELS.put(input, channel);
        DIO_INPUT_REFCOUNT.put(channel, DIO_REFCOUNT_ZERO);
      }
      int count = DIO_INPUT_REFCOUNT.getOrDefault(channel, DIO_REFCOUNT_ZERO);
      DIO_INPUT_REFCOUNT.put(channel, count + DIO_REFCOUNT_INCREMENT);
      return input;
    }
  }

  /**
   * NAME
   *   releaseDioInput - Release a shared DigitalInput reference.
   *
   * PARAMETERS
   *   input - Shared DigitalInput instance.
   *
   * SIDE EFFECTS
   *   Decrements the reference count and closes when the count reaches zero.
   */
  private static void releaseDioInput(DigitalInput input) {
    if (input == null) {
      return;
    }
    synchronized (DIO_INPUT_LOCK) {
      Integer channel = DIO_INPUT_CHANNELS.get(input);
      if (channel == null) {
        closeIfPossible(input);
        return;
      }
      int count = DIO_INPUT_REFCOUNT.getOrDefault(channel, DIO_REFCOUNT_ZERO);
      if (count <= DIO_REFCOUNT_ONE) {
        DIO_INPUT_REFCOUNT.remove(channel);
        DIO_INPUTS.remove(channel);
        DIO_INPUT_CHANNELS.remove(input);
        closeIfPossible(input);
        return;
      }
      DIO_INPUT_REFCOUNT.put(channel, count - DIO_REFCOUNT_INCREMENT);
    }
  }

  /**
   * NAME
   *   channelForDioInput - Lookup the channel for a shared DigitalInput.
   *
   * PARAMETERS
   *   input - Shared DigitalInput instance.
   *
   * RETURNS
   *   Channel number or null when unknown.
   */
  private static Integer channelForDioInput(DigitalInput input) {
    if (input == null) {
      return null;
    }
    synchronized (DIO_INPUT_LOCK) {
      return DIO_INPUT_CHANNELS.get(input);
    }
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
   *   acquireSharedDioInput - Acquire a shared DIO input for a standalone device.
   *
   * PARAMETERS
   *   channel - DIO channel number.
   *
   * RETURNS
   *   Shared DigitalInput instance.
   */
  public static DigitalInput acquireSharedDioInput(int channel) {
    return acquireDioInput(channel);
  }

  /**
   * NAME
   *   releaseSharedDioInput - Release a shared DIO input for a standalone device.
   *
   * PARAMETERS
   *   input - Shared DigitalInput instance.
   */
  public static void releaseSharedDioInput(DigitalInput input) {
    releaseDioInput(input);
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
