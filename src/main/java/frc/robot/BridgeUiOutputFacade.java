package frc.robot;

import edu.wpi.first.networktables.NetworkTable;
import frc.robot.status.StatusRuntime;

/**
 * NAME
 *   BridgeUiOutputFacade - Publish Bridge UI command outputs to NetworkTables.
 *
 * DESCRIPTION
 *   Centralizes UI ACK/OUT publication for BridgeUiCommandHandler so
 *   output-side contract logic is isolated behind a stable facade boundary.
 */
public final class BridgeUiOutputFacade {

  private static final String EMPTY_STRING = "";

  private static final String NT_KEY_ACK_SEQ = "ack/seq";
  private static final String NT_KEY_ACK_STATUS = "ack/status";
  private static final String NT_KEY_ACK_CODE = "ack/code";
  private static final String NT_KEY_ACK_CODE_TEXT = "ack/codeText";
  private static final String NT_KEY_ACK_MESSAGE = "ack/message";
  private static final String NT_KEY_ACK_NAME = "ack/name";
  private static final String NT_KEY_ACK_TS = "ack/ts";

  private static final String NT_KEY_OUT_SEQ = "out/seq";
  private static final String NT_KEY_OUT_NAME = "out/name";
  private static final String NT_KEY_OUT_TEXT = "out/text";
  private static final String NT_KEY_OUT_TS = "out/ts";
  private static final String NT_KEY_OUT_JSON = "out/json";

  private static final String NT_KEY_STATE_LAST_ACK_SEQ = "state/lastAckSeq";
  private static final String NT_KEY_STATE_LAST_ACK_MS = "state/lastAckMs";
  private static final String NT_KEY_STATE_SESSION_ID = "state/sessionId";
  private static final String NT_KEY_STATE_PROTOCOL_VERSION = "state/protocolVersion";
  private static final String NT_KEY_STATE_ACTIVE_CLIENT = "state/activeClientId";

  private final NetworkTable uiTable;
  private final int uiProtocolVersion;

  /**
   * NAME
   *   BridgeUiOutputFacade - Build output publisher facade for UI command surfaces.
   */
  public BridgeUiOutputFacade(NetworkTable uiTable, int uiProtocolVersion) {
    this.uiTable = uiTable;
    this.uiProtocolVersion = uiProtocolVersion;
  }

  /**
   * NAME
   *   publishUiAck - Publish command acknowledgement and heartbeat state.
   *
   * RETURNS
   *   Millisecond timestamp written to state/lastAckMs.
   */
  public long publishUiAck(
      long seq,
      boolean ok,
      String message,
      String name,
      double cmdTs,
      String sessionId,
      String activeClientId) {
    int statusCode = StatusRuntime.ackCode(ok);
    uiTable.getEntry(NT_KEY_ACK_SEQ).setInteger(seq);
    uiTable.getEntry(NT_KEY_ACK_STATUS).setString(StatusRuntime.ackLabel(ok));
    uiTable.getEntry(NT_KEY_ACK_CODE).setInteger(statusCode);
    uiTable.getEntry(NT_KEY_ACK_CODE_TEXT).setString(StatusRuntime.messageFor(statusCode));
    uiTable.getEntry(NT_KEY_ACK_MESSAGE).setString(coalesce(message));
    uiTable.getEntry(NT_KEY_ACK_NAME).setString(coalesce(name));
    uiTable.getEntry(NT_KEY_ACK_TS).setDouble(cmdTs);
    long ackMs = System.currentTimeMillis();
    publishUiState(seq, ackMs, sessionId, activeClientId);
    return ackMs;
  }

  /**
   * NAME
   *   publishUiOut - Publish command output payload fields.
   */
  public void publishUiOut(long seq, String name, String text, double cmdTs, String jsonText) {
    uiTable.getEntry(NT_KEY_OUT_SEQ).setInteger(seq);
    uiTable.getEntry(NT_KEY_OUT_NAME).setString(coalesce(name));
    uiTable.getEntry(NT_KEY_OUT_TEXT).setString(coalesce(text));
    uiTable.getEntry(NT_KEY_OUT_TS).setDouble(cmdTs);
    uiTable.getEntry(NT_KEY_OUT_JSON).setString(coalesce(jsonText));
  }

  /**
   * NAME
   *   publishUiState - Publish lightweight UI protocol state metadata.
   */
  private void publishUiState(long seq, long ackMs, String sessionId, String activeClientId) {
    uiTable.getEntry(NT_KEY_STATE_LAST_ACK_SEQ).setInteger(seq);
    uiTable.getEntry(NT_KEY_STATE_LAST_ACK_MS).setDouble(ackMs);
    uiTable.getEntry(NT_KEY_STATE_SESSION_ID).setString(coalesce(sessionId));
    uiTable.getEntry(NT_KEY_STATE_PROTOCOL_VERSION).setInteger(uiProtocolVersion);
    uiTable.getEntry(NT_KEY_STATE_ACTIVE_CLIENT).setString(coalesce(activeClientId));
  }

  /**
   * NAME
   *   coalesce - Convert nullable string to non-null value for NT publication.
   */
  private String coalesce(String value) {
    return value != null ? value : EMPTY_STRING;
  }
}

