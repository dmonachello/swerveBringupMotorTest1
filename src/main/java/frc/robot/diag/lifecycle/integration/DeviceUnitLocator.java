package frc.robot.diag.lifecycle.integration;

import frc.robot.devices.DeviceUnit;

/**
 * NAME
 *     DeviceUnitLocator - resolve existing bringup device wrappers by lifecycle label.
 *
 * DESCRIPTION
 *     DeviceUnitLocator is the narrow integration seam between the passive lifecycle model and
 *     the existing bringup wrapper catalog already owned by BringupCore.
 */
public interface DeviceUnitLocator {
    /**
     * NAME
     *     findByLabel - resolve one configured bringup wrapper by lifecycle label.
     *
     * PARAMETERS
     *     label - lifecycle device label.
     *
     * RETURNS
     *     Existing bringup device wrapper, or null when the label is unknown to the current core.
     */
    DeviceUnit findByLabel(String label);
}
