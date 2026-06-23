package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import org.junit.jupiter.api.Test;

class BridgeUiIngressPolicyTest {

  private static final String EMPTY = "";
  private static final String CMD_UI_PING = "uiPing";
  private static final String CMD_UI_HANDSHAKE = "uiHandshake";
  private static final String CMD_SHOW_STATUS = "showStatus";
  private static final String CMD_SHOW_VERSION = "showVersion";
  private static final String CMD_SHOW_TESTS = "showTests";
  private static final String CMD_START = "startCommand";
  private static final String CMD_STOP = "stopCommand";

  private static final String MSG_MISSING_COMMAND = "Missing command name.";
  private static final String MSG_MISSING_CLIENT = "Missing clientId.";
  private static final String MSG_HANDSHAKE_REQUIRED = "UI handshake required before commands.";
  private static final String MSG_LOCK_CONFLICT =
      "UI locked by another client. Disconnect or reboot to switch.";
  private static final String MSG_DISABLED = "Robot disabled.";

  @Test
  void validatesMissingCommandName() {
    TestDeps deps = new TestDeps();
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(EMPTY, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, false);

    assertNotNull(failure);
    assertEquals(MSG_MISSING_COMMAND, failure.message);
  }

  @Test
  void validatesMissingClientId() {
    TestDeps deps = new TestDeps();
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_UI_PING, "{}", "");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, false);

    assertNotNull(failure);
    assertEquals(MSG_MISSING_CLIENT, failure.message);
  }

  @Test
  void requiresHandshakeForTcpCommandWhenUnlocked() {
    TestDeps deps = new TestDeps();
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_SHOW_STATUS, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, true);

    assertNotNull(failure);
    assertEquals(MSG_HANDSHAKE_REQUIRED, failure.message);
  }

  @Test
  void allowsRestCommandWithoutTcpHandshakeLock() {
    TestDeps deps = new TestDeps();
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_SHOW_STATUS, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, false);

    assertNull(failure);
  }

  @Test
  void blocksDifferentClientWhenTcpSessionLocked() {
    TestDeps deps = new TestDeps();
    deps.activeUiClientId = "clientA";
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_UI_HANDSHAKE, "{}", "clientB");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, true);

    assertNotNull(failure);
    assertEquals(MSG_LOCK_CONFLICT, failure.message);
  }

  @Test
  void allowsPingWithClientWithoutHandshake() {
    TestDeps deps = new TestDeps();
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_UI_PING, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, false);

    assertNull(failure);
  }

  @Test
  void blocksTcpStartWhenStopLatchActive() {
    TestDeps deps = new TestDeps();
    deps.activeUiClientId = "clientA";
    deps.stopLatchActive = true;
    deps.stopLatchReason = "tcpTimeout";
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_START, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, true);

    assertNotNull(failure);
    assertTrue(failure.message.contains("Stop latch active"));
  }

  @Test
  void blocksDisabledRobotForNonAllowlistedCommand() {
    TestDeps deps = new TestDeps();
    deps.robotEnabled = false;
    deps.activeUiClientId = "clientA";
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_SHOW_STATUS, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, true);

    assertNotNull(failure);
    assertEquals(MSG_DISABLED, failure.message);
  }

  @Test
  void allowsDisabledRobotForAllowlistedCommand() {
    TestDeps deps = new TestDeps();
    deps.robotEnabled = false;
    deps.activeUiClientId = "clientA";
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_UI_PING, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, true);

    assertNull(failure);
  }

  @Test
  void allowsStopCommandWithoutHandshake() {
    TestDeps deps = new TestDeps();
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_STOP, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, true);

    assertNull(failure);
  }

  @Test
  void allowsDisabledRobotForShowTestsCommand() {
    TestDeps deps = new TestDeps();
    deps.robotEnabled = false;
    deps.activeUiClientId = "clientA";
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_SHOW_TESTS, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, true);

    assertNull(failure);
  }

  @Test
  void allowsDisabledRobotForShowVersionCommand() {
    TestDeps deps = new TestDeps();
    deps.robotEnabled = false;
    deps.activeUiClientId = "clientA";
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_SHOW_VERSION, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, true);

    assertNull(failure);
  }

  @Test
  void appliesTcpStopPreExecutionSideEffects() {
    TestDeps deps = new TestDeps();
    deps.activeUiClientId = "clientA";
    BridgeUiIngressPolicy policy = new BridgeUiIngressPolicy(deps);

    BridgeUiIngressPolicy.Ingress ingress = policy.parseIngress(CMD_STOP, "{}", "clientA");
    BridgeUiIngressPolicy.ValidationFailure failure = policy.validateIngress(ingress, true);
    assertNull(failure);

    policy.applyPreExecution(ingress, true);

    assertEquals(1, deps.setStopLatchCalls);
    assertEquals(1, deps.applySafetyStopCalls);
    assertEquals("tcpStop", deps.lastStopReason);
  }

  private static final class TestDeps implements BridgeUiIngressPolicy.Dependencies {
    private String activeUiClientId = EMPTY;
    private boolean stopLatchActive;
    private String stopLatchReason = EMPTY;
    private boolean robotEnabled = true;
    private int setStopLatchCalls;
    private int applySafetyStopCalls;
    private String lastStopReason = EMPTY;

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
      return CMD_UI_PING.equals(name)
          || CMD_SHOW_TESTS.equals(name)
          || CMD_SHOW_VERSION.equals(name);
    }

    @Override
    public boolean isTcpStartCommand(String name, JsonObject args) {
      return CMD_START.equals(name);
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
      lastStopReason = reason;
    }

    @Override
    public void applySafetyStop(String reason) {
      applySafetyStopCalls += 1;
      lastStopReason = reason;
    }
  }
}
