package frc.robot.diag.snapshots;

// Typed extension data attached to a DeviceSnapshot.
public abstract class DeviceAttachment {
  public final String type;

  protected DeviceAttachment(String type) {
    this.type = type;
  }
}
