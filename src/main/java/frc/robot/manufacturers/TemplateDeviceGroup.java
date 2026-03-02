package frc.robot.manufacturers;

import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.devices.template.TemplateMotorDevice;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

// Template manufacturer group for new vendor integrations.
public final class TemplateDeviceGroup implements ManufacturerGroup {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "Template",
      "TEMPLATE",
      "Manufacturer",
      "Template SDK",
      "Team",
      "2026-03-02",
      "Clone for new manufacturer integrations.");

  private final DeviceTypeBucket bucket;

  public TemplateDeviceGroup() {
    this(new int[0], new String[0], new BringupUtil.LimitConfig[0], "MotorController");
  }

  public TemplateDeviceGroup(
      int[] canIds,
      String[] labels,
      BringupUtil.LimitConfig[] limits,
      String deviceType) {
    int count = Math.min(canIds.length, labels.length);
    List<DeviceUnit> devices = new ArrayList<>();
    for (int i = 0; i < count; i++) {
      BringupUtil.LimitConfig limit =
          (limits != null && i < limits.length) ? limits[i] : new BringupUtil.LimitConfig();
      devices.add(new TemplateMotorDevice(canIds[i], labels[i], deviceType, limit));
    }
    DeviceRegistration registration = new DeviceRegistration(
        TemplateMotorDevice.HEADER,
        "TEMPLATE",
        deviceType,
        deviceType,
        DeviceRole.MOTOR,
        false,
        config -> new TemplateMotorDevice(
            config.getId(),
            config.getLabel(),
            deviceType,
            config.getLimits()));
    bucket = new DeviceTypeBucket(registration, devices, false);
  }

  @Override
  public RegistrationHeader getHeader() {
    return HEADER;
  }

  @Override
  public List<DeviceTypeBucket> getDeviceBuckets() {
    return Collections.singletonList(bucket);
  }

  @Override
  public DeviceAddResult addNextMotor() {
    return bucket.addNext();
  }

  @Override
  public void resetLowCurrentTimers() {
    bucket.resetLowCurrentTimers();
  }

  @Override
  public List<DeviceUnit> getTestDevices() {
    return new ArrayList<>();
  }

  @Override
  public void addAll() {
    bucket.addAll();
  }

  @Override
  public void setDuty(double duty) {
    for (DeviceUnit device : bucket.getDevices()) {
      device.setDuty(duty);
    }
  }

  @Override
  public void stopAll() {
    for (DeviceUnit device : bucket.getDevices()) {
      device.stop();
    }
  }

  @Override
  public void clearFaults() {
    for (DeviceUnit device : bucket.getDevices()) {
      device.clearFaults();
    }
  }

  @Override
  public void closeAll() {
    for (DeviceUnit device : bucket.getDevices()) {
      device.close();
    }
    bucket.resetAddPointer();
  }

  @Override
  public List<DeviceSnapshot> captureSnapshots(double nowSec) {
    List<DeviceSnapshot> devices = new ArrayList<>();
    for (DeviceUnit device : bucket.getDevices()) {
      devices.add(device.snapshot());
    }
    return devices;
  }
}
