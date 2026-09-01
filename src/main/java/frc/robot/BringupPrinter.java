package frc.robot;

import java.io.PrintStream;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicLong;

/**
 * NAME
 *   BringupPrinter - Throttled async console printer.
 *
 * DESCRIPTION
 *   Queues text and prints it in a background thread to avoid stalling the
 *   real-time robot loop.
 *
 * NOTES
 *   This class must remain free of vendor/robot API calls.
 */
public final class BringupPrinter {
  private static final PrintStream ORIGINAL_STDOUT = System.out;
  private static final ConcurrentLinkedQueue<String> QUEUE = new ConcurrentLinkedQueue<>();
  private static final Object RETAINED_MESSAGES_LOCK = new Object();
  private static final AtomicLong QUEUED_BYTES = new AtomicLong(0);
  private static final int MAX_QUEUE_BYTES = 64 * 1024;
  private static final int MAX_BYTES_PER_SEC = 2048;
  private static final int DEFAULT_MAX_RETAINED_MESSAGES = 256;
  private static final long THROTTLE_WINDOW_MS = 1000;
  private static final boolean DEFAULT_STDOUT_MIRROR_ENABLED = false;
  private static final int MISSING_TRAILING_NEWLINE_BYTES = 1;
  private static final long IDLE_SLEEP_MS = 20L;
  private static final long THROTTLE_SLEEP_MS = 100L;
  private static final int MIN_RETAINED_MESSAGE_LIMIT = 1;
  private static final AtomicLong DROPPED_MESSAGES = new AtomicLong(0);
  private static final AtomicLong DROPPED_BYTES = new AtomicLong(0);
  private static final AtomicLong RETAINED_DROPPED_MESSAGES = new AtomicLong(0);
  private static final Object START_LOCK = new Object();
  private static volatile LineListener LINE_LISTENER = null;
  private static volatile boolean stdoutMirrorEnabled = DEFAULT_STDOUT_MIRROR_ENABLED;
  private static volatile PrintStream stdoutMirrorStream = ORIGINAL_STDOUT;
  private static volatile int retainedMessageLimit = DEFAULT_MAX_RETAINED_MESSAGES;
  private static volatile boolean started = false;
  private static final ArrayDeque<String> RETAINED_MESSAGES = new ArrayDeque<>();

  private BringupPrinter() {}

  /**
   * NAME
   *   enqueue - Queue a string for throttled console output.
   *
   * PARAMETERS
   *   text - Message to print.
   *
   * SIDE EFFECTS
   *   Starts the printer thread and enqueues output.
   */
  public static void enqueue(String text) {
    // Fast path: ignore empty messages to avoid queue churn.
    if (text == null || text.isEmpty()) {
      return;
    }
    int bytes = text.length();
    long queued = QUEUED_BYTES.addAndGet(bytes);
    if (queued > MAX_QUEUE_BYTES) {
      // Drop newest message to avoid unbounded backlog.
      QUEUED_BYTES.addAndGet(-bytes);
      DROPPED_MESSAGES.incrementAndGet();
      DROPPED_BYTES.addAndGet(bytes);
      return;
    }
    QUEUE.add(text);
    startIfNeeded();
  }

  /**
   * NAME
   *   enqueueChunked - Queue a long report in line-limited chunks.
   *
   * PARAMETERS
   *   text - Report text to split.
   *   maxLines - Maximum lines per chunk.
   *
   * SIDE EFFECTS
   *   Enqueues one or more chunks for printing.
   */
  public static void enqueueChunked(String text, int maxLines) {
    // Break large reports into smaller blocks so the console stays responsive.
    if (text == null || text.isEmpty()) {
      return;
    }
    if (maxLines <= 0) {
      enqueue(text);
      return;
    }
    String[] lines = text.split("\\R", -1);
    StringBuilder chunk = new StringBuilder();
    int lineCount = 0;
    for (String line : lines) {
      if (line.isEmpty()) {
        continue;
      }
      chunk.append(line).append('\n');
      lineCount++;
      if (lineCount >= maxLines) {
        enqueue(chunk.toString());
        chunk.setLength(0);
        lineCount = 0;
      }
    }
    if (chunk.length() > 0) {
      enqueue(chunk.toString());
    }
  }

  /**
   * NAME
   *   LineListener - Callback for queued console lines.
   */
  public interface LineListener {
    void onLine(String text);
  }

  /**
   * NAME
   *   setLineListener - Register a listener for queued output.
   *
   * PARAMETERS
   *   listener - Callback to invoke when output is enqueued (null disables).
   */
  public static void setLineListener(LineListener listener) {
    LINE_LISTENER = listener;
  }

  /**
   * NAME
   *   setStdoutMirrorEnabled - Control whether queued bringup output is mirrored to stdout.
   *
   * PARAMETERS
   *   enabled - true to write queued messages to stdout, false to keep them in the in-process listener path only.
   */
  public static void setStdoutMirrorEnabled(boolean enabled) {
    stdoutMirrorEnabled = enabled;
  }

  /**
   * NAME
   *   isStdoutMirrorEnabled - Return whether queued bringup output is mirrored to stdout.
   */
  public static boolean isStdoutMirrorEnabled() {
    return stdoutMirrorEnabled;
  }

  /**
   * NAME
   *   startIfNeeded - Lazily start the printer thread.
   */
  private static void startIfNeeded() {
    // Lazy-start the background thread to avoid static init order issues.
    if (started) {
      return;
    }
    synchronized (START_LOCK) {
      if (started) {
        return;
      }
      Thread t = new Thread(new PrinterRunner(), "BringupPrinter");
      t.setDaemon(true);
      t.setPriority(Thread.MIN_PRIORITY);
      t.start();
      started = true;
    }
  }

  /**
   * NAME
   *   PrinterRunner - Named runnable for the printer thread.
   */
  private static final class PrinterRunner implements Runnable {
    @Override
    public void run() {
      runLoop();
    }
  }

  /**
   * NAME
   *   runLoop - Background print loop with throttling.
   *
   * SIDE EFFECTS
   *   Writes to stdout.
   */
  private static void runLoop() {
    // Poll continuously; sleep briefly when idle to reduce CPU usage.
    long windowStartMs = System.currentTimeMillis();
    int windowBytes = 0;
    while (true) {
      String msg = QUEUE.poll();
      if (msg == null) {
        sleepMs(IDLE_SLEEP_MS);
        continue;
      }
      int bytes = msg.length();
      QUEUED_BYTES.addAndGet(-bytes);
      long nowMs = System.currentTimeMillis();
      long elapsed = nowMs - windowStartMs;
      if (elapsed >= THROTTLE_WINDOW_MS) {
        windowStartMs = nowMs;
        windowBytes = 0;
      }
      if (windowBytes + bytes > MAX_BYTES_PER_SEC) {
        long remaining = THROTTLE_WINDOW_MS - elapsed;
        if (remaining > 0) {
          sleepMs(remaining);
        }
        windowStartMs = System.currentTimeMillis();
        windowBytes = 0;
      }
      windowBytes += dispatchMessage(msg, bytes);
      // Small delay to keep console spam from starving other threads.
      sleepMs(THROTTLE_SLEEP_MS);
    }
  }

  /**
   * NAME
   *   dispatchMessage - Deliver one queued message to configured sinks.
   *
   * PARAMETERS
   *   msg - queued output text.
   *   bytes - already-accounted message length.
   *
   * RETURNS
   *   Additional bytes written to stdout for throttle accounting.
   *
   * SIDE EFFECTS
   *   Optionally writes to stdout and always forwards to the registered listener.
   */
  static int dispatchMessage(String msg, int bytes) {
    int additionalBytes = 0;
    dispatchToSinks(msg);
    if (stdoutMirrorEnabled) {
      stdoutMirrorStream.print(msg);
      if (!msg.endsWith("\n")) {
        stdoutMirrorStream.println();
        additionalBytes += MISSING_TRAILING_NEWLINE_BYTES;
      }
    }
    return bytes + additionalBytes;
  }

  /**
   * NAME
   *   captureExternalLine - Deliver non-bringup stdout/stderr text into retained/listener sinks only.
   *
   * PARAMETERS
   *   text - External console line captured from the process stdout/stderr streams.
   *
   * SIDE EFFECTS
   *   Updates retained message state and notifies the registered listener without
   *   re-printing the text to stdout.
   */
  public static void captureExternalLine(String text) {
    dispatchToSinks(text);
  }

  private static void dispatchToSinks(String msg) {
    if (msg == null || msg.isEmpty()) {
      return;
    }
    retainMessage(msg);
    LineListener listener = LINE_LISTENER;
    if (listener != null) {
      listener.onLine(msg);
    }
  }

  /**
   * NAME
   *   retainMessage - Store one delivered bringup message in the bounded retained buffer.
   *
   * PARAMETERS
   *   msg - Delivered message text.
   *
   * SIDE EFFECTS
   *   Drops the oldest retained message when the buffer is full.
   */
  private static void retainMessage(String msg) {
    if (msg == null || msg.isEmpty()) {
      return;
    }
    synchronized (RETAINED_MESSAGES_LOCK) {
      while (RETAINED_MESSAGES.size() >= retainedMessageLimit) {
        if (RETAINED_MESSAGES.pollFirst() == null) {
          break;
        }
        RETAINED_DROPPED_MESSAGES.incrementAndGet();
      }
      RETAINED_MESSAGES.addLast(msg);
    }
  }

  public static long getQueuedBytes() {
    return QUEUED_BYTES.get();
  }

  public static long getDroppedMessages() {
    return DROPPED_MESSAGES.get();
  }

  public static long getDroppedBytes() {
    return DROPPED_BYTES.get();
  }

  public static int getMaxQueueBytes() {
    return MAX_QUEUE_BYTES;
  }

  public static int getMaxBytesPerSec() {
    return MAX_BYTES_PER_SEC;
  }

  public static int getRetainedMessageCount() {
    synchronized (RETAINED_MESSAGES_LOCK) {
      return RETAINED_MESSAGES.size();
    }
  }

  public static long getRetainedDroppedMessages() {
    return RETAINED_DROPPED_MESSAGES.get();
  }

  public static int getRetainedMessageLimit() {
    return retainedMessageLimit;
  }

  public static List<String> getRetainedMessagesSnapshot() {
    synchronized (RETAINED_MESSAGES_LOCK) {
      return new ArrayList<>(RETAINED_MESSAGES);
    }
  }

  public static long getThrottleWindowMs() {
    return THROTTLE_WINDOW_MS;
  }

  static void resetForTests() {
    synchronized (RETAINED_MESSAGES_LOCK) {
      RETAINED_MESSAGES.clear();
      retainedMessageLimit = DEFAULT_MAX_RETAINED_MESSAGES;
    }
    QUEUE.clear();
    QUEUED_BYTES.set(0L);
    DROPPED_MESSAGES.set(0L);
    DROPPED_BYTES.set(0L);
    RETAINED_DROPPED_MESSAGES.set(0L);
    LINE_LISTENER = null;
    stdoutMirrorEnabled = DEFAULT_STDOUT_MIRROR_ENABLED;
    stdoutMirrorStream = ORIGINAL_STDOUT;
  }

  static void setRetainedMessageLimitForTests(int limit) {
    retainedMessageLimit = Math.max(MIN_RETAINED_MESSAGE_LIMIT, limit);
  }

  static void setStdoutMirrorStreamForTests(PrintStream stream) {
    stdoutMirrorStream = stream != null ? stream : ORIGINAL_STDOUT;
  }

  /**
   * NAME
   *   sleepMs - Best-effort sleep with interrupt reassertion.
   */
  private static void sleepMs(long ms) {
    // Best-effort delay; interrupt is reasserted if it happens.
    try {
      Thread.sleep(ms);
    } catch (InterruptedException ignored) {
      Thread.currentThread().interrupt();
    }
  }
}
