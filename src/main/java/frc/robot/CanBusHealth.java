package frc.robot;

import com.google.gson.JsonObject;
import edu.wpi.first.wpilibj.RobotController;
import frc.robot.diag.snapshots.BusSnapshot;

/**
 * NAME
 *   CanBusHealth - Sample and summarize roboRIO CAN controller health.
 *
 * DESCRIPTION
 *   Reads robot-local CAN controller counters and emits summarized health
 *   signals for reporting and JSON snapshots.
 */
final class CanBusHealth {
  private static final double HIGH_UTILIZATION_PCT = 80.0;
  private static final double RECOVER_UTILIZATION_PCT = 70.0;
  private static final long LOG_PERIOD_MS = 2000;
  private static final int ERROR_SPIKE_THRESHOLD = 5;

  private long lastLogMs = 0;
  private int lastRxErrors = 0;
  private int lastTxErrors = 0;
  private int lastRxDelta = 0;
  private int lastTxDelta = 0;
  private int lastBusOffCount = 0;
  private int lastBusOffDelta = 0;
  private int lastTxFullCount = 0;
  private int lastTxFullDelta = 0;
  private double lastUtilizationPct = 0.0;
  private long lastUpdateMs = 0;
  private boolean wasHighUtil = false;

  /**
   * NAME
   *   update - Sample current CAN controller counters.
   *
   * SIDE EFFECTS
   *   Reads hardware status and may enqueue warning prints.
   */
  void update() {
    // Read current CAN controller counters and utilization.
    var status = RobotController.getCANStatus();
    double utilizationPct = status.percentBusUtilization * 100.0;
    int rxErrors = status.receiveErrorCount;
    int txErrors = status.transmitErrorCount;
    int busOffCount = status.busOffCount;
    int txFullCount = status.txFullCount;

    int rxDelta = rxErrors - lastRxErrors;
    int txDelta = txErrors - lastTxErrors;
    int busOffDelta = busOffCount - lastBusOffCount;
    int txFullDelta = txFullCount - lastTxFullCount;
    boolean errorSpike = rxDelta >= ERROR_SPIKE_THRESHOLD || txDelta >= ERROR_SPIKE_THRESHOLD;
    boolean busOffEvent = busOffDelta > 0;

    boolean nowHighUtil = utilizationPct >= HIGH_UTILIZATION_PCT;
    boolean recoveredUtil = utilizationPct <= RECOVER_UTILIZATION_PCT;

    long nowMs = System.currentTimeMillis();
    boolean logDue = (nowMs - lastLogMs) >= LOG_PERIOD_MS;

    if (busOffEvent) {
      // Bus-off is a hard failure; surface immediately.
      BringupPrinter.enqueue("[CAN] BUS OFF event detected! Check wiring/termination/noise.");
      lastLogMs = nowMs;
    }

    if (nowHighUtil && (!wasHighUtil || logDue)) {
      // Repeated warnings while overloaded are rate-limited.
      BringupPrinter.enqueue(String.format("[CAN] High utilization: %.1f%%", utilizationPct));
      lastLogMs = nowMs;
    } else if (wasHighUtil && recoveredUtil) {
      BringupPrinter.enqueue(String.format("[CAN] Utilization recovered: %.1f%%", utilizationPct));
      lastLogMs = nowMs;
    }

    if (errorSpike && logDue) {
      // Error spikes indicate noise or transmit contention.
      BringupPrinter.enqueue(String.format("[CAN] Error spike: rx=%d tx=%d (delta rx=%d tx=%d)",
          rxErrors, txErrors, rxDelta, txDelta));
      lastLogMs = nowMs;
    }

    lastRxErrors = rxErrors;
    lastTxErrors = txErrors;
    lastRxDelta = rxDelta;
    lastTxDelta = txDelta;
    lastBusOffCount = busOffCount;
    lastBusOffDelta = busOffDelta;
    lastTxFullCount = txFullCount;
    lastTxFullDelta = txFullDelta;
    lastUtilizationPct = utilizationPct;
    lastUpdateMs = nowMs;
    wasHighUtil = nowHighUtil;
  }

  /**
   * NAME
   *   appendReportSection - Append a brief report marker line.
   *
   * PARAMETERS
   *   sb - Target report buffer.
   */
  void appendReportSection(StringBuilder sb) {
    // Summary line in the report to avoid duplicating the snapshot block.
    ReportTextUtil.appendLine(sb, "Bus Health: (see CAN Bus Diagnostics summary above)");
  }

  /**
   * NAME
   *   appendSnapshot - Append a detailed CAN health snapshot.
   *
   * PARAMETERS
   *   sb - Target report buffer.
   */
  void appendSnapshot(StringBuilder sb) {
    // Full snapshot for human-readable report output.
    if (lastUpdateMs == 0) {
      ReportTextUtil.appendLine(sb, "[CAN] No status samples yet.");
      return;
    }
    double ageSec = (System.currentTimeMillis() - lastUpdateMs) / 1000.0;
    ReportTextUtil.appendLine(sb, "=== CAN Bus Diagnostics ===");
    ReportTextUtil.appendLine(sb, String.format("Utilization: %.1f%%", lastUtilizationPct));
    ReportTextUtil.appendLine(sb, String.format("RX errors: %d (delta %d)", lastRxErrors, lastRxDelta));
    ReportTextUtil.appendLine(sb, String.format("TX errors: %d (delta %d)", lastTxErrors, lastTxDelta));
    ReportTextUtil.appendLine(sb, String.format("TX full: %d (delta %d)", lastTxFullCount, lastTxFullDelta));
    ReportTextUtil.appendLine(sb, String.format("Bus off count: %d (delta %d)", lastBusOffCount, lastBusOffDelta));
    ReportTextUtil.appendLine(sb, String.format("Sample age: %.2fs", ageSec));
    ReportTextUtil.appendLine(sb, "===========================");
  }

  /**
   * NAME
   *   summaryStatus - Return a high-level bus health label.
   *
   * RETURNS
   *   Status string such as OK, HIGH_UTIL, or BUS_OFF.
   */
  String summaryStatus() {
    // High-level state for the top-line summary.
    if (lastUpdateMs == 0) {
      return "NO_DATA";
    }
    if (lastBusOffDelta > 0 || lastBusOffCount > 0) {
      return "BUS_OFF";
    }
    if (lastTxFullDelta > 0 || lastTxFullCount > 0) {
      return "TX_FULL";
    }
    if (lastRxDelta > 0 || lastTxDelta > 0) {
      return "ERRORS";
    }
    if (lastUtilizationPct >= HIGH_UTILIZATION_PCT) {
      return "HIGH_UTIL";
    }
    return "OK";
  }

  /**
   * NAME
   *   appendSnapshotJson - Append JSON fields for bus health.
   *
   * PARAMETERS
   *   target - JsonObject to populate.
   */
  void appendSnapshotJson(JsonObject target) {
    // JSON payload for machine-readable report.
    if (target == null) {
      return;
    }
    if (lastUpdateMs == 0) {
      target.addProperty("valid", false);
      return;
    }
    double ageSec = (System.currentTimeMillis() - lastUpdateMs) / 1000.0;
    target.addProperty("valid", true);
    target.addProperty("utilizationPct", lastUtilizationPct);
    target.addProperty("rxErrors", lastRxErrors);
    target.addProperty("txErrors", lastTxErrors);
    target.addProperty("rxDelta", lastRxDelta);
    target.addProperty("txDelta", lastTxDelta);
    target.addProperty("txFull", lastTxFullCount);
    target.addProperty("txFullDelta", lastTxFullDelta);
    target.addProperty("busOff", lastBusOffCount);
    target.addProperty("busOffDelta", lastBusOffDelta);
    target.addProperty("sampleAgeSec", ageSec);
  }

  /**
   * NAME
   *   buildSnapshot - Build a structured bus snapshot.
   *
   * RETURNS
   *   BusSnapshot with current counters and age.
   */
  BusSnapshot buildSnapshot() {
    BusSnapshot snap = new BusSnapshot();
    if (lastUpdateMs == 0) {
      snap.valid = false;
      return snap;
    }
    snap.valid = true;
    snap.utilizationPct = lastUtilizationPct;
    snap.rxErrors = lastRxErrors;
    snap.txErrors = lastTxErrors;
    snap.rxDelta = lastRxDelta;
    snap.txDelta = lastTxDelta;
    snap.txFull = lastTxFullCount;
    snap.txFullDelta = lastTxFullDelta;
    snap.busOff = lastBusOffCount;
    snap.busOffDelta = lastBusOffDelta;
    snap.sampleAgeSec = (System.currentTimeMillis() - lastUpdateMs) / 1000.0;
    return snap;
  }
}
