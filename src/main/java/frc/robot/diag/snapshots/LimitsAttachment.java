package frc.robot.diag.snapshots;

// DIO limit switch metadata + current state.
public final class LimitsAttachment extends DeviceAttachment {
  public int fwdDio = -1;
  public int revDio = -1;
  public boolean invert = false;
  public Boolean fwdClosed;
  public Boolean revClosed;

  public LimitsAttachment() {
    super("limits");
  }
}
