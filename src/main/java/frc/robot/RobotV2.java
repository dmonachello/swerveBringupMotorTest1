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
  private static final int TYPE_PIGEON = 4;
  private static final int TYPE_CANCODER = 7;
  private static final int TYPE_PDH = 8;
  private static final int PDH_CAN_ID = 1;
  private static final int PIGEON_CAN_ID = 1;

  private static final DeviceSpec[] DEVICE_SPECS = buildDeviceSpecs();

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
    for (DeviceSpec spec : DEVICE_SPECS) {
      printNetworkDeviceStatus(spec, nowSeconds);
    }
    System.out.println("=============================");
  }

  private void printNetworkDeviceStatus(DeviceSpec spec, double nowSeconds) {
    String base = "dev/" + spec.manufacturer + "/" + spec.deviceType + "/" + spec.deviceId;
    String label = diagTable.getEntry(base + "/label").getString(spec.label);
    String status = diagTable.getEntry(base + "/status").getString("UNKNOWN");
    double age = diagTable.getEntry(base + "/ageSec").getDouble(Double.NaN);
    double msgCount = diagTable.getEntry(base + "/msgCount").getDouble(Double.NaN);
    double lastSeen = diagTable.getEntry(base + "/lastSeen").getDouble(Double.NaN);

    if (Double.isNaN(lastSeen) || lastSeen < 0) {
      System.out.println("  " + label + " NT: no data");
      return;
    }

    double ageValue = Double.isNaN(age) ? (nowSeconds - lastSeen) : age;
    System.out.println(
        "  " + label +
        " mfg=" + spec.manufacturer +
        " type=" + spec.deviceType +
        " id=" + spec.deviceId +
        " status=" + status +
        " ageSec=" + String.format("%.1f", ageValue) +
        " msgCount=" + (Double.isNaN(msgCount) ? "?" : String.format("%.0f", msgCount)));
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
      specs[i++] = new DeviceSpec("CANCoder", CTRE_MANUFACTURER, TYPE_CANCODER, id);
    }
    specs[i++] = new DeviceSpec("PDH", REV_MANUFACTURER, TYPE_PDH, PDH_CAN_ID);
    specs[i++] = new DeviceSpec("Pigeon", CTRE_MANUFACTURER, TYPE_PIGEON, PIGEON_CAN_ID);
    return specs;
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
}
