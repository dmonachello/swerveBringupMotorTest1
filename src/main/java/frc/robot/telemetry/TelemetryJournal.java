package frc.robot.telemetry;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * NAME
 *   TelemetryJournal - Bounded robot-local history of accepted telemetry samples.
 *
 * DESCRIPTION
 *   Stores samples in primitive arrays so appends on the robot periodic thread
 *   do not allocate per-sample objects. Catalog and page objects are created
 *   only when descriptors are registered or a consumer reads history.
 */
public final class TelemetryJournal {
  private static final int NO_SIGNAL_INDEX = -1;
  private static final long NO_SEQUENCE = 0L;
  private static final int FIRST_SIGNAL_INDEX = 0;
  private static final int FIRST_RING_INDEX = 0;
  private static final long INITIAL_GENERATION = 1L;
  private static final long FIRST_SEQUENCE = 1L;
  private static final int EMPTY_SIZE = 0;
  private static final int RING_STEP = 1;

  private final long retentionDurationUs;
  private final long[] sequences;
  private final long[] timestampsUs;
  private final long[] numericValueBits;
  private final int[] signalIndexes;
  private final byte[] qualities;
  private final List<TelemetrySignalDescriptor> descriptors = new ArrayList<>();
  private final Map<String, Integer> signalIndexesByDefinitionKey = new LinkedHashMap<>();
  private String sourceInstanceId = UUID.randomUUID().toString();
  private long generation = INITIAL_GENERATION;
  private long nextSequence = FIRST_SEQUENCE;
  private long catalogRevision = NO_SEQUENCE;
  private int head = FIRST_RING_INDEX;
  private int size = EMPTY_SIZE;
  private volatile SampleListener sampleListener;

  /** NAME TelemetryJournal - Construct the production robot journal. */
  public TelemetryJournal() {
    this(
        TelemetryConstants.ROBOT_JOURNAL_MAX_RECORDS,
        TelemetryConstants.ROBOT_JOURNAL_DURATION_US);
  }

  TelemetryJournal(int capacity, long retentionDurationUs) {
    if (capacity <= EMPTY_SIZE) {
      throw new IllegalArgumentException(TelemetryConstants.CAPACITY_ERROR_MESSAGE);
    }
    this.retentionDurationUs = retentionDurationUs;
    sequences = new long[capacity];
    timestampsUs = new long[capacity];
    numericValueBits = new long[capacity];
    signalIndexes = new int[capacity];
    qualities = new byte[capacity];
  }

  /**
   * NAME
   *   registerSignal - Add a descriptor or return its existing stable index.
   *
   * RETURNS
   *   Stable journal-local signal index used by the allocation-free append path.
   */
  public synchronized int registerSignal(TelemetrySignalDescriptor descriptor) {
    if (descriptor == null || descriptor.signalDefinitionKey() == null) {
      return NO_SIGNAL_INDEX;
    }
    Integer existing = signalIndexesByDefinitionKey.get(descriptor.signalDefinitionKey());
    if (existing != null) {
      return existing;
    }
    int signalIndex = descriptors.size();
    TelemetrySignalDescriptor boundDescriptor =
        descriptor.withSourceInstance(sourceInstanceId, buildSignalId(descriptor, sourceInstanceId));
    descriptors.add(boundDescriptor);
    signalIndexesByDefinitionKey.put(boundDescriptor.signalDefinitionKey(), signalIndex);
    catalogRevision++;
    SampleListener listener = sampleListener;
    if (listener != null) {
      listener.onSignalRegistered(signalIndex, boundDescriptor);
    }
    return signalIndex;
  }

  /**
   * NAME
   *   appendNumeric - Append one accepted numeric observation.
   *
   * NOTES
   *   The successful append path allocates no objects.
   */
  public synchronized void appendNumeric(
      int signalIndex,
      long sourceTimestampUs,
      double value,
      TelemetryQuality quality) {
    if (signalIndex < FIRST_SIGNAL_INDEX || signalIndex >= descriptors.size()) {
      return;
    }
    evictExpired(sourceTimestampUs);
    if (size == sequences.length) {
      removeOldest();
    }
    int tail = (head + size) % sequences.length;
    long sequence = nextSequence++;
    sequences[tail] = sequence;
    timestampsUs[tail] = sourceTimestampUs;
    numericValueBits[tail] = Double.doubleToRawLongBits(value);
    signalIndexes[tail] = signalIndex;
    qualities[tail] = (byte) quality.ordinal();
    size++;
    SampleListener listener = sampleListener;
    if (listener != null) {
      listener.onNumericSample(
          sequence,
          signalIndex,
          sourceTimestampUs,
          value,
          quality);
    }
  }

  /**
   * NAME
   *   setSampleListener - Attach or detach the single format-neutral capture consumer.
   */
  public synchronized void setSampleListener(SampleListener listener) {
    sampleListener = listener;
    if (listener == null) {
      return;
    }
    for (int signalIndex = FIRST_SIGNAL_INDEX;
        signalIndex < descriptors.size();
        signalIndex++) {
      listener.onSignalRegistered(signalIndex, descriptors.get(signalIndex));
    }
  }

  /**
   * NAME
   *   readAfter - Copy one bounded history page after a journal cursor.
   *
   * RETURNS
   *   Records in append order plus cursor and eviction information.
   */
  public HistoryPage readAfter(long afterSequence, int maxRecords) {
    return readAfter(afterSequence, maxRecords, Collections.emptySet());
  }

  /**
   * NAME
   *   readAfter - Copy a filtered history page after a journal cursor.
   *
   * PARAMETERS
   *   signalIds - Empty for all signals, otherwise the selected stable signal IDs.
   */
  public HistoryPage readAfter(
      long afterSequence,
      int maxRecords,
      Set<String> signalIds) {
    int normalizedLimit =
        Math.min(
            TelemetryConstants.JOURNAL_MAX_READ_RECORDS,
            Math.max(EMPTY_SIZE, maxRecords));
    long[] pageSequences = new long[normalizedLimit];
    long[] pageTimestampsUs = new long[normalizedLimit];
    long[] pageValueBits = new long[normalizedLimit];
    byte[] pageQualities = new byte[normalizedLimit];
    TelemetrySignalDescriptor[] pageDescriptors =
        new TelemetrySignalDescriptor[normalizedLimit];
    long oldestSequence;
    long pageCursor;
    long pageGeneration;
    String pageSourceInstanceId;
    boolean cursorExpired;
    boolean hasMore;
    int recordCount = EMPTY_SIZE;
    synchronized (this) {
      oldestSequence = size == EMPTY_SIZE ? nextSequence : sequences[head];
      cursorExpired = afterSequence < oldestSequence - FIRST_SEQUENCE;
      long effectiveCursor = cursorExpired ? oldestSequence - FIRST_SEQUENCE : afterSequence;
      pageCursor = effectiveCursor;
      for (int offset = EMPTY_SIZE;
          offset < size && recordCount < normalizedLimit;
          offset++) {
        int index = (head + offset) % sequences.length;
        if (sequences[index] <= effectiveCursor) {
          continue;
        }
        TelemetrySignalDescriptor descriptor = descriptors.get(signalIndexes[index]);
        pageCursor = sequences[index];
        if (signalIds != null
            && !signalIds.isEmpty()
            && !signalIds.contains(descriptor.signalId())) {
          continue;
        }
        pageSequences[recordCount] = sequences[index];
        pageTimestampsUs[recordCount] = timestampsUs[index];
        pageValueBits[recordCount] = numericValueBits[index];
        pageQualities[recordCount] = qualities[index];
        pageDescriptors[recordCount] = descriptor;
        recordCount++;
      }
      hasMore = pageCursor < nextSequence - FIRST_SEQUENCE;
      pageGeneration = generation;
      pageSourceInstanceId = sourceInstanceId;
    }
    List<HistoryRecord> records = new ArrayList<>(recordCount);
    for (int index = EMPTY_SIZE; index < recordCount; index++) {
      records.add(
          new HistoryRecord(
              pageSequences[index],
              pageDescriptors[index].signalId(),
              pageTimestampsUs[index],
              Double.longBitsToDouble(pageValueBits[index]),
              TelemetryQuality.values()[pageQualities[index]]));
    }
    return new HistoryPage(
        pageGeneration,
        pageSourceInstanceId,
        oldestSequence,
        pageCursor,
        hasMore,
        cursorExpired,
        Collections.unmodifiableList(records));
  }

  /** NAME catalog - Snapshot the current signal catalog. */
  public synchronized SignalCatalog catalog() {
    return new SignalCatalog(
        generation,
        sourceInstanceId,
        catalogRevision,
        List.copyOf(descriptors));
  }

  /** NAME clear - Start a new generation without reallocating sample arrays. */
  public synchronized void clear() {
    head = FIRST_RING_INDEX;
    size = EMPTY_SIZE;
    nextSequence = FIRST_SEQUENCE;
    generation++;
    descriptors.clear();
    signalIndexesByDefinitionKey.clear();
    catalogRevision = NO_SEQUENCE;
    SampleListener listener = sampleListener;
    if (listener != null) {
      listener.onGenerationReset(sourceInstanceId);
    }
  }

  private void evictExpired(long sourceTimestampUs) {
    while (size > EMPTY_SIZE
        && sourceTimestampUs - timestampsUs[head] > retentionDurationUs) {
      removeOldest();
    }
  }

  private void removeOldest() {
    head = (head + RING_STEP) % sequences.length;
    size--;
  }

  private static String buildSignalId(
      TelemetrySignalDescriptor descriptor,
      String sourceInstanceId) {
    return sourceInstanceId
        + TelemetryConstants.SIGNAL_ID_SEPARATOR
        + descriptor.signalDefinitionKey();
  }

  /** One immutable history record returned outside the robot sampling path. */
  public record HistoryRecord(
      long sequence,
      String signalId,
      long sourceTimestampUs,
      double numericValue,
      TelemetryQuality quality) {}

  /** One cursor-addressed page of immutable history records. */
  public record HistoryPage(
      long generation,
      String sourceInstanceId,
      long oldestSequence,
      long nextSequence,
      boolean hasMore,
      boolean cursorExpired,
      List<HistoryRecord> records) {}

  /** Immutable snapshot of catalog identity and signal descriptors. */
  public record SignalCatalog(
      long generation,
      String sourceInstanceId,
      long revision,
      List<TelemetrySignalDescriptor> signals) {}

  /** Allocation-free notification boundary used by optional capture sinks. */
  public interface SampleListener {
    void onGenerationReset(String sourceInstanceId);

    void onSignalRegistered(int signalIndex, TelemetrySignalDescriptor descriptor);

    void onNumericSample(
        long sequence,
        int signalIndex,
        long sourceTimestampUs,
        double value,
        TelemetryQuality quality);
  }
}
