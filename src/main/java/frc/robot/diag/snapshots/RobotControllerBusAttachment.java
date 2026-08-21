package frc.robot.diag.snapshots;

/**
 * NAME
 *   RobotControllerBusAttachment - Shared controller-family bus-health snapshot.
 *
 * DESCRIPTION
 *   Captures controller-local CAN bus status counters behind the shared
 *   robot-controller family contract.
 */
public final class RobotControllerBusAttachment extends DeviceAttachment {
  private static final String ATTACHMENT_TYPE = "robotControllerBus";

  public double canUtilizationPct;
  public int canRxErrorCount;
  public int canTxErrorCount;
  public int canBusOffCount;
  public int canTxFullCount;

  /**
   * NAME
   *   RobotControllerBusAttachment - Construct with default type.
   */
  public RobotControllerBusAttachment() {
    super(ATTACHMENT_TYPE);
  }
}
