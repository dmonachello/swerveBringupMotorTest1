package frc.robot.rest;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import frc.robot.telemetry.SampledTelemetrySampler;
import org.junit.jupiter.api.Test;

/** NAME TelemetryRestJsonCodecTest - Versioned telemetry wire contract regressions. */
final class TelemetryRestJsonCodecTest {
  private static final long ROBOT_REPLY_US = 123_456L;

  @Test
  void catalogAndHistoryExposeGenerationClockAndReplyTime() {
    SampledTelemetrySampler sampler = new SampledTelemetrySampler();

    JsonObject catalog = TelemetryRestJsonCodec.encodeCatalog(sampler.getSignalCatalog());
    JsonObject history =
        TelemetryRestJsonCodec.encodeHistory(sampler, new JsonObject(), ROBOT_REPLY_US);

    assertTrue(catalog.has("historyGenerationId"));
    assertTrue(catalog.has("catalogRevision"));
    assertTrue(catalog.has("clockDescriptor"));
    assertEquals(ROBOT_REPLY_US, history.get("robotReplyUs").getAsLong());
    assertTrue(history.has("cursorExpired"));
  }
}
