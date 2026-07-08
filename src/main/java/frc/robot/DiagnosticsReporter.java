package frc.robot;

import com.google.gson.JsonObject;
import frc.robot.diag.can.CanSuspicionInference;
import frc.robot.diag.led.LedStatusInference;
import frc.robot.diag.report.ReportJsonBuilder;
import frc.robot.diag.report.ReportTextBuilder;
import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.CanSuspicionAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LedStatusAttachment;
import frc.robot.diag.snapshots.SnapshotBundle;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * NAME
 *   DiagnosticsReporter - Build robot-local console and JSON diagnostics reports.
 *
 * DESCRIPTION
 *   Aggregates roboRIO-local vendor API snapshots and CAN-controller health.
 *   Host-side CAN visibility is surfaced by host-owned tools and is not read
 *   back into robot diagnostics.
 */
final class DiagnosticsReporter {
  private static final String REPORT_PATH = "/home/lvuser/bringup_report.json";
  private static final long MIN_PRINT_INTERVAL_MS = 1000;

  private final ReportTextBuilder textBuilder = new ReportTextBuilder();
  private final ReportJsonBuilder jsonBuilder = new ReportJsonBuilder();

  private BringupCore core;
  private final CanBusHealth canHealth;
  private long lastCanDiagPrintMs = 0L;

  /**
   * NAME
   *   DiagnosticsReporter - Construct a diagnostics reporter.
   *
   * PARAMETERS
   *   core - BringupCore for local device snapshots.
   *   canHealth - CAN controller health sampler.
   */
  DiagnosticsReporter(BringupCore core, CanBusHealth canHealth) {
    this.core = core;
    this.canHealth = canHealth;
  }

  /**
   * NAME
   *   setCore - Swap the BringupCore instance after profile changes.
   */
  void setCore(BringupCore core) {
    this.core = core;
  }

  /**
   * NAME
   *   resetState - Clear internal counters and cached state.
   */
  void resetState() {
    lastCanDiagPrintMs = 0L;
  }

  /**
   * NAME
   *   update - Sample CAN controller health.
   */
  void update() {
    canHealth.update();
  }

  /**
   * NAME
   *   buildCanDiagnosticsReportIfReady - Build CAN report when rate-limited.
   *
   * RETURNS
   *   Report string or null when not ready.
   */
  String buildCanDiagnosticsReportIfReady() {
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastCanDiagPrintMs < MIN_PRINT_INTERVAL_MS) {
      return null;
    }
    lastCanDiagPrintMs = nowMs;
    return buildCanDiagnosticsReport();
  }

  /**
   * NAME
   *   buildQuickSummary - Build a concise robot-local status summary.
   *
   * RETURNS
   *   Multi-line summary of bus and device health.
   */
  String buildQuickSummary() {
    SnapshotBundle bundle = buildSnapshotBundle();
    StringBuilder sb = new StringBuilder(256);
    ReportTextUtil.appendLine(sb, "=== Bringup Summary ===");
    appendQuickBus(sb, bundle.bus);
    appendQuickDevices(sb, bundle.devices);
    ReportTextUtil.appendLine(sb, "=======================");
    return sb.toString();
  }

  /**
   * NAME
   *   appendQuickBus - Append concise bus status.
   */
  private void appendQuickBus(StringBuilder sb, BusSnapshot bus) {
    if (bus == null || !bus.valid) {
      ReportTextUtil.appendLine(sb, "Bus: NO_DATA");
      return;
    }
    String util = String.format("%.1f%%", bus.utilizationPct);
    ReportTextUtil.appendLine(
        sb,
        "Bus: util=" + util
            + " rxErr=" + bus.rxErrors
            + " txErr=" + bus.txErrors
            + " busOff=" + bus.busOff);
  }

  /**
   * NAME
   *   appendQuickDevices - Append device health counts.
   */
  private void appendQuickDevices(StringBuilder sb, java.util.List<DeviceSnapshot> devices) {
    if (devices == null || devices.isEmpty()) {
      ReportTextUtil.appendLine(sb, "Devices: none");
      return;
    }
    int present = 0;
    int missing = 0;
    int suspicious = 0;
    for (DeviceSnapshot snap : devices) {
      if (snap.present) {
        present++;
      } else {
        missing++;
      }
      CanSuspicionAttachment suspicion = snap.getAttachment(CanSuspicionAttachment.class);
      if (suspicion != null
          && suspicion.likelyState != null
          && !suspicion.likelyState.isBlank()
          && !"OK".equalsIgnoreCase(suspicion.likelyState)) {
        suspicious++;
      }
    }
    ReportTextUtil.appendLine(
        sb,
        "Devices: present=" + present + " missing=" + missing + " suspicious=" + suspicious);
  }

  /**
   * NAME
   *   getCanDiagCooldownRemainingMs - Return remaining cooldown for CAN reports.
   *
   * RETURNS
   *   Milliseconds remaining before CAN diagnostics can print again (0 if ready).
   */
  long getCanDiagCooldownRemainingMs() {
    long nowMs = System.currentTimeMillis();
    long remaining = MIN_PRINT_INTERVAL_MS - (nowMs - lastCanDiagPrintMs);
    return Math.max(0L, remaining);
  }

  /**
   * NAME
   *   buildReportJsonForDump - Build a JSON report payload.
   */
  String buildReportJsonForDump() {
    return buildReportJson();
  }

  /**
   * NAME
   *   buildBusHealthJson - Build machine-readable roboRIO CAN-controller health.
   *
   * RETURNS
   *   JsonObject containing the latest bus-health counters and sample age.
   */
  JsonObject buildBusHealthJson() {
    JsonObject root = new JsonObject();
    canHealth.appendSnapshotJson(root);
    return root;
  }

  /**
   * NAME
   *   writeReportJsonToFile - Write report JSON to the roboRIO filesystem.
   *
   * PARAMETERS
   *   json - JSON payload.
   *
   * RETURNS
   *   True on success.
   */
  boolean writeReportJsonToFile(String json) {
    try {
      Files.writeString(Path.of(REPORT_PATH), json);
      return true;
    } catch (Exception ex) {
      return false;
    }
  }

  /**
   * NAME
   *   getReportPath - Return the report output path.
   */
  String getReportPath() {
    return REPORT_PATH;
  }

  /**
   * NAME
   *   buildCanDiagnosticsReport - Build a robot-local CAN diagnostics report.
   */
  private String buildCanDiagnosticsReport() {
    SnapshotBundle bundle = buildSnapshotBundle();
    return textBuilder.buildCanDiagnosticsReport(bundle);
  }

  /**
   * NAME
   *   buildReportJson - Build the JSON diagnostics payload.
   */
  private String buildReportJson() {
    SnapshotBundle bundle = buildSnapshotBundle();
    return jsonBuilder.buildReportJson(bundle);
  }

  /**
   * NAME
   *   buildSnapshotBundle - Assemble snapshot data for reports.
   */
  private SnapshotBundle buildSnapshotBundle() {
    SnapshotBundle bundle = new SnapshotBundle();
    bundle.timestampSec = System.currentTimeMillis() / 1000.0;
    bundle.bus = canHealth.buildSnapshot();
    for (DeviceSnapshot snap : core.captureSnapshots()) {
      LedStatusAttachment led = LedStatusInference.infer(snap);
      if (led != null) {
        snap.addAttachment(led);
      }
      CanSuspicionAttachment canSuspicion = CanSuspicionInference.infer(snap, bundle.bus);
      if (canSuspicion != null) {
        snap.addAttachment(canSuspicion);
      }
      bundle.devices.add(snap);
    }
    return bundle;
  }
}
