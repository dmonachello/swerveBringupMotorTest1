package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import org.junit.jupiter.api.Test;

class BridgeUiRuntimeCommandsTest {

  private static final String CMD_ADD_MOTOR = "addMotor";
  private static final String CMD_ADD_ALL = "addAll";
  private static final String CMD_CLEAR_STOP_LATCH = "clearStopLatch";
  private static final String CMD_TOGGLE_DASHBOARD = "toggleDashboard";

  private static final String MSG_STAGE_FAILED =
      "Failed to stage selected profile for incremental bringup: stageFailed";
  private static final String MSG_STOP_LATCH_CLEARED = "Stop latch cleared.";
  private static final String MSG_STOP_LATCH_NOT_ACTIVE = "Stop latch not active.";

  @Test
  void addMotorStagesSelectedProfileInsteadOfActivatingRuntime() {
    TestDeps deps = new TestDeps();
    deps.profileActive = false;
    BridgeUiRuntimeCommands commands = new BridgeUiRuntimeCommands(deps);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_ADD_MOTOR), 0.0, false);

    assertTrue(result.ok);
    assertEquals("Add motor.", result.message);
    assertEquals(1, deps.stageBringupCalls);
    assertEquals(1, deps.addNextMotorCalls);
    assertEquals(0, deps.addAllDevicesCalls);
  }

  @Test
  void addAllStagesSelectedProfileInsteadOfActivatingRuntime() {
    TestDeps deps = new TestDeps();
    deps.profileActive = false;
    BridgeUiRuntimeCommands commands = new BridgeUiRuntimeCommands(deps);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_ADD_ALL), 0.0, false);

    assertTrue(result.ok);
    assertEquals("Instantiated all configured devices. Use active add to populate active-group.", result.message);
    assertEquals(1, deps.stageBringupCalls);
    assertEquals(1, deps.addAllDevicesCalls);
  }

  @Test
  void addMotorReturnsStageFailureWhenSelectedProfileCannotBePrepared() {
    TestDeps deps = new TestDeps();
    deps.profileActive = false;
    deps.stageBringupError = "stageFailed";
    BridgeUiRuntimeCommands commands = new BridgeUiRuntimeCommands(deps);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_ADD_MOTOR), 0.0, false);

    assertFalse(result.ok);
    assertEquals(MSG_STAGE_FAILED, result.message);
    assertEquals(0, deps.addNextMotorCalls);
  }

  @Test
  void clearStopLatchMessageReflectsState() {
    TestDeps deps = new TestDeps();
    BridgeUiRuntimeCommands commands = new BridgeUiRuntimeCommands(deps);

    deps.clearStopLatchResult = true;
    BridgeUiCommandResult cleared = commands.execute(ingress(CMD_CLEAR_STOP_LATCH), 0.0, false);
    assertEquals(MSG_STOP_LATCH_CLEARED, cleared.outText);

    deps.clearStopLatchResult = false;
    BridgeUiCommandResult notActive = commands.execute(ingress(CMD_CLEAR_STOP_LATCH), 0.0, false);
    assertEquals(MSG_STOP_LATCH_NOT_ACTIVE, notActive.outText);
  }

  @Test
  void toggleDashboardFlipsStateAndAppliesUpdate() {
    TestDeps deps = new TestDeps();
    deps.dashboardEnabled = false;
    BridgeUiRuntimeCommands commands = new BridgeUiRuntimeCommands(deps);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_TOGGLE_DASHBOARD), 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.dashboardEnabled);
    assertEquals(1, deps.applyDashboardStateCalls);
  }

  private static BridgeUiIngressPolicy.Ingress ingress(String name) {
    return new BridgeUiIngressPolicy.Ingress(
        name,
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
  }

  private static final class TestDeps implements BridgeUiRuntimeCommands.Dependencies {
    private boolean profileActive;
    private String stageBringupError = "";
    private int stageBringupCalls;
    private int addNextMotorCalls;
    private int addAllDevicesCalls;

    private boolean dashboardEnabled;
    private int applyDashboardStateCalls;

    private boolean clearStopLatchResult;

    @Override
    public String stageSelectedProfileForBringup() {
      stageBringupCalls += 1;
      return stageBringupError;
    }

    @Override
    public boolean isProfileActive() {
      return profileActive;
    }

    @Override
    public void addNextMotorCommand() {
      addNextMotorCalls += 1;
    }

    @Override
    public void addAllDevicesCommand() {
      addAllDevicesCalls += 1;
    }

    @Override
    public void setDashboardUpdatesEnabled(boolean enabled) {
      dashboardEnabled = enabled;
    }

    @Override
    public boolean isDashboardUpdatesEnabled() {
      return dashboardEnabled;
    }

    @Override
    public void applyDashboardUpdateState() {
      applyDashboardStateCalls += 1;
    }

    @Override
    public void enqueuePrint(String text) {}

    @Override
    public void clearAllFaults() {}

    @Override
    public boolean clearStopLatchFromUi(String reason) {
      return clearStopLatchResult;
    }

    @Override
    public String buildCanPingSweepReportText() {
      return "sweep";
    }

    @Override
    public void requestTextReport(String text, int batchSize) {}

  }
}
