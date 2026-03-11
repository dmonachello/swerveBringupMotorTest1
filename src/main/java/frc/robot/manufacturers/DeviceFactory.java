package frc.robot.manufacturers;

import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;

/**
 * NAME
 * DeviceFactory
 *
 * SYNOPSIS
 * Factory for constructing a device instance from configuration.
 */
@FunctionalInterface
public interface DeviceFactory {
  /**
   * NAME
   * create
   *
   * SYNOPSIS
   * Construct a device instance for a configured slot.
   *
   * PARAMETERS
   * config - resolved device configuration.
   *
   * RETURNS
   * A newly constructed device unit.
   */
  DeviceUnit create(BringupUtil.DeviceConfig config);
}
