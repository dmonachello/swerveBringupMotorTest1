package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import java.time.ZoneId;
import org.junit.jupiter.api.Test;

class BridgeUiSessionCommandsTest {

  private static final String CMD_UI_HANDSHAKE = "uiHandshake";
  private static final String CMD_UI_DISCONNECT = "uiDisconnect";

  @Test
  void handshakePopulatesSessionPayload() {
    SessionDeps deps = new SessionDeps();
    BridgeUiSessionCommands commands = new BridgeUiSessionCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_UI_HANDSHAKE,
        new JsonObject(),
        "clientA",
        true,
        false,
        true,
        false,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertTrue(result.ok);
    assertTrue(result.outJson.contains("sessionId"));
    assertEquals("clientA", deps.activeClientId);
  }

  @Test
  void disconnectByOtherClientFails() {
    SessionDeps deps = new SessionDeps();
    deps.activeClientId = "clientA";
    BridgeUiSessionCommands commands = new BridgeUiSessionCommands(deps);
    BridgeUiIngressPolicy.Ingress ingress = new BridgeUiIngressPolicy.Ingress(
        CMD_UI_DISCONNECT,
        new JsonObject(),
        "clientB",
        true,
        true,
        false,
        true,
        false,
        true,
        true,
        false);

    BridgeUiCommandResult result = commands.execute(ingress, 0.0, false);

    assertFalse(result.ok);
    assertEquals("UI lock held by another client.", result.message);
  }

  private static final class SessionDeps implements BridgeUiSessionCommands.Dependencies {
    private String activeClientId = "";
    private boolean uiProtocolMonitorEnabled;
    private String uiSessionId = "session0";

    @Override
    public String getActiveUiClientId() {
      return activeClientId;
    }

    @Override
    public void setActiveUiClientId(String clientId) {
      this.activeClientId = clientId;
    }

    @Override
    public boolean isUiProtocolMonitorEnabled() {
      return uiProtocolMonitorEnabled;
    }

    @Override
    public void setUiProtocolMonitorEnabled(boolean enabled) {
      this.uiProtocolMonitorEnabled = enabled;
    }

    @Override
    public NetworkTable getUiTcpTable() {
      return NetworkTableInstance.getDefault().getTable("testSessionCommands");
    }

    @Override
    public ZoneId resolveRemoteCommandZone(JsonObject args) {
      return null;
    }

    @Override
    public void setRemoteCommandZone(ZoneId zone) {}

    @Override
    public String getUiSessionId() {
      return uiSessionId;
    }

    @Override
    public void setUiSessionId(String sessionId) {
      uiSessionId = sessionId;
    }

    @Override
    public long getLastUiSeq() {
      return 0;
    }

    @Override
    public long getLastTcpSeq() {
      return 0;
    }

    @Override
    public int getUiProtocolVersion() {
      return 1;
    }

    @Override
    public String drainUiLog() {
      return "";
    }
  }
}

