package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;

class BridgeUiProfileCommandsTest {

  private static final String CMD_SELECT_PROFILE = "selectProfile";
  private static final String CMD_PROFILE_ACTIVATE = "profileActivate";
  private static final String CMD_RUNTIME_ACTIVATE = "runtimeActivate";
  private static final String CMD_RUNTIME_DEACTIVATE = "runtimeDeactivate";
  private static final String CMD_SHOW_PROFILES = "showProfiles";
  private static final String CMD_SHOW_PROFILE = "showProfile";

  @Test
  void selectProfileRequiresName() {
    ProfileDeps deps = new ProfileDeps();
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_SELECT_PROFILE,
        new JsonObject(),
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertFalse(result.ok);
    assertEquals("selectProfile requires args.name.", result.message);
  }

  @Test
  void profileActivateSuccessRunsActivateAction() {
    ProfileDeps deps = new ProfileDeps();
    deps.nextName = "alpha";
    deps.profileActive = true;
    deps.activeRuntimeProfile = "alpha";
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_PROFILE_ACTIVATE,
        new JsonObject(),
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.activateActionRan);
    assertTrue(result.message.startsWith("Profile activated:"));
  }

  @Test
  void runtimeActivateSuccessRunsActivateAction() {
    ProfileDeps deps = new ProfileDeps();
    deps.profileActive = true;
    deps.runtimeActivationAllowed = true;
    deps.activeRuntimeProfile = "beta";
    deps.nextName = "beta";
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_RUNTIME_ACTIVATE,
        new JsonObject(),
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.activateActionRan);
    assertTrue(result.message.startsWith("Profile activated:"));
  }

  @Test
  void runtimeActivatePassesScopeAllWithoutGroup() {
    ProfileDeps deps = new ProfileDeps();
    deps.profileActive = true;
    deps.runtimeActivationAllowed = true;
    deps.activeRuntimeProfile = "beta";
    deps.selectedProfileLabel = "beta";
    deps.scopeArg = "all";
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("scope", "all");
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_RUNTIME_ACTIVATE,
        args,
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertTrue(result.ok);
    assertEquals("all", deps.requestedScopeMode);
    assertEquals("", deps.requestedScopeGroup);
  }

  @Test
  void runtimeActivatePassesGroupScopeAndGroupName() {
    ProfileDeps deps = new ProfileDeps();
    deps.profileActive = true;
    deps.runtimeActivationAllowed = true;
    deps.activeRuntimeProfile = "beta";
    deps.selectedProfileLabel = "beta";
    deps.scopeModeArg = "group";
    deps.groupArg = "motors";
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("scopeMode", "group");
    args.addProperty("group", "motors");
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_RUNTIME_ACTIVATE,
        args,
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertTrue(result.ok);
    assertEquals("group", deps.requestedScopeMode);
    assertEquals("motors", deps.requestedScopeGroup);
  }

  @Test
  void runtimeActivateFailsClearlyWhenNoProfileIsSelected() {
    ProfileDeps deps = new ProfileDeps();
    deps.runtimeActivationAllowed = true;
    deps.selectedProfileLabel = "(none)";
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_RUNTIME_ACTIVATE,
        new JsonObject(),
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertFalse(result.ok);
    assertEquals("No profile selected.", result.message);
  }

  @Test
  void runtimeActivateFailsClearlyWhenRobotNotInTeleop() {
    ProfileDeps deps = new ProfileDeps();
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_RUNTIME_ACTIVATE,
        new JsonObject(),
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertFalse(result.ok);
    assertEquals(
        "Runtime activate blocked: robot not in enabled teleop. Enable teleop, then activate runtime.",
        result.message);
  }

  @Test
  void runtimeDeactivateRunsDeactivateAction() {
    ProfileDeps deps = new ProfileDeps();
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_RUNTIME_DEACTIVATE,
        new JsonObject(),
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.deactivateCalled);
    assertTrue(deps.deactivateActionRan);
    assertEquals("Runtime deactivated.", result.message);
  }

  @Test
  void selectProfileReportsSelectedProfileNotActiveProfile() {
    ProfileDeps deps = new ProfileDeps();
    deps.nextName = "beta";
    deps.selectedProfileLabel = "beta";
    deps.activeProfileLabel = "alpha";
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_SELECT_PROFILE,
        new JsonObject(),
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertTrue(result.ok);
    assertEquals("Selected profile: beta", result.message);
  }

  @Test
  void showProfilesJsonIncludesSelectedAndRuntimeState() {
    ProfileDeps deps = new ProfileDeps();
    deps.selectedProfileLabel = "beta";
    deps.activeProfileLabel = "beta (inactive)";
    deps.profileActive = false;
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_SHOW_PROFILES,
        new JsonObject(),
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertTrue(result.ok);
    assertTrue(result.outJson.contains("\"selected\":\"beta\""));
    assertTrue(result.outJson.contains("\"runtimeActive\":false"));
  }

  @Test
  void showProfileJsonIncludesDeviceLabels() {
    ProfileDeps deps = new ProfileDeps();
    deps.nextName = "alpha";
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_SHOW_PROFILE,
        new JsonObject(),
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertTrue(result.ok);
    assertTrue(result.outJson.contains("\"profile\":\"alpha\""));
    assertTrue(result.outJson.contains("\"driveA\""));
  }

  private static final class ProfileDeps implements BridgeUiProfileCommands.Dependencies {
    private String nextName;
    private boolean profileActive;
    private boolean runtimeActivationAllowed;
    private boolean activateActionRan;
    private boolean deactivateActionRan;
    private boolean deactivateCalled;
    private String activeRuntimeProfile = "";
    private String selectedProfileLabel = "alpha";
    private String activeProfileLabel = "alpha";
    private String requestedScopeMode = "all";
    private String requestedScopeGroup = "";
    private String scopeArg;
    private String scopeModeArg;
    private String groupArg;

    @Override
    public String parseUiArgString(JsonObject args, String key) {
      if ("name".equals(key)) {
        return nextName;
      }
      if ("scope".equals(key)) {
        return scopeArg;
      }
      if ("scopeMode".equals(key)) {
        return scopeModeArg;
      }
      if ("group".equals(key)) {
        return groupArg;
      }
      return null;
    }

    @Override
    public void selectCanProfile(String profileName) {}

    @Override
    public void prepareActivationForSelectedProfile() {}

    @Override
    public void activateSelectedProfile(String scopeMode, String groupName) {
      if (scopeMode != null && !scopeMode.isBlank()) {
        requestedScopeMode = scopeMode;
      }
      requestedScopeGroup = groupName != null ? groupName : "";
    }

    @Override
    public void deactivateActiveProfile() {
      deactivateCalled = true;
    }

    @Override
    public boolean isProfileActive() {
      return profileActive;
    }

    @Override
    public boolean isRuntimeDeclaredActive() {
      return profileActive;
    }

    @Override
    public boolean isRuntimeActivationAllowed() {
      return runtimeActivationAllowed;
    }

    @Override
    public String getActiveCanProfileLabel() {
      return activeProfileLabel;
    }

    @Override
    public String getSelectedCanProfileLabel() {
      return selectedProfileLabel;
    }

    @Override
    public String getActiveRuntimeProfileLabel() {
      return activeRuntimeProfile;
    }

    @Override
    public String getRequestedScopeMode() {
      return requestedScopeMode;
    }

    @Override
    public String getRequestedScopeGroup() {
      return requestedScopeGroup;
    }

    @Override
    public String reloadProfilesFromJson() {
      return "";
    }

    @Override
    public void runProfileActivateAction() {
      activateActionRan = true;
    }

    @Override
    public void runProfileDeactivateAction() {
      deactivateActionRan = true;
    }

    @Override
    public void runProfileToggleAction() {}

    @Override
    public void selectNextProfile() {}

    @Override
    public void applyProfilesApplyCommand(BridgeUiCommandResult result, JsonObject args, boolean isTcp) {}

    @Override
    public Boolean parseUiArgBoolean(JsonObject args, String key) {
      return true;
    }

    @Override
    public void applyShowResult(
        BridgeUiCommandResult result,
        String text,
        JsonObject json,
        boolean wantsJson) {
      if (wantsJson) {
        result.outJson = json.toString();
      } else {
        result.outText = text;
      }
    }

    @Override
    public String getDefaultCanProfile() {
      return "alpha";
    }

    @Override
    public List<String> getProfileNames() {
      return List.of("alpha");
    }

    @Override
    public List<BringupUtil.DeviceEntry> getProfileDevicesSorted(String profileName) {
      return List.of(new BringupUtil.DeviceEntry(
          1,
          5,
          2,
          "CAN",
          "REV",
          "motor",
          "driveA",
          "",
          null,
          Collections.emptyList(),
          null));
    }
  }
}
