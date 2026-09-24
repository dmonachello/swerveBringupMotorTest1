package frc.robot.rest;

import com.google.gson.JsonObject;
import frc.robot.telemetry.capture.WpilogTelemetryRecorder;

/** NAME TelemetryCaptureJsonCodec - REST adapter for robot-local capture status. */
public final class TelemetryCaptureJsonCodec {
  private static final String KEY_OK = "ok";
  private static final String KEY_RECORDING = "recording";
  private static final String KEY_PATH = "path";
  private static final String KEY_STORAGE = "storage";
  private static final String KEY_DROPPED_RECORDS = "droppedRecords";
  private static final String KEY_LAST_STOP_REASON = "lastStopReason";
  private static final String KEY_MESSAGE = "message";
  private static final String KEY_AUTO_MATCH_ENABLED = "autoMatchEnabled";
  private static final String KEY_AUTO_EXCEPTION_ENABLED = "autoExceptionEnabled";

  private TelemetryCaptureJsonCodec() {}

  /** NAME encode - Convert capture domain status into stable wire JSON. */
  public static JsonObject encode(WpilogTelemetryRecorder.CaptureStatus status) {
    JsonObject json = new JsonObject();
    json.addProperty(KEY_OK, status.ok());
    json.addProperty(KEY_RECORDING, status.recording());
    json.addProperty(KEY_PATH, status.path());
    json.addProperty(KEY_STORAGE, status.storage());
    json.addProperty(KEY_DROPPED_RECORDS, status.droppedRecords());
    json.addProperty(KEY_LAST_STOP_REASON, status.lastStopReason());
    json.addProperty(KEY_MESSAGE, status.message());
    json.addProperty(KEY_AUTO_MATCH_ENABLED, status.autoMatchEnabled());
    json.addProperty(KEY_AUTO_EXCEPTION_ENABLED, status.autoExceptionEnabled());
    return json;
  }
}
