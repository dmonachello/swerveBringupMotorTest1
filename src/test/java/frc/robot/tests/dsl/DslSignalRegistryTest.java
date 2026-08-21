package frc.robot.tests.dsl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import org.junit.jupiter.api.Test;

class DslSignalRegistryTest {

  @Test
  void canonicalDeviceTypeUsesSharedAliasMapCaseInsensitively() {
    assertEquals("encoderExternal", DslSignalRegistry.canonicalDeviceType("CANCoder"));
    assertEquals("encoderExternal", DslSignalRegistry.canonicalDeviceType("cancoder"));
    assertEquals("imu", DslSignalRegistry.canonicalDeviceType("Pigeon"));
    assertEquals("imu", DslSignalRegistry.canonicalDeviceType("pigeon"));
    assertEquals("robotController", DslSignalRegistry.canonicalDeviceType("roboRIO"));
    assertEquals("robotController", DslSignalRegistry.canonicalDeviceType("roborio"));
    assertEquals("robotController", DslSignalRegistry.canonicalDeviceType("SystemCore"));
    assertEquals("robotController", DslSignalRegistry.canonicalDeviceType("systemcore"));
    assertEquals("motor", DslSignalRegistry.canonicalDeviceType("motor"));
  }

  @Test
  void exportJsonIncludesDeviceTypeAliases() {
    JsonObject root = DslSignalRegistry.exportJson();
    JsonObject aliases = root.getAsJsonObject("deviceTypeAliases");

    assertTrue(aliases != null);
    assertEquals("encoderExternal", aliases.get("CANCoder").getAsString());
    assertEquals("imu", aliases.get("Pigeon").getAsString());
    assertEquals("robotController", aliases.get("roboRIO").getAsString());
    assertEquals("robotController", aliases.get("SystemCore").getAsString());
  }
}
