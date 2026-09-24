package frc.robot.rest;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import frc.robot.telemetry.TelemetryJournal;
import frc.robot.telemetry.SampledTelemetrySampler;
import frc.robot.telemetry.TelemetrySignalDescriptor;
import java.nio.charset.StandardCharsets;

/**
 * NAME
 *   TelemetryRestJsonCodec - Versioned REST adapter for telemetry domain records.
 *
 * DESCRIPTION
 *   Keeps Gson and wire-field knowledge outside the journal and sampler.
 */
public final class TelemetryRestJsonCodec {
  private static final int SCHEMA_VERSION = 1;
  private static final int DEFAULT_PAGE_RECORDS = 2_000;
  private static final int MAX_PAGE_RECORDS = 2_000;
  private static final int MAX_ENCODED_PAGE_BYTES = 1_048_576;
  private static final int RESPONSE_METADATA_BUDGET_BYTES = 2_048;
  private static final int MIN_PAGE_RECORDS = 1;
  private static final long DEFAULT_AFTER_SEQUENCE = 0L;
  private static final String KEY_SCHEMA_VERSION = "schemaVersion";
  private static final String KEY_HISTORY_GENERATION_ID = "historyGenerationId";
  private static final String KEY_SOURCE_INSTANCE_ID = "sourceInstanceId";
  private static final String KEY_CATALOG_REVISION = "catalogRevision";
  private static final String KEY_CLOCK_DESCRIPTOR = "clockDescriptor";
  private static final String KEY_CLOCK_ID = "clockId";
  private static final String KEY_CLOCK_KIND = "kind";
  private static final String KEY_TICKS_PER_SECOND = "ticksPerSecond";
  private static final String CLOCK_KIND_FPGA_MONOTONIC = "FPGA_MONOTONIC";
  private static final long CLOCK_TICKS_PER_SECOND = 1_000_000L;
  private static final String KEY_SIGNALS = "signals";
  private static final String KEY_SIGNAL_DEFINITION_KEY = "signalDefinitionKey";
  private static final String KEY_SIGNAL_ID = "signalId";
  private static final String KEY_SUBJECT_KEY = "subjectKey";
  private static final String KEY_DEVICE_LABEL = "deviceLabel";
  private static final String KEY_SIGNAL_NAME = "signalName";
  private static final String KEY_VALUE_KIND = "valueKind";
  private static final String KEY_UNIT = "unit";
  private static final String KEY_UNIT_SYMBOL = "unitSymbol";
  private static final String KEY_ENGINEERING_DIMENSION = "engineeringDimension";
  private static final String KEY_NOMINAL_CADENCE_US = "nominalCadenceUs";
  private static final String KEY_STALE_AFTER_US = "staleAfterUs";
  private static final String KEY_GRAPHABLE = "graphable";
  private static final String KEY_AFTER_SEQUENCE = "afterSequence";
  private static final String KEY_MAX_RECORDS = "maxRecords";
  private static final String KEY_OLDEST_SEQUENCE = "oldestSequence";
  private static final String KEY_NEXT_SEQUENCE = "nextSequence";
  private static final String KEY_HAS_MORE = "hasMore";
  private static final String KEY_CURSOR_EXPIRED = "cursorExpired";
  private static final String KEY_ROBOT_REPLY_US = "robotReplyUs";
  private static final String KEY_RECORDS = "records";
  private static final String KEY_SEQUENCE = "sequence";
  private static final String KEY_SOURCE_TIMESTAMP_US = "sourceTimestampUs";
  private static final String KEY_NUMERIC_VALUE = "numericValue";
  private static final String KEY_QUALITY = "quality";

  private TelemetryRestJsonCodec() {}

  /** NAME encodeCatalog - Encode a domain catalog as versioned JSON. */
  public static JsonObject encodeCatalog(TelemetryJournal.SignalCatalog catalog) {
    JsonObject root = new JsonObject();
    root.addProperty(KEY_SCHEMA_VERSION, SCHEMA_VERSION);
    root.addProperty(KEY_HISTORY_GENERATION_ID, generationId(catalog));
    root.addProperty(KEY_SOURCE_INSTANCE_ID, catalog.sourceInstanceId());
    root.addProperty(KEY_CATALOG_REVISION, catalog.revision());
    JsonObject clock = new JsonObject();
    clock.addProperty(KEY_CLOCK_ID, catalog.sourceInstanceId());
    clock.addProperty(KEY_CLOCK_KIND, CLOCK_KIND_FPGA_MONOTONIC);
    clock.addProperty(KEY_TICKS_PER_SECOND, CLOCK_TICKS_PER_SECOND);
    root.add(KEY_CLOCK_DESCRIPTOR, clock);
    JsonArray signals = new JsonArray();
    for (TelemetrySignalDescriptor descriptor : catalog.signals()) {
      JsonObject signal = new JsonObject();
      signal.addProperty(KEY_SIGNAL_DEFINITION_KEY, descriptor.signalDefinitionKey());
      signal.addProperty(KEY_SIGNAL_ID, descriptor.signalId());
      signal.addProperty(KEY_SOURCE_INSTANCE_ID, descriptor.sourceInstanceId());
      signal.addProperty(KEY_SUBJECT_KEY, descriptor.subjectKey());
      signal.addProperty(KEY_DEVICE_LABEL, descriptor.deviceLabel());
      signal.addProperty(KEY_SIGNAL_NAME, descriptor.signalName());
      signal.addProperty(KEY_VALUE_KIND, descriptor.valueKind().name());
      signal.addProperty(KEY_UNIT, descriptor.unit().canonicalName());
      signal.addProperty(KEY_UNIT_SYMBOL, descriptor.unit().symbol());
      signal.addProperty(KEY_ENGINEERING_DIMENSION, descriptor.engineeringDimension().name());
      signal.addProperty(KEY_NOMINAL_CADENCE_US, descriptor.nominalCadenceUs());
      signal.addProperty(KEY_STALE_AFTER_US, descriptor.staleAfterUs());
      signal.addProperty(KEY_GRAPHABLE, descriptor.graphable());
      signals.add(signal);
    }
    root.add(KEY_SIGNALS, signals);
    return root;
  }

  /**
   * NAME
   *   encodeHistory - Query and encode a cursor-addressed domain history page.
   */
  public static JsonObject encodeHistory(
      SampledTelemetrySampler sampler,
      JsonObject request,
      long robotReplyUs) {
    long afterSequence = longValue(request, KEY_AFTER_SEQUENCE, DEFAULT_AFTER_SEQUENCE);
    int maxRecords =
        Math.min(
            MAX_PAGE_RECORDS,
            Math.max(
                MIN_PAGE_RECORDS,
                intValue(request, KEY_MAX_RECORDS, DEFAULT_PAGE_RECORDS)));
    TelemetryJournal.HistoryPage page =
        sampler.readHistoryAfter(afterSequence, maxRecords);
    JsonObject root = new JsonObject();
    root.addProperty(KEY_SCHEMA_VERSION, SCHEMA_VERSION);
    root.addProperty(
        KEY_HISTORY_GENERATION_ID,
        page.sourceInstanceId()
            + frc.robot.telemetry.TelemetryConstants.SIGNAL_ID_SEPARATOR
            + page.generation());
    root.addProperty(KEY_SOURCE_INSTANCE_ID, page.sourceInstanceId());
    root.addProperty(KEY_OLDEST_SEQUENCE, page.oldestSequence());
    root.addProperty(KEY_CURSOR_EXPIRED, page.cursorExpired());
    root.addProperty(KEY_ROBOT_REPLY_US, robotReplyUs);
    JsonArray records = new JsonArray();
    int encodedBytes = RESPONSE_METADATA_BUDGET_BYTES;
    long encodedCursor = afterSequence;
    int encodedRecords = 0;
    for (TelemetryJournal.HistoryRecord record : page.records()) {
      JsonObject sample = new JsonObject();
      sample.addProperty(KEY_SEQUENCE, record.sequence());
      sample.addProperty(KEY_SIGNAL_ID, record.signalId());
      sample.addProperty(KEY_SOURCE_TIMESTAMP_US, record.sourceTimestampUs());
      sample.addProperty(KEY_NUMERIC_VALUE, record.numericValue());
      sample.addProperty(KEY_QUALITY, record.quality().name());
      int sampleBytes = sample.toString().getBytes(StandardCharsets.UTF_8).length;
      if (encodedRecords > 0
          && encodedBytes + sampleBytes > MAX_ENCODED_PAGE_BYTES) {
        break;
      }
      records.add(sample);
      encodedBytes += sampleBytes;
      encodedCursor = record.sequence();
      encodedRecords++;
    }
    root.addProperty(KEY_NEXT_SEQUENCE, encodedCursor);
    root.addProperty(
        KEY_HAS_MORE,
        page.hasMore() || encodedRecords < page.records().size());
    root.add(KEY_RECORDS, records);
    return root;
  }

  private static long longValue(JsonObject root, String key, long fallback) {
    return root != null && root.has(key) ? root.get(key).getAsLong() : fallback;
  }

  private static int intValue(JsonObject root, String key, int fallback) {
    return root != null && root.has(key) ? root.get(key).getAsInt() : fallback;
  }

  private static String generationId(TelemetryJournal.SignalCatalog catalog) {
    return catalog.sourceInstanceId()
        + frc.robot.telemetry.TelemetryConstants.SIGNAL_ID_SEPARATOR
        + catalog.generation();
  }
}
