package frc.robot;

import java.util.concurrent.ConcurrentLinkedQueue;

// Simple async printer to keep long console output from stalling the main loop.
// NOTE: This class only handles output formatting/printing; it must not call vendor/robot APIs.
public final class BringupPrinter {
  private static final ConcurrentLinkedQueue<String> QUEUE = new ConcurrentLinkedQueue<>();
  private static final Object START_LOCK = new Object();
  private static volatile boolean started = false;

  private BringupPrinter() {}

  public static void enqueue(String text) {
    // Fast path: ignore empty messages to avoid queue churn.
    if (text == null || text.isEmpty()) {
      return;
    }
    QUEUE.add(text);
    startIfNeeded();
  }

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

  private static void runLoop() {
    // Poll continuously; sleep briefly when idle to reduce CPU usage.
    while (true) {
      String msg = QUEUE.poll();
      if (msg == null) {
        sleepMs(20);
        continue;
      }
      System.out.print(msg);
      if (!msg.endsWith("\n")) {
        System.out.println();
      }
      // Small delay to keep console spam from starving other threads.
      sleepMs(10);
    }
  }

  private static void sleepMs(long ms) {
    // Best-effort delay; interrupt is reasserted if it happens.
    try {
      Thread.sleep(ms);
    } catch (InterruptedException ignored) {
      Thread.currentThread().interrupt();
    }
  }
}
