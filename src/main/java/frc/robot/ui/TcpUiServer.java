package frc.robot.ui;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.ServerSocket;
import java.net.Socket;

/**
 * NAME
 *   TcpUiServer - Simple line-delimited JSON TCP server for UI commands.
 *
 * DESCRIPTION
 *   Accepts a single client connection at a time and forwards parsed
 *   commands to a handler. Each command returns an ACK and OUT JSON line.
 */
public final class TcpUiServer {
  /**
   * NAME
   *   UiCommand - Parsed TCP UI command payload.
   */
  public static final class UiCommand {
    public final long seq;
    public final String name;
    public final String argsJson;
    public final double ts;
    public final String clientId;

    private UiCommand(long seq, String name, String argsJson, double ts, String clientId) {
      this.seq = seq;
      this.name = name;
      this.argsJson = argsJson;
      this.ts = ts;
      this.clientId = clientId;
    }
  }

  /**
   * NAME
   *   UiResponse - Response payloads to emit for a command.
   */
  public static final class UiResponse {
    public final String ackJson;
    public final String outJson;

    public UiResponse(String ackJson, String outJson) {
      this.ackJson = ackJson;
      this.outJson = outJson;
    }
  }

  /**
   * NAME
   *   CommandHandler - Command handler callback for TCP UI.
   */
  public interface CommandHandler {
    UiResponse handle(UiCommand command);
  }

  /**
   * NAME
   *   ConnectionListener - Callback for client connect/disconnect.
   */
  public interface ConnectionListener {
    void onConnect(Socket socket);
    void onDisconnect();
  }

  private final int port;
  private final CommandHandler handler;
  private final ConnectionListener listener;
  private final Gson gson = new Gson();
  private Thread serverThread;
  private volatile boolean running;

  /**
   * NAME
   *   TcpUiServer - Construct the TCP UI server.
   *
   * PARAMETERS
   *   port - TCP listen port.
   *   handler - Command handler callback.
   */
  public TcpUiServer(int port, CommandHandler handler) {
    this(port, handler, null);
  }

  /**
   * NAME
   *   TcpUiServer - Construct the TCP UI server with connection callbacks.
   *
   * PARAMETERS
   *   port - TCP listen port.
   *   handler - Command handler callback.
   *   listener - Connection listener (optional).
   */
  public TcpUiServer(int port, CommandHandler handler, ConnectionListener listener) {
    this.port = port;
    this.handler = handler;
    this.listener = listener;
  }

  /**
   * NAME
   *   start - Start the TCP UI server thread.
   */
  public void start() {
    if (running) {
      return;
    }
    running = true;
    serverThread = new Thread(new ServerRunner(), "ui-tcp-server");
    serverThread.setDaemon(true);
    serverThread.start();
  }

  /**
   * NAME
   *   stop - Stop the TCP UI server.
   */
  public void stop() {
    running = false;
    if (serverThread != null) {
      serverThread.interrupt();
    }
  }

  /**
   * NAME
   *   ServerRunner - Named runnable for the TCP server thread.
   */
  private final class ServerRunner implements Runnable {
    @Override
    public void run() {
      runServer();
    }
  }

  private void runServer() {
    try (ServerSocket server = new ServerSocket(port)) {
      while (running) {
        try (Socket socket = server.accept()) {
          if (listener != null) {
            listener.onConnect(socket);
          }
          handleClient(socket);
          if (listener != null) {
            listener.onDisconnect();
          }
        } catch (IOException ignored) {
          // Retry accept if interrupted or connection fails.
        }
      }
    } catch (IOException ignored) {
      // Socket failed to bind; leave running false.
      running = false;
    }
  }

  private void handleClient(Socket socket) throws IOException {
    try (BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream()));
         PrintWriter writer = new PrintWriter(socket.getOutputStream(), true)) {
      String line;
      while (running && (line = reader.readLine()) != null) {
        line = line.trim();
        if (line.isEmpty()) {
          continue;
        }
        UiCommand cmd = parseCommand(line);
        if (cmd == null) {
          writer.println(buildError("Malformed command"));
          continue;
        }
        UiResponse response = handler.handle(cmd);
        if (response != null) {
          if (response.ackJson != null && !response.ackJson.isBlank()) {
            writer.println(response.ackJson);
          }
          if (response.outJson != null && !response.outJson.isBlank()) {
            writer.println(response.outJson);
          }
        }
      }
    }
  }

  private UiCommand parseCommand(String line) {
    try {
      JsonObject obj = gson.fromJson(line, JsonObject.class);
      if (obj == null) {
        return null;
      }
      long seq = obj.has("seq") ? obj.get("seq").getAsLong() : -1;
      String name = obj.has("name") ? obj.get("name").getAsString() : "";
      String argsJson = obj.has("args") ? gson.toJson(obj.get("args")) : "";
      double ts = obj.has("ts") ? obj.get("ts").getAsDouble() : 0.0;
      String clientId = obj.has("clientId") ? obj.get("clientId").getAsString() : "";
      return new UiCommand(seq, name, argsJson, ts, clientId);
    } catch (JsonParseException ex) {
      return null;
    }
  }

  private String buildError(String message) {
    JsonObject obj = new JsonObject();
    obj.addProperty("type", "error");
    obj.addProperty("message", message != null ? message : "error");
    return gson.toJson(obj);
  }
}
