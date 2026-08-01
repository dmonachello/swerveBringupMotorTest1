package frc.robot.diag.snapshots;

/**
 * NAME
 *   ImuAttachment - Basic IMU telemetry for a device snapshot.
 */
public final class ImuAttachment extends DeviceAttachment {
  public Double yawDeg;
  public Double pitchDeg;
  public Double rollDeg;
  public Double angularVelocityXDps;
  public Double angularVelocityYDps;
  public Double angularVelocityZDps;
  public Double accelXG;
  public Double accelYG;
  public Double accelZG;
  public Double supplyVoltage;
  public Integer faultsRaw = 0;
  public Integer stickyFaultsRaw = 0;
  public Boolean faults;
  public String lastError = "";

  /**
   * NAME
   *   ImuAttachment - Construct with attachment type name.
   */
  public ImuAttachment() {
    super("imu");
  }
}
