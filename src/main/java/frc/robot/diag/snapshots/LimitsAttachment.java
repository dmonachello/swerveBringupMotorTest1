package frc.robot.diag.snapshots;

/**
 * NAME
 *   LimitsAttachment - Limit switch metadata and state.
 */
public final class LimitsAttachment extends DeviceAttachment {
  private static final String ATTACHMENT_TYPE = "limits";
  public static final String PROOF_STATE_UNPROVEN = "UNPROVEN";
  public static final String PROOF_STATE_PARTIAL = "PARTIAL";
  public static final String PROOF_STATE_PROVEN = "PROVEN";
  public static final String PROOF_STATE_STUCK = "STUCK";
  public static final String PROOF_STATE_UNKNOWN = "UNKNOWN";

  public static final class LimitSwitchState {
    public String label = "";
    public int dio = -1;
    public boolean invert = false;
    public Boolean closed;
    public Double lastChangeSec;
    public int transitionCountSinceActivate = 0;
    public boolean changedSinceActivate = false;
    public String proofState = PROOF_STATE_UNKNOWN;
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
