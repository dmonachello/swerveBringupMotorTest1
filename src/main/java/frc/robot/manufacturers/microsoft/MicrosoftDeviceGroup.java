package frc.robot.manufacturers.microsoft;

import frc.robot.BringupUtil;
import frc.robot.BringupUtil.DeviceConfig;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.manufacturers.DeviceAddResult;
import frc.robot.manufacturers.DeviceRegistration;
import frc.robot.manufacturers.DeviceRole;
import frc.robot.manufacturers.DeviceTypeBucket;
import frc.robot.manufacturers.ManufacturerGroup;
import frc.robot.registry.RegistrationHeader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * NAME
 *   MicrosoftDeviceGroup - Manufacturer group for Microsoft input devices.
 *
 * DESCRIPTION
 *   Keeps Xbox controllers in the configured device lifecycle so DSL tests
 *   reference them the same way they reference motors and sensors.
 */
public final class MicrosoftDeviceGroup implements ManufacturerGroup {
  public static final String VENDOR = "Microsoft";
  private static final String GROUP_KIND = "Manufacturer";
  private static final String GROUP_SOURCE = "WPILib";
  private static final String GROUP_OWNER = "Team";
  private static final String GROUP_VERSION = "2026-05-06";
  private static final String GROUP_DESCRIPTION = "Microsoft input device wrappers.";
  private static final String XBOX_DISPLAY_NAME = "Xbox Controller";
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      VENDOR,
      VENDOR,
      GROUP_KIND,
      GROUP_SOURCE,
      GROUP_OWNER,
      GROUP_VERSION,
      GROUP_DESCRIPTION);

  private static final DeviceRegistration XBOX_REGISTRATION = new DeviceRegistration(
      XboxControllerDevice.HEADER,
      VENDOR,
      XboxControllerDevice.DEVICE_TYPE,
      XBOX_DISPLAY_NAME,
      DeviceRole.MISC,
      false,
      config -> new XboxControllerDevice(config.getId(), config.getLabel()));

  private final List<DeviceTypeBucket> buckets = new ArrayList<>();

  /**
   * NAME
   *   MicrosoftDeviceGroup - Construct Microsoft device buckets.
   */
  public MicrosoftDeviceGroup() {
    register(XBOX_REGISTRATION);
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
  public void clearFaults() {}

  @Override
  public void closeAll() {
    for (DeviceTypeBucket bucket : buckets) {
      for (DeviceUnit device : bucket.getDevices()) {
        device.close();
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
