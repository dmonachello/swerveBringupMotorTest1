package frc.robot;

import com.google.gson.JsonObject;
import java.util.Set;

/**
 * NAME
 *   BridgeUiProfileCommands - Profile/config command family executor.
 */
final class BridgeUiProfileCommands implements BridgeUiCommandDispatcher.CommandFamily {

  private static final String CMD_SELECT_PROFILE = "selectProfile";
  private static final String CMD_PROFILE_ACTIVATE = "profileActivate";
  private static final String CMD_PROFILES_RELOAD = "profilesReload";
  private static final String CMD_PROFILE_TOGGLE = "profileToggle";
  private static final String CMD_PROFILES_APPLY = "profilesApply";

  private static final String ARG_NAME = "name";

  private static final String TEXT_PROFILE_ACTIVATE_OK = "Profile activated: %s";
  private static final String TEXT_PROFILE_ACTIVATE_FAIL = "Profile activation failed.";
  private static final String TEXT_PROFILES_RELOAD_OK = "Profiles reloaded.";
  private static final String TEXT_PROFILES_RELOAD_FAILED = "Profiles reload failed: %s";

  private static final String MESSAGE_SELECT_PROFILE_REQUIRED = "selectProfile requires args.name.";
  private static final String MESSAGE_SELECTED_PROFILE_PREFIX = "Selected profile: ";
  private static final String MESSAGE_PROFILE_SELECTED = "Profile selected.";

  private static final Set<String> COMMANDS = Set.of(
      CMD_SELECT_PROFILE,
      CMD_PROFILE_ACTIVATE,
      CMD_PROFILES_RELOAD,
      CMD_PROFILE_TOGGLE,
      CMD_PROFILES_APPLY);

  /**
   * NAME
   *   Dependencies - Narrow dependency contract for profile commands.
   */
  interface Dependencies {
    String parseUiArgString(JsonObject args, String key);

    void selectCanProfile(String profileName);

    void prepareActivationForSelectedProfile();

    void activateSelectedProfile();

    boolean isProfileActive();

    String getActiveCanProfileLabel();

    String reloadProfilesFromJson();

    void runProfileActivateAction();

    void runProfileToggleAction();

    void selectNextProfile();

    void applyProfilesApplyCommand(BridgeUiCommandResult result, JsonObject args, boolean isTcp);
  }

  private final Dependencies dependencies;

  BridgeUiProfileCommands(Dependencies dependencies) {
    this.dependencies = dependencies;
  }

  @Override
  public boolean handles(String commandName) {
    return COMMANDS.contains(commandName);
  }

  @Override
  public BridgeUiCommandResult execute(
      BridgeUiIngressPolicy.Ingress ingress,
      double cmdTs,
      boolean isTcp) {
    BridgeUiCommandResult result = new BridgeUiCommandResult();
    String commandName = ingress.name;
    JsonObject args = ingress.args;
    switch (commandName) {
      case CMD_SELECT_PROFILE:
        executeSelectProfile(args, result);
        break;
      case CMD_PROFILE_ACTIVATE:
        executeProfileActivate(args, result);
        break;
      case CMD_PROFILES_RELOAD:
        executeProfilesReload(result);
        break;
      case CMD_PROFILE_TOGGLE:
        dependencies.selectNextProfile();
        dependencies.runProfileToggleAction();
        result.message = MESSAGE_PROFILE_SELECTED;
        break;
      case CMD_PROFILES_APPLY:
        dependencies.applyProfilesApplyCommand(result, args, isTcp);
        break;
      default:
        result.ok = false;
        result.message = "Unknown command: " + commandName;
        break;
    }
    return result;
  }

  private void executeSelectProfile(JsonObject args, BridgeUiCommandResult result) {
    String profileName = dependencies.parseUiArgString(args, ARG_NAME);
    if (profileName == null || profileName.isBlank()) {
      result.ok = false;
      result.message = MESSAGE_SELECT_PROFILE_REQUIRED;
      return;
    }
    dependencies.selectCanProfile(profileName.trim());
    result.message = MESSAGE_SELECTED_PROFILE_PREFIX + dependencies.getActiveCanProfileLabel();
    result.outText = result.message;
  }

  private void executeProfileActivate(JsonObject args, BridgeUiCommandResult result) {
    String profileName = dependencies.parseUiArgString(args, ARG_NAME);
    if (profileName != null && !profileName.isBlank()) {
      dependencies.selectCanProfile(profileName.trim());
    }
    dependencies.prepareActivationForSelectedProfile();
    dependencies.activateSelectedProfile();
    if (dependencies.isProfileActive()) {
      dependencies.runProfileActivateAction();
      result.message = String.format(TEXT_PROFILE_ACTIVATE_OK, dependencies.getActiveCanProfileLabel());
      result.outText = result.message;
      return;
    }
    result.ok = false;
    result.message = TEXT_PROFILE_ACTIVATE_FAIL;
    result.outText = result.message;
  }

  private void executeProfilesReload(BridgeUiCommandResult result) {
    String error = dependencies.reloadProfilesFromJson();
    if (error != null && !error.isBlank()) {
      result.ok = false;
      result.message = String.format(TEXT_PROFILES_RELOAD_FAILED, error);
      result.outText = result.message;
      return;
    }
    dependencies.runProfileActivateAction();
    result.message = TEXT_PROFILES_RELOAD_OK;
    result.outText = result.message;
  }
}

