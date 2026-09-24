package frc.robot.telemetry.capture;

import com.google.gson.Gson;
import edu.wpi.first.util.datalog.DataLogWriter;
import edu.wpi.first.util.datalog.DoubleLogEntry;
import edu.wpi.first.util.datalog.StringLogEntry;
import frc.robot.telemetry.SampledTelemetrySampler;
import frc.robot.telemetry.TelemetryJournal;
import frc.robot.telemetry.TelemetryQuality;
import frc.robot.telemetry.TelemetrySignalDescriptor;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * NAME
 *   WpilogTelemetryRecorder - Opt-in robot-local signal-history capture.
 *
 * DESCRIPTION
 *   Writes the retained pre-trigger page followed by live records. The robot
 *   periodic listener only copies primitives into a bounded ring; WPILOG work
 *   runs on a dedicated daemon and WPILib's background file writer.
 */
public final class WpilogTelemetryRecorder implements TelemetryJournal.SampleListener {
  private static final Gson GSON = new Gson();
  private static final int EMPTY_QUEUE_SIZE = 0;
  private static final int FIRST_QUEUE_INDEX = 0;
  private static final int QUEUE_STEP = 1;

  private final SampledTelemetrySampler sampler;
  private final Path configuredDirectory;
  private final Object queueLock = new Object();
  private final Object writerLock = new Object();
  private final long[] sequences = new long[TelemetryCaptureConstants.WRITER_QUEUE_RECORDS];
  private final int[] signalIndexes = new int[TelemetryCaptureConstants.WRITER_QUEUE_RECORDS];
  private final long[] timestampsUs = new long[TelemetryCaptureConstants.WRITER_QUEUE_RECORDS];
  private final long[] valueBits = new long[TelemetryCaptureConstants.WRITER_QUEUE_RECORDS];
  private final Map<Integer, TelemetrySignalDescriptor> descriptors = new ConcurrentHashMap<>();
  private final Map<Integer, DoubleLogEntry> entries = new ConcurrentHashMap<>();
  private final Thread writerThread;
  private volatile boolean shutdown;
  private volatile boolean recording;
  private volatile int droppedRecords;
  private int pendingDroppedRecords;
  private volatile String currentPath = TelemetryCaptureConstants.STOP_REASON_NONE;
  private volatile String lastStopReason = TelemetryCaptureConstants.STOP_REASON_NONE;
  private volatile boolean autoMatchEnabled;
  private volatile boolean autoExceptionEnabled;
  private volatile boolean automaticStartRequested;
  private volatile String automaticStartAnnotation = TelemetryCaptureConstants.STOP_REASON_NONE;
  private volatile String pendingAnnotation = TelemetryCaptureConstants.STOP_REASON_NONE;
  private volatile String automaticStopReason = TelemetryCaptureConstants.STOP_REASON_NONE;
  private volatile long automaticStopAtMs;
  private volatile long lastSourceTimestampUs;
  private volatile boolean generationResetRequested;
  private volatile String pendingSourceInstanceId = TelemetryCaptureConstants.STOP_REASON_NONE;
  private long exceptionCooldownUntilMs;
  private boolean previousRobotEnabled;
  private volatile boolean automaticCapture;
  private int queueHead = FIRST_QUEUE_INDEX;
  private int queueSize = EMPTY_QUEUE_SIZE;
  private int inFlightRecords = EMPTY_QUEUE_SIZE;
  private long lastWrittenSequence;
  private long captureStartedMs;
  private int recordsSinceLimitCheck;
  private DataLogWriter log;
  private StringLogEntry gapEntry;
  private StringLogEntry annotationEntry;

  /** NAME WpilogTelemetryRecorder - Construct the production storage-selecting recorder. */
  public WpilogTelemetryRecorder(SampledTelemetrySampler sampler) {
    this(sampler, null);
  }

  WpilogTelemetryRecorder(SampledTelemetrySampler sampler, Path configuredDirectory) {
    this.sampler = sampler;
    this.configuredDirectory = configuredDirectory;
    writerThread = new Thread(this::writerLoop, "telemetry-wpilog-writer");
    writerThread.setDaemon(true);
    writerThread.start();
    sampler.setCaptureListener(this);
  }

  /**
   * NAME
   *   start - Begin one manual capture with retained pre-trigger history.
   *
   * RETURNS
   *   Current capture status including selected storage and any error.
   */
  public CaptureStatus start() {
    return startInternal(false);
  }

  private CaptureStatus startInternal(boolean automaticStart) {
    synchronized (writerLock) {
      if (recording) {
        return status(false, TelemetryCaptureConstants.ERROR_ALREADY_RECORDING);
      }
      try {
        Path directory = chooseDirectory();
        Files.createDirectories(directory);
        String filename =
            TelemetryCaptureConstants.FILE_PREFIX
                + System.currentTimeMillis()
                + TelemetryCaptureConstants.FILE_SUFFIX;
        currentPath = directory.resolve(filename).toString();
        log = new DataLogWriter(currentPath, TelemetryCaptureConstants.EXTRA_HEADER);
        entries.clear();
        clearQueue();
        lastWrittenSequence = EMPTY_QUEUE_SIZE;
        captureStartedMs = System.currentTimeMillis();
        recordsSinceLimitCheck = EMPTY_QUEUE_SIZE;
        droppedRecords = EMPTY_QUEUE_SIZE;
        pendingDroppedRecords = EMPTY_QUEUE_SIZE;
        lastStopReason = TelemetryCaptureConstants.STOP_REASON_NONE;
        automaticCapture = automaticStart;
        if (!automaticStart) {
          automaticStopAtMs = EMPTY_QUEUE_SIZE;
          automaticStopReason = TelemetryCaptureConstants.STOP_REASON_NONE;
        }
        for (Map.Entry<Integer, TelemetrySignalDescriptor> entry : descriptors.entrySet()) {
          ensureEntry(entry.getKey(), entry.getValue());
        }
        recording = true;
        appendPretriggerHistory();
        return status(true, TelemetryCaptureConstants.STOP_REASON_NONE);
      } catch (IOException | RuntimeException ex) {
        recording = false;
        automaticCapture = false;
        closeLogAfterFailure();
        return status(
            false,
            TelemetryCaptureConstants.ERROR_START_PREFIX + ex.getMessage());
      }
    }
  }

  /** NAME stop - Stop, flush, and close the active capture. */
  public CaptureStatus stop() {
    if (!recording) {
      return status(false, TelemetryCaptureConstants.ERROR_NOT_RECORDING);
    }
    recording = false;
    long deadline =
        System.currentTimeMillis() + TelemetryCaptureConstants.STOP_DRAIN_TIMEOUT_MS;
    while (queuedRecordCount() > EMPTY_QUEUE_SIZE
        && System.currentTimeMillis() < deadline) {
      Thread.yield();
    }
    markUndrainedRecordsDropped();
    synchronized (writerLock) {
      appendPendingGap(lastSourceTimestampUs);
      closeLog();
      lastStopReason = TelemetryCaptureConstants.STOP_REASON_OPERATOR;
      automaticCapture = false;
      automaticStopAtMs = EMPTY_QUEUE_SIZE;
      automaticStopReason = TelemetryCaptureConstants.STOP_REASON_NONE;
    }
    return status(true, TelemetryCaptureConstants.STOP_REASON_NONE);
  }

  /** NAME status - Return current capture state without touching storage. */
  public CaptureStatus status() {
    return status(true, TelemetryCaptureConstants.STOP_REASON_NONE);
  }

  /** NAME configureAutomaticTriggers - Apply opt-in match and exception trigger policy. */
  public CaptureStatus configureAutomaticTriggers(
      boolean matchEnable,
      boolean uncaughtException) {
    autoMatchEnabled = matchEnable;
    autoExceptionEnabled = uncaughtException;
    return status();
  }

  /** NAME updateRobotEnabled - Observe Driver Station enable edges without file I/O. */
  public void updateRobotEnabled(boolean enabled) {
    if (autoMatchEnabled && enabled && !previousRobotEnabled) {
      if (recording) {
        requestAnnotation(TelemetryCaptureConstants.ANNOTATION_MATCH_ENABLE);
      } else {
        requestAutomaticStart(TelemetryCaptureConstants.ANNOTATION_MATCH_ENABLE);
      }
      if (automaticCapture
          && TelemetryCaptureConstants.STOP_REASON_MATCH_DISABLED.equals(
              automaticStopReason)) {
        automaticStopAtMs = EMPTY_QUEUE_SIZE;
        automaticStopReason = TelemetryCaptureConstants.STOP_REASON_NONE;
      }
    }
    if (autoMatchEnabled
        && !enabled
        && previousRobotEnabled
        && recording
        && automaticCapture) {
      automaticStopAtMs =
          System.currentTimeMillis()
              + TelemetryCaptureConstants.MATCH_DISABLE_POST_TRIGGER_MS;
      automaticStopReason = TelemetryCaptureConstants.STOP_REASON_MATCH_DISABLED;
    }
    previousRobotEnabled = enabled;
  }

  /** NAME onUncaughtException - Request best-effort exception-triggered capture. */
  public void onUncaughtException() {
    long nowMs = System.currentTimeMillis();
    if (!autoExceptionEnabled || nowMs < exceptionCooldownUntilMs) {
      return;
    }
    exceptionCooldownUntilMs =
        nowMs + TelemetryCaptureConstants.EXCEPTION_TRIGGER_COOLDOWN_MS;
    if (recording) {
      requestAnnotation(TelemetryCaptureConstants.ANNOTATION_EXCEPTION);
      return;
    }
    automaticStopAtMs = nowMs + TelemetryCaptureConstants.EXCEPTION_POST_TRIGGER_MS;
    automaticStopReason = TelemetryCaptureConstants.STOP_REASON_EXCEPTION_WINDOW;
    requestAutomaticStart(TelemetryCaptureConstants.ANNOTATION_EXCEPTION);
  }

  /** NAME close - Stop the worker and detach from the sampler. */
  public void close() {
    recording = false;
    automaticCapture = false;
    shutdown = true;
    synchronized (queueLock) {
      queueLock.notifyAll();
    }
    synchronized (writerLock) {
      closeLog();
    }
    sampler.setCaptureListener(null);
  }

  @Override
  public void onGenerationReset(String sourceInstanceId) {
    pendingSourceInstanceId = sourceInstanceId;
    generationResetRequested = true;
    synchronized (queueLock) {
      droppedRecords += queueSize;
      pendingDroppedRecords += queueSize;
      queueHead = FIRST_QUEUE_INDEX;
      queueSize = EMPTY_QUEUE_SIZE;
      queueLock.notifyAll();
    }
  }

  @Override
  public void onSignalRegistered(int signalIndex, TelemetrySignalDescriptor descriptor) {
    descriptors.put(signalIndex, descriptor);
  }

  @Override
  public void onNumericSample(
      long sequence,
      int signalIndex,
      long sourceTimestampUs,
      double value,
      TelemetryQuality quality) {
    if (!recording) {
      return;
    }
    lastSourceTimestampUs = sourceTimestampUs;
    synchronized (queueLock) {
      if (queueSize == sequences.length) {
        droppedRecords++;
        pendingDroppedRecords++;
        return;
      }
      int tail = (queueHead + queueSize) % sequences.length;
      sequences[tail] = sequence;
      signalIndexes[tail] = signalIndex;
      timestampsUs[tail] = sourceTimestampUs;
      valueBits[tail] = Double.doubleToRawLongBits(value);
      queueSize++;
      queueLock.notifyAll();
    }
  }

  /**
   * Drains capture commands and sample records without blocking the robot periodic thread.
   * Runtime writer failures stop the active capture and remain available through status.
   */
  private void writerLoop() {
    while (!shutdown) {
      long sequence;
      int signalIndex;
      long timestampUs;
      double value;
      boolean startRequested;
      boolean resetRequested;
      boolean stopRequested;
      String startAnnotation;
      String annotation;
      synchronized (queueLock) {
        while (queueSize == EMPTY_QUEUE_SIZE
            && !shutdown
            && !automaticStartRequested
            && !generationResetRequested
            && pendingAnnotation.isBlank()
            && !automaticStopDue()) {
          try {
            queueLock.wait(TelemetryCaptureConstants.WRITER_IDLE_WAIT_MS);
          } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            shutdown = true;
            return;
          }
        }
        if (shutdown) {
          return;
        }
        startRequested = automaticStartRequested;
        resetRequested = generationResetRequested;
        stopRequested = automaticStopDue();
        startAnnotation = automaticStartAnnotation;
        annotation =
            !startRequested && !resetRequested && !stopRequested
                ? pendingAnnotation
                : TelemetryCaptureConstants.STOP_REASON_NONE;
        if (resetRequested) {
          generationResetRequested = false;
          startRequested = false;
        } else if (startRequested) {
          automaticStartRequested = false;
          automaticStartAnnotation = TelemetryCaptureConstants.STOP_REASON_NONE;
        }
        if (!annotation.isBlank()) {
          pendingAnnotation = TelemetryCaptureConstants.STOP_REASON_NONE;
        }
        if (startRequested || resetRequested || stopRequested || !annotation.isBlank()) {
          sequence = EMPTY_QUEUE_SIZE;
          signalIndex = EMPTY_QUEUE_SIZE;
          timestampUs = EMPTY_QUEUE_SIZE;
          value = EMPTY_QUEUE_SIZE;
        } else {
          sequence = sequences[queueHead];
          signalIndex = signalIndexes[queueHead];
          timestampUs = timestampsUs[queueHead];
          value = Double.longBitsToDouble(valueBits[queueHead]);
          queueHead = (queueHead + QUEUE_STEP) % sequences.length;
          queueSize--;
          inFlightRecords++;
        }
      }
      if (resetRequested) {
        try {
          synchronized (writerLock) {
            appendSourceReset();
          }
        } catch (RuntimeException ex) {
          handleWriterFailure(ex);
        }
        continue;
      }
      if (startRequested) {
        CaptureStatus started = startInternal(true);
        if (started.ok()) {
          try {
            synchronized (writerLock) {
              appendAnnotation(startAnnotation);
            }
          } catch (RuntimeException ex) {
            handleWriterFailure(ex);
          }
        }
        continue;
      }
      if (stopRequested) {
        try {
          synchronized (writerLock) {
            stopFromWriter(automaticStopReason);
          }
        } catch (RuntimeException ex) {
          handleWriterFailure(ex);
        }
        automaticStopAtMs = EMPTY_QUEUE_SIZE;
        automaticStopReason = TelemetryCaptureConstants.STOP_REASON_NONE;
        continue;
      }
      if (!annotation.isBlank()) {
        try {
          synchronized (writerLock) {
            appendAnnotation(annotation);
          }
        } catch (RuntimeException ex) {
          handleWriterFailure(ex);
        }
        continue;
      }
      try {
        synchronized (writerLock) {
          appendPendingGap(timestampUs);
          appendLiveRecord(sequence, signalIndex, timestampUs, value);
        }
      } catch (RuntimeException ex) {
        handleWriterFailure(ex);
      } finally {
        synchronized (queueLock) {
          inFlightRecords--;
          queueLock.notifyAll();
        }
      }
    }
  }

  private void appendLiveRecord(
      long sequence,
      int signalIndex,
      long timestampUs,
      double value) {
    if (log == null || sequence <= lastWrittenSequence) {
      return;
    }
    TelemetrySignalDescriptor descriptor = descriptors.get(signalIndex);
    DoubleLogEntry entry = ensureEntry(signalIndex, descriptor);
    if (entry != null) {
      entry.append(value, timestampUs);
      lastWrittenSequence = sequence;
      enforceLimits();
    }
  }

  private void appendHistoryRecord(TelemetryJournal.HistoryRecord record) {
    if (record.sequence() <= lastWrittenSequence) {
      return;
    }
    DoubleLogEntry entry = entryBySignalId(record.signalId());
    if (entry != null) {
      entry.append(record.numericValue(), record.sourceTimestampUs());
      lastWrittenSequence = record.sequence();
      lastSourceTimestampUs = Math.max(lastSourceTimestampUs, record.sourceTimestampUs());
    }
  }

  /**
   * Copies the journal's retained history into a newly opened log in bounded pages.
   * A source reset or expired cursor is represented by the journal's gap records.
   */
  private void appendPretriggerHistory() {
    long cursor = EMPTY_QUEUE_SIZE;
    int copiedRecords = EMPTY_QUEUE_SIZE;
    boolean hasMore;
    do {
      TelemetryJournal.HistoryPage page =
          sampler.readHistoryAfter(
              cursor,
              TelemetryCaptureConstants.PRETRIGGER_PAGE_RECORDS);
      for (TelemetryJournal.HistoryRecord record : page.records()) {
        appendHistoryRecord(record);
        copiedRecords++;
        if (copiedRecords >= TelemetryCaptureConstants.PRETRIGGER_MAX_RECORDS) {
          return;
        }
      }
      cursor = page.nextSequence();
      hasMore = page.hasMore() && !page.records().isEmpty();
    } while (hasMore);
  }

  private DoubleLogEntry entryBySignalId(String signalId) {
    for (Map.Entry<Integer, TelemetrySignalDescriptor> descriptor : descriptors.entrySet()) {
      if (descriptor.getValue().signalId().equals(signalId)) {
        return ensureEntry(descriptor.getKey(), descriptor.getValue());
      }
    }
    return null;
  }

  private DoubleLogEntry ensureEntry(
      int signalIndex,
      TelemetrySignalDescriptor descriptor) {
    if (log == null || descriptor == null) {
      return null;
    }
    return entries.computeIfAbsent(
        signalIndex,
        ignored ->
            new DoubleLogEntry(
                log,
                TelemetryCaptureConstants.ENTRY_PREFIX + descriptor.signalDefinitionKey(),
                GSON.toJson(descriptor)));
  }

  private void appendPendingGap(long timestampUs) {
    int dropped;
    synchronized (queueLock) {
      dropped = pendingDroppedRecords;
      pendingDroppedRecords = EMPTY_QUEUE_SIZE;
    }
    if (dropped <= EMPTY_QUEUE_SIZE || log == null) {
      return;
    }
    if (gapEntry == null) {
      gapEntry =
          new StringLogEntry(
              log,
              TelemetryCaptureConstants.GAP_ENTRY_NAME,
              TelemetryCaptureConstants.GAP_ENTRY_METADATA);
    }
    gapEntry.append(
        TelemetryCaptureConstants.GAP_MESSAGE_PREFIX + dropped,
        timestampUs);
  }

  private void appendSourceReset() {
    lastWrittenSequence = EMPTY_QUEUE_SIZE;
    if (log == null) {
      return;
    }
    appendPendingGap(lastSourceTimestampUs);
    for (DoubleLogEntry entry : entries.values()) {
      entry.finish();
    }
    entries.clear();
    if (gapEntry == null) {
      gapEntry =
          new StringLogEntry(
              log,
              TelemetryCaptureConstants.GAP_ENTRY_NAME,
              TelemetryCaptureConstants.GAP_ENTRY_METADATA);
    }
    gapEntry.append(
        TelemetryCaptureConstants.SOURCE_RESET_MESSAGE_PREFIX + pendingSourceInstanceId,
        lastSourceTimestampUs);
  }

  private void appendAnnotation(String annotation) {
    if (log == null || annotation == null || annotation.isBlank()) {
      return;
    }
    if (annotationEntry == null) {
      annotationEntry =
          new StringLogEntry(
              log,
              TelemetryCaptureConstants.ANNOTATION_ENTRY_NAME,
              TelemetryCaptureConstants.ANNOTATION_ENTRY_METADATA);
    }
    annotationEntry.append(annotation, lastSourceTimestampUs);
  }

  /**
   * Selects a configured directory, then removable storage, then internal storage.
   * Every candidate must satisfy the reserved-free-space requirement before use.
   */
  private Path chooseDirectory() throws IOException {
    if (configuredDirectory != null) {
      ensureFreeSpace(configuredDirectory);
      return configuredDirectory;
    }
    Path usb = Path.of(TelemetryCaptureConstants.USB_LOG_DIRECTORY);
    if (Files.isDirectory(usb) && Files.isWritable(usb)) {
      ensureFreeSpace(usb);
      return usb;
    }
    Path internal = Path.of(TelemetryCaptureConstants.INTERNAL_LOG_DIRECTORY);
    ensureFreeSpace(internal);
    return internal;
  }

  /** Stops an automatic capture when its duration or file-size limit is reached. */
  private void enforceLimits() {
    recordsSinceLimitCheck++;
    if (recordsSinceLimitCheck < TelemetryCaptureConstants.LIMIT_CHECK_RECORD_INTERVAL) {
      return;
    }
    recordsSinceLimitCheck = EMPTY_QUEUE_SIZE;
    if (log != null) {
      log.flush();
    }
    if (System.currentTimeMillis() - captureStartedMs
        >= TelemetryCaptureConstants.MAX_CAPTURE_DURATION_MS) {
      stopFromWriter(TelemetryCaptureConstants.STOP_REASON_DURATION_LIMIT);
      return;
    }
    try {
      Path path = Path.of(currentPath);
      if (Files.size(path) >= TelemetryCaptureConstants.MAX_CAPTURE_FILE_BYTES) {
        stopFromWriter(TelemetryCaptureConstants.STOP_REASON_FILE_LIMIT);
        return;
      }
      if (Files.getFileStore(path).getUsableSpace()
          < TelemetryCaptureConstants.RESERVED_FREE_BYTES) {
        stopFromWriter(TelemetryCaptureConstants.STOP_REASON_FREE_SPACE);
      }
    } catch (IOException ex) {
      stopFromWriter(TelemetryCaptureConstants.STOP_REASON_FREE_SPACE);
    }
  }

  private void stopFromWriter(String reason) {
    recording = false;
    automaticCapture = false;
    lastStopReason = reason;
    clearQueue();
    closeLog();
  }

  /** Records a fail-soft terminal status and closes resources after a writer failure. */
  private void handleWriterFailure(RuntimeException failure) {
    synchronized (writerLock) {
      recording = false;
      automaticCapture = false;
      lastStopReason =
          TelemetryCaptureConstants.STOP_REASON_WRITER_ERROR
              + TelemetryCaptureConstants.ERROR_REASON_SEPARATOR
              + failure.getClass().getSimpleName();
      closeLogAfterFailure();
    }
  }

  private void closeLogAfterFailure() {
    try {
      closeLog();
    } catch (RuntimeException ignored) {
      log = null;
      entries.clear();
      gapEntry = null;
      annotationEntry = null;
    }
  }

  private boolean automaticStopDue() {
    return recording
        && automaticStopAtMs > EMPTY_QUEUE_SIZE
        && System.currentTimeMillis() >= automaticStopAtMs;
  }

  private void requestAutomaticStart(String annotation) {
    automaticStartAnnotation = annotation;
    automaticStartRequested = true;
    synchronized (queueLock) {
      queueLock.notifyAll();
    }
  }

  private void requestAnnotation(String annotation) {
    pendingAnnotation = annotation;
    synchronized (queueLock) {
      queueLock.notifyAll();
    }
  }

  private void ensureFreeSpace(Path directory) throws IOException {
    Files.createDirectories(directory);
    if (Files.getFileStore(directory).getUsableSpace()
        < TelemetryCaptureConstants.RESERVED_FREE_BYTES) {
      throw new IOException(TelemetryCaptureConstants.ERROR_FREE_SPACE);
    }
  }

  private void clearQueue() {
    synchronized (queueLock) {
      queueHead = FIRST_QUEUE_INDEX;
      queueSize = EMPTY_QUEUE_SIZE;
    }
  }

  private int queuedRecordCount() {
    synchronized (queueLock) {
      return queueSize + inFlightRecords;
    }
  }

  /** Converts records left after a bounded stop wait into an explicit capture gap. */
  private void markUndrainedRecordsDropped() {
    synchronized (queueLock) {
      int undrained = queueSize + inFlightRecords;
      if (undrained <= EMPTY_QUEUE_SIZE) {
        return;
      }
      droppedRecords += undrained;
      pendingDroppedRecords += undrained;
      queueHead = FIRST_QUEUE_INDEX;
      queueSize = EMPTY_QUEUE_SIZE;
    }
  }

  private void closeLog() {
    if (log == null) {
      return;
    }
    for (DoubleLogEntry entry : entries.values()) {
      entry.finish();
    }
    if (gapEntry != null) {
      gapEntry.finish();
      gapEntry = null;
    }
    if (annotationEntry != null) {
      annotationEntry.finish();
      annotationEntry = null;
    }
    log.flush();
    log.close();
    log = null;
    entries.clear();
  }

  private CaptureStatus status(boolean ok, String message) {
    return new CaptureStatus(
        ok,
        recording,
        currentPath,
        previewStorage(),
        droppedRecords,
        lastStopReason,
        message,
        autoMatchEnabled,
        autoExceptionEnabled);
  }

  private String storageLabel(String path) {
    return path != null && path.startsWith(TelemetryCaptureConstants.USB_LOG_DIRECTORY)
        ? "USB"
        : "roboRIO internal";
  }

  private String previewStorage() {
    if (configuredDirectory != null) {
      return configuredDirectory.toString();
    }
    if (recording && currentPath != null && !currentPath.isBlank()) {
      return storageLabel(currentPath);
    }
    Path usb = Path.of(TelemetryCaptureConstants.USB_LOG_DIRECTORY);
    return Files.isDirectory(usb) && Files.isWritable(usb)
        ? "USB"
        : "roboRIO internal";
  }

  /** Immutable operator-facing capture state. */
  public record CaptureStatus(
      boolean ok,
      boolean recording,
      String path,
      String storage,
      int droppedRecords,
      String lastStopReason,
      String message,
      boolean autoMatchEnabled,
      boolean autoExceptionEnabled) {}
}
