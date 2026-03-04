package frc.robot;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableEntry;
import edu.wpi.first.networktables.NetworkTableValue;
import edu.wpi.first.wpilibj.Filesystem;
import frc.robot.diag.report.ReportJsonBuilder;
import frc.robot.diag.report.ReportTextBuilder;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.PcSnapshot;
import frc.robot.diag.snapshots.SnapshotBundle;
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
    ArrayList<DeviceSpec> allSpecs = new ArrayList<>();
    Collections.addAll(allSpecs, buildDeviceSpecs());
    Collections.addAll(allSpecs, findUnknownDeviceSpecs());
    printNetworkDeviceTable(sb, allSpecs, nowSeconds);
    ReportTextUtil.appendLine(sb, "=============================");
    BringupPrinter.enqueueChunked(sb.toString(), 12);
  }

  private void enqueueCanDiagnosticsReport() {
    // Full text report with summary and device health.
    SnapshotBundle bundle = buildSnapshotBundle();
    String report = textBuilder.buildCanDiagnosticsReport(bundle);
    BringupPrinter.enqueueChunked(report, 12);
  }

  private String buildReportJson() {
    // JSON payload includes: timestamp, bus, pc, devices.
    SnapshotBundle bundle = buildSnapshotBundle();
    return jsonBuilder.buildReportJson(bundle);
  }

  private SnapshotBundle buildSnapshotBundle() {
    SnapshotBundle bundle = new SnapshotBundle();
    bundle.timestampSec = System.currentTimeMillis() / 1000.0;
    bundle.bus = canHealth.buildSnapshot();
    bundle.pc = buildPcSnapshot(System.currentTimeMillis());
    for (DeviceSnapshot snap : core.captureSnapshots()) {
      bundle.devices.add(snap);
    }
    return bundle;
  }

  private PcSnapshot buildPcSnapshot(long nowMs) {
    PcSnapshot pc = new PcSnapshot();
    pc.heartbeatAgeSec = getPcHeartbeatAgeSec(nowMs);

    NetworkTableEntry openEntry = diagTable.getEntry("can/pc/openOk");
    pc.openOk = "YES".equals(formatPcBoolean(openEntry));
    pc.framesPerSec = diagTable.getEntry("can/pc/framesPerSec").getDouble(Double.NaN);
    pc.framesTotal = diagTable.getEntry("can/pc/framesTotal").getDouble(Double.NaN);
    pc.readErrors = diagTable.getEntry("can/pc/readErrors").getDouble(Double.NaN);
    pc.lastFrameAgeSec = diagTable.getEntry("can/pc/lastFrameAgeSec").getDouble(Double.NaN);

    ArrayList<DeviceSpec> allSpecs = new ArrayList<>();
    Collections.addAll(allSpecs, buildDeviceSpecs());
    Collections.addAll(allSpecs, findUnknownDeviceSpecs());
    pc.totalCount = allSpecs.size();

    int missingCount = 0;
    int flappingCount = 0;
    Map<String, ArrayList<Integer>> unknownByType = collectUnknownSeenIdsByType();

    for (DeviceSpec spec : allSpecs) {
      String key = spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId;
      String base = "dev/" + spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId;
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
        entry.key = key;
        entry.ageSec = ageSec;
        pc.staleDevices.add(entry);
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
      String presenceSource = diagTable.getEntry(base + "/presenceSource").getString("NONE");
      double statusAge = diagTable.getEntry(base + "/statusAgeSec").getDouble(Double.NaN);
      boolean statusSeen = "STATUS".equals(presenceSource) && !Double.isNaN(statusAge) && statusAge >= 0;
      if (statusSeen && !localPresent) {
        PcSnapshot.SeenNotLocalEntry entry = new PcSnapshot.SeenNotLocalEntry();
        entry.key = key;
        if (!Double.isNaN(statusAge)) {
          entry.ageSec = statusAge;
        }
        pc.seenNotLocal.add(entry);
      }

      if (missing) {
        String typeKey = spec.manufacturer + "/" + spec.deviceType;
        ArrayList<Integer> candidates = unknownByType.get(typeKey);
        if (candidates != null && !candidates.isEmpty()) {
          PcSnapshot.ProfileMismatchEntry entry = new PcSnapshot.ProfileMismatchEntry();
          entry.expected = key;
          entry.seenIds.addAll(candidates);
          pc.profileMismatch.add(entry);
        }
      }
    }

    pc.missingCount = missingCount;
    pc.flappingCount = flappingCount;
    return pc;
  }

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
    String confHeaderLong = "conf";
    String ageHeaderLong = "ageSec";
    String fpsHeaderLong = "fps";
    String msgHeaderLong = "msgCount";
    int idWidth = 3;
    int labelWidth = 20;
    int mfgIdWidth = 12;
    int typeIdWidth = 16;
    int statusWidth = 8;
    int confWidth = 8;
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
            statusHeaderLong, confHeaderLong, ageHeaderLong, fpsHeaderLong, msgHeaderLong },
        null,
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, confWidth, ageWidth, fpsWidth,
        msgWidth, maxLineWidth);

    for (DeviceRow row : rows) {
      ReportTextUtil.appendWrappedRow(
          sb,
          new String[] {
              Integer.toString(row.spec.deviceId),
              row.label,
              formatManufacturer(row.spec.manufacturer),
              formatDeviceType(row.spec.deviceType),
              row.status,
              row.confidence,
              row.ageText,
              row.fpsText,
              row.msgText
          },
          idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, confWidth, ageWidth, fpsWidth,
          msgWidth, maxLineWidth);
    }
  }

  private DeviceRow loadDeviceRow(DeviceSpec spec, double nowSeconds) {
    // Pull PC tool data for each device and compute age/fps values.
    String base = "dev/" + spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId;
    String label = diagTable.getEntry(base + "/label").getString(spec.label);
    String status = diagTable.getEntry(base + "/status").getString("UNKNOWN");
    String confidence = diagTable.getEntry(base + "/presenceConfidence").getString("-");
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
    String finalStatus = hasData ? status : "NO_DATA";
    if (hasData) {
      double ageValue = age;
      if (Double.isNaN(ageValue)) {
        ageValue = !Double.isNaN(trafficAge) ? trafficAge : statusAge;
      }
      if (!Double.isNaN(ageValue)) {
        ageText = String.format("%.3f", ageValue);
      }
      msgText = Double.isNaN(msgCount) ? "?" : String.format("%.0f", msgCount);
      fpsText = formatFps(spec, msgCount, nowSeconds);
    }

    return new DeviceRow(
        spec,
        label,
        finalStatus,
        confidence,
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

  private Map<String, ArrayList<Integer>> collectUnknownSeenIdsByType() {
    // Collect unknown device IDs per (manufacturer/type) that the PC tool has seen on wire.
    java.util.HashSet<String> known = new java.util.HashSet<>();
    for (DeviceSpec spec : buildDeviceSpecs()) {
      known.add(spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId);
    }

    Map<String, ArrayList<Integer>> unknownByType = new HashMap<>();
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
          if (known.contains(key)) {
            continue;
          }
          double lastSeen = typeTable.getSubTable(idName).getEntry("lastSeen").getDouble(Double.NaN);
          if (Double.isNaN(lastSeen) || lastSeen <= 0) {
            continue;
          }
          String typeKey = mfg + "/" + type;
          unknownByType.computeIfAbsent(typeKey, k -> new ArrayList<>()).add(id);
        }
      }
    }
    return unknownByType;
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
    int[] neo550Ids = BringupUtil.filterCanIds(BringupUtil.NEO550_CAN_IDS);
    int[] flexIds = BringupUtil.filterCanIds(BringupUtil.FLEX_CAN_IDS);
    int[] krakenIds = BringupUtil.filterCanIds(BringupUtil.KRAKEN_CAN_IDS);
    int[] falconIds = BringupUtil.filterCanIds(BringupUtil.FALCON_CAN_IDS);
    int[] cancoderIds = BringupUtil.filterCanIds(BringupUtil.CANCODER_CAN_IDS);
    int total = neoIds.length
        + neo550Ids.length
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
    for (int id : neo550Ids) {
      specs[i++] = new DeviceSpec("NEO 550", REV_MANUFACTURER, TYPE_MOTOR_CONTROLLER, id);
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

  // private static String formatDoubleOrDash(double value, int decimals) {
  //   // Normalize invalid values for a cleaner table.
  //   if (Double.isNaN(value) || Double.isInfinite(value) || value < 0.0) {
  //     return "-";
  //   }
  //   String fmt = "%." + decimals + "f";
  //   return String.format(fmt, value);
  // }

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
    private final String confidence;
    private final String ageText;
    private final String fpsText;
    private final String msgText;

    private DeviceRow(
        DeviceSpec spec,
        String label,
        String status,
        String confidence,
        String ageText,
        String fpsText,
        String msgText) {
      this.spec = spec;
      this.label = label;
      this.status = status;
      this.confidence = confidence;
      this.ageText = ageText;
      this.fpsText = fpsText;
      this.msgText = msgText;
    }
  }
}
