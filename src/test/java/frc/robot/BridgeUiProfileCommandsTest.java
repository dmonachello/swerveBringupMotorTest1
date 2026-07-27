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
  private static final String CMD_PROFILE_TOGGLE = "profileToggle";
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
    deps.runtimeScopeActivationSuccess = true;
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
    assertTrue(deps.runtimeScopeActivateCalled);
    assertTrue(result.message.startsWith("Profile activated:"));
  }

  @Test
  void runtimeActivateSameSelectedProfileDoesNotReselectAndClearRuntimeState() {
    ProfileDeps deps = new ProfileDeps();
    deps.profileActive = true;
    deps.runtimeActivationAllowed = true;
    deps.runtimeScopeActivationSuccess = true;
    deps.activeRuntimeProfile = "beta";
    deps.selectedProfileLabel = "beta";
    deps.activeProfileLabel = "beta";
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
    assertFalse(deps.selectCanProfileCalled);
    assertTrue(deps.runtimeScopeActivateCalled);
  }

  @Test
  void runtimeActivateDifferentProfileReselectsBeforeActivation() {
    ProfileDeps deps = new ProfileDeps();
    deps.profileActive = true;
    deps.runtimeActivationAllowed = true;
    deps.runtimeScopeActivationSuccess = true;
    deps.activeRuntimeProfile = "beta";
    deps.selectedProfileLabel = "alpha";
    deps.activeProfileLabel = "beta";
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
    assertTrue(deps.selectCanProfileCalled);
    assertEquals("beta", deps.lastSelectedProfileName);
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
    deps.runtimeScopeDeactivateSuccess = true;
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
    assertTrue(deps.runtimeScopeDeactivateCalled);
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
  void selectProfileBlockedWhenControlledLifecycleIsActive() {
    ProfileDeps deps = new ProfileDeps();
    deps.nextName = "beta";
    deps.controlledLifecycleActive = true;
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
    assertEquals(
        "Profile change blocked: an active scope session is running. Deactivate scope first.",
        result.message);
  }

  @Test
  void profileToggleBlockedWhenControlledLifecycleIsActive() {
    ProfileDeps deps = new ProfileDeps();
    deps.controlledLifecycleActive = true;
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_PROFILE_TOGGLE,
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
        "Profile change blocked: an active scope session is running. Deactivate scope first.",
        result.message);
  }

  @Test
  void showProfilesJsonIncludesSelectedAndRuntimeState() {
    ProfileDeps deps = new ProfileDeps();
    deps.selectedProfileLabel = "beta";
    deps.activeProfileLabel = "beta (inactive)";
    deps.profileActive = false;
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("json", true);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_SHOW_PROFILES,
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
    assertTrue(result.outJson.contains("\"selected\":\"beta\""));
    assertTrue(result.outJson.contains("\"runtimeActive\":false"));
  }

  @Test
  void showProfilesTextIncludesAvailableProfileNames() {
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
    assertTrue(result.outText.contains("  available=2"));
    assertTrue(result.outText.contains("    alpha"));
    assertTrue(result.outText.contains("    beta"));
  }

  @Test
  void showProfileJsonIncludesDeviceLabels() {
    ProfileDeps deps = new ProfileDeps();
    deps.nextName = "alpha";
    BridgeUiProfileCommands commands = new BridgeUiProfileCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("json", true);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_SHOW_PROFILE,
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
    private boolean selectCanProfileCalled;
    private boolean controlledLifecycleActive;
    private boolean runtimeScopeActivateCalled;
    private boolean runtimeScopeDeactivateCalled;
    private boolean runtimeScopeActivationSuccess;
    private boolean runtimeScopeDeactivateSuccess;
    private String nextMembershipMode;
    private String activeRuntimeProfile = "";
    private String selectedProfileLabel = "alpha";
    private String activeProfileLabel = "alpha";
    private String lastSelectedProfileName = "";

    @Override
    public String parseUiArgString(JsonObject args, String key) {
      if ("membershipMode".equals(key)) {
        return nextMembershipMode;
      }
      return nextName;
    }

    @Override
    public void selectCanProfile(String profileName) {
      selectCanProfileCalled = true;
      lastSelectedProfileName = profileName;
      selectedProfileLabel = profileName;
    }

    @Override
    public boolean isSameSelectedProfile(String profileName) {
      return profileName != null && profileName.equals(selectedProfileLabel);
    }

    @Override
    public void prepareActivationForSelectedProfile() {}

    @Override
    public void activateSelectedProfile() {}

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
    public boolean isControlledLifecycleActive() {
      return controlledLifecycleActive;
    }

    @Override
    public frc.robot.diag.lifecycle.activation.ActivationResult activateRuntimeActiveGroup(
        frc.robot.diag.lifecycle.activation.ActivationMode mode,
        frc.robot.diag.lifecycle.activation.ActivationMembershipMode membershipMode) {
      runtimeScopeActivateCalled = true;
      return new frc.robot.diag.lifecycle.activation.ActivationResult(
          runtimeScopeActivationSuccess,
          "active-group",
          "",
          mode,
          membershipMode,
          List.of(),
          List.of(),
          List.of(),
          List.of(),
          frc.robot.diag.lifecycle.activation.LifecycleState.ACTIVE,
          runtimeScopeActivationSuccess ? "" : "scope_failed",
          runtimeScopeActivationSuccess ? "" : "scope_failed");
    }

    @Override
    public frc.robot.diag.lifecycle.activation.DeactivateResult deactivateRuntimeActiveGroup() {
      runtimeScopeDeactivateCalled = true;
      return new frc.robot.diag.lifecycle.activation.DeactivateResult(
          runtimeScopeDeactivateSuccess,
          "active-group",
          "",
          List.of(),
          frc.robot.diag.lifecycle.activation.LifecycleState.INACTIVE,
          runtimeScopeDeactivateSuccess ? "" : "scope_failed",
          runtimeScopeDeactivateSuccess ? "" : "scope_failed");
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
      return args != null && args.has(key) ? args.get(key).getAsBoolean() : null;
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
      return List.of("alpha", "beta");
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

