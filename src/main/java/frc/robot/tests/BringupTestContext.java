package frc.robot.tests;

import frc.robot.devices.DeviceUnit;
import frc.robot.manufacturers.ManufacturerGroup;
import frc.robot.manufacturers.DeviceTypeBucket;
import java.util.List;

public final class BringupTestContext {
  private final List<ManufacturerGroup> groups;

  public BringupTestContext(List<ManufacturerGroup> groups) {
    this.groups = groups;
  }

  public DeviceUnit findDevice(String vendor, String deviceType, int canId) {
    if (vendor == null || deviceType == null) {
      return null;
    }
    String vendorUpper = vendor.trim().toUpperCase();
    String typeUpper = deviceType.trim().toUpperCase();
    for (ManufacturerGroup group : groups) {
      if (group == null || group.getHeader() == null) {
        continue;
      }
      String groupVendor = group.getHeader().vendor();
      if (groupVendor == null || !groupVendor.trim().equalsIgnoreCase(vendorUpper)) {
        continue;
      }
      for (DeviceTypeBucket bucket : group.getDeviceBuckets()) {
        for (DeviceUnit device : bucket.getDevices()) {
          if (device == null) {
            continue;
          }
          if (device.getCanId() != canId) {
            continue;
          }
          String deviceTypeName = device.getDeviceType();
          if (deviceTypeName != null && deviceTypeName.trim().equalsIgnoreCase(typeUpper)) {
            return device;
          }
        }
      }
    }
    return null;
  }
}
