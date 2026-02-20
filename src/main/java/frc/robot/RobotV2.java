package frc.robot;

import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.XboxController;

import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;

public class RobotV2 extends TimedRobot {

  // ---------------- CAN ID DEFINITIONS ----------------
  private static final double DEADBAND = BringupUtil.DEADBAND;
  // ---------------------------------------------------

  private final XboxController controller = new XboxController(0);
  private final BringupCore core = new BringupCore();
  private final NetworkTable diagTable =
      NetworkTableInstance.getDefault().getTable("bringup").getSubTable("diag");
  private boolean prevDiag = false;

  @Override
  public void robotInit() {
    printStartupInfo();
    BringupUtil.validateCanIds(BringupUtil.NEO_CAN_IDS, BringupUtil.KRAKEN_CAN_IDS);
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
    core.handlePrint(controller.getBButton());
    core.handleHealth(controller.getXButton());
    core.handleCANCoder(controller.getRightBumper());

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

    System.out.println("NEOs:");
    for (int id : BringupUtil.NEO_CAN_IDS) {
      printNetworkDeviceStatus("NEO", id, nowSeconds);
    }
    System.out.println("Krakens:");
    for (int id : BringupUtil.KRAKEN_CAN_IDS) {
      printNetworkDeviceStatus("KRAKEN", id, nowSeconds);
    }
    System.out.println("=============================");
  }

  private void printNetworkDeviceStatus(String label, int deviceId, double nowSeconds) {
    double lastSeen = diagTable.getEntry("lastSeen/" + deviceId).getDouble(Double.NaN);
    boolean missing = diagTable.getEntry("missing/" + deviceId).getBoolean(false);
    if (Double.isNaN(lastSeen)) {
      System.out.println("  " + label + " CAN " + deviceId + " NT: no data");
      return;
    }
    double age = nowSeconds - lastSeen;
    System.out.println(
        "  " + label + " CAN " + deviceId +
        " NT: " + (missing ? "MISSING" : "seen") +
        " lastSeen=" + lastSeen +
        " ageSec=" + String.format("%.1f", age));
  }

  // Shared behavior moved to BringupCore.
}
