package frc.robot.manufacturers;

import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.devices.template.TemplateMotorDevice;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * NAME
 * TemplateDeviceGroup
 *
 * SYNOPSIS
 * Template manufacturer group for new vendor integrations.
 *
 * DESCRIPTION
 * Provides a minimal manufacturer wrapper and device bucket for example use.
 */
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

  /**
   * NAME
   * TemplateDeviceGroup
   *
   * SYNOPSIS
   * Construct an empty template device group.
   *
   * DESCRIPTION
   * Creates a group with no configured devices.
   */
  public TemplateDeviceGroup() {
    this(new int[0], new String[0], new BringupUtil.LimitConfig[0], "MotorController");
  }

  /**
   * NAME
   * TemplateDeviceGroup
   *
   * SYNOPSIS
   * Construct a template device group from explicit configuration arrays.
   *
   * PARAMETERS
   * canIds - CAN IDs for each device.
   * labels - labels for each device.
   * limits - optional limit switch configuration per device.
   * deviceType - device type token for reporting.
   */
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

  /**
   * NAME
   * addNextMotor
   *
   * SYNOPSIS
   * Create the next device in the template bucket.
   *
   * RETURNS
   * A result describing the created device, or null if none was added.
   *
   * SIDE EFFECTS
   * Constructs hardware objects and emits report output.
   */
  @Override
  public DeviceAddResult addNextMotor() {
    return bucket.addNext();
  }

  /**
   * NAME
   * resetLowCurrentTimers
   *
   * SYNOPSIS
   * Reset low-current timers for the template bucket.
   */
  @Override
  public void resetLowCurrentTimers() {
    bucket.resetLowCurrentTimers();
  }

  /**
   * NAME
   * getTestDevices
   *
   * SYNOPSIS
   * Return devices that expose custom tests.
   *
   * RETURNS
   * Empty list for the template group by default.
   */
  @Override
  public List<DeviceUnit> getTestDevices() {
    return new ArrayList<>();
  }

  /**
   * NAME
   * addAll
   *
   * SYNOPSIS
   * Create all devices in the template bucket.
   *
   * SIDE EFFECTS
   * Constructs hardware objects and emits report output.
   */
  @Override
  public void addAll() {
    bucket.addAll();
  }

  /**
   * NAME
   * setDuty
   *
   * SYNOPSIS
   * Apply an open-loop duty request to all template devices.
   *
   * PARAMETERS
   * duty - requested output in [-1, 1].
   */
  @Override
  public void setDuty(double duty) {
    for (DeviceUnit device : bucket.getDevices()) {
      device.setDuty(duty);
    }
  }

  /**
   * NAME
   * stopAll
   *
   * SYNOPSIS
   * Stop all template device outputs.
   */
  @Override
  public void stopAll() {
    for (DeviceUnit device : bucket.getDevices()) {
      device.stop();
    }
  }

  /**
   * NAME
   * clearFaults
   *
   * SYNOPSIS
   * Clear fault status on all template devices.
   */
  @Override
  public void clearFaults() {
    for (DeviceUnit device : bucket.getDevices()) {
      device.clearFaults();
    }
  }

  /**
   * NAME
   * closeAll
   *
   * SYNOPSIS
   * Close all template devices and reset add pointers.
   *
   * SIDE EFFECTS
   * Releases device resources and resets device creation state.
   */
  @Override
  public void closeAll() {
    for (DeviceUnit device : bucket.getDevices()) {
      device.close();
    }
    bucket.resetAddPointer();
  }

  /**
   * NAME
   * captureSnapshots
   *
   * SYNOPSIS
   * Capture snapshots for all template devices.
   *
   * PARAMETERS
   * nowSec - current time in seconds for timestamping.
   *
   * RETURNS
   * List of device snapshots.
   */
  @Override
  public List<DeviceSnapshot> captureSnapshots(double nowSec) {
    List<DeviceSnapshot> devices = new ArrayList<>();
    for (DeviceUnit device : bucket.getDevices()) {
      devices.add(device.snapshot());
    }
    return devices;
  }
}
