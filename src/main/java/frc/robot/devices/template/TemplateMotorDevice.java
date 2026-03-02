package frc.robot.devices.template;

import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.BringupUtil;
import edu.wpi.first.wpilibj.DigitalInput;

// Template device wrapper for new vendor integrations.
public final class TemplateMotorDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "Template Motor",
      "TEMPLATE",
      "TEMPLATE_MOTOR",
      "Template SDK",
      "Team",
      "2026-03-02",
      "Clone this device when adding a new vendor.");
  private final int canId;
  private final String label;
  private final String deviceType;
  private final BringupUtil.LimitConfig limitConfig;
  private DigitalInput fwdLimit;
  private DigitalInput revLimit;
  private boolean created = false;

  public TemplateMotorDevice(
      int canId,
      String label,
      String deviceType,
      BringupUtil.LimitConfig limitConfig) {
    this.canId = canId;
    this.label = label;
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

  @Override
  public boolean isCreated() {
    return created;
  }

  @Override
  public void ensureCreated() {
    created = true;
  }

  @Override
  public void close() {
    created = false;
    BringupUtil.closeIfPossible(fwdLimit);
    BringupUtil.closeIfPossible(revLimit);
    fwdLimit = null;
    revLimit = null;
  }

  @Override
  public void clearFaults() {
  }

  @Override
  public void setDuty(double duty) {
  }

  @Override
  public void stop() {
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
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = "TEMPLATE";
    snap.deviceType = deviceType;
    snap.canId = canId;
    snap.label = label;
    if (created) {
      snap.present = true;
      snap.note = "template device (no SDK)";
    } else {
      snap.present = false;
      snap.note = "not added";
    }
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
