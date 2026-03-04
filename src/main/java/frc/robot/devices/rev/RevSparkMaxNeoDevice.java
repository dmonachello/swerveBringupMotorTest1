package frc.robot.devices.rev;

import com.revrobotics.PersistMode;
import com.revrobotics.ResetMode;
import com.revrobotics.spark.SparkLowLevel.MotorType;
import com.revrobotics.spark.SparkMax;
import com.revrobotics.spark.config.SparkMaxConfig;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.manufacturers.rev.diag.RevSparkMaxReader;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.registry.RegistrationHeader;
import edu.wpi.first.wpilibj.DigitalInput;

// Device wrapper for a REV Spark Max controlling a NEO.
public final class RevSparkMaxNeoDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "SparkMax NEO",
      "REV",
      "NEO",
      "REVLib",
      "Team",
      "2026-03-02",
      "Spark Max controlling a NEO motor.");
  private final int canId;
  private final String label;
  private final String motorModelOverride;
  private final BringupUtil.LimitConfig limitConfig;
  private DigitalInput fwdLimit;
  private DigitalInput revLimit;
  private SparkMax device;
  private boolean altEncoderConfigured = false;
  private int altEncoderCpr = 8192;

  public RevSparkMaxNeoDevice(
      int canId,
      String label,
      String motorModelOverride,
      BringupUtil.LimitConfig limitConfig) {
    this.canId = canId;
    this.label = label;
    this.motorModelOverride = motorModelOverride;
    this.limitConfig = limitConfig != null ? limitConfig : new BringupUtil.LimitConfig();
    initLimitInputs();
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return "NEO";
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
    device = new SparkMax(canId, MotorType.kBrushless);
    device.pauseFollowerModeAsync();
    device.configureAsync(
        new SparkMaxConfig(),
        ResetMode.kResetSafeParameters,
        PersistMode.kNoPersistParameters);
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
      device.clearFaults();
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
      snap.vendor = "REV";
      snap.deviceType = getDeviceType();
      snap.canId = canId;
      snap.present = false;
      snap.note = "not added";
      snap.label = label;
      addLimitAttachment(snap);
      return snap;
    }
    DeviceSnapshot snap = RevSparkMaxReader.read(device, canId);
    snap.deviceType = getDeviceType();
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
      return device.getEncoder().getPosition();
    } catch (Exception ex) {
      return null;
    }
  }

  @Override
  public Double getPositionRotations(String encoderSource, Integer countsPerRev) {
    if (isAltEncoder(encoderSource)) {
      return readAlternateEncoder(countsPerRev);
    }
    return getPositionRotations();
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

  private boolean isAltEncoder(String encoderSource) {
    if (encoderSource == null) {
      return false;
    }
    String normalized = encoderSource.trim().toLowerCase();
    return normalized.equals("sparkmax_alt")
        || normalized.equals("sparkmax_alternate")
        || normalized.equals("alternate")
        || normalized.equals("through_bore");
  }

  private Double readAlternateEncoder(Integer countsPerRev) {
    if (device == null) {
      return null;
    }
    int cpr = countsPerRev != null && countsPerRev > 0 ? countsPerRev.intValue() : 8192;
    if (!altEncoderConfigured || altEncoderCpr != cpr) {
      SparkMaxConfig config = new SparkMaxConfig();
      config.alternateEncoder.setSparkMaxDataPortConfig().countsPerRevolution(cpr);
      device.configureAsync(config, ResetMode.kNoResetSafeParameters, PersistMode.kNoPersistParameters);
      altEncoderConfigured = true;
      altEncoderCpr = cpr;
    }
    try {
      return device.getAlternateEncoder().getPosition();
    } catch (Exception ex) {
      return null;
    }
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

