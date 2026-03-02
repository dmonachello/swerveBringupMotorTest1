package frc.robot.devices.ctre;

import com.ctre.phoenix6.hardware.CANcoder;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.manufacturers.ctre.diag.CtreCANCoderReader;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.registry.RegistrationHeader;
import edu.wpi.first.wpilibj.DigitalInput;

// Device wrapper for a CTRE CANCoder.
public final class CtreCANCoderDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "CANCoder",
      "CTRE",
      "CANCoder",
      "Phoenix 6",
      "Team",
      "2026-03-02",
      "CTRE CAN-based absolute encoder.");
  private final int canId;
  private final String label;
  private final BringupUtil.LimitConfig limitConfig;
  private DigitalInput fwdLimit;
  private DigitalInput revLimit;
  private CANcoder device;

  public CtreCANCoderDevice(int canId, String label, BringupUtil.LimitConfig limitConfig) {
    this.canId = canId;
    this.label = label;
    this.limitConfig = limitConfig != null ? limitConfig : new BringupUtil.LimitConfig();
    initLimitInputs();
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return "CANCoder";
  }

  @Override
  public String getLabel() {
    return label;
  }

  @Override
  public RegistrationHeader getHeader() {
    return HEADER;
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
    device = new CANcoder(canId);
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
  public void activate() {
    ensureCreated();
  }

  @Override
  public DeviceSnapshot snapshot() {
    if (device == null) {
      DeviceSnapshot snap = new DeviceSnapshot();
      snap.vendor = "CTRE";
      snap.deviceType = getDeviceType();
      snap.canId = canId;
      snap.present = false;
      snap.note = "not added";
      snap.label = label;
      addLimitAttachment(snap);
      return snap;
    }
    DeviceSnapshot snap = CtreCANCoderReader.read(device, canId);
    snap.label = label;
    addLimitAttachment(snap);
    return snap;
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
}
