package frc.robot.diag.app;

// Tracks periodic loop timing to detect overruns.
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

  private static void rotateWindowIfNeeded() {
    long nowMs = System.currentTimeMillis();
    if (nowMs - windowStartMs >= 60_000) {
      windowStartMs = nowMs;
      windowSamples = 0L;
      windowOverruns = 0L;
    }
  }

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
