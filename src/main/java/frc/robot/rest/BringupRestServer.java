package frc.robot.rest;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import frc.robot.commands.local.RobotLocalCommandRegistry;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Supplier;

/**
 * NAME
 *   BringupRestServer - REST command/control server for host bringup clients.
 *
 * DESCRIPTION
 *   Exposes the first REST control-plane and command-lifecycle slice on the
 *   roboRIO. The server owns REST session state, request replay, command
 *   records, bounded output drains, and log polling. It intentionally keeps
 *   the first implementation narrow by supporting immediate read commands
 *   while preserving the full session and endpoint contract needed for later
 *   command-family migration.
 */
public final class BringupRestServer {
  private static final Gson GSON = new Gson();
  private static final String CHARSET_UTF8 = "utf-8";
  private static final String CONTENT_TYPE_JSON = "application/json; charset=" + CHARSET_UTF8;
  private static final String METHOD_GET = "GET";
  private static final String METHOD_POST = "POST";
  private static final String PATH_HEALTH = "/health";
  private static final String PATH_SESSION = "/session";
  private static final String PATH_SESSION_CONNECT = "/session/connect";
  private static final String PATH_SESSION_DISCONNECT = "/session/disconnect";
  private static final String PATH_SESSION_RESET = "/session/reset";
  private static final String PATH_SESSION_PING = "/session/ping";
  private static final String PATH_COMMANDS = "/commands";
  private static final String PATH_COMMANDS_PREFIX = "/commands/";
  private static final String PATH_OUTPUT_SUFFIX = "/output";
  private static final String PATH_STOP_SUFFIX = "/stop";
  private static final String PATH_LOGS = "/logs";
  private static final String PATH_MONITOR_ENABLE = "/monitor/enable";
  private static final String PATH_MONITOR_DISABLE = "/monitor/disable";
  private static final String PATH_INVENTORY_COMMANDS = "/inventory/commands";
  private static final String JSON_KEY_OK = "ok";
  private static final String JSON_KEY_MESSAGE = "message";
  private static final String JSON_KEY_STATUS = "status";
  private static final String JSON_KEY_REASON = "reason";
  private static final String JSON_KEY_CLIENT_ID = "clientId";
  private static final String JSON_KEY_REQUEST_ID = "requestId";
  private static final String JSON_KEY_COMMAND_ID = "commandId";
  private static final String JSON_KEY_NAME = "name";
  private static final String JSON_KEY_ARGS = "args";
  private static final String JSON_KEY_CONNECTED = "connected";
  private static final String JSON_KEY_SESSION_ID = "sessionId";
  private static final String JSON_KEY_OWNER_CLIENT_ID = "ownerClientId";
  private static final String JSON_KEY_MONITOR_ENABLED = "monitorEnabled";
  private static final String JSON_KEY_COMMAND = "command";
  private static final String JSON_KEY_LOGS = "logs";
  private static final String JSON_KEY_CHUNKS = "chunks";
  private static final String JSON_KEY_TEXT = "text";
  private static final String JSON_KEY_SEQUENCE = "sequence";
  private static final String JSON_KEY_NEXT_SEQUENCE = "nextSequence";
  private static final String JSON_KEY_DROPPED = "dropped";
  private static final String JSON_KEY_STOP_REQUESTED = "stopRequested";
  private static final String JSON_KEY_CREATED_AT_MS = "createdAtMs";
  private static final String JSON_KEY_UPDATED_AT_MS = "updatedAtMs";
  private static final String JSON_KEY_LAST_ACTIVITY_MS = "lastActivityMs";
  private static final String JSON_KEY_SERVER = "server";
  private static final String JSON_KEY_PORT = "port";
  private static final String JSON_KEY_ACTIVE_COMMAND = "activeCommand";
  private static final String JSON_KEY_COMMANDS = "commands";
  private static final String JSON_KEY_AFTER = "after";
  private static final String JSON_KEY_RESET = "reset";
  private static final String JSON_KEY_TIMESTAMP_MS = "timestampMs";
  private static final String JSON_KEY_RESULT = "result";
  private static final String JSON_KEY_OUTPUT_AVAILABLE = "outputAvailable";
  private static final String JSON_VALUE_SERVER = "bringupRest";
  private static final String STATUS_ACCEPTED = "ACCEPTED";
  private static final String STATUS_RUNNING = "RUNNING";
  private static final String STATUS_FINISHED = "FINISHED";
  private static final String STATUS_FAILED = "FAILED";
  private static final String STATUS_STOPPED = "STOPPED";
  private static final String STATUS_REJECTED = "REJECTED";
  private static final String STATUS_UNKNOWN = "UNKNOWN";
  private static final String MESSAGE_METHOD_NOT_ALLOWED = "Method not allowed.";
  private static final String MESSAGE_NOT_FOUND = "Not found.";
  private static final String MESSAGE_MALFORMED_JSON = "Malformed JSON body.";
  private static final String MESSAGE_CLIENT_REQUIRED = "clientId is required.";
  private static final String MESSAGE_REQUEST_REQUIRED = "requestId is required.";
  private static final String MESSAGE_COMMAND_NAME_REQUIRED = "name is required.";
  private static final String MESSAGE_SESSION_CONFLICT = "Another control client already owns the session.";
  private static final String MESSAGE_OWNER_REQUIRED = "Owning control client required.";
  private static final String MESSAGE_UNKNOWN_COMMAND = "Unknown command.";
  private static final String MESSAGE_UNKNOWN_COMMAND_ID = "Unknown commandId.";
  private static final String MESSAGE_BUSY = "Another command is already active.";
  private static final String MESSAGE_CONNECTED = "Session connected.";
  private static final String MESSAGE_DISCONNECTED = "Session disconnected.";
  private static final String MESSAGE_RESET = "Session reset.";
  private static final String MESSAGE_PING = "Session ping OK.";
  private static final String MESSAGE_MONITOR_ENABLED = "Monitor enabled.";
  private static final String MESSAGE_MONITOR_DISABLED = "Monitor disabled.";
  private static final String MESSAGE_STOPPED = "Command stopped.";
  private static final String MESSAGE_ALREADY_TERMINAL = "Command already terminal.";
  private static final String MESSAGE_FINISHED = "Command finished.";
  private static final String MESSAGE_REPLAY = "Duplicate request replayed.";
  private static final String MESSAGE_TIMEOUT_DISCONNECT = "sessionTimeout";
  private static final String MESSAGE_DISCONNECT_STOP = "sessionDisconnect";
  private static final String MESSAGE_RESET_STOP = "sessionReset";
  private static final String MESSAGE_MANUAL_RESET = "sessionReset";
  private static final String MESSAGE_RUNTIME_UNSUPPORTED = "Command not yet supported by REST.";
  private static final String COMMAND_SHOW_DEVICES = RobotLocalCommandRegistry.COMMAND_SHOW_DEVICES;
  private static final String COMMAND_SHOW_RUNTIME_STATE = RobotLocalCommandRegistry.COMMAND_SHOW_RUNTIME_STATE;
  private static final long SESSION_TIMEOUT_MS = 60000L;
  private static final int HTTP_OK = 200;
  private static final int HTTP_ACCEPTED = 202;
  private static final int HTTP_BAD_REQUEST = 400;
  private static final int HTTP_FORBIDDEN = 403;
  private static final int HTTP_NOT_FOUND = 404;
  private static final int HTTP_CONFLICT = 409;
  private static final int HTTP_METHOD_NOT_ALLOWED = 405;
  private static final int HTTP_INTERNAL_ERROR = 500;
  private static final int EXECUTOR_THREADS = 2;
  private static final int SERVER_BACKLOG = 0;
  private static final int LOG_BUFFER_MAX = 200;
  private static final int OUTPUT_BUFFER_MAX = 64;
  private static final String QUERY_PAIR_SEPARATOR = "&";
  private static final String QUERY_KEY_VALUE_SEPARATOR = "=";

  /**
   * NAME
   *   RestCallbacks - Robot-side suppliers reused by REST endpoints.
   *
   * DESCRIPTION
   *   Keeps the REST server transport-owned while allowing existing robot
   *   model builders to remain the single source of truth for specific JSON
   *   payloads.
   */
  public interface RestCallbacks {
    JsonObject buildDevicesJson();
    JsonObject buildRuntimeStateJson();
    frc.robot.BridgeUiCommandHandler.RestCommandResult executeCommand(
        String name,
        String argsJson,
        String clientId);
    boolean isCommandActive(String name);
  }

  private final int requestedPort;
  private final RestCallbacks callbacks;
  private final Object stateLock = new Object();
  private final Supplier<Long> timeSource;
  private HttpServer server;
  private String sessionOwnerClientId;
  private String sessionId = UUID.randomUUID().toString();
  private long sessionLastActivityMs;
  private boolean monitorEnabled;
  private final Map<String, SubmitReplay> replayByRequestId = new HashMap<>();
  private final Map<Long, CommandRecord> commandsById = new LinkedHashMap<>();
  private final List<LogEntry> logEntries = new ArrayList<>();
  private final AtomicLong commandIdAllocator = new AtomicLong(0L);
  private final AtomicLong logSequenceAllocator = new AtomicLong(0L);
  private CommandRecord activeCommand;

  public BringupRestServer(int port, RestCallbacks callbacks) {
    this(port, callbacks, System::currentTimeMillis);
  }

  /**
   * NAME
   *   BringupRestServer - Construct the REST server with an injectable clock.
   *
   * PARAMETERS
   *   port - TCP listen port, or 0 for an ephemeral test port.
   *   callbacks - Robot-side JSON builders reused by REST read commands.
   *   timeSource - Millisecond clock supplier for tests.
   */
  public BringupRestServer(int port, RestCallbacks callbacks, Supplier<Long> timeSource) {
    this.requestedPort = port;
    this.callbacks = callbacks;
    this.timeSource = timeSource;
  }

  /**
   * NAME
   *   start - Start the REST server.
   *
   * ERRORS
   *   IOException if the socket cannot be bound.
   */
  public void start() throws IOException {
    if (server != null) {
      return;
    }
    HttpServer created = HttpServer.create(new InetSocketAddress(requestedPort), SERVER_BACKLOG);
    created.setExecutor(Executors.newFixedThreadPool(EXECUTOR_THREADS));
    created.createContext(PATH_HEALTH, new RootHandler());
    created.createContext(PATH_SESSION, new RootHandler());
    created.createContext(PATH_SESSION_CONNECT, new RootHandler());
    created.createContext(PATH_SESSION_DISCONNECT, new RootHandler());
    created.createContext(PATH_SESSION_RESET, new RootHandler());
    created.createContext(PATH_SESSION_PING, new RootHandler());
    created.createContext(PATH_COMMANDS, new RootHandler());
    created.createContext(PATH_COMMANDS_PREFIX, new RootHandler());
    created.createContext(PATH_LOGS, new RootHandler());
    created.createContext(PATH_MONITOR_ENABLE, new RootHandler());
    created.createContext(PATH_MONITOR_DISABLE, new RootHandler());
    created.createContext(PATH_INVENTORY_COMMANDS, new RootHandler());
    created.start();
    server = created;
  }

  /**
   * NAME
   *   stop - Stop the REST server.
   */
  public void stop() {
    if (server == null) {
      return;
    }
    server.stop(0);
    server = null;
  }

  /**
   * NAME
   *   getBoundPort - Return the actual bound listen port.
   */
  public int getBoundPort() {
    HttpServer current = server;
    return current != null ? current.getAddress().getPort() : requestedPort;
  }

  /**
   * NAME
   *   onBringupLine - Append a printer line to the REST log buffer.
   *
   * PARAMETERS
   *   text - Bringup printer line.
   */
  public void onBringupLine(String text) {
    if (text == null || text.isBlank()) {
      return;
    }
    synchronized (stateLock) {
      long nextSequence = logSequenceAllocator.incrementAndGet();
      logEntries.add(new LogEntry(nextSequence, nowMs(), text));
      trimLogsIfNeeded();
    }
  }

  private final class RootHandler implements HttpHandler {
    @Override
    public void handle(HttpExchange exchange) throws IOException {
      try {
        route(exchange);
      } catch (RuntimeException ex) {
        JsonObject body = baseEnvelope(false, ex.getMessage() != null ? ex.getMessage() : MESSAGE_NOT_FOUND);
        sendJson(exchange, HTTP_INTERNAL_ERROR, body);
      } finally {
        exchange.close();
      }
    }
  }

  private void route(HttpExchange exchange) throws IOException {
    expireSessionIfNeeded();
    synchronized (stateLock) {
      refreshActiveCommandLocked();
    }
    String path = exchange.getRequestURI().getPath();
    if (PATH_HEALTH.equals(path)) {
      handleHealth(exchange);
      return;
    }
    if (PATH_SESSION.equals(path)) {
      handleSessionGet(exchange);
      return;
    }
    if (PATH_SESSION_CONNECT.equals(path)) {
      handleSessionConnect(exchange);
      return;
    }
    if (PATH_SESSION_DISCONNECT.equals(path)) {
      handleSessionDisconnect(exchange);
      return;
    }
    if (PATH_SESSION_RESET.equals(path)) {
      handleSessionReset(exchange);
      return;
    }
    if (PATH_SESSION_PING.equals(path)) {
      handleSessionPing(exchange);
      return;
    }
    if (PATH_COMMANDS.equals(path)) {
      handleCommands(exchange);
      return;
    }
    if (path.startsWith(PATH_COMMANDS_PREFIX) && path.length() > PATH_COMMANDS_PREFIX.length()) {
      handleCommandSubresource(exchange, path);
      return;
    }
    if (PATH_LOGS.equals(path)) {
      handleLogs(exchange);
      return;
    }
    if (PATH_MONITOR_ENABLE.equals(path)) {
      handleMonitorToggle(exchange, true);
      return;
    }
    if (PATH_MONITOR_DISABLE.equals(path)) {
      handleMonitorToggle(exchange, false);
      return;
    }
    if (PATH_INVENTORY_COMMANDS.equals(path)) {
      handleInventoryCommands(exchange);
      return;
    }
    JsonObject body = baseEnvelope(false, MESSAGE_NOT_FOUND);
    sendJson(exchange, HTTP_NOT_FOUND, body);
  }

  private void handleHealth(HttpExchange exchange) throws IOException {
    if (!METHOD_GET.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    JsonObject body = baseEnvelope(true, MESSAGE_FINISHED);
    body.addProperty(JSON_KEY_SERVER, JSON_VALUE_SERVER);
    body.addProperty(JSON_KEY_PORT, getBoundPort());
    synchronized (stateLock) {
      body.addProperty(JSON_KEY_OWNER_CLIENT_ID, sessionOwnerClientId);
      body.addProperty(JSON_KEY_SESSION_ID, sessionId);
      body.addProperty(JSON_KEY_CONNECTED, sessionOwnerClientId != null);
      body.addProperty(JSON_KEY_MONITOR_ENABLED, monitorEnabled);
      body.add(JSON_KEY_ACTIVE_COMMAND, activeCommand != null ? activeCommand.toStatusJson() : null);
    }
    sendJson(exchange, HTTP_OK, body);
  }

  private void handleSessionGet(HttpExchange exchange) throws IOException {
    if (!METHOD_GET.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    JsonObject body = sessionSnapshot(MESSAGE_FINISHED);
    sendJson(exchange, HTTP_OK, body);
  }

  private void handleSessionConnect(HttpExchange exchange) throws IOException {
    if (!METHOD_POST.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    JsonObject request = parseJsonBody(exchange);
    if (request == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_MALFORMED_JSON));
      return;
    }
    String clientId = stringArg(request, JSON_KEY_CLIENT_ID);
    if (clientId == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_CLIENT_REQUIRED));
      return;
    }
    synchronized (stateLock) {
      if (sessionOwnerClientId != null && !sessionOwnerClientId.equals(clientId)) {
        sendJson(exchange, HTTP_CONFLICT, baseEnvelope(false, MESSAGE_SESSION_CONFLICT));
        return;
      }
      sessionOwnerClientId = clientId;
      sessionLastActivityMs = nowMs();
    }
    sendJson(exchange, HTTP_OK, sessionSnapshot(MESSAGE_CONNECTED));
  }

  private void handleSessionDisconnect(HttpExchange exchange) throws IOException {
    if (!METHOD_POST.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    JsonObject request = parseJsonBody(exchange);
    if (request == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_MALFORMED_JSON));
      return;
    }
    String clientId = stringArg(request, JSON_KEY_CLIENT_ID);
    if (clientId == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_CLIENT_REQUIRED));
      return;
    }
    synchronized (stateLock) {
      if (!isOwnerClient(clientId)) {
        sendJson(exchange, HTTP_FORBIDDEN, baseEnvelope(false, MESSAGE_OWNER_REQUIRED));
        return;
      }
      stopActiveCommandLocked(MESSAGE_DISCONNECT_STOP, STATUS_STOPPED);
      clearSessionOwnerLocked();
    }
    sendJson(exchange, HTTP_OK, sessionSnapshot(MESSAGE_DISCONNECTED));
  }

  private void handleSessionReset(HttpExchange exchange) throws IOException {
    if (!METHOD_POST.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    JsonObject request = parseJsonBody(exchange);
    if (request == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_MALFORMED_JSON));
      return;
    }
    synchronized (stateLock) {
      stopActiveCommandLocked(MESSAGE_RESET_STOP, STATUS_STOPPED);
      clearSessionOwnerLocked();
      replayByRequestId.clear();
      commandsById.clear();
      commandIdAllocator.set(0L);
      logEntries.clear();
      logSequenceAllocator.set(0L);
      sessionId = UUID.randomUUID().toString();
      sessionLastActivityMs = nowMs();
    }
    JsonObject body = sessionSnapshot(MESSAGE_RESET);
    body.addProperty(JSON_KEY_RESET, true);
    sendJson(exchange, HTTP_OK, body);
  }

  private void handleSessionPing(HttpExchange exchange) throws IOException {
    if (!METHOD_POST.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    JsonObject request = parseJsonBody(exchange);
    if (request == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_MALFORMED_JSON));
      return;
    }
    String clientId = stringArg(request, JSON_KEY_CLIENT_ID);
    if (clientId == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_CLIENT_REQUIRED));
      return;
    }
    synchronized (stateLock) {
      if (!isOwnerClient(clientId)) {
        sendJson(exchange, HTTP_FORBIDDEN, baseEnvelope(false, MESSAGE_OWNER_REQUIRED));
        return;
      }
      sessionLastActivityMs = nowMs();
    }
    sendJson(exchange, HTTP_OK, sessionSnapshot(MESSAGE_PING));
  }

  private void handleCommands(HttpExchange exchange) throws IOException {
    if (METHOD_POST.equals(exchange.getRequestMethod())) {
      handleCommandSubmit(exchange);
      return;
    }
    sendMethodNotAllowed(exchange);
  }

  private void handleCommandSubmit(HttpExchange exchange) throws IOException {
    JsonObject request = parseJsonBody(exchange);
    if (request == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_MALFORMED_JSON));
      return;
    }
    String clientId = stringArg(request, JSON_KEY_CLIENT_ID);
    String requestId = stringArg(request, JSON_KEY_REQUEST_ID);
    String name = stringArg(request, JSON_KEY_NAME);
    if (clientId == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_CLIENT_REQUIRED));
      return;
    }
    if (requestId == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_REQUEST_REQUIRED));
      return;
    }
    if (name == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_COMMAND_NAME_REQUIRED));
      return;
    }
    JsonObject args = request.has(JSON_KEY_ARGS) && request.get(JSON_KEY_ARGS).isJsonObject()
        ? request.getAsJsonObject(JSON_KEY_ARGS)
        : new JsonObject();
    synchronized (stateLock) {
      if (!isOwnerClient(clientId)) {
        sendJson(exchange, HTTP_FORBIDDEN, baseEnvelope(false, MESSAGE_OWNER_REQUIRED));
        return;
      }
      sessionLastActivityMs = nowMs();
      SubmitReplay replay = replayByRequestId.get(requestId);
      if (replay != null && clientId.equals(replay.clientId)) {
        JsonObject replayBody = replay.body.deepCopy();
        replayBody.addProperty(JSON_KEY_MESSAGE, MESSAGE_REPLAY);
        sendJson(exchange, replay.httpCode, replayBody);
        return;
      }
      if (activeCommand != null && activeCommand.isRunning()) {
        JsonObject rejected = baseEnvelope(false, MESSAGE_BUSY);
        rejected.addProperty(JSON_KEY_STATUS, STATUS_REJECTED);
        rejected.addProperty(JSON_KEY_COMMAND_ID, activeCommand.commandId);
        replayByRequestId.put(requestId, new SubmitReplay(clientId, HTTP_CONFLICT, rejected.deepCopy()));
        sendJson(exchange, HTTP_CONFLICT, rejected);
        return;
      }
      long commandId = commandIdAllocator.incrementAndGet();
      CommandRecord record = new CommandRecord(commandId, clientId, requestId, name, args.deepCopy(), nowMs());
      commandsById.put(commandId, record);
      activeCommand = record;
      runImmediateCommandLocked(record);
      JsonObject accepted = commandSubmitJson(record);
      replayByRequestId.put(requestId, new SubmitReplay(clientId, HTTP_ACCEPTED, accepted.deepCopy()));
      sendJson(exchange, HTTP_ACCEPTED, accepted);
    }
  }

  private void handleCommandSubresource(HttpExchange exchange, String path) throws IOException {
    String suffix = path.substring(PATH_COMMANDS_PREFIX.length());
    if (suffix.endsWith(PATH_OUTPUT_SUFFIX)) {
      handleCommandOutput(exchange, commandIdFromPath(suffix, PATH_OUTPUT_SUFFIX));
      return;
    }
    if (suffix.endsWith(PATH_STOP_SUFFIX)) {
      handleCommandStop(exchange, commandIdFromPath(suffix, PATH_STOP_SUFFIX));
      return;
    }
    handleCommandStatus(exchange, commandIdFromPath(suffix, ""));
  }

  private void handleCommandStatus(HttpExchange exchange, Long commandId) throws IOException {
    if (!METHOD_GET.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    String clientId = queryValue(exchange.getRequestURI(), JSON_KEY_CLIENT_ID);
    if (clientId == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_CLIENT_REQUIRED));
      return;
    }
    synchronized (stateLock) {
      if (!isOwnerClient(clientId)) {
        sendJson(exchange, HTTP_FORBIDDEN, baseEnvelope(false, MESSAGE_OWNER_REQUIRED));
        return;
      }
      sessionLastActivityMs = nowMs();
      CommandRecord record = commandId != null ? commandsById.get(commandId) : null;
      if (record == null) {
        sendJson(exchange, HTTP_NOT_FOUND, unknownCommandBody());
        return;
      }
      sendJson(exchange, HTTP_OK, record.toStatusJson());
    }
  }

  private void handleCommandOutput(HttpExchange exchange, Long commandId) throws IOException {
    if (!METHOD_GET.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    String clientId = queryValue(exchange.getRequestURI(), JSON_KEY_CLIENT_ID);
    if (clientId == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_CLIENT_REQUIRED));
      return;
    }
    synchronized (stateLock) {
      if (!isOwnerClient(clientId)) {
        sendJson(exchange, HTTP_FORBIDDEN, baseEnvelope(false, MESSAGE_OWNER_REQUIRED));
        return;
      }
      sessionLastActivityMs = nowMs();
      CommandRecord record = commandId != null ? commandsById.get(commandId) : null;
      if (record == null) {
        sendJson(exchange, HTTP_NOT_FOUND, unknownCommandBody());
        return;
      }
      JsonObject body = baseEnvelope(true, MESSAGE_FINISHED);
      body.addProperty(JSON_KEY_COMMAND_ID, record.commandId);
      body.addProperty(JSON_KEY_STATUS, record.status);
      body.addProperty(JSON_KEY_DROPPED, record.outputDropped);
      body.addProperty(JSON_KEY_NEXT_SEQUENCE, record.nextOutputSequence);
      JsonArray chunks = new JsonArray();
      for (OutputChunk chunk : record.outputChunks) {
        JsonObject chunkJson = new JsonObject();
        chunkJson.addProperty(JSON_KEY_SEQUENCE, chunk.sequence);
        chunkJson.addProperty(JSON_KEY_TEXT, chunk.text);
        chunkJson.addProperty(JSON_KEY_TIMESTAMP_MS, chunk.timestampMs);
        chunks.add(chunkJson);
      }
      body.add(JSON_KEY_CHUNKS, chunks);
      record.outputChunks.clear();
      sendJson(exchange, HTTP_OK, body);
    }
  }

  private void handleCommandStop(HttpExchange exchange, Long commandId) throws IOException {
    if (!METHOD_POST.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    JsonObject request = parseJsonBody(exchange);
    if (request == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_MALFORMED_JSON));
      return;
    }
    String clientId = stringArg(request, JSON_KEY_CLIENT_ID);
    if (clientId == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_CLIENT_REQUIRED));
      return;
    }
    synchronized (stateLock) {
      if (!isOwnerClient(clientId)) {
        sendJson(exchange, HTTP_FORBIDDEN, baseEnvelope(false, MESSAGE_OWNER_REQUIRED));
        return;
      }
      sessionLastActivityMs = nowMs();
      CommandRecord record = commandId != null ? commandsById.get(commandId) : null;
      if (record == null) {
        sendJson(exchange, HTTP_NOT_FOUND, unknownCommandBody());
        return;
      }
      if (!record.isRunning()) {
        JsonObject body = baseEnvelope(true, MESSAGE_ALREADY_TERMINAL);
        body.add(JSON_KEY_COMMAND, record.toStatusJson());
        sendJson(exchange, HTTP_OK, body);
        return;
      }
      record.stopRequested = true;
      record.finish(STATUS_STOPPED, MESSAGE_STOPPED, nowMs());
      if (activeCommand == record) {
        activeCommand = null;
      }
      JsonObject body = baseEnvelope(true, MESSAGE_STOPPED);
      body.add(JSON_KEY_COMMAND, record.toStatusJson());
      sendJson(exchange, HTTP_OK, body);
    }
  }

  private void handleLogs(HttpExchange exchange) throws IOException {
    if (!METHOD_GET.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    long afterSequence = longQueryValue(exchange.getRequestURI(), JSON_KEY_AFTER, 0L);
    JsonObject body = baseEnvelope(true, MESSAGE_FINISHED);
    JsonArray logs = new JsonArray();
    long nextSequence = afterSequence;
    synchronized (stateLock) {
      for (LogEntry entry : logEntries) {
        if (entry.sequence <= afterSequence) {
          continue;
        }
        JsonObject line = new JsonObject();
        line.addProperty(JSON_KEY_SEQUENCE, entry.sequence);
        line.addProperty(JSON_KEY_TEXT, entry.text);
        line.addProperty(JSON_KEY_TIMESTAMP_MS, entry.timestampMs);
        logs.add(line);
        nextSequence = entry.sequence;
      }
    }
    body.add(JSON_KEY_LOGS, logs);
    body.addProperty(JSON_KEY_NEXT_SEQUENCE, nextSequence);
    sendJson(exchange, HTTP_OK, body);
  }

  private void handleMonitorToggle(HttpExchange exchange, boolean enabled) throws IOException {
    if (!METHOD_POST.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    JsonObject request = parseJsonBody(exchange);
    if (request == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_MALFORMED_JSON));
      return;
    }
    String clientId = stringArg(request, JSON_KEY_CLIENT_ID);
    if (clientId == null) {
      sendJson(exchange, HTTP_BAD_REQUEST, baseEnvelope(false, MESSAGE_CLIENT_REQUIRED));
      return;
    }
    synchronized (stateLock) {
      if (!isOwnerClient(clientId)) {
        sendJson(exchange, HTTP_FORBIDDEN, baseEnvelope(false, MESSAGE_OWNER_REQUIRED));
        return;
      }
      sessionLastActivityMs = nowMs();
      monitorEnabled = enabled;
    }
    sendJson(exchange, HTTP_OK, sessionSnapshot(enabled ? MESSAGE_MONITOR_ENABLED : MESSAGE_MONITOR_DISABLED));
  }

  private void handleInventoryCommands(HttpExchange exchange) throws IOException {
    if (!METHOD_GET.equals(exchange.getRequestMethod())) {
      sendMethodNotAllowed(exchange);
      return;
    }
    JsonObject body = baseEnvelope(true, MESSAGE_FINISHED);
    body.add(JSON_KEY_COMMANDS, RobotLocalCommandRegistry.buildInventoryJson().get(JSON_KEY_COMMANDS));
    sendJson(exchange, HTTP_OK, body);
  }

  private JsonObject sessionSnapshot(String message) {
    JsonObject body = baseEnvelope(true, message);
    synchronized (stateLock) {
      body.addProperty(JSON_KEY_CONNECTED, sessionOwnerClientId != null);
      body.addProperty(JSON_KEY_OWNER_CLIENT_ID, sessionOwnerClientId);
      body.addProperty(JSON_KEY_SESSION_ID, sessionId);
      body.addProperty(JSON_KEY_LAST_ACTIVITY_MS, sessionLastActivityMs);
      body.addProperty(JSON_KEY_MONITOR_ENABLED, monitorEnabled);
    }
    return body;
  }

  private JsonObject commandSubmitJson(CommandRecord record) {
    JsonObject body = baseEnvelope(true, record.message);
    body.addProperty(JSON_KEY_COMMAND_ID, record.commandId);
    body.addProperty(JSON_KEY_STATUS, record.status);
    body.addProperty(JSON_KEY_NAME, record.name);
    body.addProperty(JSON_KEY_OUTPUT_AVAILABLE, !record.outputChunks.isEmpty());
    return body;
  }

  private JsonObject unknownCommandBody() {
    JsonObject body = baseEnvelope(false, MESSAGE_UNKNOWN_COMMAND_ID);
    body.addProperty(JSON_KEY_STATUS, STATUS_UNKNOWN);
    body.addProperty(JSON_KEY_REASON, MESSAGE_UNKNOWN_COMMAND_ID);
    return body;
  }

  private void runImmediateCommandLocked(CommandRecord record) {
    record.status = STATUS_RUNNING;
    record.updatedAtMs = nowMs();
    if (COMMAND_SHOW_DEVICES.equals(record.name)) {
      JsonObject payload = callbacks.buildDevicesJson();
      if (payload != null) {
        record.appendOutput(GSON.toJson(payload), nowMs());
      }
      record.finish(STATUS_FINISHED, MESSAGE_FINISHED, nowMs());
      activeCommand = null;
      return;
    }
    if (COMMAND_SHOW_RUNTIME_STATE.equals(record.name)) {
      JsonObject payload = callbacks.buildRuntimeStateJson();
      if (payload != null) {
        record.appendOutput(GSON.toJson(payload), nowMs());
      }
      record.finish(STATUS_FINISHED, MESSAGE_FINISHED, nowMs());
      activeCommand = null;
      return;
    }
    frc.robot.BridgeUiCommandHandler.RestCommandResult result =
        callbacks.executeCommand(record.name, record.args.toString(), record.clientId);
    if (result == null) {
      record.finish(STATUS_FAILED, MESSAGE_RUNTIME_UNSUPPORTED, nowMs());
      activeCommand = null;
      return;
    }
    if (result.outJson != null && !result.outJson.isBlank()) {
      record.appendOutput(result.outJson, nowMs());
    } else if (result.outText != null && !result.outText.isBlank()) {
      record.appendOutput(result.outText, nowMs());
    }
    if (!result.ok) {
      record.finish(STATUS_FAILED, result.message, nowMs());
      activeCommand = null;
      return;
    }
    if (result.running) {
      record.message = result.message;
      record.updatedAtMs = nowMs();
      return;
    }
    record.finish(STATUS_FINISHED, result.message, nowMs());
    activeCommand = null;
  }

  private void refreshActiveCommandLocked() {
    if (activeCommand == null || !activeCommand.isRunning()) {
      return;
    }
    if (callbacks.isCommandActive(activeCommand.name)) {
      activeCommand.updatedAtMs = nowMs();
      return;
    }
    activeCommand.finish(STATUS_FINISHED, MESSAGE_FINISHED, nowMs());
    activeCommand = null;
  }

  private void stopActiveCommandLocked(String reason, String terminalStatus) {
    if (activeCommand == null) {
      return;
    }
    activeCommand.stopRequested = true;
    activeCommand.finish(terminalStatus, reason, nowMs());
    activeCommand = null;
  }

  private void clearSessionOwnerLocked() {
    sessionOwnerClientId = null;
    sessionLastActivityMs = 0L;
  }

  private void expireSessionIfNeeded() {
    synchronized (stateLock) {
      if (sessionOwnerClientId == null) {
        return;
      }
      long now = nowMs();
      if (now - sessionLastActivityMs < SESSION_TIMEOUT_MS) {
        return;
      }
      stopActiveCommandLocked(MESSAGE_TIMEOUT_DISCONNECT, STATUS_STOPPED);
      clearSessionOwnerLocked();
    }
  }

  private boolean isOwnerClient(String clientId) {
    return clientId != null && sessionOwnerClientId != null && sessionOwnerClientId.equals(clientId);
  }

  private void trimLogsIfNeeded() {
    while (logEntries.size() > LOG_BUFFER_MAX) {
      logEntries.remove(0);
    }
  }

  private JsonObject parseJsonBody(HttpExchange exchange) throws IOException {
    try (InputStream input = exchange.getRequestBody()) {
      byte[] bytes = input.readAllBytes();
      if (bytes.length == 0) {
        return new JsonObject();
      }
      String text = new String(bytes, StandardCharsets.UTF_8);
      JsonElement element = GSON.fromJson(text, JsonElement.class);
      return element != null && element.isJsonObject() ? element.getAsJsonObject() : null;
    } catch (JsonParseException ex) {
      return null;
    }
  }

  private void sendMethodNotAllowed(HttpExchange exchange) throws IOException {
    sendJson(exchange, HTTP_METHOD_NOT_ALLOWED, baseEnvelope(false, MESSAGE_METHOD_NOT_ALLOWED));
  }

  private void sendJson(HttpExchange exchange, int httpCode, JsonObject body) throws IOException {
    byte[] bytes = GSON.toJson(body).getBytes(StandardCharsets.UTF_8);
    Headers headers = exchange.getResponseHeaders();
    headers.set("Content-Type", CONTENT_TYPE_JSON);
    exchange.sendResponseHeaders(httpCode, bytes.length);
    try (OutputStream output = exchange.getResponseBody()) {
      output.write(bytes);
    }
  }

  private JsonObject baseEnvelope(boolean ok, String message) {
    JsonObject body = new JsonObject();
    body.addProperty(JSON_KEY_OK, ok);
    body.addProperty(JSON_KEY_MESSAGE, message);
    return body;
  }

  private String stringArg(JsonObject request, String key) {
    return request.has(key) && request.get(key).isJsonPrimitive()
        ? request.get(key).getAsString()
        : null;
  }

  private String queryValue(URI uri, String key) {
    String query = uri.getRawQuery();
    if (query == null || query.isBlank()) {
      return null;
    }
    String[] pairs = query.split(QUERY_PAIR_SEPARATOR);
    for (String pair : pairs) {
      String[] fields = pair.split(QUERY_KEY_VALUE_SEPARATOR, 2);
      if (fields.length == 2 && key.equals(fields[0])) {
        return fields[1];
      }
    }
    return null;
  }

  private long longQueryValue(URI uri, String key, long fallback) {
    String value = queryValue(uri, key);
    if (value == null || value.isBlank()) {
      return fallback;
    }
    try {
      return Long.parseLong(value);
    } catch (NumberFormatException ex) {
      return fallback;
    }
  }

  private Long commandIdFromPath(String suffix, String terminalSuffix) {
    String commandSegment = suffix;
    if (terminalSuffix != null && !terminalSuffix.isEmpty() && suffix.endsWith(terminalSuffix)) {
      commandSegment = suffix.substring(0, suffix.length() - terminalSuffix.length());
    }
    if (commandSegment.startsWith("/")) {
      commandSegment = commandSegment.substring(1);
    }
    if (commandSegment.endsWith("/")) {
      commandSegment = commandSegment.substring(0, commandSegment.length() - 1);
    }
    if (commandSegment.isEmpty()) {
      return null;
    }
    try {
      return Long.parseLong(commandSegment);
    } catch (NumberFormatException ex) {
      return null;
    }
  }

  private long nowMs() {
    return timeSource.get();
  }

  private static final class SubmitReplay {
    private final String clientId;
    private final int httpCode;
    private final JsonObject body;

    private SubmitReplay(String clientId, int httpCode, JsonObject body) {
      this.clientId = clientId;
      this.httpCode = httpCode;
      this.body = body;
    }
  }

  private static final class LogEntry {
    private final long sequence;
    private final long timestampMs;
    private final String text;

    private LogEntry(long sequence, long timestampMs, String text) {
      this.sequence = sequence;
      this.timestampMs = timestampMs;
      this.text = text;
    }
  }

  private static final class OutputChunk {
    private final long sequence;
    private final long timestampMs;
    private final String text;

    private OutputChunk(long sequence, long timestampMs, String text) {
      this.sequence = sequence;
      this.timestampMs = timestampMs;
      this.text = text;
    }
  }

  private static final class CommandRecord {
    private final long commandId;
    private final String clientId;
    private final String requestId;
    private final String name;
    private final JsonObject args;
    private final long createdAtMs;
    private long updatedAtMs;
    private long nextOutputSequence;
    private boolean stopRequested;
    private boolean outputDropped;
    private String status = STATUS_ACCEPTED;
    private String message = STATUS_ACCEPTED;
    private final List<OutputChunk> outputChunks = new ArrayList<>();

    private CommandRecord(
        long commandId,
        String clientId,
        String requestId,
        String name,
        JsonObject args,
        long createdAtMs) {
      this.commandId = commandId;
      this.clientId = clientId;
      this.requestId = requestId;
      this.name = name;
      this.args = args;
      this.createdAtMs = createdAtMs;
      this.updatedAtMs = createdAtMs;
      this.nextOutputSequence = 1L;
    }

    private boolean isRunning() {
      return STATUS_ACCEPTED.equals(status) || STATUS_RUNNING.equals(status);
    }

    private void appendOutput(String text, long timestampMs) {
      if (text == null) {
        return;
      }
      if (outputChunks.size() >= OUTPUT_BUFFER_MAX) {
        outputChunks.remove(0);
        outputDropped = true;
      }
      outputChunks.add(new OutputChunk(nextOutputSequence, timestampMs, text));
      nextOutputSequence++;
      updatedAtMs = timestampMs;
    }

    private void finish(String terminalStatus, String terminalMessage, long timestampMs) {
      this.status = terminalStatus;
      this.message = terminalMessage;
      this.updatedAtMs = timestampMs;
    }

    private JsonObject toStatusJson() {
      JsonObject body = new JsonObject();
      body.addProperty(JSON_KEY_COMMAND_ID, commandId);
      body.addProperty(JSON_KEY_CLIENT_ID, clientId);
      body.addProperty(JSON_KEY_REQUEST_ID, requestId);
      body.addProperty(JSON_KEY_NAME, name);
      body.add(JSON_KEY_ARGS, args.deepCopy());
      body.addProperty(JSON_KEY_STATUS, status);
      body.addProperty(JSON_KEY_MESSAGE, message);
      body.addProperty(JSON_KEY_STOP_REQUESTED, stopRequested);
      body.addProperty(JSON_KEY_CREATED_AT_MS, createdAtMs);
      body.addProperty(JSON_KEY_UPDATED_AT_MS, updatedAtMs);
      body.addProperty(JSON_KEY_OUTPUT_AVAILABLE, !outputChunks.isEmpty());
      body.addProperty(JSON_KEY_DROPPED, outputDropped);
      body.addProperty(JSON_KEY_NEXT_SEQUENCE, nextOutputSequence);
      return body;
    }
  }
}
