package frc.robot.tests;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import frc.robot.BringupPrinter;
import frc.robot.BringupUtil;
import frc.robot.tests.dsl.DslBringupTest;
import frc.robot.tests.dsl.DslModels;
import java.io.IOException;
import java.io.InputStream;
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
 *   BringupTestRegistry - Load bringup tests from the normalized DSL section.
 *
 * DESCRIPTION
 *   Reads the top-level dslTests section from bringup_system.json and resolves
 *   the named test set referenced by the active profile.
 */
public final class BringupTestRegistry {
  private static final String TESTS_SOURCE_REGISTRY = "dslTests";
  private static final String KEY_TESTS_BY_NAME = "testsByName";
  private static final String KEY_ENABLED = "enabled";
  private static final String MESSAGE_SAVE_UNAVAILABLE = "Warning: no DSL tests payload loaded; cannot save enabled state.";
  private static final String MESSAGE_SAVE_MISSING = "Warning: no matching DSL test entries found to save enabled state.";
  private static final String MESSAGE_SAVE_FAILED_PREFIX = "Warning: failed to save DSL test enabled state: ";
  private static final Gson GSON = new Gson();

  private BringupTestRegistry() {}

  public static List<BringupTest> loadTests() {
    DslModels.DslTestsRoot root = loadRoot();
    if (root == null || root.testsByName == null || root.testsByName.isEmpty()) {
      return Collections.emptyList();
    }
    List<String> names = selectTestNames(root);
    if (names.isEmpty()) {
      return Collections.emptyList();
    }
    List<BringupTest> tests = new ArrayList<>();
    for (String name : names) {
      DslModels.DslTestEntry entry = root.testsByName.get(name);
      if (entry == null || entry.normalized == null) {
        continue;
      }
      tests.add(new DslBringupTest(entry.normalized, entry.enabled));
    }
    return tests;
  }

  public static TestsInfo getTestsInfo() {
    TestsInfo info = new TestsInfo();
    info.profileName = BringupUtil.getActiveCanProfile();
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
    DslModels.DslTestsRoot root = loadRoot();
    if (root != null) {
      info.usingTestSets = root.testSets != null && !root.testSets.isEmpty();
      info.defaultTestSetName = root.defaultSet;
      info.activeTestSetName = resolveActiveSetName(root);
      info.testSetCount = root.testSets != null ? root.testSets.size() : 0;
      List<String> entries = selectTestNames(root);
      info.testCount = entries.size();
    }
    return info;
  }

  public static boolean saveTests(List<BringupTest> tests) {
    if (tests == null || tests.isEmpty()) {
      return true;
    }
    JsonObject root = BringupUtil.readCurrentProfilesJson();
    if (root == null) {
      BringupPrinter.enqueue(MESSAGE_SAVE_UNAVAILABLE);
      return false;
    }
    JsonObject dslRoot = root.has(TESTS_SOURCE_REGISTRY) && root.get(TESTS_SOURCE_REGISTRY).isJsonObject()
        ? root.getAsJsonObject(TESTS_SOURCE_REGISTRY)
        : null;
    JsonObject testsByName = dslRoot != null && dslRoot.has(KEY_TESTS_BY_NAME) && dslRoot.get(KEY_TESTS_BY_NAME).isJsonObject()
        ? dslRoot.getAsJsonObject(KEY_TESTS_BY_NAME)
        : null;
    if (testsByName == null) {
      BringupPrinter.enqueue(MESSAGE_SAVE_UNAVAILABLE);
      return false;
    }
    int updatedCount = 0;
    for (BringupTest test : tests) {
      if (test == null) {
        continue;
      }
      String testName = test.getName();
      if (testName == null || testName.isBlank() || !testsByName.has(testName) || !testsByName.get(testName).isJsonObject()) {
        continue;
      }
      testsByName.getAsJsonObject(testName).addProperty(KEY_ENABLED, test.isEnabled());
      updatedCount++;
    }
    if (updatedCount <= 0) {
      BringupPrinter.enqueue(MESSAGE_SAVE_MISSING);
      return false;
    }
    String persistError = BringupUtil.persistCurrentProfilesJson(root);
    if (!persistError.isBlank()) {
      BringupPrinter.enqueue(MESSAGE_SAVE_FAILED_PREFIX + persistError);
      return false;
    }
    return true;
  }

  public static String getStoredSource(String testName) {
    if (testName == null || testName.isBlank()) {
      return "";
    }
    DslModels.DslTestsRoot root = loadRoot();
    if (root == null || root.testsByName == null || root.testsByName.isEmpty()) {
      return "";
    }
    DslModels.DslTestEntry entry = root.testsByName.get(testName);
    if (entry == null || entry.source == null) {
      return "";
    }
    return entry.source;
  }

  private static DslModels.DslTestsRoot loadRoot() {
    JsonObject root = BringupUtil.readDslTestsRoot();
    if (root == null) {
      return null;
    }
    return GSON.fromJson(root, DslModels.DslTestsRoot.class);
  }

  private static List<String> selectTestNames(DslModels.DslTestsRoot root) {
    if (root == null || root.testsByName == null || root.testsByName.isEmpty()) {
      return Collections.emptyList();
    }
    if (root.testSets == null || root.testSets.isEmpty()) {
      return new ArrayList<>(root.testsByName.keySet());
    }
    String active = resolveActiveSetName(root);
    List<String> names = active != null ? root.testSets.get(active) : null;
    return names != null ? names : Collections.emptyList();
  }

  private static String resolveActiveSetName(DslModels.DslTestsRoot root) {
    if (root == null) {
      return null;
    }
    String profileSet = BringupUtil.getSelectedDslTestSetForProfile(BringupUtil.getActiveCanProfile());
    if (profileSet != null && !profileSet.isBlank() && root.testSets != null && root.testSets.containsKey(profileSet)) {
      return profileSet;
    }
    if (root.defaultSet != null && root.testSets != null && root.testSets.containsKey(root.defaultSet)) {
      return root.defaultSet;
    }
    if (root.testSets != null && !root.testSets.isEmpty()) {
      return root.testSets.keySet().iterator().next();
    }
    return null;
  }

  private static String hashFile(Path path) throws IOException {
    try {
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      try (InputStream input = Files.newInputStream(path)) {
        byte[] buffer = new byte[4096];
        int read;
        while ((read = input.read(buffer)) >= 0) {
          if (read > 0) {
            digest.update(buffer, 0, read);
          }
        }
      }
      byte[] hash = digest.digest();
      StringBuilder hex = new StringBuilder(hash.length * 2);
      for (byte b : hash) {
        hex.append(String.format("%02x", b));
      }
      return hex.toString();
    } catch (NoSuchAlgorithmException ex) {
      throw new IOException("SHA-256 unavailable", ex);
    }
  }

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
  }
}
