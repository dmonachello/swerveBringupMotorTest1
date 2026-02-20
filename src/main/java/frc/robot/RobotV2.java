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

  @Override
  public void robotInit() {
    printStartupInfo();
    BringupUtil.validateCanIds(
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
  }

  @Override
  public void disabledInit() {
    core.resetState();
    prevDiag = false;
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
    int idWidth = 1;
    int mfgIdWidth = 1;
    int typeIdWidth = 1;
    int labelWidth = 1;
    int mfgLabelWidth = maxLabelWidth(MANUFACTURER_LABELS, "UNKNOWN");
    int typeLabelWidth = maxLabelWidth(DEVICE_TYPE_LABELS, "UNKNOWN");
    int statusWidth = "NO_DATA".length();
    int ageWidth = "ageSec".length();
    int msgWidth = "msgCount".length();

    for (DeviceSpec spec : specs) {
      DeviceRow row = loadDeviceRow(spec, nowSeconds);
      rows.add(row);

      idWidth = Math.max(idWidth, Integer.toString(spec.deviceId).length());
      mfgIdWidth = Math.max(mfgIdWidth, Integer.toString(spec.manufacturer).length());
      typeIdWidth = Math.max(typeIdWidth, Integer.toString(spec.deviceType).length());
      labelWidth = Math.max(labelWidth, row.label.length());
      statusWidth = Math.max(statusWidth, row.status.length());
      ageWidth = Math.max(ageWidth, row.ageText.length());
      msgWidth = Math.max(msgWidth, row.msgText.length());
    }

    String format =
        "  %" + idWidth + "d  " +
        "%-" + labelWidth + "s  " +
        "%" + mfgIdWidth + "d  " +
        "%-" + mfgLabelWidth + "s  " +
        "%" + typeIdWidth + "d  " +
        "%-" + typeLabelWidth + "s  " +
        "%-" + statusWidth + "s  " +
        "%" + ageWidth + "s  " +
        "%" + msgWidth + "s";

    String headerFormat =
        "  %" + idWidth + "s  " +
        "%-" + labelWidth + "s  " +
        "%" + mfgIdWidth + "s  " +
        "%-" + mfgLabelWidth + "s  " +
        "%" + typeIdWidth + "s  " +
        "%-" + typeLabelWidth + "s  " +
        "%-" + statusWidth + "s  " +
        "%" + ageWidth + "s  " +
        "%" + msgWidth + "s";

    String header = String.format(
        headerFormat,
        "id",
        "label",
        "mfg",
        "mfgName",
        "type",
        "typeName",
        "status",
        "ageSec",
        "msgCount");
    System.out.println(header);
    System.out.println("  " + "-".repeat(header.length() - 2));

    for (DeviceRow row : rows) {
      System.out.println(String.format(
          format,
          row.spec.deviceId,
          row.label,
          row.spec.manufacturer,
          row.mfgLabel,
          row.spec.deviceType,
          row.typeLabel,
          row.status,
          row.ageText,
          row.msgText));
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
    int total = BringupUtil.NEO_CAN_IDS.length
        + BringupUtil.KRAKEN_CAN_IDS.length
        + BringupUtil.CANCODER_CAN_IDS.length
        + 2;
    DeviceSpec[] specs = new DeviceSpec[total];
    int i = 0;
    for (int id : BringupUtil.NEO_CAN_IDS) {
      specs[i++] = new DeviceSpec("NEO", REV_MANUFACTURER, TYPE_MOTOR_CONTROLLER, id);
    }
    for (int id : BringupUtil.KRAKEN_CAN_IDS) {
      specs[i++] = new DeviceSpec("KRAKEN", CTRE_MANUFACTURER, TYPE_MOTOR_CONTROLLER, id);
    }
    for (int id : BringupUtil.CANCODER_CAN_IDS) {
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
