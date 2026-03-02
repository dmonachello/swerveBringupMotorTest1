package frc.robot.diag.snapshots;

// Encoder telemetry (CANCoder).
public final class EncoderAttachment extends DeviceAttachment {
  public Double absDeg;
  public String lastError = "";

  public EncoderAttachment() {
    super("encoder");
  }
}
