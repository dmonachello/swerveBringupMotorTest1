package frc.robot;

import com.ctre.phoenix6.hardware.TalonFX;
import com.google.gson.Gson;
import com.google.gson.JsonParseException;
import com.google.gson.annotations.SerializedName;
import com.revrobotics.spark.SparkMax;
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
  
  private static final int[] FALLBACK_ROBOT_NEO_CAN_IDS = { 10, 1, 7, 4 };
  private static final int[] FALLBACK_ROBOT_KRAKEN_CAN_IDS = { 11, 2, 8, 5 };
  private static final int[] FALLBACK_ROBOT_CANCODER_CAN_IDS = { 12, 3, 9, 6 };

  private static final int[] FALLBACK_DEMO_NEO_CAN_IDS = { 25, 22, 10, -1 };
  private static final int[] FALLBACK_DEMO_KRAKEN_CAN_IDS = { -1, -1, -1, -1 };
  private static final int[] FALLBACK_DEMO_CANCODER_CAN_IDS = { -1, -1, -1, -1 };

  private static final int FALLBACK_PDH_CAN_ID = 1;
  private static final int FALLBACK_PIGEON_CAN_ID = 1;

  private static final String DEFAULT_PROFILE_NAME = "robot";
  private static final String DEFAULT_PROFILE_FILE = "bringup_profiles.json";

  private static final Gson GSON = new Gson();

  private static Map<String, CanProfileConfig> profiles = new LinkedHashMap<>();
  private static List<String> profileOrder = new ArrayList<>();
  private static String defaultProfile = DEFAULT_PROFILE_NAME;

  private static String activeProfile = DEFAULT_PROFILE_NAME;

  public static int[] NEO_CAN_IDS = FALLBACK_ROBOT_NEO_CAN_IDS;
  public static int[] KRAKEN_CAN_IDS = FALLBACK_ROBOT_KRAKEN_CAN_IDS;
  public static int[] FALCON_CAN_IDS = new int[0];
  public static int[] CANCODER_CAN_IDS = FALLBACK_ROBOT_CANCODER_CAN_IDS;
  public static int PDH_CAN_ID = FALLBACK_PDH_CAN_ID;
  public static int PIGEON_CAN_ID = FALLBACK_PIGEON_CAN_ID;
  public static final int DISABLED_CAN_ID = -1;
  public static final double DEADBAND = 0.12;

  static {
    loadProfilesFromJson();
    setActiveCanProfile(activeProfile);
  }

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

  public static void setActiveCanProfile(String profileName) {
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
    KRAKEN_CAN_IDS = toIdArray(config.krakens);
    FALCON_CAN_IDS = toIdArray(config.falcons);
    CANCODER_CAN_IDS = toIdArray(config.cancoders);
    PDH_CAN_ID = config.pdh != null ? config.pdh.id : DISABLED_CAN_ID;
    PIGEON_CAN_ID = config.pigeon != null ? config.pigeon.id : DISABLED_CAN_ID;
    activeProfile = profileName;
  }

  public static void toggleCanProfile() {
    if (profileOrder.isEmpty()) {
      return;
    }
    int index = profileOrder.indexOf(activeProfile);
    int nextIndex = (index < 0 ? 0 : (index + 1) % profileOrder.size());
    setActiveCanProfile(profileOrder.get(nextIndex));
  }

  public static String getActiveCanProfile() {
    return activeProfile;
  }

  public static String getActiveCanProfileLabel() {
    return activeProfile;
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

  public static void setAllFalcons(TalonFX[] falcons, double speed) {
    for (int i = 0; i < falcons.length; i++) {
      if (falcons[i] != null) {
        falcons[i].set(speed);
      }
    }
  }

  public static void stopAll(SparkMax[] neos, TalonFX[] krakens, TalonFX[] falcons) {
    setAllNeos(neos, 0.0);
    setAllKrakens(krakens, 0.0);
    setAllFalcons(falcons, 0.0);
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

  public static void applyProfileFromArgs() {
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

  private static void loadProfilesFromJson() {
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

  private static Path resolveProfilePath() {
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

  private static void applyFallbackProfile() {
    profiles = new LinkedHashMap<>();
    profiles.put("robot", new CanProfileConfig(
        toDevices(FALLBACK_ROBOT_NEO_CAN_IDS),
        toDevices(FALLBACK_ROBOT_KRAKEN_CAN_IDS),
        Collections.emptyList(),
        toDevices(FALLBACK_ROBOT_CANCODER_CAN_IDS),
        new DeviceRef(FALLBACK_PDH_CAN_ID),
        new DeviceRef(FALLBACK_PIGEON_CAN_ID)));
    profiles.put("demo_club", new CanProfileConfig(
        toDevices(FALLBACK_DEMO_NEO_CAN_IDS),
        toDevices(FALLBACK_DEMO_KRAKEN_CAN_IDS),
        Collections.emptyList(),
        toDevices(FALLBACK_DEMO_CANCODER_CAN_IDS),
        null,
        null));
    profiles.put("demo_home", new CanProfileConfig(
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.emptyList(),
        null,
        null));
    profileOrder = new ArrayList<>(profiles.keySet());
    defaultProfile = DEFAULT_PROFILE_NAME;
    activeProfile = defaultProfile;
    NEO_CAN_IDS = FALLBACK_ROBOT_NEO_CAN_IDS;
    KRAKEN_CAN_IDS = FALLBACK_ROBOT_KRAKEN_CAN_IDS;
    FALCON_CAN_IDS = new int[0];
    CANCODER_CAN_IDS = FALLBACK_ROBOT_CANCODER_CAN_IDS;
    PDH_CAN_ID = FALLBACK_PDH_CAN_ID;
    PIGEON_CAN_ID = FALLBACK_PIGEON_CAN_ID;
  }

  private static int[] toIdArray(List<DeviceRef> refs) {
    if (refs == null || refs.isEmpty()) {
      return new int[0];
    }
    int[] ids = new int[refs.size()];
    for (int i = 0; i < refs.size(); i++) {
      ids[i] = refs.get(i).id;
    }
    return ids;
  }

  private static List<DeviceRef> toDevices(int[] ids) {
    List<DeviceRef> refs = new ArrayList<>();
    for (int id : ids) {
      if (isEnabledCanId(id)) {
        refs.add(new DeviceRef(id));
      }
    }
    return refs;
  }

  private static final class ProfileRoot {
    @SerializedName("default_profile")
    String defaultProfile;
    LinkedHashMap<String, CanProfileConfig> profiles;
  }

  private static final class CanProfileConfig {
    List<DeviceRef> neos = Collections.emptyList();
    List<DeviceRef> krakens = Collections.emptyList();
    List<DeviceRef> falcons = Collections.emptyList();
    List<DeviceRef> cancoders = Collections.emptyList();
    DeviceRef pdh;
    DeviceRef pigeon;

    CanProfileConfig(
        List<DeviceRef> neos,
        List<DeviceRef> krakens,
        List<DeviceRef> falcons,
        List<DeviceRef> cancoders,
        DeviceRef pdh,
        DeviceRef pigeon) {
      this.neos = neos != null ? neos : Collections.emptyList();
      this.krakens = krakens != null ? krakens : Collections.emptyList();
      this.falcons = falcons != null ? falcons : Collections.emptyList();
      this.cancoders = cancoders != null ? cancoders : Collections.emptyList();
      this.pdh = pdh;
      this.pigeon = pigeon;
    }
  }

  private static final class DeviceRef {
    int id;

    DeviceRef(int id) {
      this.id = id;
    }
  }
}
