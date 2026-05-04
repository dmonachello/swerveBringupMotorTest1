package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import frc.robot.tests.BringupTest;
import frc.robot.tests.BringupTestRegistry;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;

class BringupProfileTestsLoadTest {
  private static final Gson CANONICAL_GSON = new Gson();

  @Test
  void demoBoardTestsLoadFromAppliedRegistryPayload() throws Exception {
    String rawJson = buildDemoBoardFixtureJson();
    BringupUtil.RegistryApplyReport report =
        BringupUtil.applyRegistryJson(rawJson, "demo_board_042526");

    List<BringupTest> tests = BringupTestRegistry.loadTests();

    assertEquals(true, report.overallOk);
    assertEquals(4, tests.size());
  }

  @Test
  void existingCoreLoadsDemoBoardTestsAfterProfileActivation() throws Exception {
    String rawJson = buildDemoBoardFixtureJson();
    BringupUtil.applyRegistryJson(rawJson, "robot");
    BringupCore core = new BringupCore();

    BringupUtil.RegistryApplyReport report =
        BringupUtil.applyRegistryJson(rawJson, "demo_board_042526");
    BringupCore.TestsOverview overview = core.buildTestsOverview();

    assertEquals(true, report.overallOk);
    assertEquals(4, overview.totalCount);
    assertEquals(4, overview.enabledCount);
  }

  @Test
  void existingCoreOverwritesTestsWhenActivatedProfileChanges() throws Exception {
    String rawJson = buildDemoBoardFixtureJson();
    BringupUtil.applyRegistryJson(rawJson, "demo_board_042526");
    BringupCore core = new BringupCore();

    BringupCore.TestsOverview demoOverview = core.buildTestsOverview();
    BringupUtil.RegistryApplyReport report = BringupUtil.applyRegistryJson(rawJson, "robot");
    BringupCore.TestsOverview robotOverview = core.buildTestsOverview();

    assertEquals(4, demoOverview.totalCount);
    assertEquals(true, report.overallOk);
    assertEquals(0, robotOverview.totalCount);
    assertEquals(0, robotOverview.enabledCount);
  }

  private static String buildDemoBoardFixtureJson() {
    JsonObject root = new JsonObject();
    root.addProperty("schema_version", 4);

    JsonObject profiles = root.getAsJsonObject("profiles");
    if (profiles == null) {
      profiles = new JsonObject();
      root.add("profiles", profiles);
    }

    JsonObject demoProfile = new JsonObject();
    JsonArray demoDevices = new JsonArray();
    demoDevices.add("SPARKMAX/NEO 25");
    demoDevices.add("SPARKMAX/NEO550 7");
    demoDevices.add("FALCON 9");
    demoProfile.add("devices", demoDevices);
    profiles.add("demo_board_042526", demoProfile);

    JsonObject robotProfile = new JsonObject();
    JsonArray robotDevices = new JsonArray();
    robotDevices.add("roborio");
    robotProfile.add("devices", robotDevices);
    profiles.add("robot", robotProfile);

    JsonArray devices = new JsonArray();
    devices.add(buildCanDevice("SPARKMAX/NEO 25", 5, 2, 25, "REV NEO", "motor", "REV"));
    devices.add(buildCanDevice("SPARKMAX/NEO550 7", 5, 2, 7, "REV NEO 550", "motor", "REV"));
    devices.add(buildCanDevice("FALCON 9", 4, 2, 9, "CTRE FALCON", "motor", "CTRE"));
    devices.add(buildCanDevice("roborio", 1, 1, 0, "roboRIO", "roboRIO", "NI"));
    root.add("devices", devices);
    root.addProperty("default_profile", "demo_board_042526");

    JsonObject bridgeConfig = new JsonObject();
    bridgeConfig.addProperty("schemaVersion", 2);
    bridgeConfig.add("generatedAt", JsonNull.INSTANCE);
    JsonObject byProfile = new JsonObject();
    bridgeConfig.add("byProfile", byProfile);
    root.add("bridgeConfig", bridgeConfig);

    byProfile.add("demo_board_042526", buildDemoBoardBridgeConfig());
    JsonObject robotBridge = new JsonObject();
    robotBridge.add("groups", new JsonArray());
    JsonObject selectedDevice = new JsonObject();
    selectedDevice.addProperty("device", "");
    selectedDevice.addProperty("enabled", false);
    robotBridge.add("selectedDevice", selectedDevice);
    byProfile.add("robot", robotBridge);

    root.addProperty("data_version", "test_fixture");
    root.addProperty("data_hash", computeDataHash(root));
    return root.toString();
  }

  private static JsonObject buildCanDevice(
      String label,
      int manufacturer,
      int deviceType,
      int id,
      String model,
      String type,
      String vendor) {
    JsonObject device = new JsonObject();
    device.addProperty("label", label);
    device.addProperty("deviceInterface", "CAN");
    device.addProperty("manufacturer", manufacturer);
    device.addProperty("deviceType", deviceType);
    device.addProperty("id", id);
    device.addProperty("model", model);
    device.addProperty("type", type);
    device.addProperty("vendor", vendor);
    return device;
  }

  private static JsonObject buildDemoBoardBridgeConfig() {
    JsonObject profile = new JsonObject();
    profile.add("groups", new JsonArray());

    JsonObject selectedDevice = new JsonObject();
    selectedDevice.addProperty("device", "");
    selectedDevice.addProperty("enabled", false);
    profile.add("selectedDevice", selectedDevice);

    JsonObject tests = new JsonObject();
    tests.addProperty("default_test_set", "default");
    JsonObject testSets = new JsonObject();
    JsonArray defaultSet = new JsonArray();
    defaultSet.add(buildCompositeTest("neo25_spin_low", "SPARKMAX/NEO 25"));
    defaultSet.add(buildCompositeTest("neo5507_spin_low", "SPARKMAX/NEO550 7"));
    defaultSet.add(buildCompositeTest("falcon9_spin_low", "FALCON 9"));
    defaultSet.add(buildCompositeTest(
        "all_three_spin_low",
        "SPARKMAX/NEO 25",
        "SPARKMAX/NEO550 7",
        "FALCON 9"));
    testSets.add("default", defaultSet);
    tests.add("test_sets", testSets);
    profile.add("tests", tests);
    return profile;
  }

  private static JsonObject buildCompositeTest(String name, String... motorLabels) {
    JsonObject test = new JsonObject();
    test.addProperty("name", name);
    test.addProperty("enabled", true);
    test.addProperty("type", "composite");
    test.addProperty("duty", 0.15);
    JsonArray motors = new JsonArray();
    for (String label : motorLabels) {
      motors.add(label);
    }
    test.add("motorLabels", motors);

    JsonObject time = new JsonObject();
    time.addProperty("timeoutSec", 1.5);
    time.addProperty("onTimeout", "pass");
    test.add("time", time);
    return test;
  }

  private static String computeDataHash(JsonObject source) {
    JsonObject root = source.deepCopy();
    root.addProperty("data_hash", "");
    root.remove("bridgeConfig");
    return sha256Hex(canonicalizeJson(root));
  }

  private static String canonicalizeJson(JsonElement element) {
    if (element == null || element instanceof JsonNull || element.isJsonNull()) {
      return "null";
    }
    if (element.isJsonPrimitive()) {
      JsonPrimitive primitive = element.getAsJsonPrimitive();
      return CANONICAL_GSON.toJson(primitive);
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
      JsonObject object = element.getAsJsonObject();
      List<String> keys = new ArrayList<>(object.keySet());
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
        builder.append(canonicalizeJson(object.get(key)));
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
      for (byte item : hash) {
        String value = Integer.toHexString(0xff & item);
        if (value.length() == 1) {
          hex.append('0');
        }
        hex.append(value);
      }
      return hex.toString();
    } catch (NoSuchAlgorithmException ex) {
      throw new RuntimeException("SHA-256 unavailable", ex);
    }
  }
}
