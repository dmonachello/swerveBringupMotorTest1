package frc.robot.diag.report;

import frc.robot.ReportTextUtil;
import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.CanSuspicionAttachment;
import frc.robot.diag.snapshots.LedStatusAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.EncoderAttachment;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.diag.snapshots.MotorSpecAttachment;
import frc.robot.diag.snapshots.PcSnapshot;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
import frc.robot.diag.snapshots.SnapshotBundle;
import frc.robot.diag.app.AppStatusTracker;
import frc.robot.BringupPrinter;
import java.util.List;

/**
 * NAME
 *   ReportTextBuilder - Build human-readable diagnostics reports.
 *
 * DESCRIPTION
 *   Formats snapshot bundles into a console-friendly report with device and
 *   bus summaries.
 */
public final class ReportTextBuilder {
  private static final double HIGH_UTILIZATION_PCT = 80.0;
  private static final double PC_STALE_DEVICE_AGE_SEC = 2.0;

  /**
   * NAME
   *   buildCanDiagnosticsReport - Build the CAN diagnostics report.
   */
  public String buildCanDiagnosticsReport(SnapshotBundle bundle) {
    StringBuilder sb = new StringBuilder(1024);
    ReportTextUtil.appendLine(sb, "=== CAN Diagnostics Report ===");
    ReportTextUtil.appendLine(sb, buildSummaryLine(bundle));
    appendBusSnapshot(sb, bundle.bus);
    ReportTextUtil.appendLine(sb, "Bus Health: (see CAN Bus Diagnostics summary above)");
    appendPcToolSection(sb, bundle.pc);
    appendDeviceHealth(sb, bundle.devices);
    appendLedLegend(sb, bundle.devices);
    appendAppStatus(sb);
    ReportTextUtil.appendLine(sb, "==============================");
    return sb.toString();
  }

  /**
   * NAME
   *   buildSummaryLine - Build the summary status line.
   */
  private String buildSummaryLine(SnapshotBundle bundle) {
    String bus = summaryBusStatus(bundle.bus);
    String pc = summaryPcStatus(bundle.pc);
    return "Summary: bus=" + bus + " pc=" + pc;
  }

  /**
   * NAME
   *   summaryBusStatus - Summarize bus health into a status token.
   */
  private String summaryBusStatus(BusSnapshot bus) {
    if (bus == null || !bus.valid) {
      return "NO_DATA";
    }
    if (bus.busOffDelta > 0 || bus.busOff > 0) {
      return "BUS_OFF";
    }
    if (bus.txFullDelta > 0 || bus.txFull > 0) {
      return "TX_FULL";
    }
    if (bus.rxDelta > 0 || bus.txDelta > 0) {
      return "ERRORS";
    }
    if (bus.utilizationPct >= HIGH_UTILIZATION_PCT) {
      return "HIGH_UTIL";
    }
    return "OK";
  }

  /**
   * NAME
   *   summaryPcStatus - Summarize PC sniffer health into a status token.
   */
  private String summaryPcStatus(PcSnapshot pc) {
    if (pc == null || pc.heartbeatAgeSec < 0 || !pc.openOk) {
      return "PC_TOOL_MISSING";
    }
    return "OK";
  }

  /**
   * NAME
   *   appendBusSnapshot - Append bus diagnostics section.
   */
  private void appendBusSnapshot(StringBuilder sb, BusSnapshot bus) {
    if (bus == null || !bus.valid) {
      ReportTextUtil.appendLine(sb, "[CAN] No status samples yet.");
      return;
    }
    ReportTextUtil.appendLine(sb, "=== CAN Bus Diagnostics ===");
    ReportTextUtil.appendLine(sb, String.format("Utilization: %.1f%%", bus.utilizationPct));
    ReportTextUtil.appendLine(sb, String.format("RX errors: %d (delta %d)", bus.rxErrors, bus.rxDelta));
    ReportTextUtil.appendLine(sb, String.format("TX errors: %d (delta %d)", bus.txErrors, bus.txDelta));
    ReportTextUtil.appendLine(sb, String.format("TX full: %d (delta %d)", bus.txFull, bus.txFullDelta));
    ReportTextUtil.appendLine(sb, String.format("Bus off count: %d (delta %d)", bus.busOff, bus.busOffDelta));
    ReportTextUtil.appendLine(sb, String.format("Sample age: %.2fs", bus.sampleAgeSec));
    ReportTextUtil.appendLine(sb, "===========================");
  }

  /**
   * NAME
   *   appendPcToolSection - Append PC tool diagnostics section.
   */
  private void appendPcToolSection(StringBuilder sb, PcSnapshot pc) {
    ReportTextUtil.appendLine(sb, "PC Tool:");
    if (pc == null) {
      ReportTextUtil.appendLine(sb, "  Status: PC tool not connected");
      return;
    }

    String heartbeatAgeText = (pc.heartbeatAgeSec < 0)
        ? "STALE (no data)"
        : String.format("%.2fs", pc.heartbeatAgeSec);
    if (pc.heartbeatAgeSec < 0 || !pc.openOk) {
      ReportTextUtil.appendLine(sb, "  Status: PC tool not connected");
    } else {
      ReportTextUtil.appendLine(sb, "  Status: OK");
    }

    ReportTextUtil.appendLine(sb, "  Heartbeat age: " + heartbeatAgeText);
    ReportTextUtil.appendLine(sb, "  Open OK: " + (pc.openOk ? "YES" : "NO"));
    ReportTextUtil.appendLine(sb, "  Frames/sec: " + formatDoubleOrDash(pc.framesPerSec, 1));
    ReportTextUtil.appendLine(sb, "  Frames total: " + formatDoubleOrDash(pc.framesTotal, 0));
    ReportTextUtil.appendLine(sb, "  Read errors: " + formatDoubleOrDash(pc.readErrors, 0));
    ReportTextUtil.appendLine(sb, "  Last frame age: " + formatDoubleOrDash(pc.lastFrameAgeSec, 2) + "s");

    ReportTextUtil.appendLine(
        sb,
        "  Missing devices (PC): " + pc.missingCount + " / " + pc.totalCount);
    ReportTextUtil.appendLine(sb, "  Flapping devices (PC): " + pc.flappingCount);
    if (!pc.seenNotLocal.isEmpty()) {
      ReportTextUtil.appendLine(
          sb,
          "  Seen on wire, not local: " + String.join(", ", formatSeenNotLocal(pc.seenNotLocal)));
    }
    if (!pc.profileMismatch.isEmpty()) {
      ReportTextUtil.appendLine(
          sb,
          "  Profile mismatch candidates: " + String.join("; ", formatProfileMismatch(pc.profileMismatch)));
    }
    if (!pc.staleDevices.isEmpty()) {
      ReportTextUtil.appendLine(
          sb,
          "  Stale devices (PC): " + String.join(", ", formatStaleDevices(pc.staleDevices))
              + " (age > " + String.format("%.1f", PC_STALE_DEVICE_AGE_SEC) + "s)");
    }
  }

  /**
   * NAME
   *   appendDeviceHealth - Append per-device health section.
   */
  private void appendDeviceHealth(StringBuilder sb, List<DeviceSnapshot> devices) {
    ReportTextUtil.appendLine(sb, "Device Health (local API):");
    if (devices == null) {
      return;
    }
    for (DeviceSnapshot snap : devices) {
      if ("NEO".equals(snap.deviceType) || "FLEX".equals(snap.deviceType)) {
        appendRevDevice(sb, snap);
      } else if ("KRAKEN".equals(snap.deviceType) || "FALCON".equals(snap.deviceType)) {
        appendCtreDevice(sb, snap);
      } else if ("CANCoder".equals(snap.deviceType)) {
        appendCANCoder(sb, snap);
      } else if ("CANdle".equals(snap.deviceType)) {
        appendCANdle(sb, snap);
      } else if ("roboRIO".equals(snap.deviceType)) {
        ReportTextUtil.appendLine(
            sb,
            "  roboRIO CAN " + snap.canId + ": present=YES (virtual, no API)");
      }
    }
  }

  /**
   * NAME
   *   appendRevDevice - Append REV device line.
   */
  private void appendRevDevice(StringBuilder sb, DeviceSnapshot snap) {
    if (!snap.present) {
      ReportTextUtil.appendLine(
          sb,
          "  " + snap.deviceType + " CAN " + snap.canId + ": present=NO (not added)");
      appendCanSuspicionLines(sb, snap);
      appendLedLines(sb, snap);
      return;
    }
    RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
    MotorSpecAttachment spec = snap.getAttachment(MotorSpecAttachment.class);
    LimitsAttachment limits = snap.getAttachment(LimitsAttachment.class);
    String specNote = formatMotorSpecNote(spec, rev != null ? rev.motorCurrentA : null);
    ReportTextUtil.appendLine(
        sb,
        "  " + snap.deviceType + " CAN " + snap.canId +
        ": present=YES" + formatRevFaultSummary(rev) +
        " lastErr=" + safeText(rev != null ? rev.lastError : "") +
        " reset=" + (rev != null && rev.reset ? "YES" : "NO") +
        specNote +
        formatLimitSummary(limits) +
        " busV=" + formatDouble(rev != null ? rev.busV : null, 2) + "V" +
        " appliedV=" + formatDouble(rev != null ? rev.appliedV : null, 2) + "V" +
        " motorCurrentA=" + formatDouble(rev != null ? rev.motorCurrentA : null, 4) + "A" +
        " tempC=" + formatDouble(rev != null ? rev.tempC : null, 1) + "C");
    appendCanSuspicionLines(sb, snap);
    appendLedLines(sb, snap);
  }

  /**
   * NAME
   *   appendCtreDevice - Append CTRE device line.
   */
  private void appendCtreDevice(StringBuilder sb, DeviceSnapshot snap) {
    if (!snap.present) {
      ReportTextUtil.appendLine(
          sb,
          "  " + snap.deviceType + " CAN " + snap.canId + ": present=NO (not added)");
      appendCanSuspicionLines(sb, snap);
      appendLedLines(sb, snap);
      return;
    }
    CtreMotorAttachment ctre = snap.getAttachment(CtreMotorAttachment.class);
    MotorSpecAttachment spec = snap.getAttachment(MotorSpecAttachment.class);
    LimitsAttachment limits = snap.getAttachment(LimitsAttachment.class);
    String specNote = formatMotorSpecNote(spec, ctre != null ? ctre.motorCurrentA : null);
    boolean faultOk = ctre != null && "OK".equals(ctre.faultStatus);
    boolean stickyOk = ctre != null && "OK".equals(ctre.stickyStatus);
    ReportTextUtil.appendLine(
        sb,
        "  " + snap.deviceType + " CAN " + snap.canId +
        ": present=YES fault=0x" + Integer.toHexString(ctre != null ? ctre.faultsRaw : 0) +
        formatFlagList(ctre != null ? ctre.faultFlags : null) +
        " sticky=0x" + Integer.toHexString(ctre != null ? ctre.stickyFaultsRaw : 0) +
        formatFlagList(ctre != null ? ctre.stickyFaultFlags : null) +
        " lastErr=" + safeText(ctre != null ? ctre.faultStatus : "") +
        specNote +
        formatLimitSummary(limits) +
        " busV=" + formatDouble(ctre != null ? ctre.busV : null, 2) + "V" +
        " appliedDuty=" + formatDouble(ctre != null ? ctre.appliedDuty : null, 2) + "dc" +
        " appliedV=" + formatDouble(ctre != null ? ctre.appliedV : null, 2) + "V" +
        " motorCurrentA=" + formatDouble(ctre != null ? ctre.motorCurrentA : null, 4) + "A" +
        " tempC=" + formatDouble(ctre != null ? ctre.tempC : null, 1) + "C" +
        (faultOk && stickyOk
            ? ""
            : " status=" + safeText(ctre != null ? ctre.faultStatus : "")
                + "/" + safeText(ctre != null ? ctre.stickyStatus : "")));
    appendCanSuspicionLines(sb, snap);
    appendLedLines(sb, snap);
  }

  /**
   * NAME
   *   appendCANCoder - Append CANCoder device line.
   */
  private void appendCANCoder(StringBuilder sb, DeviceSnapshot snap) {
    if (!snap.present) {
      ReportTextUtil.appendLine(
          sb,
          "  CANCoder CAN " + snap.canId + ": present=NO (not added)");
      appendCanSuspicionLines(sb, snap);
      appendLedLines(sb, snap);
      return;
    }
    EncoderAttachment encoder = snap.getAttachment(EncoderAttachment.class);
    LimitsAttachment limits = snap.getAttachment(LimitsAttachment.class);
    ReportTextUtil.appendLine(
        sb,
        "  CANCoder CAN " + snap.canId +
        ": present=YES absDeg=" + formatDouble(encoder != null ? encoder.absDeg : null, 1) +
        " lastErr=" + safeText(encoder != null ? encoder.lastError : "") +
        formatLimitSummary(limits));
    appendCanSuspicionLines(sb, snap);
    appendLedLines(sb, snap);
  }

  /**
   * NAME
   *   appendCANdle - Append CANdle device line.
   */
  private void appendCANdle(StringBuilder sb, DeviceSnapshot snap) {
    if (!snap.present) {
      ReportTextUtil.appendLine(
          sb,
          "  CANdle CAN " + snap.canId + ": present=NO (not added)");
      appendCanSuspicionLines(sb, snap);
      appendLedLines(sb, snap);
      return;
    }
    LimitsAttachment limits = snap.getAttachment(LimitsAttachment.class);
    ReportTextUtil.appendLine(
        sb,
        "  CANdle CAN " + snap.canId + ": present=YES" + formatLimitSummary(limits));
    appendCanSuspicionLines(sb, snap);
    appendLedLines(sb, snap);
  }

  /**
   * NAME
   *   appendCanSuspicionLines - Append CAN suspicion annotations.
   */
  private void appendCanSuspicionLines(StringBuilder sb, DeviceSnapshot snap) {
    CanSuspicionAttachment can = snap.getAttachment(CanSuspicionAttachment.class);
    if (can == null) {
      return;
    }
    String expected = formatStateMeaning(can.expectedState, can.expectedMeaning);
    String likely = formatStateMeaning(can.likelyState, can.likelyMeaning);
    if (!expected.isBlank()) {
      ReportTextUtil.appendLine(sb, "    CAN expected: " + expected);
    }
    if (!likely.isBlank()) {
      String confidence = can.confidence != null && !can.confidence.isBlank()
          ? " (confidence=" + can.confidence + ")"
          : "";
      ReportTextUtil.appendLine(sb, "    CAN likely: " + likely + confidence);
    }
    if (can.note != null && !can.note.isBlank()) {
      ReportTextUtil.appendLine(sb, "    CAN note: " + can.note);
    }
  }

  /**
   * NAME
   *   appendLedLines - Append LED status annotations.
   */
  private void appendLedLines(StringBuilder sb, DeviceSnapshot snap) {
    LedStatusAttachment led = snap.getAttachment(LedStatusAttachment.class);
    if (led == null) {
      return;
    }
    String expected = formatPatternMeaning(led.expectedPattern, led.expectedMeaning);
    String likely = formatPatternMeaning(led.likelyPattern, led.likelyMeaning);
    if (!expected.isBlank()) {
      ReportTextUtil.appendLine(sb, "    LED expected: " + expected);
    }
    if (!likely.isBlank()) {
      String confidence = led.confidence != null && !led.confidence.isBlank()
          ? " (confidence=" + led.confidence + ")"
          : "";
      ReportTextUtil.appendLine(sb, "    LED likely: " + likely + confidence);
    }
    if (led.note != null && !led.note.isBlank()) {
      ReportTextUtil.appendLine(sb, "    LED note: " + led.note);
    }
  }

  /**
   * NAME
   *   appendLedLegend - Append a legend for observed LED patterns.
   */
  private void appendLedLegend(StringBuilder sb, List<DeviceSnapshot> devices) {
    if (devices == null || devices.isEmpty()) {
      return;
    }
    java.util.LinkedHashMap<String, String> legend = new java.util.LinkedHashMap<>();
    for (DeviceSnapshot snap : devices) {
      LedStatusAttachment led = snap.getAttachment(LedStatusAttachment.class);
      if (led == null) {
        continue;
      }
      addLegend(legend, led.expectedPattern, led.expectedMeaning);
      addLegend(legend, led.likelyPattern, led.likelyMeaning);
    }
    if (legend.isEmpty()) {
      return;
    }
    ReportTextUtil.appendLine(sb, "LED Legend (best-effort):");
    for (java.util.Map.Entry<String, String> entry : legend.entrySet()) {
      ReportTextUtil.appendLine(sb, "  " + entry.getKey() + " = " + entry.getValue());
    }
  }

  /**
   * NAME
   *   addLegend - Add a legend entry if not already present.
   */
  private void addLegend(java.util.Map<String, String> legend, String pattern, String meaning) {
    if (pattern == null || pattern.isBlank() || meaning == null || meaning.isBlank()) {
      return;
    }
    legend.putIfAbsent(pattern, meaning);
  }

  /**
   * NAME
   *   formatPatternMeaning - Format LED pattern with meaning.
   */
  private String formatPatternMeaning(String pattern, String meaning) {
    if (pattern == null || pattern.isBlank()) {
      return "";
    }
    if (meaning == null || meaning.isBlank()) {
      return pattern;
    }
    return pattern + " — " + meaning;
  }

  /**
   * NAME
   *   formatStateMeaning - Format state with meaning.
   */
  private String formatStateMeaning(String state, String meaning) {
    if (state == null || state.isBlank()) {
      return "";
    }
    if (meaning == null || meaning.isBlank()) {
      return state;
    }
    return state + " — " + meaning;
  }

  /**
   * NAME
   *   appendAppStatus - Append app loop health metrics.
   */
  private void appendAppStatus(StringBuilder sb) {
    AppStatusTracker.AppStatusSnapshot snap = AppStatusTracker.snapshot();
    ReportTextUtil.appendLine(sb, "App Status:");
    ReportTextUtil.appendLine(
        sb,
        "  Loop ms: last=" + String.format("%.2f", snap.lastLoopMs) +
        " avg=" + String.format("%.2f", snap.avgLoopMs) +
        " max=" + String.format("%.2f", snap.maxLoopMs) +
        " (overrun> " + String.format("%.1f", snap.overrunThresholdMs) + "ms)" +
        " totalOverruns=" + snap.overrunCount);
    ReportTextUtil.appendLine(
        sb,
        "  Loop window (60s): samples=" + snap.windowSamples +
        " overruns=" + snap.windowOverruns);
    ReportTextUtil.appendLine(
        sb,
        "  Print queue: queuedBytes=" + BringupPrinter.getQueuedBytes() +
        " droppedMsgs=" + BringupPrinter.getDroppedMessages() +
        " droppedBytes=" + BringupPrinter.getDroppedBytes());
    ReportTextUtil.appendLine(
        sb,
        "  Print throttle: maxBytesPerSec=" + BringupPrinter.getMaxBytesPerSec() +
        " windowMs=" + BringupPrinter.getThrottleWindowMs() +
        " maxQueueBytes=" + BringupPrinter.getMaxQueueBytes());
  }

  /**
   * NAME
   *   formatLimitSummary - Format limit switch summary.
   */
  private String formatLimitSummary(LimitsAttachment limits) {
    if (limits == null || (limits.fwdDio < 0 && limits.revDio < 0)) {
      return "";
    }
    StringBuilder sb = new StringBuilder(64);
    sb.append(" limits=");
    if (limits.fwdDio >= 0) {
      sb.append("fwd:DIO").append(limits.fwdDio)
          .append("=").append(formatLimitState(limits.fwdClosed));
    }
    if (limits.revDio >= 0) {
      if (limits.fwdDio >= 0) {
        sb.append(",");
      }
      sb.append("rev:DIO").append(limits.revDio)
          .append("=").append(formatLimitState(limits.revClosed));
    }
    if (limits.invert) {
      sb.append(" inv");
    }
    return sb.toString();
  }

  /**
   * NAME
   *   formatLimitState - Format a limit switch state.
   */
  private String formatLimitState(Boolean closed) {
    if (closed == null) {
      return "?";
    }
    return closed ? "CLOSED" : "OPEN";
  }

  /**
   * NAME
   *   formatRevFaultSummary - Format REV fault summary.
   */
  private String formatRevFaultSummary(RevMotorAttachment rev) {
    if (rev == null) {
      return "";
    }
    StringBuilder sb = new StringBuilder(128);
    sb.append(" faults=0x").append(Integer.toHexString(rev.faultsRaw));
    sb.append(formatFlagList(rev.faultFlags));
    sb.append(" sticky=0x").append(Integer.toHexString(rev.stickyFaultsRaw));
    sb.append(formatFlagList(rev.stickyFaultFlags));
    sb.append(" warnings=0x").append(Integer.toHexString(rev.warningsRaw));
    sb.append(formatFlagList(rev.warningFlags));
    sb.append(" stickyWarn=0x").append(Integer.toHexString(rev.stickyWarningsRaw));
    sb.append(formatFlagList(rev.stickyWarningFlags));
    return sb.toString();
  }

  /**
   * NAME
   *   formatMotorSpecNote - Format motor spec/current note.
   */
  private String formatMotorSpecNote(MotorSpecAttachment spec, Double motorCurrent) {
    if (spec == null || spec.freeCurrentA == null || spec.stallCurrentA == null) {
      return "";
    }
    double free = spec.freeCurrentA;
    double stall = spec.stallCurrentA;
    double current = motorCurrent != null ? motorCurrent : 0.0;
    String ratio = free > 0.0 ? String.format("%.2fx", current / free) : "?";
    return " specFree=" + String.format("%.1f", free) + "A" +
        " specStall=" + String.format("%.0f", stall) + "A" +
        " freeRatio=" + ratio;
  }

  /**
   * NAME
   *   formatFlagList - Format a list of flags.
   */
  private String formatFlagList(List<String> flags) {
    if (flags == null || flags.isEmpty()) {
      return "";
    }
    return " [" + String.join(",", flags) + "]";
  }

  /**
   * NAME
   *   formatDoubleOrDash - Format double or return dash when NaN.
   */
  private String formatDoubleOrDash(double value, int decimals) {
    if (Double.isNaN(value)) {
      return "-";
    }
    return String.format("%." + decimals + "f", value);
  }

  /**
   * NAME
   *   formatDouble - Format a Double with fixed decimals.
   */
  private String formatDouble(Double value, int decimals) {
    if (value == null) {
      value = 0.0;
    }
    if (Double.isNaN(value)) {
      return "NaN";
    }
    return String.format("%." + decimals + "f", value);
  }

  /**
   * NAME
   *   safeText - Replace null with empty string.
   */
  private String safeText(String value) {
    return value == null ? "" : value;
  }

  /**
   * NAME
   *   formatSeenNotLocal - Format entries for seen-not-local devices.
   */
  private List<String> formatSeenNotLocal(List<PcSnapshot.SeenNotLocalEntry> entries) {
    List<String> out = new java.util.ArrayList<>();
    for (PcSnapshot.SeenNotLocalEntry entry : entries) {
      String ageText = entry.ageSec == null ? "?" : String.format("%.2f", entry.ageSec);
      out.add(entry.key + " age=" + ageText + "s");
    }
    return out;
  }

  /**
   * NAME
   *   formatProfileMismatch - Format profile mismatch entries.
   */
  private List<String> formatProfileMismatch(List<PcSnapshot.ProfileMismatchEntry> entries) {
    List<String> out = new java.util.ArrayList<>();
    for (PcSnapshot.ProfileMismatchEntry entry : entries) {
      out.add(entry.expected + " missing, saw ids " + entry.seenIds + " on wire");
    }
    return out;
  }

  /**
   * NAME
   *   formatStaleDevices - Format stale device entries.
   */
  private List<String> formatStaleDevices(List<PcSnapshot.StaleDeviceEntry> entries) {
    List<String> out = new java.util.ArrayList<>();
    for (PcSnapshot.StaleDeviceEntry entry : entries) {
      out.add(entry.key + " age=" + String.format("%.2f", entry.ageSec) + "s");
    }
    return out;
  }
}
