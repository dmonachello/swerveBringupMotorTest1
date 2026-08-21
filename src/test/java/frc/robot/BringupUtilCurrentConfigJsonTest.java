package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
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

  @Test
  void getConfiguredDeviceEntryByLabelUsesLoadedRegistryEvenWithoutActiveProfile() throws Exception {
    captureState();

    Object deviceDefinition = newInstance(CLASS_DEVICE_DEFINITION);
    setField(deviceDefinition, FIELD_DEVICE_LABEL, "cancoder");
    setField(deviceDefinition, "id", 18);
    setField(deviceDefinition, "manufacturer", 4);
    setField(deviceDefinition, "deviceType", 7);
    setField(deviceDefinition, "deviceInterface", "CAN");
    setField(deviceDefinition, "type", "encoderExternal");
    @SuppressWarnings("unchecked")
    Map<String, Object> deviceRegistry = (Map<String, Object>) getStaticField(FIELD_DEVICE_REGISTRY);
    deviceRegistry.clear();
    deviceRegistry.put(normalizeKey("cancoder"), deviceDefinition);

    BringupUtil.DeviceEntry entry = BringupUtil.getConfiguredDeviceEntryByLabel("cancoder");

    assertNotNull(entry);
    assertEquals("cancoder", entry.label);
    assertEquals(18, entry.id);
    assertEquals(4, entry.manufacturer);
    assertEquals(7, entry.deviceType);
  }

  @Test
  void getConfiguredDeviceEntryByLabelRejectsUnknownLabel() throws Exception {
    captureState();
    @SuppressWarnings("unchecked")
    Map<String, Object> deviceRegistry = (Map<String, Object>) getStaticField(FIELD_DEVICE_REGISTRY);
    deviceRegistry.clear();

    BringupUtil.DeviceEntry entry = BringupUtil.getConfiguredDeviceEntryByLabel("missing");

    assertNull(entry);
  }

  @Test
  void buildDeviceEntryNormalizesGenericRevMotorControllerModelToRevNeoSpec() throws Exception {
    Object deviceDefinition = newInstance(CLASS_DEVICE_DEFINITION);
    setField(deviceDefinition, FIELD_DEVICE_LABEL, "REV_MOTORCONTROLLER_25");
    setField(deviceDefinition, "id", 25);
    setField(deviceDefinition, "manufacturer", 5);
    setField(deviceDefinition, "deviceType", 2);
    setField(deviceDefinition, "deviceInterface", "CAN");
    setField(deviceDefinition, "model", "MotorController");
    setField(deviceDefinition, "type", "motor");

    Object entry = invokePrivateStaticMethod("buildDeviceEntry", deviceDefinition);
    String motor = (String) getField(entry, "motor");
    String type = (String) getField(entry, "type");

    assertEquals("NEO", type);
    assertEquals("REV NEO", motor);
  }

  @Test
  void buildDeviceEntryPreservesSemanticRobotControllerType() throws Exception {
    Object deviceDefinition = newInstance(CLASS_DEVICE_DEFINITION);
    setField(deviceDefinition, FIELD_DEVICE_LABEL, "main-controller-rio");
    setField(deviceDefinition, "id", 0);
    setField(deviceDefinition, "manufacturer", 1);
    setField(deviceDefinition, "deviceType", 1);
    setField(deviceDefinition, "deviceInterface", "CAN");
    setField(deviceDefinition, "model", "roboRIO");
    setField(deviceDefinition, "type", "robotController");

    Object entry = invokePrivateStaticMethod("buildDeviceEntry", deviceDefinition);
    String type = (String) getField(entry, "type");
    String semanticType = (String) getField(entry, "semanticType");

    assertEquals("robotController", type);
    assertEquals("robotController", semanticType);
    assertTrue(BringupUtil.isRobotControllerEntry((BringupUtil.DeviceEntry) entry));
  }

  @Test
  void validateSingleActiveRobotControllerStrictRejectsMultipleControllers() throws Exception {
    captureState();

    Object profileConfig = newInstance(CLASS_PROFILE_CONFIG);
    setField(profileConfig, FIELD_PROFILE_DEVICES, List.of("main-controller-rio", "main-controller-systemcore"));

    Object rioDefinition = newInstance(CLASS_DEVICE_DEFINITION);
    setField(rioDefinition, FIELD_DEVICE_LABEL, "main-controller-rio");
    setField(rioDefinition, "id", 0);
    setField(rioDefinition, "manufacturer", 1);
    setField(rioDefinition, "deviceType", 1);
    setField(rioDefinition, "deviceInterface", "CAN");
    setField(rioDefinition, "model", "roboRIO");
    setField(rioDefinition, "type", "robotController");

    Object systemCoreDefinition = newInstance(CLASS_DEVICE_DEFINITION);
    setField(systemCoreDefinition, FIELD_DEVICE_LABEL, "main-controller-systemcore");
    setField(systemCoreDefinition, "id", 0);
    setField(systemCoreDefinition, "manufacturer", 0);
    setField(systemCoreDefinition, "deviceType", 0);
    setField(systemCoreDefinition, "deviceInterface", "CAN");
    setField(systemCoreDefinition, "model", "SystemCore");
    setField(systemCoreDefinition, "type", "robotController");

    @SuppressWarnings("unchecked")
    Map<String, Object> deviceRegistry = (Map<String, Object>) getStaticField(FIELD_DEVICE_REGISTRY);
    deviceRegistry.clear();
    deviceRegistry.put(normalizeKey("main-controller-rio"), rioDefinition);
    deviceRegistry.put(normalizeKey("main-controller-systemcore"), systemCoreDefinition);

    Exception ex =
        assertThrows(
            Exception.class,
            () ->
                invokePrivateStaticMethod(
                    "validateSingleActiveRobotControllerStrict",
                    new Class<?>[] {String.class, Class.forName(CLASS_PROFILE_CONFIG)},
                    new Object[] {"test_profile", profileConfig}));

    assertTrue(ex.getCause().getMessage().contains("more than one robot controller"));
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

  private static Object getField(Object target, String name) throws Exception {
    Field field = target.getClass().getDeclaredField(name);
    field.setAccessible(true);
    return field.get(target);
  }

  private static Object invokePrivateStaticMethod(String name, Object arg) throws Exception {
    Method method = BringupUtil.class.getDeclaredMethod(name, arg.getClass());
    method.setAccessible(true);
    return method.invoke(null, arg);
  }

  private static Object invokePrivateStaticMethod(
      String name,
      Class<?>[] parameterTypes,
      Object[] args) throws Exception {
    Method method = BringupUtil.class.getDeclaredMethod(name, parameterTypes);
    method.setAccessible(true);
    return method.invoke(null, args);
  }

  private static String normalizeKey(String value) {
    return value == null ? "" : value.trim().toUpperCase().replaceAll("[^A-Z0-9]+", "");
  }
}
