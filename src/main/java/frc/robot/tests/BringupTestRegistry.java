package frc.robot.tests;

import com.google.gson.Gson;
import com.google.gson.JsonParseException;
import com.google.gson.annotations.SerializedName;
import edu.wpi.first.wpilibj.Filesystem;
import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

public final class BringupTestRegistry {
  private static final String TESTS_FILE = "bringup_tests.json";
  private static final Gson GSON = new Gson();
  private static String overrideTestsPath = null;
  private static boolean usingTestSets = false;
  private static String activeTestSetName = null;

  private BringupTestRegistry() {}

  public static List<BringupTest> loadTests() {
    Path path = resolveTestsPath();
    if (path == null || !Files.exists(path)) {
      return Collections.emptyList();
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      TestRootLoad root = GSON.fromJson(reader, TestRootLoad.class);
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
    } catch (IOException | JsonParseException ex) {
      System.out.println("Warning: failed to read bringup tests JSON: " + ex.getMessage());
      return Collections.emptyList();
    }
  }

  public static void setOverrideTestsPath(String path) {
    if (path == null || path.isBlank()) {
      overrideTestsPath = null;
    } else {
      overrideTestsPath = path.trim();
    }
  }

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
      }
    }
    Path path = resolveTestsPath();
    if (path == null) {
      return false;
    }
    try {
      TestRootSave root = new TestRootSave();
      if (usingTestSets) {
        TestRootLoad existing = readRoot(path);
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
      String json = GSON.toJson(root);
      Files.writeString(path, json + System.lineSeparator(), StandardCharsets.UTF_8);
      return true;
    } catch (IOException ex) {
      System.out.println("Warning: failed to write bringup tests JSON: " + ex.getMessage());
      return false;
    }
  }

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
    System.out.println("Warning: unknown test type '" + entry.type + "'.");
    return null;
  }

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

  private static String resolveDefaultTestSet(TestRootLoad root, String fallback) {
    if (root != null && root.defaultTestSet != null && !root.defaultTestSet.isBlank()) {
      return root.defaultTestSet;
    }
    return fallback;
  }

  private static TestRootLoad readRoot(Path path) {
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      return GSON.fromJson(reader, TestRootLoad.class);
    } catch (IOException | JsonParseException ex) {
      return null;
    }
  }

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

  private static BringupTest buildComposite(TestEntry entry) {
    CompositeTest.Config config = new CompositeTest.Config();
    config.name = entry.name != null ? entry.name : config.name;
    config.enabled = entry.enabled != null ? entry.enabled.booleanValue() : config.enabled;
    config.duty = entry.duty != null ? entry.duty.doubleValue() : config.duty;
    if (entry.motorKeys != null && !entry.motorKeys.isEmpty()) {
      java.util.List<MotorRef> refs = new java.util.ArrayList<>();
      for (String key : entry.motorKeys) {
        MotorRef ref = parseDeviceRef(key);
        if (ref != null) {
          refs.add(ref);
        }
      }
      config.motors = refs;
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

  private static BringupTest buildJoystick(TestEntry entry) {
    JoystickTest.Config config = new JoystickTest.Config();
    config.name = entry.name != null ? entry.name : config.name;
    config.enabled = entry.enabled != null ? entry.enabled.booleanValue() : config.enabled;
    config.deadband = entry.deadband != null ? entry.deadband.doubleValue() : config.deadband;
    config.inputAxis = entry.inputAxis != null ? entry.inputAxis : config.inputAxis;
    if (entry.motorKeys != null && !entry.motorKeys.isEmpty()) {
      java.util.List<MotorRef> refs = new java.util.ArrayList<>();
      for (String key : entry.motorKeys) {
        MotorRef ref = parseDeviceRef(key);
        if (ref != null) {
          refs.add(ref);
        }
      }
      config.motors = refs;
    }
    return new JoystickTest(config);
  }

  private static Path resolveTestsPath() {
    if (overrideTestsPath != null && !overrideTestsPath.isBlank()) {
      Path override = resolveOverridePath(overrideTestsPath);
      if (override != null && Files.exists(override)) {
        return override;
      }
      System.out.println("Warning: bringup tests override not found: " + overrideTestsPath);
    }
    try {
      Path deployPath = Filesystem.getDeployDirectory().toPath().resolve(TESTS_FILE);
      if (Files.exists(deployPath)) {
        return deployPath;
      }
    } catch (Exception ex) {
      // Fall through to local dev path.
    }
    Path devPath = Paths.get("src", "main", "deploy", TESTS_FILE);
    if (Files.exists(devPath)) {
      return devPath;
    }
    return Paths.get(TESTS_FILE);
  }

  private static Path resolveOverridePath(String path) {
    try {
      Path candidate = Paths.get(path);
      if (candidate.isAbsolute()) {
        return candidate;
      }
      try {
        Path deployPath = Filesystem.getDeployDirectory().toPath().resolve(candidate);
        if (Files.exists(deployPath)) {
          return deployPath;
        }
      } catch (Exception ex) {
        // Fall through to dev path.
      }
      Path devPath = Paths.get("src", "main", "deploy").resolve(candidate);
      if (Files.exists(devPath)) {
        return devPath;
      }
      return candidate;
    } catch (Exception ex) {
      return null;
    }
  }

  private static final class TestRootLoad {
    @SerializedName(value = "default_test_set", alternate = {"defaultTestSet"})
    String defaultTestSet;
    @SerializedName(value = "test_sets", alternate = {"testSets"})
    Map<String, List<TestEntry>> testSets;
    List<TestEntry> tests = Collections.emptyList();
  }

  private static final class TestRootSave {
    @SuppressWarnings("unused")
    List<Map<String, Object>> tests = Collections.emptyList();
    @SerializedName(value = "default_test_set", alternate = {"defaultTestSet"})
    String defaultTestSet;
    @SerializedName(value = "test_sets", alternate = {"testSets"})
    Map<String, List<TestEntry>> testSets = Collections.emptyMap();
  }

  private static final class TestEntry {
    String type;
    String name;
    Boolean enabled;
    Double duty;
    Double limitRot;
    Double timeoutSec;
    Double durationSec;
    List<String> motorKeys;
    String encoderKey;
    String encoderSource;
    Integer encoderCountsPerRev;
    CompositeTest.RotationCheck rotation;
    CompositeTest.TimeCheck time;
    CompositeTest.LimitSwitchCheck limitSwitch;
    CompositeTest.HoldCheck hold;
    Double deadband;
    String inputAxis;
    Integer encoderMotorIndex;
  }

  static MotorRef parseDeviceRef(String value) {
    if (value == null || value.isBlank()) {
      return null;
    }
    String[] parts = value.split(":");
    if (parts.length != 3) {
      return null;
    }
    MotorRef ref = new MotorRef();
    ref.vendor = parts[0].trim();
    ref.type = parts[1].trim();
    try {
      ref.id = Integer.parseInt(parts[2].trim());
    } catch (NumberFormatException ex) {
      return null;
    }
    return ref;
  }

  static EncoderRef parseEncoderRef(String value) {
    if (value == null || value.isBlank()) {
      return null;
    }
    String trimmed = value.trim();
    EncoderRef ref = new EncoderRef();
    if ("internal".equalsIgnoreCase(trimmed)) {
      ref.source = "internal";
      return ref;
    }
    if ("external".equalsIgnoreCase(trimmed)) {
      ref.source = "external";
      return ref;
    }
    String[] parts = trimmed.split(":");
    if (parts.length != 3) {
      return null;
    }
    ref.source = "external";
    ref.vendor = parts[0].trim();
    ref.type = parts[1].trim();
    try {
      ref.id = Integer.parseInt(parts[2].trim());
    } catch (NumberFormatException ex) {
      return null;
    }
    return ref;
  }

  static final class MotorRef {
    String vendor;
    String type;
    int id = -1;
  }

  static final class EncoderRef {
    String source;
    String vendor;
    String type;
    int id = -1;
  }
}
