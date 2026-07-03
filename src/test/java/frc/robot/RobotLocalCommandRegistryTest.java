package frc.robot;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import frc.robot.commands.local.RobotLocalCommandDefinition;
import frc.robot.commands.local.RobotLocalCommandRegistry;
import org.junit.jupiter.api.Test;

class RobotLocalCommandRegistryTest {
  private static final String JSON_KEY_COMMANDS = "commands";
  private static final String JSON_KEY_NAME = "name";
  private static final String JSON_KEY_SHOW_IN_HOST_UI = "showInHostUi";
  private static final String COMMAND_LIFECYCLE_ACTIVATE = "lifecycleActivate";
  private static final String COMMAND_PRINT_NT_DIAG = "printNTdiag";
  private static final String COMMAND_SHOW_LIFECYCLE_STATE = "showLifecycleState";

  @Test
  void registryResolvesEveryDeclaredCommand() {
    for (String commandName : RobotLocalCommandRegistry.commandNames()) {
      RobotLocalCommandDefinition definition =
          RobotLocalCommandRegistry.definition(commandName);
      assertNotNull(definition, "Missing registry definition for " + commandName);
    }
    assertTrue(RobotLocalCommandRegistry.isKnownAxisCommand("leftDrive"));
    assertTrue(RobotLocalCommandRegistry.isKnownAxisCommand("rightDrive"));
  }

  @Test
  void inventoryJsonExportsUiVisibleCommands() {
    JsonObject inventory = RobotLocalCommandRegistry.buildInventoryJson();
    JsonArray commands = inventory.getAsJsonArray(JSON_KEY_COMMANDS);
    assertNotNull(commands);
    boolean foundAddAll = false;
    boolean foundStop = false;
    for (int i = 0; i < commands.size(); i++) {
      JsonObject row = commands.get(i).getAsJsonObject();
      String name = row.get(JSON_KEY_NAME).getAsString();
      if ("addAll".equals(name)) {
        foundAddAll = true;
        assertTrue(row.get(JSON_KEY_SHOW_IN_HOST_UI).getAsBoolean());
      }
      if ("stopCommand".equals(name)) {
        foundStop = true;
      }
    }
    assertTrue(foundAddAll);
    assertTrue(foundStop);
    assertFalse(commands.isEmpty());
  }

  @Test
  void registryIncludesLifecycleCommands() {
    assertNotNull(RobotLocalCommandRegistry.definition(COMMAND_LIFECYCLE_ACTIVATE));
    assertNotNull(RobotLocalCommandRegistry.definition(COMMAND_SHOW_LIFECYCLE_STATE));
    assertTrue(RobotLocalCommandRegistry.isKnownCommand(COMMAND_LIFECYCLE_ACTIVATE));
    assertTrue(RobotLocalCommandRegistry.isKnownCommand(COMMAND_SHOW_LIFECYCLE_STATE));
  }

  @Test
  void registryNoLongerIncludesNtDiagnosticsCommand() {
    assertFalse(RobotLocalCommandRegistry.isKnownCommand(COMMAND_PRINT_NT_DIAG));
    assertFalse(RobotLocalCommandRegistry.commandNames().contains(COMMAND_PRINT_NT_DIAG));
  }
}
