package frc.robot.telemetry;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/**
 * NAME
 *   TelemetryJournalTest - Primitive journal retention and paging regressions.
 */
final class TelemetryJournalTest {
  private static final int CAPACITY = 2;
  private static final long RETENTION_US = 1_000L;
  private static final long FIRST_TIMESTAMP_US = 100L;
  private static final long SECOND_TIMESTAMP_US = 200L;
  private static final long THIRD_TIMESTAMP_US = 300L;
  private static final long FOURTH_TIMESTAMP_US = 400L;
  private static final double FIRST_VALUE = 1.0;
  private static final double SECOND_VALUE = 2.0;
  private static final double THIRD_VALUE = 3.0;
  private static final double FOURTH_VALUE = 4.0;
  private static final int PAGE_LIMIT = 10;
  private static final long START_CURSOR = 0L;
  private static final long EVICTED_CURSOR = 1L;
  private static final String DEFINITION_KEY = "test|motor|1|current_actual";
  private static final String SUBJECT_KEY = "test|motor|1";
  private static final String DEVICE_LABEL = "motor1";

  @Test
  void countEvictionReportsExpiredCursorAndKeepsOrder() {
    TelemetryJournal journal = new TelemetryJournal(CAPACITY, RETENTION_US);
    int signalIndex = journal.registerSignal(descriptor());

    journal.appendNumeric(signalIndex, FIRST_TIMESTAMP_US, FIRST_VALUE, TelemetryQuality.GOOD);
    journal.appendNumeric(signalIndex, SECOND_TIMESTAMP_US, SECOND_VALUE, TelemetryQuality.GOOD);
    journal.appendNumeric(signalIndex, THIRD_TIMESTAMP_US, THIRD_VALUE, TelemetryQuality.GOOD);
    journal.appendNumeric(signalIndex, FOURTH_TIMESTAMP_US, FOURTH_VALUE, TelemetryQuality.GOOD);

    TelemetryJournal.HistoryPage page = journal.readAfter(EVICTED_CURSOR, PAGE_LIMIT);
    assertTrue(page.cursorExpired());
    assertEquals(2, page.records().size());
    assertEquals(THIRD_TIMESTAMP_US, page.records().get(0).sourceTimestampUs());
    assertEquals(FOURTH_TIMESTAMP_US, page.records().get(1).sourceTimestampUs());
    assertFalse(page.hasMore());
  }

  @Test
  void catalogBindsSignalToCurrentSourceInstance() {
    TelemetryJournal journal = new TelemetryJournal(CAPACITY, RETENTION_US);
    journal.registerSignal(descriptor());

    TelemetryJournal.SignalCatalog catalog = journal.catalog();
    assertEquals(1, catalog.signals().size());
    assertEquals(catalog.sourceInstanceId(), catalog.signals().get(0).sourceInstanceId());
    assertTrue(catalog.signals().get(0).signalId().contains(DEFINITION_KEY));
    assertTrue(journal.readAfter(START_CURSOR, PAGE_LIMIT).records().isEmpty());
  }

  @Test
  void timeRetentionEvictsSamplesOutsideWindow() {
    TelemetryJournal journal = new TelemetryJournal(CAPACITY, FIRST_TIMESTAMP_US);
    int signalIndex = journal.registerSignal(descriptor());
    journal.appendNumeric(signalIndex, FIRST_TIMESTAMP_US, FIRST_VALUE, TelemetryQuality.GOOD);
    journal.appendNumeric(signalIndex, THIRD_TIMESTAMP_US, THIRD_VALUE, TelemetryQuality.GOOD);

    TelemetryJournal.HistoryPage page = journal.readAfter(START_CURSOR, PAGE_LIMIT);

    assertEquals(1, page.records().size());
    assertEquals(THIRD_TIMESTAMP_US, page.records().get(0).sourceTimestampUs());
  }

  @Test
  void readPageNeverExceedsRobotPageLimit() {
    int sampleCount = TelemetryConstants.JOURNAL_MAX_READ_RECORDS + 1;
    TelemetryJournal journal = new TelemetryJournal(sampleCount, Long.MAX_VALUE);
    int signalIndex = journal.registerSignal(descriptor());
    for (int index = 0; index < sampleCount; index++) {
      journal.appendNumeric(signalIndex, index, index, TelemetryQuality.GOOD);
    }

    TelemetryJournal.HistoryPage page =
        journal.readAfter(START_CURSOR, Integer.MAX_VALUE);

    assertEquals(TelemetryConstants.JOURNAL_MAX_READ_RECORDS, page.records().size());
    assertTrue(page.hasMore());
  }

  private static TelemetrySignalDescriptor descriptor() {
    return new TelemetrySignalDescriptor(
        DEFINITION_KEY,
        "",
        "",
        SUBJECT_KEY,
        DEVICE_LABEL,
        SampledSignalNames.CURRENT_ACTUAL,
        TelemetryValueKind.NUMBER,
        TelemetryUnit.AMPERE,
        TelemetryEngineeringDimension.ELECTRIC_CURRENT,
        TelemetryConstants.DEFAULT_NOMINAL_CADENCE_US,
        TelemetryConstants.DEFAULT_STALE_AFTER_US,
        true);
  }
}
