package frc.robot.manufacturers;

import frc.robot.devices.DeviceUnit;
import frc.robot.BringupPrinter;
import java.util.List;

// Holds per-device-type state and devices for a manufacturer.
public final class DeviceTypeBucket {
  private final DeviceRegistration registration;
  private final List<DeviceUnit> devices;
  private final double[] lowCurrentStartSec;
  private int nextIndex = 0;

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

  public void resetLowCurrentTimers() {
    if (lowCurrentStartSec == null) {
      return;
    }
    for (int i = 0; i < lowCurrentStartSec.length; i++) {
      lowCurrentStartSec[i] = -1.0;
    }
  }

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

  public void resetAddPointer() {
    nextIndex = 0;
  }
}
