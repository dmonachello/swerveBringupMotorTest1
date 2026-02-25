package frc.robot;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import edu.wpi.first.wpilibj.Filesystem;
import edu.wpi.first.wpilibj.RobotController;
import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
import edu.wpi.first.wpilibj.livewindow.LiveWindow;
import edu.wpi.first.wpilibj.shuffleboard.Shuffleboard;
import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableEntry;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.networktables.NetworkTableValue;

public class RobotV2 extends TimedRobot {

  // ---------------- CAN ID DEFINITIONS ----------------
  private static final double DEADBAND = BringupUtil.DEADBAND;
  // ---------------------------------------------------

  private static final int REV_MANUFACTURER = 5;
  private static final int CTRE_MANUFACTURER = 4;
  private static final int NI_MANUFACTURER = 1;
  private static final int TYPE_MOTOR_CONTROLLER = 2;
  private static final int TYPE_GYRO_SENSOR = 4;
  private static final int TYPE_ENCODER = 7;
  private static final int TYPE_POWER_DISTRIBUTION_MODULE = 8;
  private static final String REPORT_PATH = "/home/lvuser/bringup_report.json";
  private static final int TYPE_ROBOT_CONTROLLER = 1;

  private static final String CAN_MAP_FILE = "can_mappings.json";
  private static final Gson GSON = new Gson();
  private static final Map<Integer, String> MANUFACTURER_NAMES = loadManufacturerNames();
  private static final Map<Integer, String> DEVICE_TYPE_NAMES = loadDeviceTypeNames();

  private final XboxController controller = new XboxController(0);
  private BringupCore core = new BringupCore();
  private final NetworkTable diagTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("diag");
  private boolean prevDiag = false;
  private boolean prevBindings = false;
  private boolean prevProfileToggle = false;
  private boolean prevSpeedPrint = false;
  private boolean prevNudge = false;
  private boolean prevCanDiag = false;
  private boolean prevReportDump = false;
  private boolean prevDashboardToggle = false;
  private boolean dashboardUpdatesEnabled = false;
  private final Map<String, Double> prevMsgCount = new HashMap<>();
  private final Map<String, Double> prevMsgTime = new HashMap<>();
  private double lastPcHeartbeat = Double.NaN;
  private long lastPcHeartbeatMs = 0L;
  private final Map<String, String> pcLastStatus = new HashMap<>();
  private final Map<String, Integer> pcStatusFlaps = new HashMap<>();
  private final Map<String, Long> pcLastStatusChangeMs = new HashMap<>();
  private final CanHealthMonitor canHealth = new CanHealthMonitor();
  private static final long MIN_PRINT_INTERVAL_MS = 1000;
  private long lastStartupPrintMs = 0L;
  private long lastNetworkPrintMs = 0L;
  private long lastCanDiagPrintMs = 0L;

  @Override
  public void robotInit() {
    BringupUtil.applyProfileFromArgs();
    applyDashboardUpdateState();
    printStartupInfo();
    validateCanIds();
  }

  @Override
  public void teleopInit() {
    core.resetState();
    prevDiag = false;
    prevBindings = false;
    prevProfileToggle = false;
    prevSpeedPrint = false;
    prevNudge = false;
    prevCanDiag = false;
    prevReportDump = false;
    prevDashboardToggle = false;
  }

  @Override
  public void disabledInit() {
    core.resetState();
    prevDiag = false;
    prevBindings = false;
    prevProfileToggle = false;
    prevSpeedPrint = false;
    prevNudge = false;
    prevCanDiag = false;
    prevReportDump = false;
    prevDashboardToggle = false;
  }

  @Override
  public void robotPeriodic() {
    canHealth.update();
  }

  @Override
  public void teleopPeriodic() {

    core.handleAdd(controller.getAButton());
    core.handleAddAll(controller.getStartButton());
    core.handlePrint(controller.getBButton());
    boolean healthNow = controller.getPOV() == 270;
    core.handleHealth(healthNow);
    core.handleCANCoder(controller.getRightBumperButton());

    boolean profileToggleNow = controller.getBackButton();
    if (profileToggleNow && !prevProfileToggle) {
      BringupUtil.toggleCanProfile();
      core.resetState();
      core = new BringupCore();
      validateCanIds();
      printStartupInfo();
    }
    prevProfileToggle = profileToggleNow;

    // D-pad Down: print NetworkTables diagnostics
    boolean diagNow = controller.getPOV() == 180;
    if (diagNow && !prevDiag) {
      printNetworkDiagnostics();
    }
    prevDiag = diagNow;

    boolean bindingsNow = controller.getLeftBumperButton();
    if (bindingsNow && !prevBindings) {
      printStartupInfo();
    }
    prevBindings = bindingsNow;

    boolean canDiagNow = controller.getPOV() == 0;
    if (canDiagNow && !prevCanDiag) {
      printCanDiagnosticsReport();
    }
    prevCanDiag = canDiagNow;

    boolean dashboardToggleNow = controller.getYButton();
    if (dashboardToggleNow && !prevDashboardToggle) {
      dashboardUpdatesEnabled = !dashboardUpdatesEnabled;
      applyDashboardUpdateState();
      BringupPrinter.enqueue(
          "Dashboard/Shuffleboard updates: " + (dashboardUpdatesEnabled ? "ON" : "OFF"));
    }
    prevDashboardToggle = dashboardToggleNow;

    double neoSpeed = BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
    double krakenSpeed = BringupUtil.deadband(-controller.getRightY(), DEADBAND);

    boolean speedPrintNow = controller.getPOV() == 90;
    if (speedPrintNow && !prevSpeedPrint) {
      BringupPrinter.enqueue(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")");
    }
    prevSpeedPrint = speedPrintNow;

    boolean nudgeNow = controller.getLeftStickButton();
    if (nudgeNow && !prevNudge) {
      core.triggerNudge(0.2, 0.5);
      BringupPrinter.enqueue("Nudge: 0.2 for 0.5s (all motors)");
    }
    prevNudge = nudgeNow;

    boolean reportDumpNow = controller.getXButton();
    if (reportDumpNow && !prevReportDump) {
      dumpReportJsonToConsoleAndFile();
    }
    prevReportDump = reportDumpNow;

    core.setSpeeds(neoSpeed, krakenSpeed);
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  private void printStartupInfo() {
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastStartupPrintMs < MIN_PRINT_INTERVAL_MS) {
      return;
    }
    lastStartupPrintMs = nowMs;
    StringBuilder sb = new StringBuilder(512);
    appendLine(sb, "=== Swerve Bringup V2 ===");
    appendLine(sb, "A: add motor (alternates SPARK/CTRE)");
    appendLine(sb, "Start: add all motors + CANCoders");
    appendLine(sb, "B: print state");
    appendLine(sb, "D-pad Left: print health status");
    appendLine(sb, "Right Bumper: print CANCoder absolute positions");
    appendLine(sb, "Back: toggle CAN profile");
    appendLine(sb, "D-pad Down: print NetworkTables diagnostics");
    appendLine(sb, "Left Bumper: reprint bindings");
    appendLine(sb, "D-pad Up: print CAN diagnostics report");
    appendLine(sb, "D-pad Right: print speed inputs");
    appendLine(sb, "Left Stick: nudge motors (0.2 for 0.5s)");
    appendLine(sb, "X: dump CAN report JSON");
    appendLine(sb, "Y: toggle dashboard/shuffleboard updates");
    appendLine(sb, "Left Y: NEO/FLEX speed, Right Y: KRAKEN/FALCON speed");
    appendLine(sb, "Deadband: " + DEADBAND);
    appendLine(sb, "Dashboard updates: " + (dashboardUpdatesEnabled ? "ON" : "OFF"));
    appendLine(sb, "CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    appendLine(sb, "NEO CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO_CAN_IDS));
    appendLine(sb, "FLEX CAN IDs: " + BringupUtil.joinIds(BringupUtil.FLEX_CAN_IDS));
    appendLine(sb, "KRAKEN CAN IDs: " + BringupUtil.joinIds(BringupUtil.KRAKEN_CAN_IDS));
    appendLine(sb, "FALCON CAN IDs: " + BringupUtil.joinIds(BringupUtil.FALCON_CAN_IDS));
    appendLine(sb, "=========================");
    enqueueBlockChunked(sb, 12);
  }

  private void printNetworkDiagnostics() {
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastNetworkPrintMs < MIN_PRINT_INTERVAL_MS) {
      return;
    }
    lastNetworkPrintMs = nowMs;
    enqueueNetworkDiagnosticsReport();
  }

  private void printCanDiagnosticsReport() {
    long nowMs = System.currentTimeMillis();
    if (nowMs - lastCanDiagPrintMs < MIN_PRINT_INTERVAL_MS) {
      return;
    }
    lastCanDiagPrintMs = nowMs;
    enqueueCanDiagnosticsReport();
  }

  private void applyDashboardUpdateState() {
    setNetworkTablesFlushEnabled(dashboardUpdatesEnabled);
    LiveWindow.setEnabled(dashboardUpdatesEnabled);
    if (dashboardUpdatesEnabled) {
      Shuffleboard.enableActuatorWidgets();
    } else {
      Shuffleboard.disableActuatorWidgets();
    }
  }

  private void enqueueNetworkDiagnosticsReport() {
    StringBuilder sb = new StringBuilder(1024);
    appendLine(sb, "=== Bringup NetworkTables (CAN Bus via PC Tool) ===");
    double nowSeconds = System.currentTimeMillis() / 1000.0;

    double busErrors = diagTable.getEntry("busErrorCount").getDouble(Double.NaN);
    if (!Double.isNaN(busErrors)) {
      appendLine(sb, "Bus error count: " + (long) busErrors);
    }

    appendLine(sb, "Devices:");
    java.util.ArrayList<DeviceSpec> allSpecs = new java.util.ArrayList<>();
    java.util.Collections.addAll(allSpecs, buildDeviceSpecs());
    java.util.Collections.addAll(allSpecs, findUnknownDeviceSpecs());
    printNetworkDeviceTable(sb, allSpecs, nowSeconds);
    appendLine(sb, "=============================");
    enqueueBlockChunked(sb, 12);
  }

  private void enqueueCanDiagnosticsReport() {
    StringBuilder sb = new StringBuilder(1024);
    appendLine(sb, "=== CAN Diagnostics Report ===");
    appendLine(sb, buildSummaryLine());
    canHealth.appendSnapshot(sb);
    canHealth.appendReportSection(sb);
    appendPcToolSection(sb);
    core.appendDeviceDiagnosticsReport(sb);
    appendLine(sb, "==============================");
    enqueueBlockChunked(sb, 12);
  }

  private void dumpReportJsonToConsoleAndFile() {
    String json = buildReportJson();
    BringupPrinter.enqueueChunked(wrapLongLine(json, 120), 12);
    try {
      java.nio.file.Files.writeString(java.nio.file.Path.of(REPORT_PATH), json);
      BringupPrinter.enqueue("Wrote CAN report JSON to " + REPORT_PATH);
    } catch (Exception ex) {
      BringupPrinter.enqueue("Failed to write CAN report JSON: " + ex.getMessage());
    }
  }

  private String buildSummaryLine() {
    String bus = canHealth.summaryStatus();
    String pc = buildPcSummaryStatus();
    return "Summary: bus=" + bus + " pc=" + pc;
  }

  private String buildPcSummaryStatus() {
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
    java.util.ArrayList<DeviceSpec> allSpecs = new java.util.ArrayList<>();
    java.util.Collections.addAll(allSpecs, buildDeviceSpecs());
    java.util.Collections.addAll(allSpecs, findUnknownDeviceSpecs());

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
    appendLine(sb, "PC Tool:");
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
      appendLine(sb, "  Status: PC tool not connected");
    } else {
      appendLine(sb, "  Status: OK");
    }

    double fps = diagTable.getEntry("can/pc/framesPerSec").getDouble(Double.NaN);
    double total = diagTable.getEntry("can/pc/framesTotal").getDouble(Double.NaN);
    double readErrors = diagTable.getEntry("can/pc/readErrors").getDouble(Double.NaN);
    double lastFrameAge = diagTable.getEntry("can/pc/lastFrameAgeSec").getDouble(Double.NaN);

    appendLine(sb, "  Heartbeat age: " + heartbeatAgeText);
    appendLine(sb, "  Open OK: " + openOkText);
    appendLine(sb, "  Frames/sec: " + formatDoubleOrDash(fps, 1));
    appendLine(sb, "  Frames total: " + formatDoubleOrDash(total, 0));
    appendLine(sb, "  Read errors: " + formatDoubleOrDash(readErrors, 0));
    appendLine(sb, "  Last frame age: " + formatDoubleOrDash(lastFrameAge, 2) + "s");

    appendPcDeviceSummary(sb, nowMs);
  }

  private void appendPcDeviceSummary(StringBuilder sb, long nowMs) {
    java.util.ArrayList<DeviceSpec> allSpecs = new java.util.ArrayList<>();
    java.util.Collections.addAll(allSpecs, buildDeviceSpecs());
    java.util.Collections.addAll(allSpecs, findUnknownDeviceSpecs());

    int missingCount = 0;
    int flappingCount = 0;
    java.util.ArrayList<String> seenNotLocal = new java.util.ArrayList<>();

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

    appendLine(sb, "  Missing devices (PC): " + missingCount + " / " + allSpecs.size());
    appendLine(sb, "  Flapping devices (PC): " + flappingCount);
    if (!seenNotLocal.isEmpty()) {
      appendLine(sb, "  Seen on wire, not local: " + String.join(", ", seenNotLocal));
    }
  }

  private static String formatPcBoolean(NetworkTableEntry entry) {
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
    if (Double.isNaN(value) || Double.isInfinite(value) || value < 0.0) {
      return "-";
    }
    String fmt = "%." + decimals + "f";
    return String.format(fmt, value);
  }

  private void printNetworkDeviceTable(
      StringBuilder sb,
      java.util.List<DeviceSpec> specs,
      double nowSeconds) {
    java.util.ArrayList<DeviceRow> rows = new java.util.ArrayList<>();
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

    for (DeviceSpec spec : specs) {
      DeviceRow row = loadDeviceRow(spec, nowSeconds);
      rows.add(row);

    }

    appendWrappedHeaders(
        sb,
        new String[] { idHeaderLong, labelHeaderLong, mfgHeaderLong, typeHeaderLong,
            statusHeaderLong, ageHeaderLong, fpsHeaderLong, msgHeaderLong },
        null,
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth,
        maxLineWidth);

    for (DeviceRow row : rows) {
      appendWrappedRow(
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

  private static void appendWrappedHeaders(
      StringBuilder sb,
      String[] headerShort,
      String[] headerLong,
      int idWidth,
      int labelWidth,
      int mfgIdWidth,
      int typeIdWidth,
      int statusWidth,
      int ageWidth,
      int fpsWidth,
      int msgWidth,
      int maxLineWidth) {
    appendLine(sb, buildHeaderLine(
        headerShort,
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth,
        maxLineWidth));
    if (headerLong != null) {
      appendLine(sb, buildHeaderLine(
          headerLong,
          idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth,
          maxLineWidth));
    }
    appendLine(sb, "-".repeat(maxLineWidth));
  }

  private static String buildHeaderLine(
      String[] values,
      int idWidth,
      int labelWidth,
      int mfgIdWidth,
      int typeIdWidth,
      int statusWidth,
      int ageWidth,
      int fpsWidth,
      int msgWidth,
      int maxLineWidth) {
    int[] widths = new int[] {
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth
    };
    StringBuilder row = new StringBuilder(maxLineWidth);
    for (int col = 0; col < values.length; col++) {
      String value = values[col] == null ? "" : values[col];
      if (value.length() > widths[col]) {
        value = truncate(value, widths[col]);
      }
      String padded = padRight(value, widths[col], '.');
      if (col > 0) {
        row.append(' ');
      }
      row.append(padded);
    }
    String rowText = row.toString();
    if (rowText.length() > maxLineWidth) {
      rowText = rowText.substring(0, maxLineWidth);
    }
    return rowText;
  }

  private static void appendWrappedRow(
      StringBuilder sb,
      String[] values,
      int idWidth,
      int labelWidth,
      int mfgIdWidth,
      int typeIdWidth,
      int statusWidth,
      int ageWidth,
      int fpsWidth,
      int msgWidth,
      int maxLineWidth) {
    int[] widths = new int[] {
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth
    };
    String[][] columns = new String[values.length][];
    int maxLines = 1;
    for (int i = 0; i < values.length; i++) {
      columns[i] = wrapToLines(values[i], widths[i], 4);
      maxLines = Math.max(maxLines, columns[i].length);
    }

    for (int line = 0; line < maxLines; line++) {
      StringBuilder row = new StringBuilder(maxLineWidth);
      for (int col = 0; col < columns.length; col++) {
        String[] colLines = columns[col];
        String value = line < colLines.length ? colLines[line] : "";
        String padded = padRight(value, widths[col], '.');
        if (col > 0) {
          row.append(' ');
        }
        row.append(padded);
      }
      String rowText = row.toString();
      if (rowText.length() > maxLineWidth) {
        rowText = rowText.substring(0, maxLineWidth);
      }
      appendLine(sb, rowText);
    }
  }

  private static String padRight(String value, int width, char fill) {
    if (value == null) {
      value = "";
    }
    int missing = width - value.length();
    if (missing <= 0) {
      return value;
    }
    return value + repeatChar(fill, missing);
  }

  private static String repeatChar(char fill, int count) {
    if (count <= 0) {
      return "";
    }
    return String.valueOf(fill).repeat(count);
  }

  private static String truncate(String value, int width) {
    if (value == null) {
      return "";
    }
    if (value.length() <= width) {
      return value;
    }
    if (width <= 3) {
      return value.substring(0, width);
    }
    return value.substring(0, width - 3) + "...";
  }

  private static String[] wrapToLines(String value, int width, int maxLines) {
    if (value == null) {
      value = "";
    }
    if (width <= 0) {
      return new String[] { "" };
    }
    int maxChars = width * maxLines;
    String trimmed = value.length() > maxChars
        ? truncate(value, maxChars)
        : value;
    int lines = (int) Math.ceil(trimmed.length() / (double) width);
    lines = Math.min(lines, maxLines);
    String[] result = new String[lines == 0 ? 1 : lines];
    if (trimmed.isEmpty()) {
      result[0] = "";
      return result;
    }
    for (int i = 0; i < lines; i++) {
      int start = i * width;
      int end = Math.min(start + width, trimmed.length());
      result[i] = trimmed.substring(start, end);
    }
    return result;
  }

  private static void appendLine(StringBuilder sb, String line) {
    sb.append(line).append('\n');
  }

  private static String wrapLongLine(String value, int width) {
    if (value == null) {
      return "";
    }
    if (width <= 0 || value.length() <= width) {
      return value;
    }
    StringBuilder sb = new StringBuilder(value.length() + (value.length() / width) + 2);
    for (int i = 0; i < value.length(); i += width) {
      int end = Math.min(i + width, value.length());
      sb.append(value, i, end).append('\n');
    }
    return sb.toString();
  }

  // private void enqueueBlock(StringBuilder sb) {
  //   BringupPrinter.enqueue(sb.toString());
  // }

  private void enqueueBlockChunked(StringBuilder sb, int maxLines) {
    BringupPrinter.enqueueChunked(sb.toString(), maxLines);
  }


  private String formatFps(DeviceSpec spec, double msgCount, double nowSeconds) {
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
    Map<Integer, String> fallback = new HashMap<>();
    fallback.put(1, "NI");
    fallback.put(4, "CTRE");
    fallback.put(5, "REV");
    fallback.put(9, "Kauai");
    fallback.put(11, "PWF");
    return loadCanMapSection("manufacturers", fallback);
  }

  private static Map<Integer, String> loadDeviceTypeNames() {
    Map<Integer, String> fallback = new HashMap<>();
    fallback.put(2, "Motor");
    fallback.put(4, "Gyro");
    fallback.put(7, "Encoder");
    fallback.put(8, "PDM");
    return loadCanMapSection("device_types", fallback);
  }

  private static Map<Integer, String> loadCanMapSection(String key, Map<Integer, String> fallback) {
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
    java.util.HashSet<String> known = new java.util.HashSet<>();
    for (DeviceSpec spec : buildDeviceSpecs()) {
      known.add(spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId);
    }

    java.util.ArrayList<DeviceSpec> unknowns = new java.util.ArrayList<>();
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

  // Shared behavior moved to BringupCore.

  private static DeviceSpec[] buildDeviceSpecs() {
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

  private void validateCanIds() {
    ArrayList<String> labels = new ArrayList<>();
    ArrayList<int[]> groups = new ArrayList<>();

    labels.add("NEO");
    groups.add(BringupUtil.NEO_CAN_IDS);
    labels.add("FLEX");
    groups.add(BringupUtil.FLEX_CAN_IDS);
    labels.add("KRAKEN");
    groups.add(BringupUtil.KRAKEN_CAN_IDS);
    labels.add("FALCON");
    groups.add(BringupUtil.FALCON_CAN_IDS);
    labels.add("CANCoder");
    groups.add(BringupUtil.CANCODER_CAN_IDS);
    if (BringupUtil.isEnabledCanId(BringupUtil.PDH_CAN_ID)) {
      labels.add("PDH");
      groups.add(new int[] { BringupUtil.PDH_CAN_ID });
    }
    if (BringupUtil.isEnabledCanId(BringupUtil.PIGEON_CAN_ID)) {
      labels.add("Pigeon");
      groups.add(new int[] { BringupUtil.PIGEON_CAN_ID });
    }
    if (BringupUtil.isEnabledCanId(BringupUtil.ROBORIO_CAN_ID)) {
      labels.add("roboRIO");
      groups.add(new int[] { BringupUtil.ROBORIO_CAN_ID });
    }

    BringupUtil.validateCanIds(
        labels.toArray(new String[0]),
        groups.toArray(new int[0][]));
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

  private static final class CanHealthMonitor {
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

    void update() {
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
        BringupPrinter.enqueue("[CAN] BUS OFF event detected! Check wiring/termination/noise.");
        lastLogMs = nowMs;
      }

      if (nowHighUtil && (!wasHighUtil || logDue)) {
        BringupPrinter.enqueue(String.format("[CAN] High utilization: %.1f%%", utilizationPct));
        lastLogMs = nowMs;
      } else if (wasHighUtil && recoveredUtil) {
        BringupPrinter.enqueue(String.format("[CAN] Utilization recovered: %.1f%%", utilizationPct));
        lastLogMs = nowMs;
      }

      if (errorSpike && logDue) {
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

    void appendReportSection(StringBuilder sb) {
      appendLine(sb, "Bus Health: (see CAN Bus Diagnostics summary above)");
    }

    void appendSnapshot(StringBuilder sb) {
      if (lastUpdateMs == 0) {
        appendLine(sb, "[CAN] No status samples yet.");
        return;
      }
      double ageSec = (System.currentTimeMillis() - lastUpdateMs) / 1000.0;
      appendLine(sb, "=== CAN Bus Diagnostics ===");
      appendLine(sb, String.format("Utilization: %.1f%%", lastUtilizationPct));
      appendLine(sb, String.format("RX errors: %d (delta %d)", lastRxErrors, lastRxDelta));
      appendLine(sb, String.format("TX errors: %d (delta %d)", lastTxErrors, lastTxDelta));
      appendLine(sb, String.format("TX full: %d (delta %d)", lastTxFullCount, lastTxFullDelta));
      appendLine(sb, String.format("Bus off count: %d (delta %d)", lastBusOffCount, lastBusOffDelta));
      appendLine(sb, String.format("Sample age: %.2fs", ageSec));
      appendLine(sb, "===========================");
    }

    String summaryStatus() {
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

    void appendSnapshotJson(JsonObject target) {
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
  }
}
