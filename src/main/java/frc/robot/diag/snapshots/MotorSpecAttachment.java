package frc.robot.diag.snapshots;

// Motor spec metadata used for sanity checks.
public final class MotorSpecAttachment extends DeviceAttachment {
  public String model = "";
  public Double nominalV;
  public Double freeCurrentA;
  public Double stallCurrentA;

  public MotorSpecAttachment() {
    super("motorSpec");
  }
}
