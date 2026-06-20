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
      if (entry == null || Boolean.FALSE.equals(entry.runnable) || entry.normalized == null) {
        continue;
      }
      tests.add(new DslBringupTest(entry.normalized));
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
      info.testCount = loadTests().size();
    }
    return info;
  }

  public static boolean saveTests(List<BringupTest> tests) {
    BringupPrinter.enqueue("Warning: robot-side DSL test save is not supported; use host compile/save.");
    return false;
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
