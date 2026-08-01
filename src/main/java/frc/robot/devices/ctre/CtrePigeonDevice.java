package frc.robot.devices.ctre;

import com.ctre.phoenix6.BaseStatusSignal;
import com.ctre.phoenix6.hardware.Pigeon2;
import edu.wpi.first.units.Units;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.devices.DeviceDslSupport;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.ImuAttachment;
import frc.robot.registry.RegistrationHeader;

/**
 * NAME
 *   CtrePigeonDevice - DeviceUnit wrapper for a CTRE Pigeon 2 IMU.
 *
 * DESCRIPTION
 *   Provides the minimal bringup lifecycle needed for runtime activation and
 *   presence snapshots while broader IMU telemetry support is implemented.
 */
public final class CtrePigeonDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER =
      new RegistrationHeader(
          "Pigeon",
          "CTRE",
          "Pigeon",
          "Phoenix 6",
          "Team",
          "2026-07-30",
          "CTRE Pigeon 2 IMU wrapper for bringup activation.");

  private static final String VENDOR = "CTRE";
  private static final String DEVICE_TYPE = "Pigeon";
  private static final String NOTE_NOT_ADDED = "not added";
  private static final String NOTE_READ_FAIL_PREFIX = "Pigeon read failed: ";
  private static final int NO_FAULTS = 0;

  private final int canId;
  private final String label;
  private Pigeon2 device;

  /**
   * NAME
   *   CtrePigeonDevice - Construct one Pigeon device wrapper.
   *
   * PARAMETERS
   *   canId - CAN ID of the IMU.
   *   label - Human-readable device label.
   */
  public CtrePigeonDevice(int canId, String label) {
    this.canId = canId;
    this.label = label;
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return DEVICE_TYPE;
  }

  @Override
  public String getLabel() {
    return label;
  }

  @Override
  public RegistrationHeader getHeader() {
    return HEADER;
  }

  /**
   * NAME
   *   getActiveHandleForProbe - Return the current runtime-owned Pigeon2 handle.
   *
   * RETURNS
   *   Active Pigeon2 instance, or null when the runtime has not created it.
   */
  public Pigeon2 getActiveHandleForProbe() {
    return device;
  }

  @Override
  public boolean isCreated() {
    return device != null;
  }

  @Override
  public void ensureCreated() {
    if (device != null) {
      BringupUtil.claimDeviceInstance(this);
      return;
    }
    if (!BringupUtil.claimDeviceInstance(this)) {
      return;
    }
    device = new Pigeon2(canId);
  }

  @Override
  public void close() {
    BringupUtil.closeIfPossible(device);
    device = null;
    BringupUtil.releaseDeviceInstance(this);
  }

  @Override
  public void clearFaults() {
    if (device != null) {
      device.clearStickyFaults();
    }
  }

  @Override
  public void activate() {
    ensureCreated();
  }

  @Override
  public DeviceSnapshot snapshot() {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = VENDOR;
    snap.deviceType = DEVICE_TYPE;
    snap.canId = canId;
    snap.label = label;
    if (device == null) {
      snap.present = false;
      snap.note = NOTE_NOT_ADDED;
      return snap;
    }
    try {
      var yaw = device.getYaw();
      var pitch = device.getPitch();
      var roll = device.getRoll();
      var angularVelocityX = device.getAngularVelocityXDevice();
      var angularVelocityY = device.getAngularVelocityYDevice();
      var angularVelocityZ = device.getAngularVelocityZDevice();
      var accelX = device.getAccelerationX();
      var accelY = device.getAccelerationY();
      var accelZ = device.getAccelerationZ();
      var supplyVoltage = device.getSupplyVoltage();
      var faultsRaw = device.getFaultField();
      var stickyFaultsRaw = device.getStickyFaultField();
      BaseStatusSignal.refreshAll(
          yaw,
          pitch,
          roll,
          angularVelocityX,
          angularVelocityY,
          angularVelocityZ,
          accelX,
          accelY,
          accelZ,
          supplyVoltage,
          faultsRaw,
          stickyFaultsRaw);
      ImuAttachment imu = new ImuAttachment();
      imu.yawDeg = yaw.getValue().in(Units.Degrees);
      imu.pitchDeg = pitch.getValue().in(Units.Degrees);
      imu.rollDeg = roll.getValue().in(Units.Degrees);
      imu.angularVelocityXDps = angularVelocityX.getValue().in(Units.DegreesPerSecond);
      imu.angularVelocityYDps = angularVelocityY.getValue().in(Units.DegreesPerSecond);
      imu.angularVelocityZDps = angularVelocityZ.getValue().in(Units.DegreesPerSecond);
      imu.accelXG = accelX.getValue().in(Units.Gs);
      imu.accelYG = accelY.getValue().in(Units.Gs);
      imu.accelZG = accelZ.getValue().in(Units.Gs);
      imu.supplyVoltage = supplyVoltage.getValue().in(Units.Volts);
      imu.faultsRaw = faultsRaw.getValue();
      imu.stickyFaultsRaw = stickyFaultsRaw.getValue();
      imu.faults = imu.faultsRaw != NO_FAULTS || imu.stickyFaultsRaw != NO_FAULTS;
      imu.lastError = String.valueOf(yaw.getStatus());
      snap.addAttachment(imu);
      snap.present = true;
    } catch (RuntimeException ex) {
      snap.present = false;
      snap.note = NOTE_READ_FAIL_PREFIX + ex.getMessage();
    }
    return snap;
  }

  @Override
  public Object readDslSignal(String signalName) {
    return DeviceDslSupport.readImuSignal(this, signalName);
  }
}
