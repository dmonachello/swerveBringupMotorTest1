package frc.robot.devices.ctre;

import com.ctre.phoenix6.hardware.TalonFX;
import edu.wpi.first.units.Units;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.manufacturers.ctre.diag.CtreTalonFxReader;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.registry.RegistrationHeader;
import edu.wpi.first.wpilibj.DigitalInput;

// Device wrapper for a CTRE TalonFX-based motor (Kraken/Falcon).
public final class CtreTalonFxDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "TalonFX",
      "CTRE",
      "TalonFX",
      "Phoenix 6",
      "Team",
      "2026-03-02",
      "TalonFX-based motor controller (Kraken/Falcon).");
  private final int canId;
  private final String label;
  private final String motorModelOverride;
  private final String deviceType;
  private final BringupUtil.LimitConfig limitConfig;
  private DigitalInput fwdLimit;
  private DigitalInput revLimit;
  private TalonFX device;

  public CtreTalonFxDevice(
      int canId,
      String label,
      String motorModelOverride,
      String deviceType,
      BringupUtil.LimitConfig limitConfig) {
    this.canId = canId;
    this.label = label;
    this.motorModelOverride = motorModelOverride;
    this.deviceType = deviceType;
    this.limitConfig = limitConfig != null ? limitConfig : new BringupUtil.LimitConfig();
    initLimitInputs();
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return deviceType;
  }

  @Override
  public String getLabel() {
    return label;
  }

  @Override
  public RegistrationHeader getHeader() {
    return HEADER;
  }

  public String getMotorModelOverride() {
    return motorModelOverride;
  }

  @Override
  public boolean isCreated() {
    return device != null;
  }

  @Override
  public void ensureCreated() {
    if (device != null) {
      return;
    }
    device = new TalonFX(canId);
  }

  @Override
  public void close() {
    BringupUtil.closeIfPossible(device);
    device = null;
    BringupUtil.closeIfPossible(fwdLimit);
    BringupUtil.closeIfPossible(revLimit);
    fwdLimit = null;
    revLimit = null;
  }

  @Override
  public void clearFaults() {
    if (device != null) {
      device.clearStickyFaults();
    }
  }

  @Override
  public void setDuty(double duty) {
    if (device != null) {
      device.set(applyLimit(duty));
    }
  }

  @Override
  public void stop() {
    if (device != null) {
      device.stopMotor();
    }
  }

  @Override
  public void activate() {
    ensureCreated();
  }

  @Override
  public void deactivate() {
    stop();
  }

  @Override
  public DeviceSnapshot snapshot() {
    if (device == null) {
      DeviceSnapshot snap = new DeviceSnapshot();
      snap.vendor = "CTRE";
      snap.deviceType = deviceType;
      snap.canId = canId;
      snap.present = false;
      snap.note = "not added";
      snap.label = label;
      addLimitAttachment(snap);
      return snap;
    }
    DeviceSnapshot snap = CtreTalonFxReader.read(device, deviceType, canId);
    snap.label = label;
    addLimitAttachment(snap);
    return snap;
  }

  @Override
  public Double getPositionRotations() {
    if (device == null) {
      return null;
    }
    try {
      return device.getPosition().getValue().in(Units.Rotations);
    } catch (Exception ex) {
      return null;
    }
  }

  private void initLimitInputs() {
    if (limitConfig.hasForward()) {
      fwdLimit = new DigitalInput(limitConfig.fwdDio);
    }
    if (limitConfig.hasReverse()) {
      revLimit = new DigitalInput(limitConfig.revDio);
    }
  }

  private void addLimitAttachment(DeviceSnapshot snap) {
    if (!limitConfig.hasForward() && !limitConfig.hasReverse()) {
      return;
    }
    LimitsAttachment limits = new LimitsAttachment();
    limits.invert = limitConfig.invert;
    if (limitConfig.hasForward()) {
      limits.fwdDio = limitConfig.fwdDio;
      limits.fwdClosed = readLimit(fwdLimit);
    }
    if (limitConfig.hasReverse()) {
      limits.revDio = limitConfig.revDio;
      limits.revClosed = readLimit(revLimit);
    }
    snap.addAttachment(limits);
  }

  private Boolean readLimit(DigitalInput input) {
    if (input == null) {
      return null;
    }
    boolean raw = input.get();
    return limitConfig.invert ? !raw : raw;
  }

  private double applyLimit(double duty) {
    Boolean fwdClosed = readLimit(fwdLimit);
    if (Boolean.TRUE.equals(fwdClosed) && duty > 0.0) {
      return 0.0;
    }
    Boolean revClosed = readLimit(revLimit);
    if (Boolean.TRUE.equals(revClosed) && duty < 0.0) {
      return 0.0;
    }
    return duty;
  }
}
