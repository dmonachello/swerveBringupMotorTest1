package frc.robot;

import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableEntry;
import edu.wpi.first.networktables.NetworkTableValue;
import frc.robot.diag.report.ReportJsonBuilder;
import frc.robot.diag.report.ReportTextBuilder;
import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LedStatusAttachment;
import frc.robot.diag.snapshots.PcSnapshot;
import frc.robot.diag.snapshots.SnapshotBundle;
import frc.robot.diag.led.LedStatusInference;
import frc.robot.diag.can.CanSuspicionInference;
import frc.robot.diag.snapshots.CanSuspicionAttachment;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * NAME
 *   DiagnosticsReporter - Build console and JSON diagnostics reports.
 *
 * DESCRIPTION
 *   Aggregates robot-local data and optional PC sniffer data from NetworkTables
 *   to produce human-readable reports and JSON snapshots.
 */
final class DiagnosticsReporter {
  private static final String REPORT_PATH = "/home/lvuser/bringup_report.json";
  private static final long MIN_PRINT_INTERVAL_MS = 1000;
  private static final double PC_STALE_DEVICE_AGE_SEC = 2.0;
  private static final double PC_STALE_HEARTBEAT_SEC = 1.0;

  private final ReportTextBuilder textBuilder = new ReportTextBuilder();
  private final ReportJsonBuilder jsonBuilder = new ReportJsonBuilder();

  // Core robot device access (local vendor APIs).
  private BringupCore core;
  // CAN controller health (roboRIO local).
  private final CanBusHealth canHealth;
  // PC tool diagnostics (NetworkTables bringup/diag).
  private final NetworkTable diagTable;

  private final Map<String, Double> prevMsgCount = new HashMap<>();
  private final Map<String, Double> prevMsgTime = new HashMap<>();
  private double lastPcHeartbeat = Double.NaN;
  private long lastPcHeartbeatMs = 0L;
  private final Map<String, String> pcLastStatus = new HashMap<>();
  private final Map<String, Integer> pcStatusFlaps = new HashMap<>();
  private final Map<String, Long> pcLastStatusChangeMs = new HashMap<>();
  private long lastNetworkPrintMs = 0L;
  private long lastCanDiagPrintMs = 0L;

  // Wire all dependencies explicitly to keep data flow obvious.
  /**
   * NAME
   *   DiagnosticsReporter - Construct a diagnostics reporter.
   *
   * PARAMETERS
   *   core - BringupCore for local device snapshots.
   *   canHealth - CAN controller health sampler.
   *   diagTable - NetworkTables bringup/diag subtable.
   */
  DiagnosticsReporter(BringupCore core, CanBusHealth canHealth, NetworkTable diagTable) {
    this.core = core;
    this.canHealth = canHealth;
    this.diagTable = diagTable;
  }

  /**
   * NAME
   *   setCore - Swap the BringupCore instance after profile changes.
   */
  void setCore(BringupCore core) {
    // Called when profiles reset and a new BringupCore is constructed.
    this.core = core;
  }

  /**
   * NAME
   *   resetState - Clear internal counters and cached state.
   */
  void resetState() {
    // Clear derived counters and previous samples between runs.
    prevMsgCount.clear();
    prevMsgTime.clear();
    pcLastStatus.clear();
    pcStatusFlaps.clear();
    pcLastStatusChangeMs.clear();
    lastPcHeartbeat = Double.NaN;
    lastPcHeartbeatMs = 0L;
    lastNetworkPrintMs = 0L;
    lastCanDiagPrintMs = 0L;
  }

  /**
   * NAME
   *   update - Sample CAN controller health.
   */
  void update() {
    // Periodic sampling from the CAN controller.
    canHealth.update();
  }

  /**
   * NAME
   *   buildNetworkDiagnosticsReportIfReady - Build NT report when rate-limited.
   *
   * RETURNS
   *   Report string or null when not ready.
   */
  String buildNetworkDiagnosticsReportIfReady() {
    // Returns a NetworkTables report snapshot when rate limiting allows.
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastNetworkPrintMs < MIN_PRINT_INTERVAL_MS) {
      return null;
    }
    lastNetworkPrintMs = nowMs;
    return buildNetworkDiagnosticsReport();
  }

  /**
   * NAME
   *   buildCanDiagnosticsReportIfReady - Build CAN report when rate-limited.
   *
   * RETURNS
   *   Report string or null when not ready.
   */
  String buildCanDiagnosticsReportIfReady() {
    // Returns a combined bus + PC tool + local device report when allowed.
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastCanDiagPrintMs < MIN_PRINT_INTERVAL_MS) {
      return null;
    }
    lastCanDiagPrintMs = nowMs;
    return buildCanDiagnosticsReport();
  }

  /**
   * NAME
   *   buildQuickSummary - Build a concise status summary.
   *
   * RETURNS
   *   Multi-line summary of bus, PC tool, and device health.
   */
  String buildQuickSummary() {
    SnapshotBundle bundle = buildSnapshotBundle();
    StringBuilder sb = new StringBuilder(256);
    ReportTextUtil.appendLine(sb, "=== Bringup Summary ===");
    appendQuickBus(sb, bundle.bus);
    appendQuickPc(sb, bundle.pc);
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
        "Bus: util=" + util +
        " rxErr=" + bus.rxErrors +
        " txErr=" + bus.txErrors +
        " busOff=" + bus.busOff);
  }

  /**
   * NAME
   *   appendQuickPc - Append concise PC tool status.
   */
  private void appendQuickPc(StringBuilder sb, PcSnapshot pc) {
    if (pc == null) {
      ReportTextUtil.appendLine(sb, "PC: NOT CONNECTED");
      return;
    }
    String status = (pc.openOk && pc.heartbeatAgeSec >= 0.0 && pc.heartbeatAgeSec <= PC_STALE_HEARTBEAT_SEC)
        ? "OK"
        : "STALE";
    String hb = pc.heartbeatAgeSec < 0 ? "-" : String.format("%.2fs", pc.heartbeatAgeSec);
    ReportTextUtil.appendLine(
        sb,
        "PC: " + status +
        " hb=" + hb +
        " fps=" + formatDoubleOrDash(pc.framesPerSec, 1) +
        " missing=" + pc.missingCount + "/" + pc.totalCount);
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
      if (suspicion != null && suspicion.likelyState != null && !suspicion.likelyState.isBlank()
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
   *   buildNetworkDiagnosticsReport - Build a NetworkTables diagnostics report.
   */
  private String buildNetworkDiagnosticsReport() {
    // NetworkTables snapshot: PC sniffer device visibility and rates.
    StringBuilder sb = new StringBuilder(1024);
    ReportTextUtil.appendLine(sb, "=== Bringup NetworkTables (CAN Bus via PC Tool) ===");
    long nowMs = System.currentTimeMillis();
    double nowSeconds = nowMs / 1000.0;

    double heartbeatAgeSec = getPcHeartbeatAgeSec(nowMs);
    boolean openOk = "YES".equals(formatPcBoolean(diagTable.getEntry("can/pc/openOk")));
    boolean pcConnected = openOk && heartbeatAgeSec >= 0.0 && heartbeatAgeSec <= PC_STALE_HEARTBEAT_SEC;
    ReportTextUtil.appendLine(
        sb,
        "PC CAN Sniffer: " + (pcConnected ? "CONNECTED" : "DISCONNECTED"));
    if (heartbeatAgeSec >= 0.0) {
      ReportTextUtil.appendLine(sb, "PC heartbeat age: " + String.format("%.3f", heartbeatAgeSec) + "s");
    }

    double busErrors = diagTable.getEntry("busErrorCount").getDouble(Double.NaN);
    if (!Double.isNaN(busErrors)) {
      ReportTextUtil.appendLine(sb, "Bus error count: " + (long) busErrors);
    }

    ReportTextUtil.appendLine(sb, "Devices:");
    DeviceSpec[] expectedSpecs = buildDeviceSpecs();
    ArrayList<DeviceSpec> allSpecs = new ArrayList<>();
    Collections.addAll(allSpecs, expectedSpecs);
    Collections.addAll(allSpecs, findUnknownDeviceSpecs(expectedSpecs));
    printNetworkDeviceTable(sb, allSpecs, nowSeconds);
    appendConsoleAlerts(sb, nowSeconds);
    ReportTextUtil.appendLine(sb, "=============================");
    return sb.toString();
  }

  /**
   * NAME
   *   appendConsoleAlerts - Append PC console warning/error summaries.
   *
   * PARAMETERS
   *   sb - Target StringBuilder.
   *   nowSeconds - Current time for age calculations.
   */
  private void appendConsoleAlerts(StringBuilder sb, double nowSeconds) {
    NetworkTable console = diagTable.getSubTable("console");
    double rulesLoaded = console.getEntry("rulesLoaded").getDouble(Double.NaN);
    if (Double.isNaN(rulesLoaded)) {
      return;
    }
    double activeCount = console.getEntry("activeCount").getDouble(Double.NaN);
    double totalCount = console.getEntry("totalCount").getDouble(Double.NaN);
    double linesReceived = console.getEntry("linesReceived").getDouble(Double.NaN);
    double linesMatched = console.getEntry("linesMatched").getDouble(Double.NaN);
    double lastPublish = console.getEntry("lastPublish").getDouble(Double.NaN);
    String lastSource = console.getEntry("lastSource").getString("");

    ReportTextUtil.appendLine(sb, "Console Alerts (PC):");
    ReportTextUtil.appendLine(
        sb,
        "  rulesLoaded=" + formatDoubleOrDash(rulesLoaded, 0) +
        " active=" + formatDoubleOrDash(activeCount, 0) +
        " total=" + formatDoubleOrDash(totalCount, 0) +
        " matched=" + formatDoubleOrDash(linesMatched, 0) +
        " lines=" + formatDoubleOrDash(linesReceived, 0) +
        " lastPublishAge=" + formatAgeSince(lastPublish, nowSeconds) +
        (lastSource.isBlank() ? "" : " source=" + lastSource));

    NetworkTable system = console.getSubTable("system");
    for (String event : system.getSubTables()) {
      appendConsoleEvent(sb, system.getSubTable(event), "system", null, event, nowSeconds);
    }
    NetworkTable devices = console.getSubTable("devices");
    for (String labelKey : devices.getSubTables()) {
      String label = BringupUtil.decodeLabelFromNt(labelKey);
      NetworkTable deviceTable = devices.getSubTable(labelKey);
      for (String event : deviceTable.getSubTables()) {
        appendConsoleEvent(sb, deviceTable.getSubTable(event), "device", label, event, nowSeconds);
      }
    }
  }

  /**
   * NAME
   *   appendConsoleEvent - Append one console event row when active.
   *
   * PARAMETERS
   *   sb - Target StringBuilder.
   *   table - Event subtable.
   *   scope - "system" or "device".
   *   deviceLabel - Device label when scope is device.
   *   eventType - Event type key.
   *   nowSeconds - Current time for age calculations.
   */
  private void appendConsoleEvent(
      StringBuilder sb,
      NetworkTable table,
      String scope,
      String deviceLabel,
      String eventType,
      double nowSeconds) {
    boolean active = table.getEntry("Active").getBoolean(false);
    if (!active) {
      return;
    }
    double count = table.getEntry("Count").getDouble(Double.NaN);
    double lastSeen = table.getEntry("LastSeen").getDouble(Double.NaN);
    String severity = table.getEntry("Severity").getString("");
    String message = table.getEntry("Message").getString("");
    String target = "system".equals(scope)
        ? "system"
        : "device " + deviceLabel;
    ReportTextUtil.appendLine(
        sb,
        "  [" + (severity.isBlank() ? "INFO" : severity) + "] " +
        target + " " + eventType +
        " count=" + formatDoubleOrDash(count, 0) +
        " age=" + formatAgeSince(lastSeen, nowSeconds) +
        (message.isBlank() ? "" : " msg=\"" + message + "\""));
  }

  /**
   * NAME
   *   formatAgeSince - Format age from a timestamp.
   */
  private String formatAgeSince(double timestampSec, double nowSeconds) {
    if (Double.isNaN(timestampSec) || timestampSec <= 0) {
      return "-";
    }
    double age = nowSeconds - timestampSec;
    if (age < 0.0) {
      return "-";
    }
    return String.format("%.3fs", age);
  }

  /**
   * NAME
   *   buildCanDiagnosticsReport - Build a combined CAN diagnostics report.
   */
  private String buildCanDiagnosticsReport() {
    // Full text report with summary and device health.
    SnapshotBundle bundle = buildSnapshotBundle();
    return textBuilder.buildCanDiagnosticsReport(bundle);
  }

  /**
   * NAME
   *   buildReportJson - Build the JSON diagnostics payload.
   */
  private String buildReportJson() {
    // JSON payload includes: timestamp, bus, pc, devices.
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
    bundle.pc = buildPcSnapshot(System.currentTimeMillis());
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

  /**
   * NAME
   *   buildPcSnapshot - Build a snapshot from PC sniffer NetworkTables data.
   */
  private PcSnapshot buildPcSnapshot(long nowMs) {
    PcSnapshot pc = new PcSnapshot();
    pc.heartbeatAgeSec = getPcHeartbeatAgeSec(nowMs);

    NetworkTableEntry openEntry = diagTable.getEntry("can/pc/openOk");
    pc.openOk = "YES".equals(formatPcBoolean(openEntry));
    pc.framesPerSec = diagTable.getEntry("can/pc/framesPerSec").getDouble(Double.NaN);
    pc.framesTotal = diagTable.getEntry("can/pc/framesTotal").getDouble(Double.NaN);
    pc.readErrors = diagTable.getEntry("can/pc/readErrors").getDouble(Double.NaN);
    pc.lastFrameAgeSec = diagTable.getEntry("can/pc/lastFrameAgeSec").getDouble(Double.NaN);

    DeviceSpec[] expectedSpecs = buildDeviceSpecs();
    DeviceSpec[] unknownSpecs = findUnknownDeviceSpecs(expectedSpecs);
    ArrayList<DeviceSpec> allSpecs = new ArrayList<>();
    Collections.addAll(allSpecs, expectedSpecs);
    Collections.addAll(allSpecs, unknownSpecs);
    pc.totalCount = allSpecs.size();

    java.util.HashSet<String> expectedLabels = new java.util.HashSet<>();
    for (DeviceSpec spec : expectedSpecs) {
      expectedLabels.add(spec.label);
    }
    java.util.ArrayList<String> unknownLabels = new java.util.ArrayList<>();
    for (DeviceSpec spec : unknownSpecs) {
      unknownLabels.add(spec.label);
    }

    int missingCount = 0;
    int flappingCount = 0;

    for (DeviceSpec spec : allSpecs) {
      String label = spec.label;
      String labelKey = spec.labelKey;
      String base = "dev/" + labelKey;
      String status = diagTable.getEntry(base + "/status").getString("UNKNOWN");
      double ageSec = diagTable.getEntry(base + "/ageSec").getDouble(Double.NaN);

      boolean missing =
          "MISSING".equals(status) || "NO_DATA".equals(status) || "CONTROL_ONLY".equals(status);
      if (missing) {
        missingCount++;
      }

      boolean stale = !missing && !Double.isNaN(ageSec) && ageSec > PC_STALE_DEVICE_AGE_SEC;
      if (stale) {
        PcSnapshot.StaleDeviceEntry entry = new PcSnapshot.StaleDeviceEntry();
        entry.key = label;
        entry.ageSec = ageSec;
        pc.staleDevices.add(entry);
      }

      String prev = pcLastStatus.get(label);
      if (prev != null && !prev.equals(status)) {
        int flaps = pcStatusFlaps.getOrDefault(label, 0) + 1;
        pcStatusFlaps.put(label, flaps);
        pcLastStatusChangeMs.put(label, nowMs);
      }
      pcLastStatus.put(label, status);

      int flaps = pcStatusFlaps.getOrDefault(label, 0);
      if (flaps > 0) {
        flappingCount++;
      }

      boolean localPresent = core != null && core.findDeviceByLabel(label) != null;
      String presenceSource = diagTable.getEntry(base + "/presenceSource").getString("NONE");
      double statusAge = diagTable.getEntry(base + "/statusAgeSec").getDouble(Double.NaN);
      boolean statusSeen = "STATUS".equals(presenceSource) && !Double.isNaN(statusAge) && statusAge >= 0;
      if (statusSeen && !localPresent) {
        PcSnapshot.SeenNotLocalEntry entry = new PcSnapshot.SeenNotLocalEntry();
        entry.key = label;
        if (!Double.isNaN(statusAge)) {
          entry.ageSec = statusAge;
        }
        pc.seenNotLocal.add(entry);
      }

      if (missing && expectedLabels.contains(label) && !unknownLabels.isEmpty()) {
        PcSnapshot.ProfileMismatchEntry entry = new PcSnapshot.ProfileMismatchEntry();
        entry.expected = label;
        entry.seenLabels.addAll(unknownLabels);
        pc.profileMismatch.add(entry);
      }
    }

    pc.missingCount = missingCount;
    pc.flappingCount = flappingCount;
    return pc;
  }

  /**
   * NAME
   *   getPcHeartbeatAgeSec - Compute age of PC heartbeat.
   */
  private double getPcHeartbeatAgeSec(long nowMs) {
    NetworkTableEntry heartbeatEntry = diagTable.getEntry("can/pc/heartbeat");
    double heartbeat = heartbeatEntry.getDouble(Double.NaN);
    if (Double.isNaN(heartbeat)) {
      return -1.0;
    }
    if (heartbeat != lastPcHeartbeat) {
      lastPcHeartbeat = heartbeat;
      lastPcHeartbeatMs = nowMs;
    }
    return (nowMs - lastPcHeartbeatMs) / 1000.0;
  }

  /**
   * NAME
   *   printNetworkDeviceTable - Append a formatted device table.
   */
  private void printNetworkDeviceTable(
      StringBuilder sb,
      java.util.List<DeviceSpec> specs,
      double nowSeconds) {
    ArrayList<DeviceRow> rows = new ArrayList<>();
    String labelHeaderLong = "label";
    String statusHeaderLong = "status";
    String confHeaderLong = "conf";
    String scoreHeaderLong = "score";
    String warnHeaderLong = "warn";
    String errHeaderLong = "err";
    String fatalHeaderLong = "fatal";
    String ageHeaderLong = "ageSec";
    String fpsHeaderLong = "fps";
    String msgHeaderLong = "msgCount";
    int labelWidth = 28;
    int statusWidth = 8;
    int confWidth = 8;
    int scoreWidth = 5;
    int warnWidth = 5;
    int errWidth = 5;
    int fatalWidth = 6;
    int ageWidth = 7;
    int fpsWidth = 7;
    int msgWidth = 12;
    int[] widths = new int[] {
        labelWidth, statusWidth, confWidth, scoreWidth, warnWidth,
        errWidth, fatalWidth, ageWidth, fpsWidth, msgWidth
    };
    int maxLineWidth = computeLineWidth(widths);

    Map<String, ConsoleCounts> consoleCounts = buildConsoleCounts();

    // Build rows first so we can compute column widths and wrap lines.
    for (DeviceSpec spec : specs) {
      DeviceRow row = loadDeviceRow(spec, nowSeconds, consoleCounts);
      rows.add(row);
    }

    ReportTextUtil.appendWrappedHeaders(
        sb,
        new String[] { labelHeaderLong, statusHeaderLong, confHeaderLong, scoreHeaderLong,
            warnHeaderLong, errHeaderLong, fatalHeaderLong, ageHeaderLong, fpsHeaderLong, msgHeaderLong },
        null,
        widths,
        maxLineWidth);

    for (DeviceRow row : rows) {
      ReportTextUtil.appendWrappedRow(
          sb,
          new String[] {
              row.label,
              row.status,
              row.confidence,
              row.scoreText,
              row.warnCount,
              row.errCount,
              row.fatalCount,
              row.ageText,
              row.fpsText,
              row.msgText
          },
          widths,
          maxLineWidth);
    }
  }

  /**
   * NAME
   *   loadDeviceRow - Load per-device row data from NetworkTables.
   */
  private DeviceRow loadDeviceRow(
      DeviceSpec spec,
      double nowSeconds,
      Map<String, ConsoleCounts> consoleCounts) {
    // Pull PC tool data for each device and compute age/fps values.
    String base = "dev/" + spec.labelKey;
    String label = diagTable.getEntry(base + "/label").getString(spec.label);
    String status = diagTable.getEntry(base + "/status").getString("UNKNOWN");
    String presenceSource = diagTable.getEntry(base + "/presenceSource").getString("NONE");
    double age = diagTable.getEntry(base + "/ageSec").getDouble(Double.NaN);
    double msgCount = diagTable.getEntry(base + "/msgCount").getDouble(Double.NaN);
    double trafficAge = diagTable.getEntry(base + "/trafficAgeSec").getDouble(Double.NaN);
    double statusAge = diagTable.getEntry(base + "/statusAgeSec").getDouble(Double.NaN);

    boolean hasData =
        !"NONE".equals(presenceSource)
        || !(Double.isNaN(trafficAge) || trafficAge < 0)
        || !(Double.isNaN(statusAge) || statusAge < 0);
    String ageText = "-";
    String fpsText = "-";
    String msgText = "-";
    double ageValue = Double.NaN;
    double fpsValue = Double.NaN;
    String finalStatus = hasData ? status : "NO_DATA";
    if (hasData) {
      ageValue = age;
      if (Double.isNaN(ageValue)) {
        ageValue = !Double.isNaN(trafficAge) ? trafficAge : statusAge;
      }
      if (!Double.isNaN(ageValue)) {
        ageText = String.format("%.3f", ageValue);
      }
      msgText = Double.isNaN(msgCount) ? "?" : String.format("%.0f", msgCount);
      fpsValue = computeFps(spec, msgCount, nowSeconds);
      fpsText = Double.isNaN(fpsValue) ? "-" : String.format("%.1f", fpsValue);
    }

    ConsoleCounts counts = consoleCounts.get(spec.labelKey);
    String warnCount = counts != null && counts.warn > 0 ? Integer.toString(counts.warn) : "-";
    String errCount = counts != null && counts.err > 0 ? Integer.toString(counts.err) : "-";
    String fatalCount = counts != null && counts.fatal > 0 ? Integer.toString(counts.fatal) : "-";
    ConfidenceScore score = computeConfidenceScore(presenceSource, ageValue, fpsValue, counts);
    String confidence = score.label;
    String scoreText = score.score >= 0 ? Integer.toString(score.score) : "-";

    return new DeviceRow(
        spec,
        label,
        finalStatus,
        confidence,
        scoreText,
        warnCount,
        errCount,
        fatalCount,
        ageText,
        fpsText,
        msgText);
  }

  /**
   * NAME
   *   buildConsoleCounts - Aggregate active console events per device.
   *
   * PARAMETERS
   *   specs - Device specs from the active profile.
   *
   * RETURNS
   *   Map of device key to warning/error counts.
   */
  private Map<String, ConsoleCounts> buildConsoleCounts() {
    Map<String, ConsoleCounts> counts = new HashMap<>();
    NetworkTable console = diagTable.getSubTable("console");
    double rulesLoaded = console.getEntry("rulesLoaded").getDouble(Double.NaN);
    if (Double.isNaN(rulesLoaded)) {
      return counts;
    }
    NetworkTable devices = console.getSubTable("devices");
    for (String labelKey : devices.getSubTables()) {
      NetworkTable deviceTable = devices.getSubTable(labelKey);
      int warn = (int) Math.round(deviceTable.getEntry("warnCount").getDouble(0.0));
      int err = (int) Math.round(deviceTable.getEntry("errorCount").getDouble(0.0));
      int fatal = (int) Math.round(deviceTable.getEntry("fatalCount").getDouble(0.0));
      if (warn <= 0 && err <= 0 && fatal <= 0) {
        continue;
      }
      ConsoleCounts entry = counts.computeIfAbsent(labelKey, k -> new ConsoleCounts());
      entry.warn += Math.max(0, warn);
      entry.err += Math.max(0, err);
      entry.fatal += Math.max(0, fatal);
    }
    return counts;
  }

  /**
   * NAME
   *   computeConfidenceScore - Compute a numeric confidence score and label.
   */
  private ConfidenceScore computeConfidenceScore(
      String presenceSource,
      double ageSec,
      double fps,
      ConsoleCounts counts) {
    int score = 0;
    if ("STATUS".equals(presenceSource)) {
      score += 60;
    } else if ("TRAFFIC".equals(presenceSource)) {
      score += 35;
    } else if ("CONTROL_ONLY".equals(presenceSource)) {
      score += 25;
    }

    if (!Double.isNaN(ageSec)) {
      if (ageSec <= 0.05) {
        score += 10;
      } else if (ageSec <= 0.20) {
        score += 6;
      } else if (ageSec <= 0.50) {
        score += 3;
      }
    }

    if (!Double.isNaN(fps)) {
      if (fps >= 50.0) {
        score += 10;
      } else if (fps >= 10.0) {
        score += 6;
      } else if (fps >= 1.0) {
        score += 2;
      }
    }

    if (counts != null) {
      int penalty = (counts.fatal * 30) + (counts.err * 20) + (counts.warn * 10);
      if (penalty > 50) {
        penalty = 50;
      }
      score -= penalty;
    }

    if (score < 0) {
      score = 0;
    } else if (score > 100) {
      score = 100;
    }

    String label;
    if (score >= 80) {
      label = "HIGH";
    } else if (score >= 60) {
      label = "MEDIUM";
    } else if (score >= 30) {
      label = "LOW";
    } else {
      label = "OFF";
    }
    return new ConfidenceScore(score, label);
  }

  /**
   * NAME
   *   computeLineWidth - Compute total table width for separators.
   */
  private static int computeLineWidth(int[] widths) {
    int sum = 0;
    for (int width : widths) {
      sum += width;
    }
    return sum;
  }

  /**
   * NAME
   *   computeFps - Compute message rate from deltas.
   */
  private double computeFps(DeviceSpec spec, double msgCount, double nowSeconds) {
    if (Double.isNaN(msgCount)) {
      return Double.NaN;
    }
    String key = spec.label;
    Double prevCount = prevMsgCount.get(key);
    Double prevTime = prevMsgTime.get(key);
    prevMsgCount.put(key, msgCount);
    prevMsgTime.put(key, nowSeconds);
    if (prevCount == null || prevTime == null) {
      return Double.NaN;
    }
    double dt = nowSeconds - prevTime;
    double delta = msgCount - prevCount;
    if (dt <= 0.0 || delta < 0.0) {
      return Double.NaN;
    }
    return delta / dt;
  }

  /**
   * NAME
   *   findUnknownDeviceSpecs - Enumerate devices seen by PC tool but not local.
   */
  private DeviceSpec[] findUnknownDeviceSpecs(DeviceSpec[] expectedSpecs) {
    // Any device published by the PC tool but not in our profile is "unknown".
    java.util.HashSet<String> knownKeys = new java.util.HashSet<>();
    for (DeviceSpec spec : expectedSpecs) {
      knownKeys.add(spec.labelKey);
    }

    ArrayList<DeviceSpec> unknowns = new ArrayList<>();
    NetworkTable devTable = diagTable.getSubTable("dev");
    for (String labelKey : devTable.getSubTables()) {
      if (knownKeys.contains(labelKey)) {
        continue;
      }
      NetworkTable deviceTable = devTable.getSubTable(labelKey);
      String label = deviceTable.getEntry("label").getString("");
      if (label == null || label.isBlank()) {
        label = BringupUtil.decodeLabelFromNt(labelKey);
      }
      unknowns.add(new DeviceSpec(label, labelKey));
    }
    return unknowns.toArray(new DeviceSpec[0]);
  }

  /**
   * NAME
   *   buildDeviceSpecs - Build expected devices from active profile.
   */
  private static DeviceSpec[] buildDeviceSpecs() {
    // Build the expected device list from the active profile.
    java.util.List<BringupUtil.DeviceEntry> expected = BringupUtil.getActiveDevices();
    java.util.List<DeviceSpec> specs = new java.util.ArrayList<>();
    for (BringupUtil.DeviceEntry entry : expected) {
      if (entry == null || !BringupUtil.isEnabledCanId(entry.id)) {
        continue;
      }
      String label = entry.label != null ? entry.label.trim() : "";
      if (label.isBlank()) {
        continue;
      }
      specs.add(DeviceSpec.fromLabel(label));
    }
    return specs.toArray(new DeviceSpec[0]);
  }

  /**
   * NAME
   *   formatPcBoolean - Normalize boolean values from NetworkTables.
   */
  private static String formatPcBoolean(NetworkTableEntry entry) {
    // PC tool boolean values may arrive as bool or numeric.
    NetworkTableValue value = entry.getValue();
    if (value == null) {
      return "UNKNOWN";
    }
    if (value.isBoolean()) {
      return value.getBoolean() ? "YES" : "NO";
    }
    if (value.isDouble()) {
      return value.getDouble() != 0.0 ? "YES" : "NO";
    }
    return "UNKNOWN";
  }

  /**
   * NAME
   *   formatDoubleOrDash - Normalize invalid values for a cleaner table.
   */
  private static String formatDoubleOrDash(double value, int decimals) {
    if (Double.isNaN(value) || Double.isInfinite(value) || value < 0.0) {
      return "-";
    }
    String fmt = "%." + decimals + "f";
    return String.format(fmt, value);
  }

  /**
   * NAME
   *   DeviceSpec - Expected device metadata for report rendering.
   */
  private static final class DeviceSpec {
    private final String label;
    private final String labelKey;

    private DeviceSpec(String label, String labelKey) {
      this.label = label;
      this.labelKey = labelKey;
    }

    private static DeviceSpec fromLabel(String label) {
      return new DeviceSpec(label, BringupUtil.encodeLabelForNt(label));
    }
  }

  /**
   * NAME
   *   DeviceRow - Row data for NetworkTables device report.
   */
  private static final class DeviceRow {
    @SuppressWarnings("unused")
    private final DeviceSpec spec;
    private final String label;
    private final String status;
    private final String confidence;
    private final String scoreText;
    private final String warnCount;
    private final String errCount;
    private final String fatalCount;
    private final String ageText;
    private final String fpsText;
    private final String msgText;

    private DeviceRow(
        DeviceSpec spec,
        String label,
        String status,
        String confidence,
        String scoreText,
        String warnCount,
        String errCount,
        String fatalCount,
        String ageText,
        String fpsText,
        String msgText) {
      this.spec = spec;
      this.label = label;
      this.status = status;
      this.confidence = confidence;
      this.scoreText = scoreText;
      this.warnCount = warnCount;
      this.errCount = errCount;
      this.fatalCount = fatalCount;
      this.ageText = ageText;
      this.fpsText = fpsText;
      this.msgText = msgText;
    }
  }

  /**
   * NAME
   *   ConsoleCounts - Warning/error counters for console events.
   */
  private static final class ConsoleCounts {
    private int warn = 0;
    private int err = 0;
    private int fatal = 0;
  }

  /**
   * NAME
   *   ConfidenceScore - Numeric confidence score and label.
   */
  private static final class ConfidenceScore {
    private final int score;
    private final String label;

    private ConfidenceScore(int score, String label) {
      this.score = score;
      this.label = label;
    }
  }
}
