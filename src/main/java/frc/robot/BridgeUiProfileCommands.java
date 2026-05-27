package frc.robot;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.util.List;
import java.util.Set;

/**
 * NAME
 *   BridgeUiProfileCommands - Profile/config command family executor.
 */
final class BridgeUiProfileCommands implements BridgeUiCommandDispatcher.CommandFamily {

  private static final String CMD_SELECT_PROFILE = "selectProfile";
  private static final String CMD_PROFILE_ACTIVATE = "profileActivate";
  private static final String CMD_RUNTIME_ACTIVATE = "runtimeActivate";
  private static final String CMD_RUNTIME_DEACTIVATE = "runtimeDeactivate";
  private static final String CMD_PROFILES_RELOAD = "profilesReload";
  private static final String CMD_PROFILE_TOGGLE = "profileToggle";
  private static final String CMD_PROFILES_APPLY = "profilesApply";
  private static final String CMD_SHOW_PROFILES = "showProfiles";
  private static final String CMD_SHOW_PROFILE = "showProfile";

  private static final String ARG_NAME = "name";
  private static final String ARG_JSON = "json";
  private static final String JSON_KEY_PROFILE = "profile";
  private static final String JSON_KEY_ACTIVE = "active";
  private static final String JSON_KEY_SELECTED = "selected";
  private static final String JSON_KEY_ACTIVE_RUNTIME = "activeRuntime";
  private static final String JSON_KEY_RUNTIME_ACTIVE = "runtimeActive";
  private static final String JSON_KEY_DEFAULT = "default";
  private static final String JSON_KEY_AVAILABLE = "available";
  private static final String JSON_KEY_PROFILE_DEVICES = "profile_devices";
  private static final String TEXT_PROFILE_HEADER = "Profile:";
  private static final String TEXT_PROFILE_ACTIVE_FMT = "  active=%s";
  private static final String TEXT_PROFILE_SELECTED_FMT = "  selected=%s";
  private static final String TEXT_PROFILE_ACTIVE_RUNTIME_FMT = "  activeRuntime=%s";
  private static final String TEXT_PROFILE_RUNTIME_ACTIVE_FMT = "  runtimeActive=%s";
  private static final String TEXT_PROFILE_DEFAULT_FMT = "  default=%s";
  private static final String TEXT_PROFILE_AVAILABLE_FMT = "  available=%d";
  private static final String TEXT_PROFILE_NAME_FMT = "  name=%s";
  private static final String TEXT_PROFILE_DEVICES_HEADER_FMT = "  devices=%d";
  private static final String TEXT_PROFILE_DEVICE_FMT = "    %s";

  private static final String TEXT_PROFILE_ACTIVATE_OK = "Profile activated: %s";
  private static final String TEXT_PROFILE_ACTIVATE_FAIL = "Profile activation failed.";
  private static final String TEXT_RUNTIME_DEACTIVATE_OK = "Runtime deactivated.";
  private static final String TEXT_PROFILES_RELOAD_OK = "Profiles reloaded.";
  private static final String TEXT_PROFILES_RELOAD_FAILED = "Profiles reload failed: %s";
  private static final String MESSAGE_PROFILE_NOT_FOUND = "Profile not found.";

  private static final String MESSAGE_SELECT_PROFILE_REQUIRED = "selectProfile requires args.name.";
  private static final String MESSAGE_SHOW_PROFILE_REQUIRED = "showProfile requires args.name.";
  private static final String MESSAGE_SELECTED_PROFILE_PREFIX = "Selected profile: ";
  private static final String MESSAGE_PROFILE_SELECTED = "Profile selected.";

  private static final Set<String> COMMANDS = Set.of(
      CMD_SELECT_PROFILE,
      CMD_PROFILE_ACTIVATE,
      CMD_RUNTIME_ACTIVATE,
      CMD_RUNTIME_DEACTIVATE,
      CMD_PROFILES_RELOAD,
      CMD_PROFILE_TOGGLE,
      CMD_PROFILES_APPLY,
      CMD_SHOW_PROFILES,
      CMD_SHOW_PROFILE);

  /**
   * NAME
   *   Dependencies - Narrow dependency contract for profile commands.
   */
  interface Dependencies {
    String parseUiArgString(JsonObject args, String key);

    void selectCanProfile(String profileName);

    void prepareActivationForSelectedProfile();

    void activateSelectedProfile();

    void deactivateActiveProfile();

    boolean isProfileActive();

    String getActiveCanProfileLabel();

    String getSelectedCanProfileLabel();

    String getActiveRuntimeProfileLabel();

    String reloadProfilesFromJson();

    void runProfileActivateAction();

    void runProfileDeactivateAction();

    void runProfileToggleAction();

    void selectNextProfile();

    void applyProfilesApplyCommand(BridgeUiCommandResult result, JsonObject args, boolean isTcp);

    Boolean parseUiArgBoolean(JsonObject args, String key);

    void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson);

    String getDefaultCanProfile();

    List<String> getProfileNames();

    List<BringupUtil.DeviceEntry> getProfileDevicesSorted(String profileName);
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
      case CMD_RUNTIME_ACTIVATE:
        executeProfileActivate(args, result);
        break;
      case CMD_RUNTIME_DEACTIVATE:
        executeRuntimeDeactivate(result);
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
      case CMD_SHOW_PROFILES:
        executeShowProfiles(args, result);
        break;
      case CMD_SHOW_PROFILE:
        executeShowProfile(args, result);
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
    result.message = MESSAGE_SELECTED_PROFILE_PREFIX + dependencies.getSelectedCanProfileLabel();
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

  private void executeRuntimeDeactivate(BridgeUiCommandResult result) {
    dependencies.deactivateActiveProfile();
    dependencies.runProfileDeactivateAction();
    result.message = TEXT_RUNTIME_DEACTIVATE_OK;
    result.outText = result.message;
  }

  private void executeShowProfiles(JsonObject args, BridgeUiCommandResult result) {
    boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, ARG_JSON));
    List<String> names = dependencies.getProfileNames();
    dependencies.applyShowResult(result, buildProfilesText(names), buildProfilesJson(names), wantsJson);
  }

  private void executeShowProfile(JsonObject args, BridgeUiCommandResult result) {
    String profileName = dependencies.parseUiArgString(args, ARG_NAME);
    if (profileName == null || profileName.isBlank()) {
      result.ok = false;
      result.message = MESSAGE_SHOW_PROFILE_REQUIRED;
      result.outText = result.message;
      return;
    }
    String selected = profileName.trim();
    List<String> names = dependencies.getProfileNames();
    if (!names.contains(selected)) {
      result.ok = false;
      result.message = MESSAGE_PROFILE_NOT_FOUND;
      result.outText = result.message;
      return;
    }
    List<BringupUtil.DeviceEntry> devices = dependencies.getProfileDevicesSorted(selected);
    boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, ARG_JSON));
    dependencies.applyShowResult(
        result,
        buildProfileText(selected, devices),
        buildProfileJson(selected, devices),
        wantsJson);
  }

  private String buildProfilesText(List<String> names) {
    StringBuilder sb = new StringBuilder();
    sb.append(TEXT_PROFILE_HEADER).append('\n');
    sb.append(String.format(
        TEXT_PROFILE_ACTIVE_FMT,
        dependencies.getActiveCanProfileLabel())).append('\n');
    sb.append(String.format(
        TEXT_PROFILE_SELECTED_FMT,
        dependencies.getSelectedCanProfileLabel())).append('\n');
    sb.append(String.format(
        TEXT_PROFILE_ACTIVE_RUNTIME_FMT,
        dependencies.getActiveRuntimeProfileLabel())).append('\n');
    sb.append(String.format(
        TEXT_PROFILE_RUNTIME_ACTIVE_FMT,
        dependencies.isProfileActive())).append('\n');
    sb.append(String.format(
        TEXT_PROFILE_DEFAULT_FMT,
        dependencies.getDefaultCanProfile())).append('\n');
    sb.append(String.format(TEXT_PROFILE_AVAILABLE_FMT, names.size()));
    return sb.toString();
  }

  private JsonObject buildProfilesJson(List<String> names) {
    JsonObject info = new JsonObject();
    info.addProperty(JSON_KEY_ACTIVE, dependencies.getActiveCanProfileLabel());
    info.addProperty(JSON_KEY_SELECTED, dependencies.getSelectedCanProfileLabel());
    info.addProperty(JSON_KEY_ACTIVE_RUNTIME, dependencies.getActiveRuntimeProfileLabel());
    info.addProperty(JSON_KEY_RUNTIME_ACTIVE, dependencies.isProfileActive());
    info.addProperty(JSON_KEY_DEFAULT, dependencies.getDefaultCanProfile());
    JsonArray available = new JsonArray();
    for (String name : names) {
      available.add(name);
    }
    info.add(JSON_KEY_AVAILABLE, available);
    JsonObject root = new JsonObject();
    root.add(JSON_KEY_PROFILE, info);
    return root;
  }

  private String buildProfileText(String profileName, List<BringupUtil.DeviceEntry> devices) {
    StringBuilder sb = new StringBuilder();
    sb.append(TEXT_PROFILE_HEADER).append('\n');
    sb.append(String.format(TEXT_PROFILE_NAME_FMT, profileName)).append('\n');
    sb.append(String.format(TEXT_PROFILE_DEVICES_HEADER_FMT, devices.size()));
    for (BringupUtil.DeviceEntry entry : devices) {
      if (entry != null && entry.label != null && !entry.label.isBlank()) {
        sb.append('\n').append(String.format(TEXT_PROFILE_DEVICE_FMT, entry.label));
      }
    }
    return sb.toString();
  }

  private JsonObject buildProfileJson(String profileName, List<BringupUtil.DeviceEntry> devices) {
    JsonObject root = new JsonObject();
    root.addProperty(JSON_KEY_PROFILE, profileName);
    JsonArray labels = new JsonArray();
    for (BringupUtil.DeviceEntry entry : devices) {
      if (entry != null && entry.label != null && !entry.label.isBlank()) {
        labels.add(entry.label);
      }
    }
    root.add(JSON_KEY_PROFILE_DEVICES, labels);
    return root;
  }
}

