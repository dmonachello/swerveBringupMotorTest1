package frc.robot;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableEntry;
import edu.wpi.first.networktables.NetworkTableValue;
import edu.wpi.first.wpilibj.Filesystem;
import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

// Builds and emits diagnostics reports (console + JSON) using robot-local data
// and optional PC sniffer data from NetworkTables.
final class DiagnosticsReporter {
  private static final int REV_MANUFACTURER = 5;
  private static final int CTRE_MANUFACTURER = 4;
  private static final int NI_MANUFACTURER = 1;
  private static final int TYPE_MOTOR_CONTROLLER = 2;
  private static final int TYPE_GYRO_SENSOR = 4;
  private static final int TYPE_ENCODER = 7;
  private static final int TYPE_POWER_DISTRIBUTION_MODULE = 8;
  private static final int TYPE_ROBOT_CONTROLLER = 1;

  private static final String REPORT_PATH = "/home/lvuser/bringup_report.json";
  private static final String CAN_MAP_FILE = "can_mappings.json";
  private static final Gson GSON = new Gson();
  private static final Map<Integer, String> MANUFACTURER_NAMES = loadManufacturerNames();
  private static final Map<Integer, String> DEVICE_TYPE_NAMES = loadDeviceTypeNames();
  private static final long MIN_PRINT_INTERVAL_MS = 1000;

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
  DiagnosticsReporter(BringupCore core, CanBusHealth canHealth, NetworkTable diagTable) {
    this.core = core;
    this.canHealth = canHealth;
    this.diagTable = diagTable;
  }

  void setCore(BringupCore core) {
    // Called when profiles reset and a new BringupCore is constructed.
    this.core = core;
  }

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

  void update() {
    // Periodic sampling from the CAN controller.
    canHealth.update();
  }

  void printNetworkDiagnostics() {
    // Prints the NetworkTables table of PC tool CAN visibility.
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastNetworkPrintMs < MIN_PRINT_INTERVAL_MS) {
      return;
    }
    lastNetworkPrintMs = nowMs;
    enqueueNetworkDiagnosticsReport();
  }

  void printCanDiagnosticsReport() {
    // Prints the combined bus + PC tool + local device report.
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastCanDiagPrintMs < MIN_PRINT_INTERVAL_MS) {
      return;
    }
    lastCanDiagPrintMs = nowMs;
    enqueueCanDiagnosticsReport();
  }

  void dumpReportJsonToConsoleAndFile() {
    // JSON report is for machine parsing and AI diagnostics.
    String json = buildReportJson();
    BringupPrinter.enqueueChunked(ReportTextUtil.wrapLongLine(json, 120), 12);
    try {
      Files.writeString(Path.of(REPORT_PATH), json);
      BringupPrinter.enqueue("Wrote CAN report JSON to " + REPORT_PATH);
    } catch (Exception ex) {
      BringupPrinter.enqueue("Failed to write CAN report JSON: " + ex.getMessage());
    }
  }

  private void enqueueNetworkDiagnosticsReport() {
    // NetworkTables snapshot: PC sniffer device visibility and rates.
    StringBuilder sb = new StringBuilder(1024);
    ReportTextUtil.appendLine(sb, "=== Bringup NetworkTables (CAN Bus via PC Tool) ===");
    double nowSeconds = System.currentTimeMillis() / 1000.0;

    double busErrors = diagTable.getEntry("busErrorCount").getDouble(Double.NaN);
    if (!Double.isNaN(busErrors)) {
      ReportTextUtil.appendLine(sb, "Bus error count: " + (long) busErrors);
    }

    ReportTextUtil.appendLine(sb, "Devices:");
    ArrayList<DeviceSpec> allSpecs = new ArrayList<>();
    Collections.addAll(allSpecs, buildDeviceSpecs());
    Collections.addAll(allSpecs, findUnknownDeviceSpecs());
    printNetworkDeviceTable(sb, allSpecs, nowSeconds);
    ReportTextUtil.appendLine(sb, "=============================");
    BringupPrinter.enqueueChunked(sb.toString(), 12);
  }

  private void enqueueCanDiagnosticsReport() {
    // Full text report with summary and device health.
    StringBuilder sb = new StringBuilder(1024);
    ReportTextUtil.appendLine(sb, "=== CAN Diagnostics Report ===");
    ReportTextUtil.appendLine(sb, buildSummaryLine());
    canHealth.appendSnapshot(sb);
    canHealth.appendReportSection(sb);
    appendPcToolSection(sb);
    core.appendDeviceDiagnosticsReport(sb);
    ReportTextUtil.appendLine(sb, "==============================");
    BringupPrinter.enqueueChunked(sb.toString(), 12);
  }

  private String buildSummaryLine() {
    // Single-line summary used at the top of the report.
    String bus = canHealth.summaryStatus();
    String pc = buildPcSummaryStatus();
    return "Summary: bus=" + bus + " pc=" + pc;
  }

  private String buildPcSummaryStatus() {
    // Treat missing heartbeat/openOk as "PC tool missing".
    NetworkTableEntry heartbeatEntry = diagTable.getEntry("can/pc/heartbeat");
    double heartbeat = heartbeatEntry.getDouble(Double.NaN);
    NetworkTableEntry openEntry = diagTable.getEntry("can/pc/openOk");
    String openOkText = formatPcBoolean(openEntry);
    if (Double.isNaN(heartbeat) || !"YES".equals(openOkText)) {
      return "PC_TOOL_MISSING";
    }
    return "OK";
  }

  private String buildReportJson() {
    // JSON payload includes: timestamp, bus, pc, devices.
    JsonObject root = new JsonObject();
    root.addProperty("timestamp", System.currentTimeMillis() / 1000.0);

    JsonObject bus = new JsonObject();
    canHealth.appendSnapshotJson(bus);
    root.add("bus", bus);

    JsonObject pc = buildPcJson();
    root.add("pc", pc);

    JsonArray devices = new JsonArray();
    core.appendDeviceDiagnosticsJson(devices);
    root.add("devices", devices);

    return GSON.toJson(root);
  }

  private JsonObject buildPcJson() {
    // PC tool section: heartbeat age and sniffer stats.
    JsonObject pc = new JsonObject();
    long nowMs = System.currentTimeMillis();

    NetworkTableEntry heartbeatEntry = diagTable.getEntry("can/pc/heartbeat");
    double heartbeat = heartbeatEntry.getDouble(Double.NaN);
    if (Double.isNaN(heartbeat)) {
      pc.addProperty("heartbeatAgeSec", -1.0);
    } else {
      if (heartbeat != lastPcHeartbeat) {
        lastPcHeartbeat = heartbeat;
        lastPcHeartbeatMs = nowMs;
      }
      pc.addProperty("heartbeatAgeSec", (nowMs - lastPcHeartbeatMs) / 1000.0);
    }

    NetworkTableEntry openEntry = diagTable.getEntry("can/pc/openOk");
    pc.addProperty("openOk", "YES".equals(formatPcBoolean(openEntry)));
    pc.addProperty("framesPerSec", diagTable.getEntry("can/pc/framesPerSec").getDouble(Double.NaN));
    pc.addProperty("framesTotal", diagTable.getEntry("can/pc/framesTotal").getDouble(Double.NaN));
    pc.addProperty("readErrors", diagTable.getEntry("can/pc/readErrors").getDouble(Double.NaN));
    pc.addProperty("lastFrameAgeSec", diagTable.getEntry("can/pc/lastFrameAgeSec").getDouble(Double.NaN));

    JsonObject summary = buildPcDeviceSummaryJson(nowMs);
    pc.add("deviceSummary", summary);
    return pc;
  }

  private JsonObject buildPcDeviceSummaryJson(long nowMs) {
    // Derived summary: missing count, flapping count, seen-not-local.
    ArrayList<DeviceSpec> allSpecs = new ArrayList<>();
    Collections.addAll(allSpecs, buildDeviceSpecs());
    Collections.addAll(allSpecs, findUnknownDeviceSpecs());

    int missingCount = 0;
    int flappingCount = 0;
    JsonArray seenNotLocal = new JsonArray();

    for (DeviceSpec spec : allSpecs) {
      String key = spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId;
      String base = "dev/" + spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId;
      String status = diagTable.getEntry(base + "/status").getString("UNKNOWN");
      double lastSeen = diagTable.getEntry(base + "/lastSeen").getDouble(Double.NaN);
      double ageSec = diagTable.getEntry(base + "/ageSec").getDouble(Double.NaN);

      if ("MISSING".equals(status) || "NO_DATA".equals(status)) {
        missingCount++;
      }

      String prev = pcLastStatus.get(key);
      if (prev != null && !prev.equals(status)) {
        int flaps = pcStatusFlaps.getOrDefault(key, 0) + 1;
        pcStatusFlaps.put(key, flaps);
        pcLastStatusChangeMs.put(key, nowMs);
      }
      pcLastStatus.put(key, status);

      int flaps = pcStatusFlaps.getOrDefault(key, 0);
      if (flaps > 0) {
        flappingCount++;
      }

      boolean localPresent = core.isDeviceInstantiated(spec.manufacturer, spec.deviceType, spec.deviceId);
      if (!Double.isNaN(lastSeen) && lastSeen > 0 && !localPresent) {
        JsonObject entry = new JsonObject();
        entry.addProperty("key", key);
        if (!Double.isNaN(ageSec)) {
          entry.addProperty("ageSec", ageSec);
        }
        seenNotLocal.add(entry);
      }
    }

    JsonObject summary = new JsonObject();
    summary.addProperty("missingCount", missingCount);
    summary.addProperty("totalCount", allSpecs.size());
    summary.addProperty("flappingCount", flappingCount);
    summary.add("seenNotLocal", seenNotLocal);
    return summary;
  }

  private void appendPcToolSection(StringBuilder sb) {
    // Human-readable PC tool status block.
    ReportTextUtil.appendLine(sb, "PC Tool:");
    long nowMs = System.currentTimeMillis();

    NetworkTableEntry heartbeatEntry = diagTable.getEntry("can/pc/heartbeat");
    double heartbeat = heartbeatEntry.getDouble(Double.NaN);
    String heartbeatAgeText;
    if (Double.isNaN(heartbeat)) {
      heartbeatAgeText = "STALE (no data)";
    } else {
      if (heartbeat != lastPcHeartbeat) {
        lastPcHeartbeat = heartbeat;
        lastPcHeartbeatMs = nowMs;
      }
      double ageSec = (nowMs - lastPcHeartbeatMs) / 1000.0;
      heartbeatAgeText = String.format("%.2fs", ageSec);
    }

    NetworkTableEntry openEntry = diagTable.getEntry("can/pc/openOk");
    String openOkText = formatPcBoolean(openEntry);
    boolean pcOk = !Double.isNaN(heartbeat) && "YES".equals(openOkText);
    if (!pcOk) {
      ReportTextUtil.appendLine(sb, "  Status: PC tool not connected");
    } else {
      ReportTextUtil.appendLine(sb, "  Status: OK");
    }

    double fps = diagTable.getEntry("can/pc/framesPerSec").getDouble(Double.NaN);
    double total = diagTable.getEntry("can/pc/framesTotal").getDouble(Double.NaN);
    double readErrors = diagTable.getEntry("can/pc/readErrors").getDouble(Double.NaN);
    double lastFrameAge = diagTable.getEntry("can/pc/lastFrameAgeSec").getDouble(Double.NaN);

    ReportTextUtil.appendLine(sb, "  Heartbeat age: " + heartbeatAgeText);
    ReportTextUtil.appendLine(sb, "  Open OK: " + openOkText);
    ReportTextUtil.appendLine(sb, "  Frames/sec: " + formatDoubleOrDash(fps, 1));
    ReportTextUtil.appendLine(sb, "  Frames total: " + formatDoubleOrDash(total, 0));
    ReportTextUtil.appendLine(sb, "  Read errors: " + formatDoubleOrDash(readErrors, 0));
    ReportTextUtil.appendLine(sb, "  Last frame age: " + formatDoubleOrDash(lastFrameAge, 2) + "s");

    appendPcDeviceSummary(sb, nowMs);
  }

  private void appendPcDeviceSummary(StringBuilder sb, long nowMs) {
    // Derived summary for console: missing, flapping, seen-not-local.
    ArrayList<DeviceSpec> allSpecs = new ArrayList<>();
    Collections.addAll(allSpecs, buildDeviceSpecs());
    Collections.addAll(allSpecs, findUnknownDeviceSpecs());

    int missingCount = 0;
    int flappingCount = 0;
    ArrayList<String> seenNotLocal = new ArrayList<>();

    for (DeviceSpec spec : allSpecs) {
      String key = spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId;
      String base = "dev/" + spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId;
      String status = diagTable.getEntry(base + "/status").getString("UNKNOWN");
      double lastSeen = diagTable.getEntry(base + "/lastSeen").getDouble(Double.NaN);
      double ageSec = diagTable.getEntry(base + "/ageSec").getDouble(Double.NaN);

      if ("MISSING".equals(status) || "NO_DATA".equals(status)) {
        missingCount++;
      }

      String prev = pcLastStatus.get(key);
      if (prev != null && !prev.equals(status)) {
        int flaps = pcStatusFlaps.getOrDefault(key, 0) + 1;
        pcStatusFlaps.put(key, flaps);
        pcLastStatusChangeMs.put(key, nowMs);
      }
      pcLastStatus.put(key, status);

      int flaps = pcStatusFlaps.getOrDefault(key, 0);
      if (flaps > 0) {
        flappingCount++;
      }

      boolean localPresent = core.isDeviceInstantiated(spec.manufacturer, spec.deviceType, spec.deviceId);
      if (!Double.isNaN(lastSeen) && lastSeen > 0 && !localPresent) {
        String ageText = Double.isNaN(ageSec) ? "?" : String.format("%.2f", ageSec);
        seenNotLocal.add(key + " age=" + ageText + "s");
      }
    }

    ReportTextUtil.appendLine(sb, "  Missing devices (PC): " + missingCount + " / " + allSpecs.size());
    ReportTextUtil.appendLine(sb, "  Flapping devices (PC): " + flappingCount);
    if (!seenNotLocal.isEmpty()) {
      ReportTextUtil.appendLine(sb, "  Seen on wire, not local: " + String.join(", ", seenNotLocal));
    }
  }

  private void printNetworkDeviceTable(
      StringBuilder sb,
      java.util.List<DeviceSpec> specs,
      double nowSeconds) {
    ArrayList<DeviceRow> rows = new ArrayList<>();
    String idHeaderLong = "id";
    String labelHeaderLong = "label";
    String mfgHeaderLong = "mfg";
    String typeHeaderLong = "type";
    String statusHeaderLong = "status";
    String ageHeaderLong = "ageSec";
    String fpsHeaderLong = "fps";
    String msgHeaderLong = "msgCount";
    int idWidth = 3;
    int labelWidth = 20;
    int mfgIdWidth = 12;
    int typeIdWidth = 16;
    int statusWidth = 8;
    int ageWidth = 6;
    int fpsWidth = 6;
    int msgWidth = 16;
    int maxLineWidth = 120;

    // Build rows first so we can compute column widths and wrap lines.
    for (DeviceSpec spec : specs) {
      DeviceRow row = loadDeviceRow(spec, nowSeconds);
      rows.add(row);
    }

    ReportTextUtil.appendWrappedHeaders(
        sb,
        new String[] { idHeaderLong, labelHeaderLong, mfgHeaderLong, typeHeaderLong,
            statusHeaderLong, ageHeaderLong, fpsHeaderLong, msgHeaderLong },
        null,
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth,
        maxLineWidth);

    for (DeviceRow row : rows) {
      ReportTextUtil.appendWrappedRow(
          sb,
          new String[] {
              Integer.toString(row.spec.deviceId),
              row.label,
              formatManufacturer(row.spec.manufacturer),
              formatDeviceType(row.spec.deviceType),
              row.status,
              row.ageText,
              row.fpsText,
              row.msgText
          },
          idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth,
          maxLineWidth);
    }
  }

  private DeviceRow loadDeviceRow(DeviceSpec spec, double nowSeconds) {
    // Pull PC tool data for each device and compute age/fps values.
    String base = "dev/" + spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId;
    String label = diagTable.getEntry(base + "/label").getString(spec.label);
    String status = diagTable.getEntry(base + "/status").getString("UNKNOWN");
    double age = diagTable.getEntry(base + "/ageSec").getDouble(Double.NaN);
    double msgCount = diagTable.getEntry(base + "/msgCount").getDouble(Double.NaN);
    double lastSeen = diagTable.getEntry(base + "/lastSeen").getDouble(Double.NaN);

    boolean hasData = !(Double.isNaN(lastSeen) || lastSeen < 0);
    String ageText = "-";
    String fpsText = "-";
    String msgText = "-";
    String finalStatus = hasData ? status : "NO_DATA";
    if (hasData) {
      double ageValue = Double.isNaN(age) ? (nowSeconds - lastSeen) : age;
      ageText = String.format("%.3f", ageValue);
      msgText = Double.isNaN(msgCount) ? "?" : String.format("%.0f", msgCount);
      fpsText = formatFps(spec, msgCount, nowSeconds);
    }

    return new DeviceRow(
        spec,
        label,
        finalStatus,
        ageText,
        fpsText,
        msgText);
  }

  private String formatFps(DeviceSpec spec, double msgCount, double nowSeconds) {
    // Compute fps from message count deltas between prints.
    if (Double.isNaN(msgCount)) {
      return "?";
    }
    String key = spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId;
    Double prevCount = prevMsgCount.get(key);
    Double prevTime = prevMsgTime.get(key);
    prevMsgCount.put(key, msgCount);
    prevMsgTime.put(key, nowSeconds);
    if (prevCount == null || prevTime == null) {
      return "-";
    }
    double dt = nowSeconds - prevTime;
    double delta = msgCount - prevCount;
    if (dt <= 0.0 || delta < 0.0) {
      return "-";
    }
    return String.format("%.1f", delta / dt);
  }

  private static String formatManufacturer(int manufacturer) {
    String name = MANUFACTURER_NAMES.get(manufacturer);
    if (name == null) {
      return Integer.toString(manufacturer);
    }
    return name + " (" + manufacturer + ")";
  }

  private static String formatDeviceType(int deviceType) {
    String name = DEVICE_TYPE_NAMES.get(deviceType);
    if (name == null) {
      return Integer.toString(deviceType);
    }
    return name + " (" + deviceType + ")";
  }

  private static Map<Integer, String> loadManufacturerNames() {
    // Load friendly names from can_mappings.json with a fallback map.
    Map<Integer, String> fallback = new HashMap<>();
    fallback.put(1, "NI");
    fallback.put(4, "CTRE");
    fallback.put(5, "REV");
    fallback.put(9, "Kauai");
    fallback.put(11, "PWF");
    return loadCanMapSection("manufacturers", fallback);
  }

  private static Map<Integer, String> loadDeviceTypeNames() {
    // Load friendly names from can_mappings.json with a fallback map.
    Map<Integer, String> fallback = new HashMap<>();
    fallback.put(2, "Motor");
    fallback.put(4, "Gyro");
    fallback.put(7, "Encoder");
    fallback.put(8, "PDM");
    return loadCanMapSection("device_types", fallback);
  }

  private static Map<Integer, String> loadCanMapSection(String key, Map<Integer, String> fallback) {
    // Read can_mappings.json (deploy or local) for display names.
    Path path = resolveCanMapPath();
    if (path == null || !Files.exists(path)) {
      return fallback;
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      JsonObject root = GSON.fromJson(reader, JsonObject.class);
      if (root == null || !root.has(key) || !root.get(key).isJsonObject()) {
        return fallback;
      }
      JsonObject section = root.getAsJsonObject(key);
      Map<Integer, String> result = new HashMap<>(fallback);
      for (Map.Entry<String, JsonElement> entry : section.entrySet()) {
        String name = entry.getKey();
        if (name == null || name.isBlank()) {
          continue;
        }
        String value = entry.getValue().getAsString();
        try {
          int id = Integer.parseInt(name);
          result.put(id, value);
        } catch (NumberFormatException ignored) {
          // skip invalid keys
        }
      }
      return Collections.unmodifiableMap(result);
    } catch (IOException | RuntimeException ex) {
      return fallback;
    }
  }

  private static Path resolveCanMapPath() {
    // Prefer deploy directory; fall back to repo path for local dev.
    try {
      Path deployPath = Filesystem.getDeployDirectory().toPath().resolve(CAN_MAP_FILE);
      if (Files.exists(deployPath)) {
        return deployPath;
      }
    } catch (Exception ex) {
      // Fall through to local dev path.
    }
    Path devPath = Path.of("src", "main", "deploy", CAN_MAP_FILE);
    if (Files.exists(devPath)) {
      return devPath;
    }
    return Path.of(CAN_MAP_FILE);
  }

  private DeviceSpec[] findUnknownDeviceSpecs() {
    // Any device published by the PC tool but not in our profile is "unknown".
    java.util.HashSet<String> known = new java.util.HashSet<>();
    for (DeviceSpec spec : buildDeviceSpecs()) {
      known.add(spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId);
    }

    ArrayList<DeviceSpec> unknowns = new ArrayList<>();
    NetworkTable devTable = diagTable.getSubTable("dev");
    for (String mfgName : devTable.getSubTables()) {
      int mfg = parseIntOrDefault(mfgName, -1);
      NetworkTable mfgTable = devTable.getSubTable(mfgName);
      for (String typeName : mfgTable.getSubTables()) {
        int type = parseIntOrDefault(typeName, -1);
        NetworkTable typeTable = mfgTable.getSubTable(typeName);
        for (String idName : typeTable.getSubTables()) {
          int id = parseIntOrDefault(idName, -1);
          if (mfg < 0 || type < 0 || id < 0) {
            continue;
          }
          String key = mfg + "/" + type + "/" + id;
          if (!known.contains(key)) {
            unknowns.add(new DeviceSpec("UNKNOWN", mfg, type, id));
          }
        }
      }
    }
    return unknowns.toArray(new DeviceSpec[0]);
  }

  private static int parseIntOrDefault(String value, int fallback) {
    try {
      return Integer.parseInt(value);
    } catch (NumberFormatException ex) {
      return fallback;
    }
  }

  private static DeviceSpec[] buildDeviceSpecs() {
    // Build the expected device list from the active profile.
    int[] neoIds = BringupUtil.filterCanIds(BringupUtil.NEO_CAN_IDS);
    int[] flexIds = BringupUtil.filterCanIds(BringupUtil.FLEX_CAN_IDS);
    int[] krakenIds = BringupUtil.filterCanIds(BringupUtil.KRAKEN_CAN_IDS);
    int[] falconIds = BringupUtil.filterCanIds(BringupUtil.FALCON_CAN_IDS);
    int[] cancoderIds = BringupUtil.filterCanIds(BringupUtil.CANCODER_CAN_IDS);
    int total = neoIds.length
        + flexIds.length
        + krakenIds.length
        + falconIds.length
        + cancoderIds.length;
    if (BringupUtil.isEnabledCanId(BringupUtil.PDH_CAN_ID)) {
      total += 1;
    }
    if (BringupUtil.isEnabledCanId(BringupUtil.PIGEON_CAN_ID)) {
      total += 1;
    }
    if (BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)) {
      total += 1;
    }
    DeviceSpec[] specs = new DeviceSpec[total];
    int i = 0;
    for (int id : neoIds) {
      specs[i++] = new DeviceSpec("NEO", REV_MANUFACTURER, TYPE_MOTOR_CONTROLLER, id);
    }
    for (int id : flexIds) {
      specs[i++] = new DeviceSpec("FLEX", REV_MANUFACTURER, TYPE_MOTOR_CONTROLLER, id);
    }
    for (int id : krakenIds) {
      specs[i++] = new DeviceSpec("KRAKEN", CTRE_MANUFACTURER, TYPE_MOTOR_CONTROLLER, id);
    }
    for (int id : falconIds) {
      specs[i++] = new DeviceSpec("FALCON", CTRE_MANUFACTURER, TYPE_MOTOR_CONTROLLER, id);
    }
    for (int id : cancoderIds) {
      specs[i++] = new DeviceSpec("CANCoder", CTRE_MANUFACTURER, TYPE_ENCODER, id);
    }
    if (BringupUtil.isEnabledCanId(BringupUtil.PDH_CAN_ID)) {
      specs[i++] =
          new DeviceSpec("PDH", REV_MANUFACTURER, TYPE_POWER_DISTRIBUTION_MODULE, BringupUtil.PDH_CAN_ID);
    }
    if (BringupUtil.isEnabledCanId(BringupUtil.PIGEON_CAN_ID)) {
      specs[i++] =
          new DeviceSpec("Pigeon", CTRE_MANUFACTURER, TYPE_GYRO_SENSOR, BringupUtil.PIGEON_CAN_ID);
    }
    if (BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)) {
      specs[i++] =
          new DeviceSpec("roboRIO", NI_MANUFACTURER, TYPE_ROBOT_CONTROLLER, BringupUtil.ROBORIO_CAN_ID);
    }
    return specs;
  }

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

  private static String formatDoubleOrDash(double value, int decimals) {
    // Normalize invalid values for a cleaner table.
    if (Double.isNaN(value) || Double.isInfinite(value) || value < 0.0) {
      return "-";
    }
    String fmt = "%." + decimals + "f";
    return String.format(fmt, value);
  }

  private static final class DeviceSpec {
    private final String label;
    private final int manufacturer;
    private final int deviceType;
    private final int deviceId;

    private DeviceSpec(String label, int manufacturer, int deviceType, int deviceId) {
      this.label = label;
      this.manufacturer = manufacturer;
      this.deviceType = deviceType;
      this.deviceId = deviceId;
    }
  }

  private static final class DeviceRow {
    private final DeviceSpec spec;
    private final String label;
    private final String status;
    private final String ageText;
    private final String fpsText;
    private final String msgText;

    private DeviceRow(
        DeviceSpec spec,
        String label,
        String status,
        String ageText,
        String fpsText,
        String msgText) {
      this.spec = spec;
      this.label = label;
      this.status = status;
      this.ageText = ageText;
      this.fpsText = fpsText;
      this.msgText = msgText;
    }
  }
}
