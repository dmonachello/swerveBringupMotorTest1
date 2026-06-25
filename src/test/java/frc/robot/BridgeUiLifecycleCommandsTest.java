package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import frc.robot.diag.lifecycle.activation.ActivationMode;
import frc.robot.diag.lifecycle.activation.ActivationResult;
import frc.robot.diag.lifecycle.activation.DeactivateResult;
import frc.robot.diag.lifecycle.activation.LifecycleState;
import java.util.List;
import org.junit.jupiter.api.Test;

class BridgeUiLifecycleCommandsTest {

  private static final String CMD_LIFECYCLE_ACTIVATE = "lifecycleActivate";
  private static final String CMD_LIFECYCLE_DEACTIVATE = "lifecycleDeactivate";
  private static final String CMD_LIFECYCLE_DEACTIVATE_ACTIVE =
      "lifecycleDeactivateActive";
  private static final String CMD_SHOW_LIFECYCLE_STATE = "showLifecycleState";
  private static final String CMD_ACTIVATE_SELECTED_TEST_DEVICES =
      "activateSelectedTestDevices";
  private static final String CMD_DEACTIVATE_SELECTED_TEST_DEVICES =
      "deactivateSelectedTestDevices";
  private static final String LABEL_DRIVE = "front_left_drive";

  @Test
  void lifecycleActivateRequiresLabel() {
    LifecycleDeps deps = new LifecycleDeps();
    deps.runtimeActivationAllowed = true;
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_LIFECYCLE_ACTIVATE, new JsonObject()), 0.0, false);

    assertFalse(result.ok);
    assertEquals("lifecycleActivate requires args.label.", result.message);
  }

  @Test
  void lifecycleActivateRejectsInvalidMode() {
    LifecycleDeps deps = new LifecycleDeps();
    deps.runtimeActivationAllowed = true;
    JsonObject args = new JsonObject();
    args.addProperty("label", LABEL_DRIVE);
    args.addProperty("mode", "bogus");
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_LIFECYCLE_ACTIVATE, args), 0.0, false);

    assertFalse(result.ok);
    assertEquals("Invalid lifecycle mode: bogus", result.message);
  }

  @Test
  void lifecycleActivateSuccessReturnsStructuredJson() {
    LifecycleDeps deps = new LifecycleDeps();
    deps.runtimeActivationAllowed = true;
    deps.activationResult =
        new ActivationResult(
            true,
            LABEL_DRIVE,
            "session-1",
            ActivationMode.PROBE_ONLY,
            List.of(LABEL_DRIVE),
            List.of(LABEL_DRIVE),
            List.of(),
            LifecycleState.ACTIVE,
            null,
            null);
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("label", LABEL_DRIVE);
    args.addProperty("mode", "probe_only");

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_LIFECYCLE_ACTIVATE, args), 0.0, false);

    assertTrue(result.ok);
    assertEquals(LABEL_DRIVE, deps.activatedLabel);
    assertEquals(ActivationMode.PROBE_ONLY, deps.activatedMode);
    assertEquals("Lifecycle activated: front_left_drive", result.message);
    assertTrue(result.outJson.contains("\"operation\":\"activate\""));
    assertTrue(result.outJson.contains("\"lifecycle\""));
  }

  @Test
  void lifecycleActivateBlocksWhenRobotNotInEnabledTeleop() {
    LifecycleDeps deps = new LifecycleDeps();
    deps.runtimeActivationAllowed = false;
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("label", LABEL_DRIVE);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_LIFECYCLE_ACTIVATE, args), 0.0, false);

    assertFalse(result.ok);
    assertEquals(
        "Lifecycle activate blocked: robot not in enabled teleop. Enable teleop, then activate lifecycle.",
        result.message);
  }

  @Test
  void lifecycleDeactivateUsesRequestedLabel() {
    LifecycleDeps deps = new LifecycleDeps();
    deps.deactivateResult =
        new DeactivateResult(
            true,
            LABEL_DRIVE,
            "session-1",
            List.of(LABEL_DRIVE),
            LifecycleState.INACTIVE,
            null,
            null);
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("label", LABEL_DRIVE);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_LIFECYCLE_DEACTIVATE, args), 0.0, false);

    assertTrue(result.ok);
    assertEquals(LABEL_DRIVE, deps.deactivatedLabel);
    assertEquals("Lifecycle deactivated: front_left_drive", result.message);
  }

  @Test
  void lifecycleDeactivateActiveUsesActivePath() {
    LifecycleDeps deps = new LifecycleDeps();
    deps.deactivateResult =
        new DeactivateResult(
            true,
            "groupA",
            "session-1",
            List.of(LABEL_DRIVE),
            LifecycleState.INACTIVE,
            null,
            null);
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_LIFECYCLE_DEACTIVATE_ACTIVE, new JsonObject()), 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.deactivateActiveCalled);
    assertEquals("group deactivated", result.message);
  }

  @Test
  void lifecycleActivateForActiveGroupUsesScopeReadyMessage() {
    LifecycleDeps deps = new LifecycleDeps();
    deps.runtimeActivationAllowed = true;
    deps.activationResult =
        new ActivationResult(
            true,
            "active-group",
            "session-1",
            ActivationMode.READ_ONLY,
            List.of("FALCON 9"),
            List.of("FALCON 9"),
            List.of(),
            LifecycleState.ACTIVE,
            null,
            null);
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("label", "active-group");

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_LIFECYCLE_ACTIVATE, args), 0.0, false);

    assertTrue(result.ok);
    assertEquals("active-group active - ready to run", result.message);
  }

  @Test
  void activateSelectedTestDevicesUsesSelectedTestPath() {
    LifecycleDeps deps = new LifecycleDeps();
    deps.runtimeActivationAllowed = true;
    deps.activationResult =
        new ActivationResult(
            true,
            "selected-test:testA",
            "session-1",
            ActivationMode.READ_ONLY,
            List.of("SPARKMAX/NEO 25"),
            List.of("SPARKMAX/NEO 25"),
            List.of(),
            LifecycleState.ACTIVE,
            null,
            null);
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);

    BridgeUiCommandResult result =
        commands.execute(
            ingress(CMD_ACTIVATE_SELECTED_TEST_DEVICES, new JsonObject()), 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.activateSelectedTestDevicesCalled);
    assertEquals("active-group active - ready to run", result.message);
  }

  @Test
  void deactivateSelectedTestDevicesUsesSelectedTestPath() {
    LifecycleDeps deps = new LifecycleDeps();
    deps.deactivateResult =
        new DeactivateResult(
            true,
            "selected-test:testA",
            "session-1",
            List.of("SPARKMAX/NEO 25"),
            LifecycleState.INACTIVE,
            null,
            null);
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);

    BridgeUiCommandResult result =
        commands.execute(
            ingress(CMD_DEACTIVATE_SELECTED_TEST_DEVICES, new JsonObject()), 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.deactivateSelectedTestDevicesCalled);
    assertEquals("group deactivated", result.message);
  }

  @Test
  void lifecycleDeactivateActiveAlreadyInactiveReturnsReminder() {
    LifecycleDeps deps = new LifecycleDeps();
    deps.deactivateResult =
        new DeactivateResult(
            true,
            "active-group",
            null,
            List.of(),
            LifecycleState.INACTIVE,
            null,
            null);
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_LIFECYCLE_DEACTIVATE_ACTIVE, new JsonObject()), 0.0, false);

    assertTrue(result.ok);
    assertEquals("Group already inactive. Nothing changed.", result.message);
  }

  @Test
  void showLifecycleStateSupportsJsonMode() {
    LifecycleDeps deps = new LifecycleDeps();
    BridgeUiLifecycleCommands commands = new BridgeUiLifecycleCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty("json", true);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_SHOW_LIFECYCLE_STATE, args), 0.0, false);

    assertTrue(result.ok);
    assertEquals("", result.outText);
    assertTrue(result.outJson.contains("\"available\":true"));
  }

  private static BridgeUiIngressPolicy.Ingress ingress(String name, JsonObject args) {
    return new BridgeUiIngressPolicy.Ingress(
        name,
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
  }

  private static final class LifecycleDeps implements BridgeUiLifecycleCommands.Dependencies {
    private String activatedLabel;
    private ActivationMode activatedMode;
    private String deactivatedLabel;
    private boolean deactivateActiveCalled;
    private boolean activateSelectedTestDevicesCalled;
    private boolean deactivateSelectedTestDevicesCalled;
    private boolean runtimeActivationAllowed;
    private ActivationResult activationResult =
        new ActivationResult(
            false,
            "",
            null,
            ActivationMode.READ_ONLY,
            List.of(),
            List.of(),
            List.of(),
            LifecycleState.INACTIVE,
            "error",
            "error");
    private DeactivateResult deactivateResult =
        new DeactivateResult(
            false,
            "",
            null,
            List.of(),
            LifecycleState.INACTIVE,
            "error",
            "error");

    @Override
    public String parseUiArgString(JsonObject args, String key) {
      if (args == null || !args.has(key)) {
        return null;
      }
      return args.get(key).getAsString();
    }

    @Override
    public Boolean parseUiArgBoolean(JsonObject args, String key) {
      if (args == null || !args.has(key)) {
        return null;
      }
      return args.get(key).getAsBoolean();
    }

    @Override
    public void applyShowResult(
        BridgeUiCommandResult result,
        String text,
        JsonObject json,
        boolean wantsJson) {
      result.ok = true;
      if (wantsJson) {
        result.outText = "";
        result.outJson = json.toString();
      } else {
        result.outText = text;
      }
    }

    @Override
    public boolean isRuntimeActivationAllowed() {
      return runtimeActivationAllowed;
    }

    @Override
    public ActivationResult activateLifecycle(String label, ActivationMode mode) {
      activatedLabel = label;
      activatedMode = mode;
      return activationResult;
    }

    @Override
    public ActivationResult activateSelectedTestDevices(ActivationMode mode) {
      activateSelectedTestDevicesCalled = true;
      activatedMode = mode;
      return activationResult;
    }

    @Override
    public DeactivateResult deactivateLifecycle(String label) {
      deactivatedLabel = label;
      return deactivateResult;
    }

    @Override
    public DeactivateResult deactivateSelectedTestDevices() {
      deactivateSelectedTestDevicesCalled = true;
      return deactivateResult;
    }

    @Override
    public DeactivateResult deactivateActiveLifecycle() {
      deactivateActiveCalled = true;
      return deactivateResult;
    }

    @Override
    public String buildLifecycleStateText() {
      return "lifecycle text";
    }

    @Override
    public JsonObject buildLifecycleStateJson() {
      JsonObject json = new JsonObject();
      json.addProperty("available", true);
      return json;
    }
  }
}
