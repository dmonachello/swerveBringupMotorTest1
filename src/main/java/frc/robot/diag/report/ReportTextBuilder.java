package frc.robot.diag.report;

import frc.robot.ReportTextUtil;
import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.CanSuspicionAttachment;
import frc.robot.diag.snapshots.LedStatusAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.EncoderAttachment;
import frc.robot.diag.snapshots.ImuAttachment;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.diag.snapshots.MotorSpecAttachment;
import frc.robot.manufacturers.ctre.diag.PdpStatusAttachment;
import frc.robot.manufacturers.rev.diag.PdhStatusAttachment;
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
  private static final String LIMITS_PREFIX = " limits=";
  private static final String LIMITS_SEPARATOR = ",";
  private static final String LIMITS_DIO_PREFIX = "DIO";
  private static final String LIMITS_INVERT_SUFFIX = " inv";
  private static final String LIMIT_STATE_UNKNOWN = "?";
  private static final String LIMIT_STATE_CLOSED = "CLOSED";
  private static final String LIMIT_STATE_OPEN = "OPEN";
  private static final String DEVICE_TYPE_PDP = "PDP";
  private static final String PREFIX_PDP_CAN = "  PDP CAN ";
  private static final String TEXT_PRESENT_NO = ": present=NO";
  private static final String TEXT_PRESENT_YES = ": present=YES";
  private static final String TEXT_NO_STATUS_ATTACHMENT = " (no status attachment)";
  private static final String TEXT_VOLTAGE = " voltage=";
  private static final String TEXT_TOTAL_CURRENT = " totalCurrent=";
  private static final String TEXT_SWITCHABLE = " switchable=";
  private static final String TEXT_TEMP = " tempC=";
  private static final String TEXT_VOLT = "V";
  private static final String TEXT_AMP = "A";
  private static final String TEXT_ON = "ON";
  private static final String TEXT_OFF = "OFF";
  private static final String TEXT_FAULTS_PREFIX = "    Faults: brownout=";
  private static final String TEXT_CAN_WARN = " canWarn=";
  private static final String TEXT_HW_FAULT = " hwFault=";
  private static final String TEXT_STICKY_PREFIX = "    Sticky: brownout=";
  private static final String TEXT_BUS_OFF = " busOff=";
  private static final String TEXT_HAS_RESET = " hasReset=";
  private static final String TEXT_CH_PREFIX = "    Ch ";
  private static final String TEXT_CURRENT_PREFIX = " current=";
  private static final String TEXT_ACTIVE_FAULT = " activeFault=";
  private static final String TEXT_STICKY_FAULT = " stickyFault=";
  private static final String TEXT_STATUS = " status=";
  private static final String STATUS_STICKY_FAULT = "STICKY_FAULT";
  private static final String STATUS_ACTIVE_FAULT = "ACTIVE_FAULT";
  private static final String STATUS_OK = "OK";
  private static final String TEXT_VIRTUAL_NO_API = ": present=YES (virtual, no API)";
  private static final String TEXT_PIGEON_FAULT = " fault=0x";
  private static final String TEXT_PIGEON_STICKY = " sticky=0x";
  private static final String FORMAT_CH = "%02d";
  private static final String FORMAT_CURRENT = "%6.2f";

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
    return "Summary: bus=" + bus;
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
      } else if ("PDH".equals(snap.deviceType)) {
        appendPdhDevice(sb, snap);
      } else if (DEVICE_TYPE_PDP.equals(snap.deviceType)) {
        appendPdpDevice(sb, snap);
      } else if ("Pigeon".equals(snap.deviceType)) {
        appendPigeon(sb, snap);
      } else if ("roboRIO".equals(snap.deviceType)) {
        ReportTextUtil.appendLine(
            sb,
            "  roboRIO CAN " + snap.canId + TEXT_VIRTUAL_NO_API);
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
        " cmdDuty=" + formatDouble(ctre != null ? ctre.cmdDuty : null, 2) + "dc" +
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
   *   appendPigeon - Append Pigeon device line.
   */
  private void appendPigeon(StringBuilder sb, DeviceSnapshot snap) {
    if (!snap.present) {
      ReportTextUtil.appendLine(
          sb,
          "  Pigeon CAN " + snap.canId + ": present=NO (not added)");
      appendCanSuspicionLines(sb, snap);
      appendLedLines(sb, snap);
      return;
    }
    ImuAttachment imu = snap.getAttachment(ImuAttachment.class);
    ReportTextUtil.appendLine(
        sb,
        "  Pigeon CAN " + snap.canId
            + ": present=YES yawDeg=" + formatDouble(imu != null ? imu.yawDeg : null, 1)
            + " pitchDeg=" + formatDouble(imu != null ? imu.pitchDeg : null, 1)
            + " rollDeg=" + formatDouble(imu != null ? imu.rollDeg : null, 1)
            + TEXT_PIGEON_FAULT + Integer.toHexString(imu != null && imu.faultsRaw != null ? imu.faultsRaw : 0)
            + TEXT_PIGEON_STICKY + Integer.toHexString(imu != null && imu.stickyFaultsRaw != null ? imu.stickyFaultsRaw : 0)
            + " lastErr=" + safeText(imu != null ? imu.lastError : ""));
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
   *   appendPdhDevice - Append PDH status section.
   */
  private void appendPdhDevice(StringBuilder sb, DeviceSnapshot snap) {
    if (!snap.present) {
      ReportTextUtil.appendLine(
          sb,
          "  PDH CAN " + snap.canId + ": present=NO" + formatNote(snap.note));
      return;
    }
    PdhStatusAttachment pdh = snap.getAttachment(PdhStatusAttachment.class);
    if (pdh == null) {
      ReportTextUtil.appendLine(
          sb,
          "  PDH CAN " + snap.canId + ": present=YES (no status attachment)");
      return;
    }
    ReportTextUtil.appendLine(
        sb,
        "  PDH CAN " + snap.canId +
        ": present=YES" +
        " voltage=" + formatDouble(pdh.voltage, 2) + "V" +
        " totalCurrent=" + formatDouble(pdh.totalCurrent, 2) + "A" +
        " switchable=" + (pdh.switchableEnabled ? "ON" : "OFF") +
        " tempC=" + formatDouble(pdh.temperature, 1));

    ReportTextUtil.appendLine(
        sb,
        "    Faults: brownout=" + formatBoolean(pdh.brownout) +
        " canWarn=" + formatBoolean(pdh.canWarning) +
        " hwFault=" + formatBoolean(pdh.hardwareFault));
    ReportTextUtil.appendLine(
        sb,
        "    Sticky: brownout=" + formatBoolean(pdh.stickyBrownout) +
        " canWarn=" + formatBoolean(pdh.stickyCanWarning) +
        " busOff=" + formatBoolean(pdh.stickyCanBusOff) +
        " hasReset=" + formatBoolean(pdh.stickyHasReset));

    if (pdh.channelCurrentA != null) {
      for (int ch = 0; ch < pdh.channelCurrentA.length; ch++) {
        boolean active = pdh.channelFault != null && ch < pdh.channelFault.length && pdh.channelFault[ch];
        boolean sticky = pdh.channelStickyFault != null && ch < pdh.channelStickyFault.length
            && pdh.channelStickyFault[ch];
        String status = sticky ? "STICKY_FAULT" : (active ? "ACTIVE_FAULT" : "OK");
        ReportTextUtil.appendLine(
            sb,
            "    Ch " + String.format("%02d", ch) +
            " current=" + String.format("%6.2f", pdh.channelCurrentA[ch]) + "A" +
            " activeFault=" + formatBoolean(active) +
            " stickyFault=" + formatBoolean(sticky) +
            " status=" + status);
      }
    }
  }

  /**
   * NAME
   *   appendPdpDevice - Append PDP status section.
   */
  private void appendPdpDevice(StringBuilder sb, DeviceSnapshot snap) {
    if (!snap.present) {
      ReportTextUtil.appendLine(
          sb,
          PREFIX_PDP_CAN + snap.canId + TEXT_PRESENT_NO + formatNote(snap.note));
      return;
    }
    PdpStatusAttachment pdp = snap.getAttachment(PdpStatusAttachment.class);
    if (pdp == null) {
      ReportTextUtil.appendLine(
          sb,
          PREFIX_PDP_CAN + snap.canId + TEXT_PRESENT_YES + TEXT_NO_STATUS_ATTACHMENT);
      return;
    }
    ReportTextUtil.appendLine(
        sb,
        PREFIX_PDP_CAN + snap.canId +
        TEXT_PRESENT_YES +
        TEXT_VOLTAGE + formatDouble(pdp.voltage, 2) + TEXT_VOLT +
        TEXT_TOTAL_CURRENT + formatDouble(pdp.totalCurrent, 2) + TEXT_AMP +
        TEXT_SWITCHABLE + (pdp.switchableEnabled ? TEXT_ON : TEXT_OFF) +
        TEXT_TEMP + formatDouble(pdp.temperature, 1));

    ReportTextUtil.appendLine(
        sb,
        TEXT_FAULTS_PREFIX + formatBoolean(pdp.brownout) +
        TEXT_CAN_WARN + formatBoolean(pdp.canWarning) +
        TEXT_HW_FAULT + formatBoolean(pdp.hardwareFault));
    ReportTextUtil.appendLine(
        sb,
        TEXT_STICKY_PREFIX + formatBoolean(pdp.stickyBrownout) +
        TEXT_CAN_WARN + formatBoolean(pdp.stickyCanWarning) +
        TEXT_BUS_OFF + formatBoolean(pdp.stickyCanBusOff) +
        TEXT_HAS_RESET + formatBoolean(pdp.stickyHasReset));

    if (pdp.channelCurrentA != null) {
      for (int ch = 0; ch < pdp.channelCurrentA.length; ch++) {
        boolean active = pdp.channelFault != null && ch < pdp.channelFault.length && pdp.channelFault[ch];
        boolean sticky = pdp.channelStickyFault != null && ch < pdp.channelStickyFault.length
            && pdp.channelStickyFault[ch];
        String status = sticky ? STATUS_STICKY_FAULT : (active ? STATUS_ACTIVE_FAULT : STATUS_OK);
        ReportTextUtil.appendLine(
            sb,
            TEXT_CH_PREFIX + String.format(FORMAT_CH, ch) +
            TEXT_CURRENT_PREFIX + String.format(FORMAT_CURRENT, pdp.channelCurrentA[ch]) + TEXT_AMP +
            TEXT_ACTIVE_FAULT + formatBoolean(active) +
            TEXT_STICKY_FAULT + formatBoolean(sticky) +
            TEXT_STATUS + status);
      }
    }
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
    if (limits == null || limits.switches == null || limits.switches.isEmpty()) {
      return "";
    }
    StringBuilder sb = new StringBuilder(64);
    sb.append(LIMITS_PREFIX);
    boolean first = true;
    for (LimitsAttachment.LimitSwitchState state : limits.switches) {
      if (state == null) {
        continue;
      }
      if (!first) {
        sb.append(LIMITS_SEPARATOR);
      }
      String label = state.label != null && !state.label.isBlank()
          ? state.label
          : LIMITS_DIO_PREFIX + state.dio;
      sb.append(label)
          .append("=")
          .append(formatLimitState(state.closed));
      if (state.invert) {
        sb.append(LIMITS_INVERT_SUFFIX);
      }
      first = false;
    }
    return sb.toString();
  }

  /**
   * NAME
   *   formatLimitState - Format a limit switch state.
   */
  private String formatLimitState(Boolean closed) {
    if (closed == null) {
      return LIMIT_STATE_UNKNOWN;
    }
    return closed ? LIMIT_STATE_CLOSED : LIMIT_STATE_OPEN;
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
   *   formatBoolean - Format boolean values for report output.
   */
  private String formatBoolean(boolean value) {
    return value ? "YES" : "NO";
  }

  /**
   * NAME
   *   formatNote - Format a note suffix when present.
   */
  private String formatNote(String note) {
    if (note == null || note.isBlank()) {
      return "";
    }
    return " (" + note + ")";
  }

  /**
   * NAME
   *   safeText - Replace null with empty string.
   */
  private String safeText(String value) {
    return value == null ? "" : value;
  }

}

