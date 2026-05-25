package frc.robot;

import com.google.gson.JsonObject;

/**
 * NAME
 *   BridgeUiIngressPolicy - Parse/validate/pre-exec policy for UI command ingress.
 */
final class BridgeUiIngressPolicy {

  private static final String CMD_UI_PING = "uiPing";
  private static final String CMD_UI_HANDSHAKE = "uiHandshake";
  private static final String CMD_UI_DISCONNECT = "uiDisconnect";
  private static final String CMD_STOP = "stopCommand";
  private static final String TEXT_UI_MISSING_COMMAND_NAME = "Missing command name.";
  private static final String TEXT_UI_MISSING_CLIENT_ID = "Missing clientId.";
  private static final String TEXT_UI_LOCKED_BY_OTHER_CLIENT =
      "UI locked by another client. Disconnect or reboot to switch.";
  private static final String TEXT_UI_HANDSHAKE_REQUIRED = "UI handshake required before commands.";
  private static final String TEXT_UI_STOP_LATCH_ACTIVE_PREFIX = "Stop latch active";
  private static final String TEXT_UI_STOP_LATCH_ACTIVE_CLEAR_SUFFIX =
      " Clear from Xbox or UI to resume.";
  private static final String TEXT_UI_DISABLED = "Robot disabled.";
  private static final String TEXT_UI_DISABLED_ESTOP = "Robot disabled (E-Stop).";
  private static final String STOP_REASON_TCP_STOP = "tcpStop";

  /**
   * NAME
   *   Dependencies - Runtime dependencies for ingress policy decisions.
   */
  interface Dependencies {
    JsonObject parseUiArgs(String argsJson);

    String getActiveUiClientId();

    boolean stopLatchActive();

    String stopLatchReason();

    boolean isUiCommandAllowedWhenDisabled(String name);

    boolean isTcpStartCommand(String name, JsonObject args);

    boolean isTcpStopCommand(String name, JsonObject args);

    boolean isRobotEnabled();

    boolean isRobotEStopped();

    void setStopLatch(String reason);

    void applySafetyStop(String reason);
  }

  /**
   * NAME
   *   Ingress - Parsed ingress context for UI command processing.
   */
  static final class Ingress {
    final String name;
    final JsonObject args;
    final String client;
    final boolean hasClient;
    final boolean locked;
    final boolean isHandshake;
    final boolean isDisconnect;
    final boolean isPing;
    final boolean allowWhenDisabled;
    final boolean isEnabled;
    final boolean isEStopped;

    Ingress(
        String name,
        JsonObject args,
        String client,
        boolean hasClient,
        boolean locked,
        boolean isHandshake,
        boolean isDisconnect,
        boolean isPing,
        boolean allowWhenDisabled,
        boolean isEnabled,
        boolean isEStopped) {
      this.name = name;
      this.args = args;
      this.client = client;
      this.hasClient = hasClient;
      this.locked = locked;
      this.isHandshake = isHandshake;
      this.isDisconnect = isDisconnect;
      this.isPing = isPing;
      this.allowWhenDisabled = allowWhenDisabled;
      this.isEnabled = isEnabled;
      this.isEStopped = isEStopped;
    }
  }

  /**
   * NAME
   *   ValidationFailure - Encoded ingress validation failure message.
   */
  static final class ValidationFailure {
    final String message;

    ValidationFailure(String message) {
      this.message = message;
    }
  }

  private final Dependencies dependencies;

  BridgeUiIngressPolicy(Dependencies dependencies) {
    this.dependencies = dependencies;
  }

  Ingress parseIngress(String name, String argsJson, String clientId) {
    JsonObject args = dependencies.parseUiArgs(argsJson);
    String client = clientId != null ? clientId.trim() : "";
    boolean hasClient = !client.isEmpty();
    String activeClientId = dependencies.getActiveUiClientId();
    boolean locked = activeClientId != null && !activeClientId.isBlank();
    boolean isHandshake = CMD_UI_HANDSHAKE.equals(name);
    boolean isDisconnect = CMD_UI_DISCONNECT.equals(name);
    boolean isPing = CMD_UI_PING.equals(name);
    boolean allowWhenDisabled = dependencies.isUiCommandAllowedWhenDisabled(name);
    boolean isEnabled = dependencies.isRobotEnabled();
    boolean isEStopped = dependencies.isRobotEStopped();
    return new Ingress(
        name,
        args,
        client,
        hasClient,
        locked,
        isHandshake,
        isDisconnect,
        isPing,
        allowWhenDisabled,
        isEnabled,
        isEStopped);
  }

  ValidationFailure validateIngress(Ingress ingress, boolean isTcp) {
    if (ingress.name == null || ingress.name.isBlank()) {
      return new ValidationFailure(TEXT_UI_MISSING_COMMAND_NAME);
    }
    String activeClientId = dependencies.getActiveUiClientId();
    if (!ingress.hasClient) {
      return new ValidationFailure(TEXT_UI_MISSING_CLIENT_ID);
    }
    if (ingress.locked && !ingress.client.equals(activeClientId)) {
      return new ValidationFailure(TEXT_UI_LOCKED_BY_OTHER_CLIENT);
    }
    if (!ingress.locked
        && !ingress.isHandshake
        && !ingress.isDisconnect
        && !ingress.isPing
        && !CMD_STOP.equals(ingress.name)) {
      return new ValidationFailure(TEXT_UI_HANDSHAKE_REQUIRED);
    }
    if (isTcp && dependencies.isTcpStartCommand(ingress.name, ingress.args) && dependencies.stopLatchActive()) {
      String reason = dependencies.stopLatchReason();
      String detail = (reason == null || reason.isBlank()) ? "." : " (" + reason + ").";
      return new ValidationFailure(
          TEXT_UI_STOP_LATCH_ACTIVE_PREFIX + detail + TEXT_UI_STOP_LATCH_ACTIVE_CLEAR_SUFFIX);
    }
    if (!ingress.isHandshake
        && !ingress.isDisconnect
        && !ingress.allowWhenDisabled
        && !ingress.isEnabled) {
      return new ValidationFailure(ingress.isEStopped ? TEXT_UI_DISABLED_ESTOP : TEXT_UI_DISABLED);
    }
    return null;
  }

  void applyPreExecution(Ingress ingress, boolean isTcp) {
    if (isTcp && dependencies.isTcpStopCommand(ingress.name, ingress.args)) {
      dependencies.setStopLatch(STOP_REASON_TCP_STOP);
      dependencies.applySafetyStop(STOP_REASON_TCP_STOP);
    }
  }
}

