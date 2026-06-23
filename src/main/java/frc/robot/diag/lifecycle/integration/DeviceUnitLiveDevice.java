package frc.robot.diag.lifecycle.integration;

import frc.robot.devices.DeviceUnit;
import frc.robot.diag.lifecycle.factory.LiveDevice;

/**
 * NAME
 *     DeviceUnitLiveDevice - lifecycle LiveDevice wrapper around an existing bringup DeviceUnit.
 *
 * DESCRIPTION
 *     ActivationManager only needs label identity and close semantics. This wrapper delegates both
 *     to the existing bringup device wrapper that already owns vendor-resource lifetime.
 */
public final class DeviceUnitLiveDevice implements LiveDevice {
    private final DeviceUnit deviceUnit;

    public DeviceUnitLiveDevice(DeviceUnit deviceUnit) {
        this.deviceUnit = deviceUnit;
    }

    @Override
    public String label() {
        return deviceUnit.getLabel();
    }

    @Override
    public boolean isClosed() {
        return !deviceUnit.isCreated();
    }

    @Override
    public void close() {
        deviceUnit.close();
    }
}
