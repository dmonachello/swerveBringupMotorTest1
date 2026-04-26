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
    private boolean activateActionRan;

    @Override
    public String parseUiArgString(JsonObject args, String key) {
      return nextName;
    }

    @Override
    public void selectCanProfile(String profileName) {}

    @Override
    public void prepareActivationForSelectedProfile() {}

    @Override
    public void activateSelectedProfile() {}

    @Override
    public boolean isProfileActive() {
      return profileActive;
    }

    @Override
    public String getActiveCanProfileLabel() {
      return "alpha";
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

