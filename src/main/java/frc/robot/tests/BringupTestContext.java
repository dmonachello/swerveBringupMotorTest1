package frc.robot.tests;

import frc.robot.DeviceLifecycleRegistry;
import frc.robot.devices.DeviceUnit;
import frc.robot.manufacturers.ManufacturerGroup;
import frc.robot.manufacturers.DeviceTypeBucket;
import java.util.List;

/**
 * NAME
 *   BringupTestContext - Device lookup context for tests.
 *
 * DESCRIPTION
 *   Provides access to instantiated devices grouped by manufacturer.
 */
public final class BringupTestContext {
  private final List<ManufacturerGroup> groups;
  private final DeviceLifecycleRegistry deviceLifecycle;
  private long runId = 0;

  /**
   * NAME
   *   BringupTestContext - Construct a test context.
   *
   * PARAMETERS
   *   groups - Manufacturer groups to search.
   */
  public BringupTestContext(
      List<ManufacturerGroup> groups,
      DeviceLifecycleRegistry deviceLifecycle) {
    this.groups = groups;
    this.deviceLifecycle = deviceLifecycle;
  }

  public BringupTestContext(List<ManufacturerGroup> groups) {
    this(groups, null);
  }

  /**
   * NAME
   *   setRunId - Set the current test run identifier.
   *
   * PARAMETERS
   *   runId - Monotonic test run identifier.
   */
  public void setRunId(long runId) {
    this.runId = runId;
  }

  /**
   * NAME
   *   getRunId - Return the current test run identifier.
   *
   * RETURNS
   *   Current run identifier or 0 when unset.
   */
  public long getRunId() {
    return runId;
  }

  /**
   * NAME
   *   findDevice - Locate a device by vendor/type/id.
   *
   * PARAMETERS
   *   vendor - Vendor name.
   *   deviceType - Device type name.
   *   canId - CAN ID.
   *
   * RETURNS
   *   Matching DeviceUnit or null if not found.
   */
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

  /**
   * NAME
   *   findDeviceByLabel - Locate a device by label.
   *
   * PARAMETERS
   *   label - Device label from bringup_system.json.
   *
   * RETURNS
   *   Matching DeviceUnit or null if not found.
   */
  public DeviceUnit findDeviceByLabel(String label) {
    if (label == null || label.isBlank()) {
      return null;
    }
    String needle = label.trim();
    if (needle.isEmpty()) {
      return null;
    }
    for (ManufacturerGroup group : groups) {
      if (group == null) {
        continue;
      }
      for (DeviceTypeBucket bucket : group.getDeviceBuckets()) {
        for (DeviceUnit device : bucket.getDevices()) {
          if (device == null) {
            continue;
          }
          String deviceLabel = device.getLabel();
          if (deviceLabel == null || deviceLabel.isBlank()) {
            continue;
          }
          if (deviceLabel.trim().equalsIgnoreCase(needle)) {
            return device;
          }
        }
      }
    }
    return null;
  }

  /**
   * NAME
   *   isDeviceTestable - Return whether a device is lifecycle-testable.
   *
   * PARAMETERS
   *   label - Device label from bringup_system.json.
   *
   * RETURNS
   *   True when lifecycle state currently permits active testing.
   */
  public boolean isDeviceTestable(String label) {
    return deviceLifecycle == null || deviceLifecycle.isOperationAllowed(label);
  }

  public boolean isDeviceOperationAllowed(String label) {
    return isDeviceTestable(label);
  }

  /**
   * NAME
   *   isDeviceInstantiable - Return whether a device may be instantiated now.
   *
   * PARAMETERS
   *   label - Device label from bringup_system.json.
   *
   * RETURNS
   *   True when lifecycle state currently permits instantiation.
   */
  public boolean isDeviceInstantiable(String label) {
    return deviceLifecycle == null || deviceLifecycle.isInstantiationAllowed(label);
  }

  /**
   * NAME
   *   isDeviceSnapshotAllowed - Return whether a device may be sampled now.
   *
   * PARAMETERS
   *   label - Device label from bringup_system.json.
   *
   * RETURNS
   *   True when lifecycle state currently permits snapshot/signal access.
   */
  public boolean isDeviceSnapshotAllowed(String label) {
    return deviceLifecycle == null || deviceLifecycle.isSnapshotAllowed(label);
  }

  /**
   * NAME
   *   deviceLifecycleView - Return lifecycle view for one device label.
   *
   * PARAMETERS
   *   label - Device label from bringup_system.json.
   *
   * RETURNS
   *   Published lifecycle view or null when unavailable.
   */
  public DeviceLifecycleRegistry.DeviceLifecycleView deviceLifecycleView(String label) {
    return deviceLifecycle != null ? deviceLifecycle.viewForLabel(label) : null;
  }
}
