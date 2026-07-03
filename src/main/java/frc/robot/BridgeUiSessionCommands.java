package frc.robot;

import com.google.gson.JsonObject;
import java.time.ZoneId;
import java.util.Set;
import java.util.UUID;

/**
 * NAME
 *   BridgeUiSessionCommands - Session/protocol command family executor.
 */
final class BridgeUiSessionCommands implements BridgeUiCommandDispatcher.CommandFamily {

  private static final String CMD_UI_PING = "uiPing";
  private static final String CMD_UI_HANDSHAKE = "uiHandshake";
  private static final String CMD_UI_DISCONNECT = "uiDisconnect";
  private static final String CMD_UI_MONITOR_ENABLE = "uiMonitorEnable";
  private static final String CMD_UI_MONITOR_DISABLE = "uiMonitorDisable";
  private static final String CMD_UI_POLL_LOG = "uiPollLog";

  private static final Set<String> COMMANDS = Set.of(
      CMD_UI_PING,
      CMD_UI_HANDSHAKE,
      CMD_UI_DISCONNECT,
      CMD_UI_MONITOR_ENABLE,
      CMD_UI_MONITOR_DISABLE,
      CMD_UI_POLL_LOG);

  private static final String KEY_RESET = "reset";
  private static final String KEY_SESSION_ID = "sessionId";
  private static final String KEY_LAST_ACK_SEQ = "lastAckSeq";
  private static final String KEY_MIN_NEXT_SEQ = "minNextSeq";
  private static final String KEY_PROTOCOL_VERSION = "protocolVersion";
  private static final String KEY_CONNECTED = "connected";
  private static final String KEY_ENABLED = "enabled";

  private static final String MESSAGE_OK = "OK";
  private static final String MESSAGE_UI_SESSION_RESET = "UI session reset.";
  private static final String MESSAGE_UI_HANDSHAKE_OK = "UI handshake OK.";
  private static final String MESSAGE_UI_LOCK_RELEASED = "UI lock released.";
  private static final String MESSAGE_NO_ACTIVE_LOCK = "No active UI lock.";
  private static final String MESSAGE_LOCK_HELD_OTHER = "UI lock held by another client.";
  private static final String MESSAGE_MONITOR_ENABLED = "Protocol monitor enabled.";
  private static final String MESSAGE_MONITOR_DISABLED = "Protocol monitor disabled.";

  /**
   * NAME
   *   Dependencies - Narrow dependency contract for session commands.
   */
  interface Dependencies {
    String getActiveUiClientId();

    void setActiveUiClientId(String clientId);

    boolean isUiProtocolMonitorEnabled();

    void setUiProtocolMonitorEnabled(boolean enabled);

    ZoneId resolveRemoteCommandZone(JsonObject args);

    void setRemoteCommandZone(ZoneId zone);

    String getUiSessionId();

    void setUiSessionId(String sessionId);

    void resetUiSessionRuntimeContext();

    long getLastUiSeq();

    int getUiProtocolVersion();

    String drainUiLog();
  }

  private final Dependencies dependencies;

  BridgeUiSessionCommands(Dependencies dependencies) {
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
      case CMD_UI_PING:
        result.message = MESSAGE_OK;
        result.outText = "";
        break;
      case CMD_UI_HANDSHAKE:
        executeHandshake(ingress, args, result);
        break;
      case CMD_UI_DISCONNECT:
        executeDisconnect(ingress, result);
        break;
      case CMD_UI_MONITOR_ENABLE:
        dependencies.setUiProtocolMonitorEnabled(true);
        result.message = MESSAGE_MONITOR_ENABLED;
        break;
      case CMD_UI_MONITOR_DISABLE:
        dependencies.setUiProtocolMonitorEnabled(false);
        result.message = MESSAGE_MONITOR_DISABLED;
        break;
      case CMD_UI_POLL_LOG:
        result.outText = dependencies.drainUiLog();
        break;
      default:
        result.ok = false;
        result.message = "Unknown command: " + commandName;
        break;
    }
    return result;
  }

  private void executeHandshake(
      BridgeUiIngressPolicy.Ingress ingress,
      JsonObject args,
      BridgeUiCommandResult result) {
    if (!ingress.locked) {
      dependencies.setActiveUiClientId(ingress.client);
    }
    boolean reset = args != null && args.has(KEY_RESET) && args.get(KEY_RESET).getAsBoolean();
    ZoneId zone = dependencies.resolveRemoteCommandZone(args);
    if (zone != null) {
      dependencies.setRemoteCommandZone(zone);
    }
    if (reset) {
      dependencies.setUiSessionId(UUID.randomUUID().toString());
      dependencies.resetUiSessionRuntimeContext();
    }
    long baseSeq = dependencies.getLastUiSeq();
    JsonObject payload = new JsonObject();
    payload.addProperty(KEY_SESSION_ID, dependencies.getUiSessionId());
    payload.addProperty(KEY_LAST_ACK_SEQ, baseSeq);
    payload.addProperty(KEY_MIN_NEXT_SEQ, baseSeq + 1);
    payload.addProperty(KEY_PROTOCOL_VERSION, dependencies.getUiProtocolVersion());
    result.outJson = payload.toString();
    result.message = reset ? MESSAGE_UI_SESSION_RESET : MESSAGE_UI_HANDSHAKE_OK;
  }

  private void executeDisconnect(BridgeUiIngressPolicy.Ingress ingress, BridgeUiCommandResult result) {
    String activeClientId = dependencies.getActiveUiClientId();
    if (ingress.locked && activeClientId != null && activeClientId.equals(ingress.client)) {
      dependencies.setActiveUiClientId(null);
      result.message = MESSAGE_UI_LOCK_RELEASED;
      return;
    }
    if (!ingress.locked) {
      result.message = MESSAGE_NO_ACTIVE_LOCK;
      return;
    }
    result.ok = false;
    result.message = MESSAGE_LOCK_HELD_OTHER;
  }
}

