package frc.robot.diag.lifecycle.integration;

import frc.robot.BringupCore;
import frc.robot.devices.DeviceUnit;

/**
 * NAME
 *     BringupCoreDeviceUnitLocator - core-backed resolver for existing bringup device wrappers.
 *
 * DESCRIPTION
 *     This adapter reuses the current BringupCore device-wrapper inventory instead of allocating
 *     a second set of wrapper objects for the lifecycle proof-of-concept port.
 */
public final class BringupCoreDeviceUnitLocator implements DeviceUnitLocator {
    private final BringupCore core;

    public BringupCoreDeviceUnitLocator(BringupCore core) {
        this.core = core;
    }

    @Override
    public DeviceUnit findByLabel(String label) {
        return core != null ? core.findDeviceByLabel(label) : null;
    }
}
