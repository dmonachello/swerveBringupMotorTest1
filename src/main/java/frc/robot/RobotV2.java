package frc.robot;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import edu.wpi.first.wpilibj.Filesystem;
import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;
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
import edu.wpi.first.networktables.NetworkTableInstance;

public class RobotV2 extends TimedRobot {

  // ---------------- CAN ID DEFINITIONS ----------------
  private static final double DEADBAND = BringupUtil.DEADBAND;
  // ---------------------------------------------------

  private static final int REV_MANUFACTURER = 5;
  private static final int CTRE_MANUFACTURER = 4;
  private static final int TYPE_MOTOR_CONTROLLER = 2;
  private static final int TYPE_GYRO_SENSOR = 4;
  private static final int TYPE_ENCODER = 7;
  private static final int TYPE_POWER_DISTRIBUTION_MODULE = 8;

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
  private final Map<String, Double> prevMsgCount = new HashMap<>();
  private final Map<String, Double> prevMsgTime = new HashMap<>();

  @Override
  public void robotInit() {
    BringupUtil.applyProfileFromArgs();
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
  }

  @Override
  public void disabledInit() {
    core.resetState();
    prevDiag = false;
    prevBindings = false;
    prevProfileToggle = false;
    prevSpeedPrint = false;
    prevNudge = false;
  }

  @Override
  public void teleopPeriodic() {

    core.handleAdd(controller.getAButton());
    core.handleAddAll(controller.getStartButton());
    core.handlePrint(controller.getBButton());
    core.handleHealth(controller.getXButton());
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

    // Y button: print NetworkTables diagnostics
    boolean diagNow = controller.getYButton();
    if (diagNow && !prevDiag) {
      printNetworkDiagnostics();
    }
    prevDiag = diagNow;

    boolean bindingsNow = controller.getLeftBumperButton();
    if (bindingsNow && !prevBindings) {
      printStartupInfo();
    }
    prevBindings = bindingsNow;

    double neoSpeed = BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
    double krakenSpeed = BringupUtil.deadband(-controller.getRightY(), DEADBAND);

    boolean speedPrintNow = controller.getRightStickButton();
    if (speedPrintNow && !prevSpeedPrint) {
      System.out.println(
          "Inputs: leftY=" + String.format("%.2f", neoSpeed) +
          " rightY=" + String.format("%.2f", krakenSpeed) +
          " (NEO/FLEX=" + String.format("%.2f", neoSpeed) +
          ", KRAKEN/FALCON=" + String.format("%.2f", krakenSpeed) + ")");
    }
    prevSpeedPrint = speedPrintNow;

    boolean nudgeNow = controller.getLeftStickButton();
    if (nudgeNow && !prevNudge) {
      core.triggerNudge(0.2, 0.5);
      System.out.println("Nudge: 0.2 for 0.5s (all motors)");
    }
    prevNudge = nudgeNow;

    core.setSpeeds(neoSpeed, krakenSpeed);
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  private void printStartupInfo() {
    System.out.println("=== Swerve Bringup V2 ===");
    System.out.println("A: add motor (alternates SPARK/CTRE)");
    System.out.println("Start: add all motors + CANCoders");
    System.out.println("B: print state");
    System.out.println("X: print health status");
    System.out.println("Right Bumper: print CANCoder absolute positions");
    System.out.println("Back: toggle CAN profile");
    System.out.println("Y: print NetworkTables diagnostics");
    System.out.println("Left Bumper: reprint bindings");
    System.out.println("Right Stick: print speed inputs");
    System.out.println("Left Stick: nudge motors (0.2 for 0.5s)");
    System.out.println("Left Y: NEO/FLEX speed, Right Y: KRAKEN/FALCON speed");
    System.out.println("Deadband: " + DEADBAND);
    System.out.println("CAN profile: " + BringupUtil.getActiveCanProfileLabel());
    System.out.println("NEO CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO_CAN_IDS));
    System.out.println("FLEX CAN IDs: " + BringupUtil.joinIds(BringupUtil.FLEX_CAN_IDS));
    System.out.println("KRAKEN CAN IDs: " + BringupUtil.joinIds(BringupUtil.KRAKEN_CAN_IDS));
    System.out.println("FALCON CAN IDs: " + BringupUtil.joinIds(BringupUtil.FALCON_CAN_IDS));
    System.out.println("=========================");
  }

  private void printNetworkDiagnostics() {
    System.out.println("=== Bringup NetworkTables (CAN Bus via PC Tool) ===");
    double nowSeconds = System.currentTimeMillis() / 1000.0;

    double busErrors = diagTable.getEntry("busErrorCount").getDouble(Double.NaN);
    if (!Double.isNaN(busErrors)) {
      System.out.println("Bus error count: " + (long) busErrors);
    }

    System.out.println("Devices:");
    java.util.ArrayList<DeviceSpec> allSpecs = new java.util.ArrayList<>();
    java.util.Collections.addAll(allSpecs, buildDeviceSpecs());
    java.util.Collections.addAll(allSpecs, findUnknownDeviceSpecs());
    printNetworkDeviceTable(allSpecs, nowSeconds);
    System.out.println("=============================");
  }

  private void printNetworkDeviceTable(java.util.List<DeviceSpec> specs, double nowSeconds) {
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

    printWrappedHeaders(
        new String[] { idHeaderLong, labelHeaderLong, mfgHeaderLong, typeHeaderLong,
            statusHeaderLong, ageHeaderLong, fpsHeaderLong, msgHeaderLong },
        null,
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth,
        maxLineWidth);

    for (DeviceRow row : rows) {
      printWrappedRow(
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

  private static void printWrappedHeaders(
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
    System.out.println(buildHeaderLine(
        headerShort,
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth,
        maxLineWidth));
    if (headerLong != null) {
      System.out.println(buildHeaderLine(
          headerLong,
          idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth,
          maxLineWidth));
    }
    System.out.println("-".repeat(maxLineWidth));
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

  private static void printWrappedRow(
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
      System.out.println(rowText);
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
}


