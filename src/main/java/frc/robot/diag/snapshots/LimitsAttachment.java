package frc.robot.diag.snapshots;

/**
 * NAME
 *   LimitsAttachment - Limit switch metadata and state.
 */
public final class LimitsAttachment extends DeviceAttachment {
  private static final String ATTACHMENT_TYPE = "limits";

  public static final class LimitSwitchState {
    public String label = "";
    public int dio = -1;
    public boolean invert = false;
    public Boolean closed;
  }

  public final java.util.List<LimitSwitchState> switches = new java.util.ArrayList<>();

  /**
   * NAME
   *   LimitsAttachment - Construct with attachment type name.
   */
  public LimitsAttachment() {
    super(ATTACHMENT_TYPE);
  }
}
