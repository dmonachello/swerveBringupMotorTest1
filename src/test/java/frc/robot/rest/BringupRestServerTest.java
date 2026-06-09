package frc.robot.rest;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   BringupRestServerTest - Focused REST control-plane regression tests.
 *
 * DESCRIPTION
 *   Verifies the first REST slice without requiring live robot hardware by
 *   running an ephemeral in-process server and exercising the session,
 *   command, output, and log endpoints.
 */
public final class BringupRestServerTest {
  private static final Gson GSON = new Gson();
  private static final String CLIENT_A = "clientA";
  private static final String CLIENT_B = "clientB";
  private static final String REQUEST_ID = "req1";
  private static final String COMMAND_SHOW_DEVICES = "showDevices";
  private static final String TEXT_DEVICES = "devices";
  private static final String TEXT_CLIENT_ID = "clientId";
  private static final String TEXT_REQUEST_ID = "requestId";
  private static final String TEXT_NAME = "name";
  private static final String TEXT_COMMAND_ID = "commandId";
  private static final String TEXT_STATUS = "status";
  private static final String TEXT_OUTPUT = "output";
  private static final String TEXT_CHUNKS = "chunks";
  private static final String TEXT_NEXT_SEQUENCE = "nextSequence";
  private static final String TEXT_CONFIG = "config";
  private static final String STATUS_FINISHED = "FINISHED";
  private static final int HTTP_OK = 200;
  private static final int HTTP_ACCEPTED = 202;
  private static final int HTTP_CONFLICT = 409;

  private BringupRestServer server;

  @AfterEach
  public void tearDown() {
    if (server != null) {
      server.stop();
      server = null;
    }
  }

  @Test
  public void restServerHandlesConnectImmediateCommandAndOutputDrain() throws Exception {
    server = new BringupRestServer(0, new TestCallbacks());
    server.start();
    HttpClient client = HttpClient.newHttpClient();

    JsonObject connect = new JsonObject();
    connect.addProperty(TEXT_CLIENT_ID, CLIENT_A);
    HttpResponse<String> connectResponse =
        client.send(post("/session/connect", connect), HttpResponse.BodyHandlers.ofString());
    assertEquals(HTTP_OK, connectResponse.statusCode());

    JsonObject secondConnect = new JsonObject();
    secondConnect.addProperty(TEXT_CLIENT_ID, CLIENT_B);
    HttpResponse<String> secondConnectResponse =
        client.send(post("/session/connect", secondConnect), HttpResponse.BodyHandlers.ofString());
    assertEquals(HTTP_CONFLICT, secondConnectResponse.statusCode());

    JsonObject submit = new JsonObject();
    submit.addProperty(TEXT_CLIENT_ID, CLIENT_A);
    submit.addProperty(TEXT_REQUEST_ID, REQUEST_ID);
    submit.addProperty(TEXT_NAME, COMMAND_SHOW_DEVICES);
    HttpResponse<String> submitResponse =
        client.send(post("/commands", submit), HttpResponse.BodyHandlers.ofString());
    assertEquals(HTTP_ACCEPTED, submitResponse.statusCode());
    JsonObject submitJson = GSON.fromJson(submitResponse.body(), JsonObject.class);
    long commandId = submitJson.get(TEXT_COMMAND_ID).getAsLong();

    HttpResponse<String> statusResponse =
        client.send(get("/commands/" + commandId + "?clientId=" + CLIENT_A), HttpResponse.BodyHandlers.ofString());
    assertEquals(HTTP_OK, statusResponse.statusCode());
    JsonObject statusJson = GSON.fromJson(statusResponse.body(), JsonObject.class);
    assertEquals(STATUS_FINISHED, statusJson.get(TEXT_STATUS).getAsString());

    HttpResponse<String> outputResponse =
        client.send(get("/commands/" + commandId + "/output?clientId=" + CLIENT_A), HttpResponse.BodyHandlers.ofString());
    assertEquals(HTTP_OK, outputResponse.statusCode());
    JsonObject outputJson = GSON.fromJson(outputResponse.body(), JsonObject.class);
    JsonArray chunks = outputJson.getAsJsonArray(TEXT_CHUNKS);
    assertTrue(chunks.size() > 0);

    HttpResponse<String> secondOutputResponse =
        client.send(get("/commands/" + commandId + "/output?clientId=" + CLIENT_A), HttpResponse.BodyHandlers.ofString());
    JsonObject secondOutputJson = GSON.fromJson(secondOutputResponse.body(), JsonObject.class);
    assertEquals(0, secondOutputJson.getAsJsonArray(TEXT_CHUNKS).size());

    server.onBringupLine("hello");
    HttpResponse<String> logsResponse =
        client.send(get("/logs?after=0"), HttpResponse.BodyHandlers.ofString());
    JsonObject logsJson = GSON.fromJson(logsResponse.body(), JsonObject.class);
    assertTrue(logsJson.getAsJsonArray("logs").size() > 0);
    assertTrue(logsJson.get(TEXT_NEXT_SEQUENCE).getAsLong() > 0L);

    HttpResponse<String> configResponse =
        client.send(get("/config/current?clientId=" + CLIENT_A), HttpResponse.BodyHandlers.ofString());
    assertEquals(HTTP_OK, configResponse.statusCode());
    JsonObject configJson = GSON.fromJson(configResponse.body(), JsonObject.class);
    assertTrue(configJson.getAsJsonObject(TEXT_CONFIG).has("schema_version"));
  }

  private HttpRequest post(String path, JsonObject body) {
    return HttpRequest.newBuilder(baseUri(path))
        .header("Content-Type", "application/json")
        .POST(HttpRequest.BodyPublishers.ofString(GSON.toJson(body)))
        .build();
  }

  private HttpRequest get(String path) {
    return HttpRequest.newBuilder(baseUri(path)).GET().build();
  }

  private URI baseUri(String path) {
    return URI.create("http://127.0.0.1:" + server.getBoundPort() + path);
  }

  private static final class TestCallbacks implements BringupRestServer.RestCallbacks {
    @Override
    public JsonObject buildDevicesJson() {
      JsonObject root = new JsonObject();
      JsonArray devices = new JsonArray();
      JsonObject device = new JsonObject();
      device.addProperty("label", "motorA");
      devices.add(device);
      root.add(TEXT_DEVICES, devices);
      return root;
    }

    @Override
    public JsonObject buildRuntimeStateJson() {
      JsonObject root = new JsonObject();
      root.addProperty(TEXT_STATUS, STATUS_FINISHED);
      return root;
    }

    @Override
    public JsonObject buildCurrentConfigJson() {
      JsonObject root = new JsonObject();
      root.addProperty("schema_version", 1);
      root.addProperty("defaultProfile", "test");
      return root;
    }

    @Override
    public JsonObject buildCommandOutputJson(String name) {
      return null;
    }

    @Override
    public frc.robot.BridgeUiCommandHandler.RestCommandResult executeCommand(
        String name,
        String argsJson,
        String clientId) {
      return null;
    }

    @Override
    public boolean isCommandActive(String name) {
      return false;
    }
  }
}
