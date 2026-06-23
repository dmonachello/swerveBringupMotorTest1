package frc.robot.diag.lifecycle.factory;

import frc.robot.diag.lifecycle.devices.DeviceRecord;

/**
 * NAME
 *     DeviceFactory - construct live lifecycle-managed device wrappers from declared records.
 */
public interface DeviceFactory {
    /**
     * NAME
     *     create - build a live device wrapper for one declared device.
     *
     * PARAMETERS
     *     deviceRecord - declared lifecycle device facts.
     *
     * RETURNS
     *     A live device wrapper.
     */
    LiveDevice create(DeviceRecord deviceRecord);
}
