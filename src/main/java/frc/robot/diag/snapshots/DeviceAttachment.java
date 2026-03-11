package frc.robot.diag.snapshots;

/**
 * NAME
 *   DeviceAttachment - Typed extension data for device snapshots.
 */
public abstract class DeviceAttachment {
  public final String type;

  /**
   * NAME
   *   DeviceAttachment - Construct with a type identifier.
   */
  protected DeviceAttachment(String type) {
    this.type = type;
  }
}
