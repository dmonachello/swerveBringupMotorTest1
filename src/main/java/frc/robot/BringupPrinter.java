package frc.robot;

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
  private static final ConcurrentLinkedQueue<String> QUEUE = new ConcurrentLinkedQueue<>();
  private static final AtomicLong QUEUED_BYTES = new AtomicLong(0);
  private static final int MAX_QUEUE_BYTES = 64 * 1024;
  private static final int MAX_BYTES_PER_SEC = 2048;
  private static final long THROTTLE_WINDOW_MS = 1000;
  private static final AtomicLong DROPPED_MESSAGES = new AtomicLong(0);
  private static final AtomicLong DROPPED_BYTES = new AtomicLong(0);
  private static final Object START_LOCK = new Object();
  private static volatile boolean started = false;

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
      Thread t = new Thread(BringupPrinter::runLoop, "BringupPrinter");
      t.setDaemon(true);
      t.setPriority(Thread.MIN_PRIORITY);
      t.start();
      started = true;
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
        sleepMs(20);
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
      System.out.print(msg);
      windowBytes += bytes;
      if (!msg.endsWith("\n")) {
        System.out.println();
        windowBytes += 1;
      }
      // Small delay to keep console spam from starving other threads.
      sleepMs(100);
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

  public static long getThrottleWindowMs() {
    return THROTTLE_WINDOW_MS;
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
