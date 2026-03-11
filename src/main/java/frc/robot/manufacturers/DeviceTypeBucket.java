package frc.robot.manufacturers;

import frc.robot.devices.DeviceUnit;
import frc.robot.BringupPrinter;
import java.util.List;

/**
 * NAME
 * DeviceTypeBucket
 *
 * SYNOPSIS
 * Holds per-device-type state and devices for a manufacturer.
 *
 * DESCRIPTION
 * Tracks construction status and optional low-current timers for a device type.
 */
public final class DeviceTypeBucket {
  private final DeviceRegistration registration;
  private final List<DeviceUnit> devices;
  private final double[] lowCurrentStartSec;
  private int nextIndex = 0;

  /**
   * NAME
   * DeviceTypeBucket
   *
   * SYNOPSIS
   * Create a bucket for devices of a single type.
   *
   * PARAMETERS
   * registration - registration metadata for the device type.
   * devices - ordered list of device instances.
   * trackLowCurrent - whether to track low current timing per device.
   *
   * SIDE EFFECTS
   * Initializes low-current timers when tracking is enabled.
   */
  public DeviceTypeBucket(
      DeviceRegistration registration,
      List<DeviceUnit> devices,
      boolean trackLowCurrent) {
    this.registration = registration;
    this.devices = devices;
    this.lowCurrentStartSec = trackLowCurrent ? new double[devices.size()] : null;
    if (trackLowCurrent) {
      resetLowCurrentTimers();
    }
  }

  public DeviceRegistration getRegistration() {
    return registration;
  }

  public List<DeviceUnit> getDevices() {
    return devices;
  }

  public double[] getLowCurrentStartSec() {
    return lowCurrentStartSec;
  }

  public boolean tracksLowCurrent() {
    return lowCurrentStartSec != null;
  }

  /**
   * NAME
   * resetLowCurrentTimers
   *
   * SYNOPSIS
   * Reset all low-current timers to an unset state.
   *
   * SIDE EFFECTS
   * Overwrites low-current timer state for each device.
   */
  public void resetLowCurrentTimers() {
    if (lowCurrentStartSec == null) {
      return;
    }
    for (int i = 0; i < lowCurrentStartSec.length; i++) {
      lowCurrentStartSec[i] = -1.0;
    }
  }

  /**
   * NAME
   * addNext
   *
   * SYNOPSIS
   * Create the next device in this bucket if available.
   *
   * DESCRIPTION
   * Ensures the next device is constructed, advances the index, and reports it.
   *
   * RETURNS
   * A result describing the created device, or null if none was created.
   *
   * SIDE EFFECTS
   * Constructs hardware objects and emits report output.
   */
  public DeviceAddResult addNext() {
    if (nextIndex < devices.size() && !devices.get(nextIndex).isCreated()) {
      int index = nextIndex;
      DeviceUnit device = devices.get(nextIndex);
      device.ensureCreated();
      BringupPrinter.enqueue(
          "Device created: " + registration.displayName() +
          " index " + index +
          " CAN " + device.getCanId());
      nextIndex++;
      return new DeviceAddResult(device, index, registration);
    }
    return null;
  }

  /**
   * NAME
   * addAll
   *
   * SYNOPSIS
   * Create all devices in this bucket.
   *
   * SIDE EFFECTS
   * Constructs hardware objects and emits report output per device.
   */
  public void addAll() {
    for (int i = 0; i < devices.size(); i++) {
      DeviceUnit device = devices.get(i);
      device.ensureCreated();
      BringupPrinter.enqueue(
          "Device created: " + registration.displayName() +
          " index " + i +
          " CAN " + device.getCanId());
    }
    nextIndex = devices.size();
  }

  /**
   * NAME
   * resetAddPointer
   *
   * SYNOPSIS
   * Reset the add pointer to the start of the device list.
   */
  public void resetAddPointer() {
    nextIndex = 0;
  }
}
