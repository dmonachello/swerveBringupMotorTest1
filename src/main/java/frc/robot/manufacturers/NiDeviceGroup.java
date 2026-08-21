package frc.robot.manufacturers;

import frc.robot.BringupUtil;
import frc.robot.BringupUtil.DeviceConfig;
import frc.robot.devices.DeviceUnit;
import frc.robot.devices.ni.DioLimitSwitchDevice;
import frc.robot.devices.ni.RoboRioDevice;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * NAME
 *   NiDeviceGroup - Manufacturer group for NI virtual controller devices.
 *
 * DESCRIPTION
 *   Keeps roboRIO identity in the same device lifecycle and snapshot pipeline
 *   used by vendor CAN devices.
 */
public final class NiDeviceGroup implements ManufacturerGroup {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "NI",
      "NI",
      "Manufacturer",
      "WPILib",
      "Team",
      "2026-04-26",
      "NI controller device wrappers.");

  private static final DeviceRegistration ROBORIO_REGISTRATION = new DeviceRegistration(
      RoboRioDevice.HEADER,
      "NI",
      "robotController",
      "robotController",
      DeviceRole.MISC,
      false,
      config -> new RoboRioDevice(config.getId(), config.getLabel()));

  private static final DeviceRegistration LIMIT_SWITCH_REGISTRATION = new DeviceRegistration(
      DioLimitSwitchDevice.HEADER,
      "NI",
      DioLimitSwitchDevice.DEVICE_TYPE,
      "Limit Switch",
      DeviceRole.MISC,
      false,
      config -> new DioLimitSwitchDevice(config.getId(), config.getLabel(), config.isInvert()));

  private final List<DeviceTypeBucket> buckets = new ArrayList<>();

  /**
   * NAME
   *   NiDeviceGroup - Construct NI device buckets.
   */
  public NiDeviceGroup() {
    register(ROBORIO_REGISTRATION);
    register(LIMIT_SWITCH_REGISTRATION);
  }

  @Override
  public RegistrationHeader getHeader() {
    return HEADER;
  }

  @Override
  public List<DeviceTypeBucket> getDeviceBuckets() {
    return Collections.unmodifiableList(buckets);
  }

  @Override
  public DeviceAddResult addNextMotor() {
    return null;
  }

  @Override
  public void resetLowCurrentTimers() {}

  @Override
  public List<DeviceUnit> getTestDevices() {
    return new ArrayList<>();
  }

  @Override
  public void addAll() {
    for (DeviceTypeBucket bucket : buckets) {
      bucket.addAll();
    }
  }

  @Override
  public void setDuty(double duty) {}

  @Override
  public void stopAll() {}

  @Override
  public void clearFaults() {
    for (DeviceTypeBucket bucket : buckets) {
      for (DeviceUnit device : bucket.getDevices()) {
        device.clearFaults();
      }
    }
  }

  @Override
  public void closeAll() {
    for (DeviceTypeBucket bucket : buckets) {
      for (DeviceUnit device : bucket.getDevices()) {
        device.shutdown();
      }
      bucket.resetAddPointer();
    }
  }

  @Override
  public List<DeviceSnapshot> captureSnapshots(double nowSec) {
    List<DeviceSnapshot> devices = new ArrayList<>();
    for (DeviceTypeBucket bucket : buckets) {
      for (DeviceUnit device : bucket.getDevices()) {
        devices.add(device.snapshot());
      }
    }
    return devices;
  }

  private void register(DeviceRegistration registration) {
    List<DeviceConfig> configs = BringupUtil.getDeviceConfigs(
        registration.vendor(),
        registration.deviceType());
    List<DeviceUnit> devices = new ArrayList<>();
    for (DeviceConfig config : configs) {
      devices.add(registration.factory().create(config));
    }
    buckets.add(new DeviceTypeBucket(registration, devices, false));
  }
}
