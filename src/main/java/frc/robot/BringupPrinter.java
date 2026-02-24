package frc.robot;

import java.util.concurrent.ConcurrentLinkedQueue;

public final class BringupPrinter {
  private static final ConcurrentLinkedQueue<String> QUEUE = new ConcurrentLinkedQueue<>();
  private static final ConcurrentLinkedQueue<Runnable> TASKS = new ConcurrentLinkedQueue<>();
  private static final Object START_LOCK = new Object();
  private static volatile boolean started = false;

  private BringupPrinter() {}

  public static void enqueue(String text) {
    if (text == null || text.isEmpty()) {
      return;
    }
    QUEUE.add(text);
    startIfNeeded();
  }

  public static void enqueueTask(Runnable task) {
    if (task == null) {
      return;
    }
    TASKS.add(task);
    startIfNeeded();
  }

  public static void enqueueChunked(String text, int maxLines) {
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
    while (true) {
      Runnable task = TASKS.poll();
      if (task != null) {
        try {
          task.run();
        } catch (Throwable ignored) {
          // Keep printer thread alive even if a task fails.
        }
        continue;
      }
      String msg = QUEUE.poll();
      if (msg == null) {
        sleepMs(20);
        continue;
      }
      System.out.print(msg);
      if (!msg.endsWith("\n")) {
        System.out.println();
      }
      sleepMs(10);
    }
  }

  private static void sleepMs(long ms) {
    try {
      Thread.sleep(ms);
    } catch (InterruptedException ignored) {
      Thread.currentThread().interrupt();
    }
  }
}
