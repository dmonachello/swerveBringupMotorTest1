package frc.robot.diag.snapshots;

/**
 * NAME
 *   LimitsAttachment - Limit switch metadata and state.
 */
public final class LimitsAttachment extends DeviceAttachment {
  public int fwdDio = -1;
  public int revDio = -1;
  public boolean invert = false;
  public Boolean fwdClosed;
  public Boolean revClosed;

  /**
   * NAME
   *   LimitsAttachment - Construct with attachment type name.
   */
  public LimitsAttachment() {
    super("limits");
  }
}
