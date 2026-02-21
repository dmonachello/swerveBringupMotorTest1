package frc.robot;

import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;

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
  private static final int PDH_CAN_ID = 1;
  private static final int PIGEON_CAN_ID = 1;

  private static final DeviceSpec[] DEVICE_SPECS = buildDeviceSpecs();
  private static final java.util.Map<Integer, String> MANUFACTURER_LABELS = buildManufacturerLabels();
  private static final java.util.Map<Integer, String> DEVICE_TYPE_LABELS = buildDeviceTypeLabels();

  private final XboxController controller = new XboxController(0);
  private final BringupCore core = new BringupCore();
  private final NetworkTable diagTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("diag");
  private boolean prevDiag = false;
  private boolean prevBindings = false;

  @Override
  public void robotInit() {
    printStartupInfo();
    BringupUtil.validateCanIds(
        new String[] { "NEO", "KRAKEN", "CANCoder", "PDH", "Pigeon" },
        BringupUtil.NEO_CAN_IDS,
        BringupUtil.KRAKEN_CAN_IDS,
        BringupUtil.CANCODER_CAN_IDS,
        new int[] { PDH_CAN_ID },
        new int[] { PIGEON_CAN_ID });
  }

  @Override
  public void teleopInit() {
    core.resetState();
    prevDiag = false;
    prevBindings = false;
  }

  @Override
  public void disabledInit() {
    core.resetState();
    prevDiag = false;
    prevBindings = false;
  }

  @Override
  public void teleopPeriodic() {

    core.handleAdd(controller.getAButton());
    core.handleAddAll(controller.getStartButton());
    core.handlePrint(controller.getBButton());
    core.handleHealth(controller.getXButton());
    core.handleCANCoder(controller.getRightBumperButton());

    // Y button: print NetworkTables diagnostics
    boolean diagNow = controller.getYButton();
    if (diagNow && !prevDiag) {
      printNetworkDiagnostics();
    }
    prevDiag = diagNow;

    boolean bindingsNow = controller.getBackButton();
    if (bindingsNow && !prevBindings) {
      printStartupInfo();
    }
    prevBindings = bindingsNow;

    double neoSpeed = BringupUtil.deadband(-controller.getLeftY(), DEADBAND);
    double krakenSpeed = BringupUtil.deadband(-controller.getRightY(), DEADBAND);

    core.setSpeeds(neoSpeed, krakenSpeed);
  }

  // ---------------------------------------------------
  // Diagnostics
  // ---------------------------------------------------

  private void printStartupInfo() {
    System.out.println("=== Swerve Bringup V2 ===");
    System.out.println("A: add motor (alternates NEO/KRAKEN)");
    System.out.println("Start: add all motors + CANCoders");
    System.out.println("B: print state");
    System.out.println("X: print health status");
    System.out.println("Right Bumper: print CANCoder absolute positions");
    System.out.println("Y: print NetworkTables diagnostics");
    System.out.println("Back: reprint bindings");
    System.out.println("Left Y: NEO speed, Right Y: KRAKEN speed");
    System.out.println("Deadband: " + DEADBAND);
    System.out.println("NEO CAN IDs: " + BringupUtil.joinIds(BringupUtil.NEO_CAN_IDS));
    System.out.println("KRAKEN CAN IDs: " + BringupUtil.joinIds(BringupUtil.KRAKEN_CAN_IDS));
    System.out.println("=========================");
  }

  private void printNetworkDiagnostics() {
    System.out.println("=== Bringup NetworkTables ===");
    double nowSeconds = System.currentTimeMillis() / 1000.0;

    double busErrors = diagTable.getEntry("busErrorCount").getDouble(Double.NaN);
    if (!Double.isNaN(busErrors)) {
      System.out.println("Bus error count: " + (long) busErrors);
    }

    System.out.println("Devices:");
    java.util.ArrayList<DeviceSpec> allSpecs = new java.util.ArrayList<>();
    java.util.Collections.addAll(allSpecs, DEVICE_SPECS);
    java.util.Collections.addAll(allSpecs, findUnknownDeviceSpecs());
    printNetworkDeviceTable(allSpecs, nowSeconds);
    System.out.println("=============================");
  }

  private void printNetworkDeviceTable(java.util.List<DeviceSpec> specs, double nowSeconds) {
    java.util.ArrayList<DeviceRow> rows = new java.util.ArrayList<>();
    String idHeader = "id";
    String labelHeader = "label";
    String mfgHeader = "mfg";
    String typeHeader = "type";
    String statusHeader = "status";
    String ageHeader = "ageSec";
    String msgHeader = "msgCount";
    String idHeaderLong = "id";
    String labelHeaderLong = "label";
    String mfgHeaderLong = "mfg";
    String typeHeaderLong = "type";
    String statusHeaderLong = "status";
    String ageHeaderLong = "ageSec";
    String msgHeaderLong = "msgCount";
    int idWidth = 3;
    int labelWidth = 20;
    int mfgIdWidth = 3;
    int typeIdWidth = 4;
    int statusWidth = 8;
    int ageWidth = 6;
    int msgWidth = 16;
    int maxLineWidth = 86;

    for (DeviceSpec spec : specs) {
      DeviceRow row = loadDeviceRow(spec, nowSeconds);
      rows.add(row);

    }

    printWrappedHeaders(
        new String[] { idHeaderLong, labelHeaderLong, mfgHeaderLong, typeHeaderLong,
            statusHeaderLong, ageHeaderLong, msgHeaderLong },
        null,
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, msgWidth,
        maxLineWidth);

    for (DeviceRow row : rows) {
      printWrappedRow(
          new String[] {
              Integer.toString(row.spec.deviceId),
              row.label,
              Integer.toString(row.spec.manufacturer),
              Integer.toString(row.spec.deviceType),
              row.status,
              row.ageText,
              row.msgText
          },
          idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, msgWidth,
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
    String msgText = "-";
    String finalStatus = hasData ? status : "NO_DATA";
    if (hasData) {
      double ageValue = Double.isNaN(age) ? (nowSeconds - lastSeen) : age;
      ageText = String.format("%.1f", ageValue);
      msgText = Double.isNaN(msgCount) ? "?" : String.format("%.0f", msgCount);
    }

    String mfgLabel = MANUFACTURER_LABELS.getOrDefault(spec.manufacturer, "UNKNOWN");
    String typeLabel = DEVICE_TYPE_LABELS.getOrDefault(spec.deviceType, "UNKNOWN");
    return new DeviceRow(
        spec,
        label,
        mfgLabel,
        typeLabel,
        finalStatus,
        ageText,
        msgText);
  }

  private static int maxLabelWidth(java.util.Map<Integer, String> labels, String fallback) {
    int width = fallback.length();
    for (String value : labels.values()) {
      width = Math.max(width, value.length());
    }
    return width;
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
      int msgWidth,
      int maxLineWidth) {
    System.out.println(buildHeaderLine(
        headerShort,
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, msgWidth,
        maxLineWidth));
    if (headerLong != null) {
      System.out.println(buildHeaderLine(
          headerLong,
          idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, msgWidth,
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
      int msgWidth,
      int maxLineWidth) {
    int[] widths = new int[] {
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, msgWidth
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
      int msgWidth,
      int maxLineWidth) {
    int[] widths = new int[] {
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, msgWidth
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

  private static String padLeft(String value, int width, char fill) {
    if (value == null) {
      value = "";
    }
    int missing = width - value.length();
    if (missing <= 0) {
      return value;
    }
    return repeatChar(fill, missing) + value;
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

  private DeviceSpec[] findUnknownDeviceSpecs() {
    java.util.HashSet<String> known = new java.util.HashSet<>();
    for (DeviceSpec spec : DEVICE_SPECS) {
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
    int[] krakenIds = BringupUtil.filterCanIds(BringupUtil.KRAKEN_CAN_IDS);
    int[] cancoderIds = BringupUtil.filterCanIds(BringupUtil.CANCODER_CAN_IDS);
    int total = neoIds.length
        + krakenIds.length
        + cancoderIds.length
        + 2;
    DeviceSpec[] specs = new DeviceSpec[total];
    int i = 0;
    for (int id : neoIds) {
      specs[i++] = new DeviceSpec("NEO", REV_MANUFACTURER, TYPE_MOTOR_CONTROLLER, id);
    }
    for (int id : krakenIds) {
      specs[i++] = new DeviceSpec("KRAKEN", CTRE_MANUFACTURER, TYPE_MOTOR_CONTROLLER, id);
    }
    for (int id : cancoderIds) {
      specs[i++] = new DeviceSpec("CANCoder", CTRE_MANUFACTURER, TYPE_ENCODER, id);
    }
    specs[i++] = new DeviceSpec("PDH", REV_MANUFACTURER, TYPE_POWER_DISTRIBUTION_MODULE, PDH_CAN_ID);
    specs[i++] = new DeviceSpec("Pigeon", CTRE_MANUFACTURER, TYPE_GYRO_SENSOR, PIGEON_CAN_ID);
    return specs;
  }

  private static java.util.Map<Integer, String> buildManufacturerLabels() {
    java.util.HashMap<Integer, String> labels = new java.util.HashMap<>();
    labels.put(0, "Broadcast");
    labels.put(1, "NI");
    labels.put(2, "LuminaryMicro");
    labels.put(3, "DEKA");
    labels.put(4, "CTRElectronics");
    labels.put(5, "REVRobotics");
    labels.put(6, "Grapple");
    labels.put(7, "MindSensors");
    labels.put(8, "TeamUse");
    labels.put(9, "KauaiLabs");
    labels.put(10, "Copperforge");
    labels.put(11, "PlayingWithFusion");
    labels.put(12, "Studica");
    labels.put(13, "TheThriftyBot");
    labels.put(14, "ReduxRobotics");
    labels.put(15, "AndyMark");
    labels.put(16, "VividHosting");
    labels.put(17, "VertosRobotics");
    labels.put(18, "SWYFTRobotics");
    labels.put(19, "LumynLabs");
    labels.put(20, "BrushlandLabs");
    labels.put(REV_MANUFACTURER, "REV");
    labels.put(CTRE_MANUFACTURER, "CTRE");
    return labels;
  }

  private static java.util.Map<Integer, String> buildDeviceTypeLabels() {
    java.util.HashMap<Integer, String> labels = new java.util.HashMap<>();
    labels.put(0, "BroadcastMessages");
    labels.put(1, "RobotController");
    labels.put(TYPE_MOTOR_CONTROLLER, "MotorController");
    labels.put(3, "RelayController");
    labels.put(TYPE_GYRO_SENSOR, "GyroSensor");
    labels.put(5, "Accelerometer");
    labels.put(6, "DistanceSensor");
    labels.put(TYPE_ENCODER, "Encoder");
    labels.put(TYPE_POWER_DISTRIBUTION_MODULE, "PowerDistributionModule");
    labels.put(9, "PneumaticsController");
    labels.put(10, "Miscellaneous");
    labels.put(11, "IOBreakout");
    labels.put(12, "ServoController");
    labels.put(13, "ColorSensor");
    labels.put(31, "FirmwareUpdate");
    return labels;
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
    private final String mfgLabel;
    private final String typeLabel;
    private final String status;
    private final String ageText;
    private final String msgText;

    private DeviceRow(
        DeviceSpec spec,
        String label,
        String mfgLabel,
        String typeLabel,
        String status,
        String ageText,
        String msgText) {
      this.spec = spec;
      this.label = label;
      this.mfgLabel = mfgLabel;
      this.typeLabel = typeLabel;
      this.status = status;
      this.ageText = ageText;
      this.msgText = msgText;
    }
  }
}
