package frc.robot.diag.lifecycle.integration;

import frc.robot.BringupCore;
import frc.robot.diag.lifecycle.activation.ActivationManager;

/**
 * NAME
 *     ControlledBringupLifecycleRuntime - internal robot-side runtime wrapper for lifecycle core.
 *
 * DESCRIPTION
 *     This class binds the passive lifecycle catalogs to the current BringupCore wrapper inventory
 *     through a DeviceUnit-backed lifecycle factory. It remains internal until the existing robot
 *     command path is migrated to call it deliberately.
 */
public final class ControlledBringupLifecycleRuntime {
    private final LifecycleCatalogBundle catalogBundle;
    private final ActivationManager activationManager;

    public ControlledBringupLifecycleRuntime(
            LifecycleCatalogBundle catalogBundle,
            ActivationManager activationManager) {
        this.catalogBundle = catalogBundle;
        this.activationManager = activationManager;
    }

    /**
     * NAME
     *     fromBringupCore - bind lifecycle catalogs to the current bringup core wrappers.
     *
     * PARAMETERS
     *     core - active bringup core.
     *     catalogBundle - passive lifecycle catalogs derived from the current profile.
     *
     * RETURNS
     *     Internal lifecycle runtime ready for activation-manager use.
     */
    public static ControlledBringupLifecycleRuntime fromBringupCore(
            BringupCore core, LifecycleCatalogBundle catalogBundle) {
        DeviceUnitLifecycleFactory factory =
                new DeviceUnitLifecycleFactory(new BringupCoreDeviceUnitLocator(core));
        ActivationManager manager =
                new ActivationManager(
                        catalogBundle.deviceCatalog(), catalogBundle.labelResolver(), factory);
        return new ControlledBringupLifecycleRuntime(catalogBundle, manager);
    }

    public LifecycleCatalogBundle catalogBundle() {
        return catalogBundle;
    }

    public ActivationManager activationManager() {
        return activationManager;
    }
}
