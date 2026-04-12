package frc.robot.tests;

import frc.robot.BringupPrinter;
import frc.robot.BringupUtil;
import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.annotations.SerializedName;
import java.io.InputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * NAME
 *   BringupTestRegistry - Load and persist bringup tests from JSON.
 *
 * DESCRIPTION
 *   Handles reading tests from bringup_system.json bridgeConfig entries,
 *   selecting test sets, and saving test enable state.
 */
public final class BringupTestRegistry {
  private static final String KEY_BRIDGE_CONFIG = "bridgeConfig";
  private static final String KEY_BRIDGE_BY_PROFILE = "byProfile";
  private static final String KEY_BRIDGE_TESTS = "tests";
  private static final String TESTS_SOURCE_REGISTRY = "registry";
  private static final Gson GSON = new Gson();
  private static boolean usingTestSets = false;
  private static String activeTestSetName = null;

  private BringupTestRegistry() {}

  /**
   * NAME
   *   loadTests - Load bringup tests from JSON.
   *
   * RETURNS
   *   List of BringupTest instances.
   */
  public static List<BringupTest> loadTests() {
    TestRootLoad root = loadTestsRoot();
    if (root == null) {
      return Collections.emptyList();
    }
    List<TestEntry> entries = selectTestEntries(root);
    if (entries == null || entries.isEmpty()) {
      return Collections.emptyList();
    }
    List<BringupTest> tests = new ArrayList<>();
    for (TestEntry entry : entries) {
      BringupTest test = buildTest(entry);
      if (test != null) {
        tests.add(test);
      }
    }
    return tests;
  }

  /**
   * NAME
   *   loadTestsRoot - Load tests payload from override or registry.
   */
  private static TestRootLoad loadTestsRoot() {
    return loadTestsRootFromRegistry();
  }

  /**
   * NAME
   *   loadTestsRootFromRegistry - Load tests payload from in-memory registry.
   */
  private static TestRootLoad loadTestsRootFromRegistry() {
    JsonElement payload = BringupUtil.getProfileTestsPayload(BringupUtil.getActiveCanProfile());
    if (payload != null && payload.isJsonObject()) {
      return GSON.fromJson(payload, TestRootLoad.class);
    }
    return null;
  }

  /**
   * NAME
   *   loadTestsRootFromRegistryObject - Load tests payload from bringup_system.json root.
   */
  private static TestRootLoad loadTestsRootFromRegistryObject(JsonObject root) {
    if (root == null) {
      return null;
    }
    JsonElement bridgeElement = root.get(KEY_BRIDGE_CONFIG);
    if (bridgeElement == null || !bridgeElement.isJsonObject()) {
      return null;
    }
    JsonObject bridge = bridgeElement.getAsJsonObject();
    JsonElement byProfileElement = bridge.get(KEY_BRIDGE_BY_PROFILE);
    if (byProfileElement == null || !byProfileElement.isJsonObject()) {
      return null;
    }
    JsonObject byProfile = byProfileElement.getAsJsonObject();
    String profileName = BringupUtil.getActiveCanProfile();
    if (profileName == null || profileName.isBlank()) {
      return null;
    }
    JsonElement profileElement = byProfile.get(profileName);
    if (profileElement == null || !profileElement.isJsonObject()) {
      return null;
    }
    JsonObject profile = profileElement.getAsJsonObject();
    JsonElement testsElement = profile.get(KEY_BRIDGE_TESTS);
    if (testsElement == null || !testsElement.isJsonObject()) {
      return null;
    }
    return GSON.fromJson(testsElement, TestRootLoad.class);
  }

  /**
   * NAME
   *   getTestsInfo - Gather metadata about tests payload.
   */
  public static TestsInfo getTestsInfo() {
    TestsInfo info = new TestsInfo();
    info.profileName = BringupUtil.getActiveCanProfile();
    TestRootLoad root = null;
    info.source = TESTS_SOURCE_REGISTRY;
    Path profilePath = BringupUtil.getProfilePath();
    info.path = profilePath;
    info.exists = profilePath != null && Files.exists(profilePath);
    if (info.exists && profilePath != null) {
      try {
        info.sizeBytes = Files.size(profilePath);
        info.lastModifiedMs = Files.getLastModifiedTime(profilePath).toMillis();
        info.sha256 = hashFile(profilePath);
      } catch (IOException ex) {
        info.readError = ex.getMessage();
      }
    }
    root = loadTestsRootFromRegistry();
    if (root != null && root.testSets != null && !root.testSets.isEmpty()) {
      info.usingTestSets = true;
      info.activeTestSetName = resolveActiveSetName(root);
      info.defaultTestSetName = root.defaultTestSet;
      info.testSetCount = root.testSets.size();
      List<TestEntry> entries = root.testSets.get(info.activeTestSetName);
      if (entries != null) {
        info.testCount = entries.size();
      }
    } else if (root != null && root.tests != null) {
      info.usingTestSets = false;
      info.testCount = root.tests.size();
    }
    return info;
  }

  /**
   * NAME
   *   saveTests - Persist bringup tests to JSON.
   *
   * DESCRIPTION
   *   Writes tests into bringup_system.json under bridgeConfig.byProfile.
   *
   * PARAMETERS
   *   tests - List of tests to serialize.
   *
   * RETURNS
   *   True on successful write.
   */
  public static boolean saveTests(List<BringupTest> tests) {
    if (tests == null) {
      return false;
    }
    List<Map<String, Object>> entries = new ArrayList<>();
    for (BringupTest test : tests) {
      if (test instanceof CompositeTest composite) {
        entries.add(composite.toEntry());
      } else if (test instanceof JoystickTest joystick) {
        entries.add(joystick.toEntry());
      } else if (test instanceof DeadbandSweepTest sweep) {
        entries.add(sweep.toEntry());
      } else if (test instanceof DeviceActionTest deviceAction) {
        entries.add(deviceAction.toEntry());
      }
    }
    try {
      TestRootSave root = new TestRootSave();
      if (usingTestSets) {
        TestRootLoad existing = loadTestsRootFromRegistry();
        String setName = resolveSaveSetName(existing);
        Map<String, List<TestEntry>> sets = new java.util.LinkedHashMap<>();
        if (existing != null && existing.testSets != null && !existing.testSets.isEmpty()) {
          sets.putAll(existing.testSets);
        }
        sets.put(setName, toTestEntries(entries));
        root.testSets = sets;
        root.defaultTestSet = resolveDefaultTestSet(existing, setName);
      } else {
        root.tests = entries;
      }
      String profileName = BringupUtil.getActiveCanProfile();
      if (profileName == null || profileName.isBlank()) {
        return false;
      }
      Path path = BringupUtil.getProfilePath();
      if (path == null || !Files.exists(path)) {
        return false;
      }
      String rawJson = Files.readString(path, StandardCharsets.UTF_8);
      JsonElement parsed = JsonParser.parseString(rawJson);
      if (parsed == null || !parsed.isJsonObject()) {
        return false;
      }
      JsonObject rootObj = parsed.getAsJsonObject();
      JsonObject bridge = rootObj.has(KEY_BRIDGE_CONFIG)
          && rootObj.get(KEY_BRIDGE_CONFIG).isJsonObject()
          ? rootObj.getAsJsonObject(KEY_BRIDGE_CONFIG)
          : new JsonObject();
      JsonObject byProfile = bridge.has(KEY_BRIDGE_BY_PROFILE)
          && bridge.get(KEY_BRIDGE_BY_PROFILE).isJsonObject()
          ? bridge.getAsJsonObject(KEY_BRIDGE_BY_PROFILE)
          : new JsonObject();
      JsonObject profile = byProfile.has(profileName)
          && byProfile.get(profileName).isJsonObject()
          ? byProfile.getAsJsonObject(profileName)
          : new JsonObject();
      JsonElement testsElement = GSON.toJsonTree(root);
      profile.add(KEY_BRIDGE_TESTS, testsElement);
      byProfile.add(profileName, profile);
      bridge.add(KEY_BRIDGE_BY_PROFILE, byProfile);
      rootObj.add(KEY_BRIDGE_CONFIG, bridge);
      String updated = GSON.toJson(rootObj);
      Files.writeString(path, updated + System.lineSeparator(), StandardCharsets.UTF_8);
      BringupUtil.updateProfileTests(profileName, testsElement);
      return true;
    } catch (IOException ex) {
      BringupPrinter.enqueue("Warning: failed to write bringup tests JSON: " + ex.getMessage());
      return false;
    }
  }

  /**
   * NAME
   *   buildTest - Instantiate a test from a JSON entry.
   */
  private static BringupTest buildTest(TestEntry entry) {
    if (entry == null || entry.type == null) {
      return null;
    }
    if (CompositeTest.TYPE.equalsIgnoreCase(entry.type)) {
      return buildComposite(entry);
    }
    if (JoystickTest.TYPE.equalsIgnoreCase(entry.type)) {
      return buildJoystick(entry);
    }
    if (DeadbandSweepTest.TYPE.equalsIgnoreCase(entry.type)) {
      return buildDeadbandSweep(entry);
    }
    if (DeviceActionTest.TYPE.equalsIgnoreCase(entry.type)) {
      return buildDeviceAction(entry);
    }
    BringupPrinter.enqueue("Warning: unknown test type '" + entry.type + "'.");
    return null;
  }

  /**
   * NAME
   *   selectTestEntries - Select test entries from the active set.
   */
  private static List<TestEntry> selectTestEntries(TestRootLoad root) {
    if (root.testSets != null && !root.testSets.isEmpty()) {
      usingTestSets = true;
      String setName = resolveActiveSetName(root);
      activeTestSetName = setName;
      List<TestEntry> entries = root.testSets.get(setName);
      if (entries != null) {
        return entries;
      }
      for (List<TestEntry> fallback : root.testSets.values()) {
        if (fallback != null && !fallback.isEmpty()) {
          return fallback;
        }
      }
      return Collections.emptyList();
    }
    usingTestSets = false;
    activeTestSetName = null;
    return root.tests != null ? root.tests : Collections.emptyList();
  }

  /**
   * NAME
   *   resolveActiveSetName - Resolve which test set to use.
   */
  private static String resolveActiveSetName(TestRootLoad root) {
    if (root == null || root.testSets == null || root.testSets.isEmpty()) {
      return null;
    }
    if (root.defaultTestSet != null && root.testSets.containsKey(root.defaultTestSet)) {
      return root.defaultTestSet;
    }
    if (root.testSets.containsKey("default")) {
      return "default";
    }
    return root.testSets.keySet().iterator().next();
  }

  /**
   * NAME
   *   resolveSaveSetName - Resolve which set name to save into.
   */
  private static String resolveSaveSetName(TestRootLoad root) {
    if (activeTestSetName != null && !activeTestSetName.isBlank()) {
      return activeTestSetName;
    }
    String resolved = resolveActiveSetName(root);
    if (resolved != null && !resolved.isBlank()) {
      return resolved;
    }
    return "default";
  }

  /**
   * NAME
   *   resolveDefaultTestSet - Resolve the default test set name to save.
   */
  private static String resolveDefaultTestSet(TestRootLoad root, String fallback) {
    if (root != null && root.defaultTestSet != null && !root.defaultTestSet.isBlank()) {
      return root.defaultTestSet;
    }
    return fallback;
  }

  /**
   * NAME
   *   toTestEntries - Convert raw map entries into typed TestEntry list.
   */
  private static List<TestEntry> toTestEntries(List<Map<String, Object>> entries) {
    if (entries == null) {
      return Collections.emptyList();
    }
    List<TestEntry> converted = new ArrayList<>();
    for (Map<String, Object> entry : entries) {
      String json = GSON.toJson(entry);
      TestEntry parsed = GSON.fromJson(json, TestEntry.class);
      if (parsed != null) {
        converted.add(parsed);
      }
    }
    return converted;
  }

  /**
   * NAME
   *   buildComposite - Build a CompositeTest from a JSON entry.
   */
  private static BringupTest buildComposite(TestEntry entry) {
    CompositeTest.Config config = new CompositeTest.Config();
    config.name = entry.name != null ? entry.name : config.name;
    config.enabled = entry.enabled != null ? entry.enabled.booleanValue() : config.enabled;
    config.duty = entry.duty != null ? entry.duty.doubleValue() : config.duty;
    if (entry.motorLabels != null && !entry.motorLabels.isEmpty()) {
      config.motorLabels = new java.util.ArrayList<>(entry.motorLabels);
    }
    if (entry.rotation != null) {
      config.rotation = entry.rotation;
      if (config.rotation.encoderKey == null && entry.encoderKey != null) {
        config.rotation.encoderKey = entry.encoderKey;
      }
      if (config.rotation.encoderSource == null && entry.encoderSource != null) {
        config.rotation.encoderSource = entry.encoderSource;
      }
      if (config.rotation.encoderCountsPerRev == null && entry.encoderCountsPerRev != null) {
        config.rotation.encoderCountsPerRev = entry.encoderCountsPerRev;
      }
      if (config.rotation.encoderMotorIndex < 0) {
        config.rotation.encoderMotorIndex = 0;
      }
    } else if (entry.limitRot != null || entry.encoderKey != null) {
      CompositeTest.RotationCheck rotation = new CompositeTest.RotationCheck();
      rotation.limitRot = entry.limitRot != null ? entry.limitRot.doubleValue() : rotation.limitRot;
      rotation.encoderKey = entry.encoderKey != null ? entry.encoderKey : rotation.encoderKey;
      rotation.encoderSource = entry.encoderSource != null ? entry.encoderSource : rotation.encoderSource;
      rotation.encoderCountsPerRev = entry.encoderCountsPerRev;
      rotation.encoderMotorIndex = entry.encoderMotorIndex != null ? entry.encoderMotorIndex.intValue() : 0;
      config.rotation = rotation;
    }
    if (entry.time != null) {
      config.time = entry.time;
      if (config.time.onTimeout == null) {
        config.time.onTimeout = "pass";
      }
    } else if (entry.timeoutSec != null || entry.durationSec != null) {
      CompositeTest.TimeCheck time = new CompositeTest.TimeCheck();
      double timeout = entry.timeoutSec != null ? entry.timeoutSec.doubleValue() : 0.0;
      double duration = entry.durationSec != null ? entry.durationSec.doubleValue() : 0.0;
      time.timeoutSec = timeout > 0.0 ? timeout : duration;
      config.time = time;
    }
    if (entry.limitSwitch != null) {
      config.limitSwitch = entry.limitSwitch;
      if (config.limitSwitch.onHit == null) {
        config.limitSwitch.onHit = "pass";
      }
    }
    if (entry.hold != null) {
      config.hold = entry.hold;
      if (config.hold.onRelease == null) {
        config.hold.onRelease = "pass";
      }
    }
    return new CompositeTest(config);
  }

  /**
   * NAME
   *   buildDeadbandSweep - Build a DeadbandSweepTest from a JSON entry.
   */
  private static BringupTest buildDeadbandSweep(TestEntry entry) {
    DeadbandSweepTest.Config config = new DeadbandSweepTest.Config();
    config.name = entry.name != null ? entry.name : config.name;
    config.enabled = entry.enabled != null ? entry.enabled.booleanValue() : config.enabled;
    if (entry.motorLabels != null && !entry.motorLabels.isEmpty()) {
      config.motorLabels = new ArrayList<>(entry.motorLabels);
    }
    if (entry.deadbandSweep != null) {
      DeadbandSweepTest.SweepConfig sweep = entry.deadbandSweep;
      config.startDuty = sweep.startDuty;
      config.maxDuty = sweep.maxDuty;
      config.stepDuty = sweep.stepDuty;
      config.stepHoldSec = sweep.stepHoldSec;
      config.motionThresholdRot = sweep.motionThresholdRot;
      config.requiredSamples = sweep.requiredSamples;
      config.encoderKey = sweep.encoderKey != null ? sweep.encoderKey : config.encoderKey;
      config.encoderSource = sweep.encoderSource;
      config.encoderCountsPerRev = sweep.encoderCountsPerRev;
      config.encoderMotorIndex = sweep.encoderMotorIndex;
    }
    return new DeadbandSweepTest(config);
  }

  /**
   * NAME
   *   buildDeviceAction - Build a DeviceActionTest from a JSON entry.
   */
  private static BringupTest buildDeviceAction(TestEntry entry) {
    DeviceActionTest.Config config = new DeviceActionTest.Config();
    config.name = entry.name != null ? entry.name : config.name;
    config.enabled = entry.enabled != null ? entry.enabled.booleanValue() : config.enabled;
    if (entry.motorLabels != null && !entry.motorLabels.isEmpty()) {
      config.deviceLabels = new ArrayList<>(entry.motorLabels);
    }
    config.action = entry.action;
    config.color = entry.color;
    config.pattern = entry.pattern;
    config.brightness = entry.brightness;
    config.durationSec = entry.durationSec;
    return new DeviceActionTest(config);
  }

  /**
   * NAME
   *   buildJoystick - Build a JoystickTest from a JSON entry.
   */
  private static BringupTest buildJoystick(TestEntry entry) {
    JoystickTest.Config config = new JoystickTest.Config();
    config.name = entry.name != null ? entry.name : config.name;
    config.enabled = entry.enabled != null ? entry.enabled.booleanValue() : config.enabled;
    config.deadband = entry.deadband != null ? entry.deadband.doubleValue() : config.deadband;
    if (entry.inputSource != null && !entry.inputSource.isBlank()) {
      config.inputSource = entry.inputSource;
    } else {
      config.inputSource = null;
      config.enabled = false;
      BringupPrinter.enqueue("Warning: joystick test '" + config.name + "' missing inputSource; disabled.");
    }
    if (entry.motorLabels != null && !entry.motorLabels.isEmpty()) {
      config.motorLabels = new java.util.ArrayList<>(entry.motorLabels);
    }
    return new JoystickTest(config);
  }

  /**
   * NAME
   *   hashFile - Compute SHA-256 for a file.
   */
  private static String hashFile(Path path) throws IOException {
    MessageDigest digest;
    try {
      digest = MessageDigest.getInstance("SHA-256");
    } catch (NoSuchAlgorithmException ex) {
      return "unavailable";
    }
    try (InputStream input = Files.newInputStream(path)) {
      byte[] buffer = new byte[8192];
      int read;
      while ((read = input.read(buffer)) > 0) {
        digest.update(buffer, 0, read);
      }
    }
    byte[] hash = digest.digest();
    StringBuilder sb = new StringBuilder(hash.length * 2);
    for (byte b : hash) {
      sb.append(String.format("%02x", b));
    }
    return sb.toString();
  }

  /**
   * NAME
   *   TestsInfo - Summary metadata for tests payload.
   */
  public static final class TestsInfo {
    public Path path;
    public String profileName;
    public String source;
    public boolean exists;
    public boolean usingTestSets;
    public String activeTestSetName;
    public String defaultTestSetName;
    public int testSetCount;
    public int testCount;
    public long sizeBytes;
    public long lastModifiedMs;
    public String sha256;
    public String readError;

    private TestsInfo() {}
  }

  /**
   * NAME
   *   TestRootLoad - JSON root for loading tests.
   */
  private static final class TestRootLoad {
    @SerializedName(value = "default_test_set", alternate = {"defaultTestSet"})
    String defaultTestSet;
    @SerializedName(value = "test_sets", alternate = {"testSets"})
    Map<String, List<TestEntry>> testSets;
    List<TestEntry> tests = Collections.emptyList();
  }

  /**
   * NAME
   *   TestRootSave - JSON root for saving tests.
   */
  private static final class TestRootSave {
    @SuppressWarnings("unused")
    List<Map<String, Object>> tests = Collections.emptyList();
    @SerializedName(value = "default_test_set", alternate = {"defaultTestSet"})
    String defaultTestSet;
    @SerializedName(value = "test_sets", alternate = {"testSets"})
    Map<String, List<TestEntry>> testSets = Collections.emptyMap();
  }

  /**
   * NAME
   *   TestEntry - JSON test entry schema.
   */
  private static final class TestEntry {
    String type;
    String name;
    Boolean enabled;
    Double duty;
    Double limitRot;
    Double timeoutSec;
    Double durationSec;
    List<String> motorLabels;
    String encoderKey;
    String encoderSource;
    Integer encoderCountsPerRev;
    CompositeTest.RotationCheck rotation;
    CompositeTest.TimeCheck time;
    CompositeTest.LimitSwitchCheck limitSwitch;
    CompositeTest.HoldCheck hold;
    DeadbandSweepTest.SweepConfig deadbandSweep;
    Double deadband;
    String inputSource;
    Integer encoderMotorIndex;
    String action;
    String color;
    String pattern;
    Double brightness;
  }

}
