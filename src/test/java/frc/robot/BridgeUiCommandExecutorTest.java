package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import java.util.List;
import org.junit.jupiter.api.Test;

class BridgeUiCommandExecutorTest {

  private static final String CMD_UI_PING = "uiPing";
  private static final String CMD_UI_HANDSHAKE = "uiHandshake";
  private static final String CMD_UNKNOWN = "doesNotExist";
  private static final String CMD_STOP = "stopCommand";

  private static final String CLIENT_A = "clientA";
  private static final String EMPTY = "";

  private static final String MSG_MISSING_CLIENT = "Missing clientId.";
  private static final String MSG_UNKNOWN_PREFIX = "Unknown command: ";
  private static final String CUSTOM_SUCCESS = "customSuccess";
  private static final String CUSTOM_OUT_TEXT = "customOut";

  @Test
  void validationFailureReturnsErrorWithoutDispatch() {
    TestDeps deps = new TestDeps();
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);
    TrackingFamily family = new TrackingFamily(CMD_UI_PING);
    BridgeUiCommandDispatcher dispatcher = new BridgeUiCommandDispatcher(List.of(family));
    BridgeUiCommandExecutor executor = new BridgeUiCommandExecutor(policy, dispatcher);

    BridgeUiCommandResult result = executor.executeRaw(CMD_UI_PING, "{}", 0.0, EMPTY, false);

    assertFalse(result.ok);
    assertEquals(MSG_MISSING_CLIENT, result.message);
    assertFalse(family.executed);
  }

  @Test
  void validatedIngressDispatchesToFamily() {
    TestDeps deps = new TestDeps();
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);
    TrackingFamily family = new TrackingFamily(CMD_UI_PING);
    BridgeUiCommandDispatcher dispatcher = new BridgeUiCommandDispatcher(List.of(family));
    BridgeUiCommandExecutor executor = new BridgeUiCommandExecutor(policy, dispatcher);

    BridgeUiCommandResult result = executor.executeRaw(CMD_UI_PING, "{}", 2.0, CLIENT_A, false);

    assertTrue(result.ok);
    assertEquals("OK", result.message);
    assertTrue(family.executed);
    assertEquals(CMD_UI_PING, family.executedCommand);
  }

  @Test
  void preExecutionRunsBeforeDispatchForTcpStop() {
    TestDeps deps = new TestDeps();
    deps.activeUiClientId = CLIENT_A;
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);
    TrackingFamily family = new TrackingFamily(CMD_STOP);
    family.deps = deps;
    BridgeUiCommandDispatcher dispatcher = new BridgeUiCommandDispatcher(List.of(family));
    BridgeUiCommandExecutor executor = new BridgeUiCommandExecutor(policy, dispatcher);

    BridgeUiCommandResult result = executor.executeRaw(CMD_STOP, "{}", 3.0, CLIENT_A, true);

    assertTrue(result.ok);
    assertTrue(family.preExecutionObserved);
    assertEquals(1, deps.setStopLatchCalls);
    assertEquals(1, deps.applySafetyStopCalls);
  }

  @Test
  void successPathReturnsDispatcherResultUnchanged() {
    TestDeps deps = new TestDeps();
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);
    TrackingFamily family = new TrackingFamily(CMD_UI_PING);
    family.resultMessage = CUSTOM_SUCCESS;
    family.resultOutText = CUSTOM_OUT_TEXT;
    BridgeUiCommandDispatcher dispatcher = new BridgeUiCommandDispatcher(List.of(family));
    BridgeUiCommandExecutor executor = new BridgeUiCommandExecutor(policy, dispatcher);

    BridgeUiCommandResult result = executor.executeRaw(CMD_UI_PING, "{}", 4.0, CLIENT_A, false);

    assertTrue(result.ok);
    assertEquals(CUSTOM_SUCCESS, result.message);
    assertEquals(CUSTOM_OUT_TEXT, result.outText);
  }

  @Test
  void unknownCommandBehaviorStableThroughExecutorPath() {
    TestDeps deps = new TestDeps();
    deps.activeUiClientId = CLIENT_A;
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);
    BridgeUiCommandDispatcher dispatcher = new BridgeUiCommandDispatcher(List.of());
    BridgeUiCommandExecutor executor = new BridgeUiCommandExecutor(policy, dispatcher);

    BridgeUiCommandResult result = executor.executeRaw(CMD_UNKNOWN, "{}", 5.0, CLIENT_A, true);

    assertFalse(result.ok);
    assertEquals(MSG_UNKNOWN_PREFIX + CMD_UNKNOWN, result.message);
    assertEquals(result.message, result.outText);
  }

  @Test
  void handshakeDispatchesAndReturnsResult() {
    TestDeps deps = new TestDeps();
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);
    TrackingFamily family = new TrackingFamily(CMD_UI_HANDSHAKE);
    BridgeUiCommandDispatcher dispatcher = new BridgeUiCommandDispatcher(List.of(family));
    BridgeUiCommandExecutor executor = new BridgeUiCommandExecutor(policy, dispatcher);

    BridgeUiCommandResult result = executor.executeRaw(CMD_UI_HANDSHAKE, "{}", 6.0, CLIENT_A, false);

    assertNotNull(result);
    assertTrue(result.ok);
    assertTrue(family.executed);
  }

  private static final class TrackingFamily implements BridgeUiCommandDispatcher.CommandFamily {
    private final String handledCommand;
    private boolean executed;
    private String executedCommand = EMPTY;
    private String resultMessage = "OK";
    private String resultOutText = EMPTY;
    private TestDeps deps;
    private boolean preExecutionObserved;

    TrackingFamily(String handledCommand) {
      this.handledCommand = handledCommand;
    }

    @Override
    public boolean handles(String commandName) {
      return handledCommand.equals(commandName);
    }

    @Override
    public BridgeUiCommandResult execute(BridgeUiIngressPolicy.Ingress ingress, double cmdTs, boolean isTcp) {
      BridgeUiCommandResult result = new BridgeUiCommandResult();
      executed = true;
      executedCommand = ingress.name;
      if (deps != null) {
        preExecutionObserved = deps.setStopLatchCalls > 0 && deps.applySafetyStopCalls > 0;
      }
      result.ok = true;
      result.message = resultMessage;
      result.outText = resultOutText;
      return result;
    }
  }

  private static final class TestDeps implements BridgeUiIngressPolicy.Dependencies {
    private String activeUiClientId = EMPTY;
    private boolean stopLatchActive;
    private String stopLatchReason = EMPTY;
    private boolean robotEnabled = true;
    private int setStopLatchCalls;
    private int applySafetyStopCalls;

    @Override
    public JsonObject parseUiArgs(String argsJson) {
      return new JsonObject();
    }

    @Override
    public String getActiveUiClientId() {
      return activeUiClientId;
    }

    @Override
    public boolean stopLatchActive() {
      return stopLatchActive;
    }

    @Override
    public String stopLatchReason() {
      return stopLatchReason;
    }

    @Override
    public boolean isUiCommandAllowedWhenDisabled(String name) {
      return CMD_UI_PING.equals(name);
    }

    @Override
    public boolean isTcpStartCommand(String name, JsonObject args) {
      return false;
    }

    @Override
    public boolean isTcpStopCommand(String name, JsonObject args) {
      return CMD_STOP.equals(name);
    }

    @Override
    public boolean isRobotEnabled() {
      return robotEnabled;
    }

    @Override
    public boolean isRobotEStopped() {
      return false;
    }

    @Override
    public void setStopLatch(String reason) {
      setStopLatchCalls += 1;
    }

    @Override
    public void applySafetyStop(String reason) {
      applySafetyStopCalls += 1;
    }
  }
}

