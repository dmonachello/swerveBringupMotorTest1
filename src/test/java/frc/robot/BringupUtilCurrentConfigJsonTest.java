package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

class BringupUtilCurrentConfigJsonTest {
  private static final String FIELD_CURRENT_DATA_VERSION = "currentDataVersion";
  private static final String FIELD_DEFAULT_PROFILE = "defaultProfile";
  private static final String FIELD_PROFILES = "profiles";
  private static final String FIELD_PROFILE_ORDER = "profileOrder";
  private static final String FIELD_DEVICE_REGISTRY = "DEVICE_REGISTRY";
  private static final String FIELD_PROFILE_TESTS = "PROFILE_TESTS";
  private static final String FIELD_PROFILE_BRIDGE_CONFIGS = "PROFILE_BRIDGE_CONFIGS";
  private static final String FIELD_DSL_TESTS_ROOT = "dslTestsRoot";
  private static final String CLASS_PROFILE_CONFIG = "frc.robot.BringupUtil$ProfileConfig";
  private static final String CLASS_DEVICE_DEFINITION = "frc.robot.BringupUtil$DeviceDefinition";
  private static final String FIELD_PROFILE_DEVICES = "devices";
  private static final String FIELD_PROFILE_DSL_TEST_SET = "dslTestSet";
  private static final String FIELD_DEVICE_LABEL = "label";

  private String savedDataVersion;
  private String savedDefaultProfile;
  private JsonObject savedDslTestsRoot;
  private Map<String, Object> savedProfiles;
  private List<String> savedProfileOrder;
  private Map<String, Object> savedDeviceRegistry;
  private Map<String, Object> savedProfileTests;
  private Map<String, Object> savedProfileBridgeConfigs;
  private boolean captured = false;

  @AfterEach
  void tearDown() throws Exception {
    if (!captured) {
      return;
    }
    setStaticField(FIELD_CURRENT_DATA_VERSION, savedDataVersion);
    setStaticField(FIELD_DEFAULT_PROFILE, savedDefaultProfile);
    setStaticField(FIELD_DSL_TESTS_ROOT, savedDslTestsRoot);
    replaceMapField(FIELD_PROFILES, savedProfiles);
    setStaticField(FIELD_PROFILE_ORDER, savedProfileOrder);
    replaceMapField(FIELD_DEVICE_REGISTRY, savedDeviceRegistry);
    replaceMapField(FIELD_PROFILE_TESTS, savedProfileTests);
    replaceMapField(FIELD_PROFILE_BRIDGE_CONFIGS, savedProfileBridgeConfigs);
  }

  @Test
  void buildCurrentProfilesJsonReflectsLoadedInMemoryRegistry() throws Exception {
    captureState();

    Object profileConfig = newInstance(CLASS_PROFILE_CONFIG);
    setField(profileConfig, FIELD_PROFILE_DEVICES, List.of("FALCON 9"));
    setField(profileConfig, FIELD_PROFILE_DSL_TEST_SET, "test_minimal_25_9");

    @SuppressWarnings("unchecked")
    Map<String, Object> profiles = (Map<String, Object>) getStaticField(FIELD_PROFILES);
    profiles.clear();
    profiles.put("test_minimal_25_9", profileConfig);
    setStaticField(FIELD_PROFILE_ORDER, List.of("test_minimal_25_9"));

    Object deviceDefinition = newInstance(CLASS_DEVICE_DEFINITION);
    setField(deviceDefinition, FIELD_DEVICE_LABEL, "FALCON 9");
    @SuppressWarnings("unchecked")
    Map<String, Object> deviceRegistry = (Map<String, Object>) getStaticField(FIELD_DEVICE_REGISTRY);
    deviceRegistry.clear();
    deviceRegistry.put(normalizeKey("FALCON 9"), deviceDefinition);

    JsonObject testsRoot = JsonParser.parseString(
        "{\"schemaVersion\":1,\"defaultSet\":\"test_minimal_25_9\",\"testSets\":{\"test_minimal_25_9\":[\"falcon9_move_150_rotations\"]},\"testsByName\":{\"falcon9_move_150_rotations\":{\"runnable\":true}}}")
        .getAsJsonObject();
    setStaticField(FIELD_DSL_TESTS_ROOT, testsRoot);
    setStaticField(FIELD_CURRENT_DATA_VERSION, "test-version");
    setStaticField(FIELD_DEFAULT_PROFILE, "test_minimal_25_9");
    replaceMapField(FIELD_PROFILE_TESTS, Collections.emptyMap());
    replaceMapField(FIELD_PROFILE_BRIDGE_CONFIGS, Collections.emptyMap());

    JsonObject current = BringupUtil.buildCurrentProfilesJson();

    assertEquals("test-version", current.get("data_version").getAsString());
    assertEquals("test_minimal_25_9", current.get("default_profile").getAsString());
    assertTrue(current.getAsJsonObject("profiles").has("test_minimal_25_9"));
    assertEquals(
        "test_minimal_25_9",
        current.getAsJsonObject("dslTests").get("defaultSet").getAsString());
    assertEquals(
        "falcon9_move_150_rotations",
        current.getAsJsonObject("dslTests")
            .getAsJsonObject("testSets")
            .getAsJsonArray("test_minimal_25_9")
            .get(0)
            .getAsString());
    assertTrue(current.getAsJsonArray("devices").size() > 0);
    assertTrue(current.has("data_hash"));
    assertTrue(!current.get("data_hash").getAsString().isBlank());
  }

  private void captureState() throws Exception {
    captured = true;
    savedDataVersion = (String) getStaticField(FIELD_CURRENT_DATA_VERSION);
    savedDefaultProfile = (String) getStaticField(FIELD_DEFAULT_PROFILE);
    JsonObject root = (JsonObject) getStaticField(FIELD_DSL_TESTS_ROOT);
    savedDslTestsRoot = root != null ? root.deepCopy() : null;
    savedProfiles = new LinkedHashMap<>(castMap(getStaticField(FIELD_PROFILES)));
    savedProfileOrder = List.copyOf(castList(getStaticField(FIELD_PROFILE_ORDER)));
    savedDeviceRegistry = new LinkedHashMap<>(castMap(getStaticField(FIELD_DEVICE_REGISTRY)));
    savedProfileTests = new LinkedHashMap<>(castMap(getStaticField(FIELD_PROFILE_TESTS)));
    savedProfileBridgeConfigs = new LinkedHashMap<>(castMap(getStaticField(FIELD_PROFILE_BRIDGE_CONFIGS)));
  }

  @SuppressWarnings("unchecked")
  private static Map<String, Object> castMap(Object value) {
    return (Map<String, Object>) value;
  }

  @SuppressWarnings("unchecked")
  private static List<String> castList(Object value) {
    return (List<String>) value;
  }

  private static Object getStaticField(String name) throws Exception {
    Field field = BringupUtil.class.getDeclaredField(name);
    field.setAccessible(true);
    return field.get(null);
  }

  private static void setStaticField(String name, Object value) throws Exception {
    Field field = BringupUtil.class.getDeclaredField(name);
    field.setAccessible(true);
    field.set(null, value);
  }

  @SuppressWarnings("unchecked")
  private static void replaceMapField(String name, Map<String, ?> values) throws Exception {
    Field field = BringupUtil.class.getDeclaredField(name);
    field.setAccessible(true);
    Map<String, Object> target = (Map<String, Object>) field.get(null);
    target.clear();
    target.putAll((Map<String, Object>) values);
  }

  private static Object newInstance(String className) throws Exception {
    Class<?> type = Class.forName(className);
    Constructor<?> constructor = type.getDeclaredConstructor();
    constructor.setAccessible(true);
    return constructor.newInstance();
  }

  private static void setField(Object target, String name, Object value) throws Exception {
    Field field = target.getClass().getDeclaredField(name);
    field.setAccessible(true);
    field.set(target, value);
  }

  private static String normalizeKey(String value) {
    return value == null ? "" : value.trim().toUpperCase().replaceAll("[^A-Z0-9]+", "");
  }
}
