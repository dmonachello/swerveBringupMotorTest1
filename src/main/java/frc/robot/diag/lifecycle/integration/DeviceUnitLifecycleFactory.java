package frc.robot.diag.lifecycle.integration;

import frc.robot.devices.DeviceLifecycleOwnership;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.lifecycle.devices.DeviceLifecycleKind;
import frc.robot.diag.lifecycle.devices.DeviceRecord;
import frc.robot.diag.lifecycle.factory.DeviceFactory;
import frc.robot.diag.lifecycle.factory.LiveDevice;

/**
 * NAME
 *     DeviceUnitLifecycleFactory - lifecycle factory that activates existing bringup device wrappers.
 *
 * DESCRIPTION
 *     The main repo already constructs one wrapper per configured device label. This factory keeps
 *     that model intact and treats ensureCreated()/close() as the lifecycle-owned vendor boundary.
 */
public final class DeviceUnitLifecycleFactory implements DeviceFactory {
    private static final String ERROR_MISSING_DEVICE_WRAPPER =
            "Missing bringup device wrapper for lifecycle label: ";
    private static final String ERROR_DEVICE_NOT_CREATED =
            "Bringup device wrapper did not enter created state: ";
    private static final String ERROR_EXPECTED_SINGLETON =
            "Lifecycle declaration expects singleton wrapper ownership: ";
    private static final String ERROR_EXPECTED_RUNTIME_OWNED =
            "Lifecycle declaration expects runtime-owned wrapper ownership: ";

    private final DeviceUnitLocator locator;

    public DeviceUnitLifecycleFactory(DeviceUnitLocator locator) {
        this.locator = locator;
    }

    @Override
    public LiveDevice create(DeviceRecord deviceRecord) {
        DeviceUnit deviceUnit = locator.findByLabel(deviceRecord.label());
        if (deviceUnit == null) {
            throw new IllegalStateException(ERROR_MISSING_DEVICE_WRAPPER + deviceRecord.label());
        }
        validateOwnership(deviceRecord, deviceUnit);
        deviceUnit.ensureCreated();
        if (!deviceUnit.isCreated()) {
            throw new IllegalStateException(ERROR_DEVICE_NOT_CREATED + deviceRecord.label());
        }
        return new DeviceUnitLiveDevice(deviceUnit);
    }

    private void validateOwnership(DeviceRecord deviceRecord, DeviceUnit deviceUnit) {
        boolean recordSingleton = deviceRecord.lifecycleKind() == DeviceLifecycleKind.SINGLETON;
        boolean wrapperSingleton =
                deviceUnit.getLifecycleOwnership()
                        == DeviceLifecycleOwnership.APP_OWNED_SINGLETON_SERVICE;
        if (recordSingleton && !wrapperSingleton) {
            throw new IllegalStateException(ERROR_EXPECTED_SINGLETON + deviceRecord.label());
        }
        if (!recordSingleton && wrapperSingleton) {
            throw new IllegalStateException(ERROR_EXPECTED_RUNTIME_OWNED + deviceRecord.label());
        }
    }
}
