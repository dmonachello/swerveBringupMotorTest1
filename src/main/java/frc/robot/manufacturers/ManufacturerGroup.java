package frc.robot.manufacturers;

import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.devices.DeviceUnit;
import frc.robot.registry.RegistrationHeader;
import java.util.List;

/**
 * NAME
 * ManufacturerGroup
 *
 * SYNOPSIS
 * Common interface for manufacturer device groups.
 *
 * DESCRIPTION
 * Provides lifecycle and diagnostic operations for all devices of a vendor.
 */
public interface ManufacturerGroup {
  /**
   * NAME
   * getHeader
   *
   * SYNOPSIS
   * Return the vendor registration header.
   *
   * RETURNS
   * Header metadata describing the vendor group.
   */
  RegistrationHeader getHeader();

  /**
   * NAME
   * getDeviceBuckets
   *
   * SYNOPSIS
   * Return buckets grouped by device type.
   *
   * RETURNS
   * List of per-type buckets for this vendor.
   */
  List<DeviceTypeBucket> getDeviceBuckets();

  /**
   * NAME
   * addNextMotor
   *
   * SYNOPSIS
   * Create the next motor in the group, if any.
   *
   * RETURNS
   * A result describing the created device, or null if no motor was added.
   *
   * SIDE EFFECTS
   * Constructs hardware objects and emits report output.
   */
  DeviceAddResult addNextMotor();

  /**
   * NAME
   * resetLowCurrentTimers
   *
   * SYNOPSIS
   * Reset low-current timers for all buckets that track them.
   */
  void resetLowCurrentTimers();

  /**
   * NAME
   * getTestDevices
   *
   * SYNOPSIS
   * Return devices that expose custom tests.
   *
   * RETURNS
   * Devices with tests that can be surfaced in the UI.
   */
  List<DeviceUnit> getTestDevices();

  /**
   * NAME
   * addAll
   *
   * SYNOPSIS
   * Create all devices in the group.
   *
   * SIDE EFFECTS
   * Constructs hardware objects and emits report output.
   */
  void addAll();

  /**
   * NAME
   * setDuty
   *
   * SYNOPSIS
   * Apply an open-loop duty request to all motor devices.
   *
   * PARAMETERS
   * duty - requested output in [-1, 1].
   */
  void setDuty(double duty);

  /**
   * NAME
   * stopAll
   *
   * SYNOPSIS
   * Stop all actuators managed by this group.
   */
  void stopAll();

  /**
   * NAME
   * clearFaults
   *
   * SYNOPSIS
   * Clear fault status on supported devices.
   */
  void clearFaults();

  /**
   * NAME
   * closeAll
   *
   * SYNOPSIS
   * Release all vendor resources in this group.
   */
  void closeAll();

  /**
   * NAME
   * captureSnapshots
   *
   * SYNOPSIS
   * Capture device snapshots for reporting.
   *
   * PARAMETERS
   * nowSec - current time in seconds for timestamping.
   *
   * RETURNS
   * Snapshot list for all known devices.
   */
  List<DeviceSnapshot> captureSnapshots(double nowSec);
}
