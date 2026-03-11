package frc.robot.diag.app;

/**
 * NAME
 * AppStatusTracker
 *
 * SYNOPSIS
 * Static tracker for robot periodic loop timing statistics.
 *
 * DESCRIPTION
 * Maintains rolling and windowed loop timing metrics to flag 20 ms overruns.
 */
public final class AppStatusTracker {
  private static final double OVERRUN_THRESHOLD_MS = 20.0;
  private static long lastLoopNs = 0L;
  private static double lastLoopMs = 0.0;
  private static double maxLoopMs = 0.0;
  private static double avgLoopMs = 0.0;
  private static long sampleCount = 0L;
  private static long overrunCount = 0L;

  private static long windowStartMs = System.currentTimeMillis();
  private static long windowSamples = 0L;
  private static long windowOverruns = 0L;

  private AppStatusTracker() {}

  /**
   * NAME
   * recordLoop
   *
   * SYNOPSIS
   * Record the elapsed time since the previous loop call.
   *
   * DESCRIPTION
   * Updates rolling averages, maximums, and overrun counters using a 20 ms
   * threshold.
   *
   * SIDE EFFECTS
   * Updates static timing state and window counters.
   */
  public static void recordLoop() {
    long nowNs = System.nanoTime();
    if (lastLoopNs > 0L) {
      lastLoopMs = (nowNs - lastLoopNs) / 1_000_000.0;
      sampleCount++;
      windowSamples++;
      avgLoopMs = (avgLoopMs == 0.0) ? lastLoopMs : (avgLoopMs * 0.95 + lastLoopMs * 0.05);
      if (lastLoopMs > maxLoopMs) {
        maxLoopMs = lastLoopMs;
      }
      if (lastLoopMs > OVERRUN_THRESHOLD_MS) {
        overrunCount++;
        windowOverruns++;
      }
    }
    lastLoopNs = nowNs;
    rotateWindowIfNeeded();
  }

  /**
   * NAME
   * rotateWindowIfNeeded
   *
   * SYNOPSIS
   * Reset the 60-second window counters when the window expires.
   *
   * DESCRIPTION
   * Uses wall-clock time to bound the window for overrun rate reporting.
   *
   * SIDE EFFECTS
   * Resets window counters and window start time.
   */
  private static void rotateWindowIfNeeded() {
    long nowMs = System.currentTimeMillis();
    if (nowMs - windowStartMs >= 60_000) {
      windowStartMs = nowMs;
      windowSamples = 0L;
      windowOverruns = 0L;
    }
  }

  /**
   * NAME
   * snapshot
   *
   * SYNOPSIS
   * Capture the current loop timing metrics.
   *
   * RETURNS
   * A populated snapshot with rolling and windowed timing values.
   */
  public static AppStatusSnapshot snapshot() {
    AppStatusSnapshot snap = new AppStatusSnapshot();
    snap.lastLoopMs = lastLoopMs;
    snap.avgLoopMs = avgLoopMs;
    snap.maxLoopMs = maxLoopMs;
    snap.sampleCount = sampleCount;
    snap.overrunCount = overrunCount;
    snap.windowSamples = windowSamples;
    snap.windowOverruns = windowOverruns;
    snap.overrunThresholdMs = OVERRUN_THRESHOLD_MS;
    return snap;
  }

  /**
   * NAME
   * AppStatusSnapshot
   *
   * SYNOPSIS
   * Plain data carrier for loop timing statistics.
   *
   * DESCRIPTION
   * Intended for reporting without exposing mutable tracker internals.
   */
  public static final class AppStatusSnapshot {
    public double lastLoopMs;
    public double avgLoopMs;
    public double maxLoopMs;
    public long sampleCount;
    public long overrunCount;
    public long windowSamples;
    public long windowOverruns;
    public double overrunThresholdMs;
  }
}
