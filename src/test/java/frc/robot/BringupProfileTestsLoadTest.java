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
import java.nio.file.Files;
import java.nio.file.Path;
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
    String rawJson = Files.readString(Path.of("data", "bringup_system.json"));
    BringupUtil.RegistryApplyReport report =
        BringupUtil.applyRegistryJson(rawJson, "demo_board_042526");

    List<BringupTest> tests = BringupTestRegistry.loadTests();

    assertEquals(true, report.overallOk);
    assertEquals(4, tests.size());
  }

  @Test
  void existingCoreLoadsDemoBoardTestsAfterProfileActivation() throws Exception {
    String rawJson = Files.readString(Path.of("data", "bringup_system.json"));
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
    String rawJson = withRobotProfile(Files.readString(Path.of("data", "bringup_system.json")));
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

  private static String withRobotProfile(String rawJson) {
    JsonObject root = JsonParser.parseString(rawJson).getAsJsonObject();
    JsonObject profiles = root.getAsJsonObject("profiles");
    JsonObject robotProfile = new JsonObject();
    JsonArray robotDevices = new JsonArray();
    robotDevices.add("roborio");
    robotProfile.add("devices", robotDevices);
    profiles.add("robot", robotProfile);

    JsonObject bridgeConfig = root.getAsJsonObject("bridgeConfig");
    JsonObject byProfile = bridgeConfig.getAsJsonObject("byProfile");
    JsonObject robotBridge = new JsonObject();
    robotBridge.add("groups", new JsonArray());
    JsonObject selectedDevice = new JsonObject();
    selectedDevice.addProperty("device", "");
    selectedDevice.addProperty("enabled", false);
    robotBridge.add("selectedDevice", selectedDevice);
    byProfile.add("robot", robotBridge);

    root.addProperty("data_hash", computeDataHash(root));
    return root.toString();
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
