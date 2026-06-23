package frc.robot.diag.lifecycle.devices;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

import frc.robot.diag.lifecycle.labels.LabelKind;
import frc.robot.diag.lifecycle.runtime.DeviceRuntimeState;
import frc.robot.diag.lifecycle.runtime.HealthState;
import frc.robot.diag.lifecycle.runtime.PresenceState;
import java.util.List;
import org.junit.jupiter.api.Test;

class DeviceCatalogTest {
    private static final String DRIVE_LABEL = "front_left_drive";
    private static final String PDH_LABEL = "pdh";
    private static final int EXPECTED_DEVICE_COUNT = 2;
    private static final int EXPECTED_LIVE_DEVICE_COUNT = 0;

    @Test
    void deviceRecordsExistAfterLoad() {
        DeviceCatalog catalog = loadCatalog();

        DeviceRecord drive = catalog.deviceRecord(DRIVE_LABEL);
        DeviceRecord pdh = catalog.deviceRecord(PDH_LABEL);

        assertEquals(DRIVE_LABEL, drive.label());
        assertEquals(PDH_LABEL, pdh.label());
        assertEquals(EXPECTED_DEVICE_COUNT, catalog.deviceRecords().size());
    }

    @Test
    void runtimeStateExistsAfterLoad() {
        DeviceCatalog catalog = loadCatalog();

        DeviceRuntimeState driveRuntime = catalog.runtimeState(DRIVE_LABEL);
        DeviceRuntimeState pdhRuntime = catalog.runtimeState(PDH_LABEL);

        assertNotNull(driveRuntime);
        assertNotNull(pdhRuntime);
        assertEquals(EXPECTED_DEVICE_COUNT, catalog.runtimeStates().size());
    }

    @Test
    void noLiveDeviceObjectsAreCreatedAfterLoad() {
        DeviceCatalog catalog = loadCatalog();

        assertEquals(EXPECTED_LIVE_DEVICE_COUNT, catalog.liveDeviceCount());
        assertFalse(catalog.runtimeState(DRIVE_LABEL).isInstantiated());
        assertFalse(catalog.runtimeState(PDH_LABEL).isInstantiated());
    }

    @Test
    void singletonFlagIsStoredCorrectly() {
        DeviceCatalog catalog = loadCatalog();

        assertEquals(DeviceLifecycleKind.SINGLETON, catalog.deviceRecord(PDH_LABEL).lifecycleKind());
    }

    @Test
    void normalFlagIsStoredCorrectly() {
        DeviceCatalog catalog = loadCatalog();

        assertEquals(DeviceLifecycleKind.NORMAL, catalog.deviceRecord(DRIVE_LABEL).lifecycleKind());
    }

    @Test
    void loadRegistersDeviceLabelsInTheGlobalNamespace() {
        DeviceCatalog catalog = loadCatalog();

        assertEquals(LabelKind.DEVICE, catalog.labelRegistry().labelKindOf(DRIVE_LABEL));
        assertEquals(LabelKind.DEVICE, catalog.labelRegistry().labelKindOf(PDH_LABEL));
    }

    @Test
    void runtimeStateStartsInactiveAndUnknown() {
        DeviceCatalog catalog = loadCatalog();

        DeviceRuntimeState runtimeState = catalog.runtimeState(DRIVE_LABEL);

        assertFalse(runtimeState.isActive());
        assertFalse(runtimeState.isInstantiated());
        assertNull(runtimeState.activeSessionId());
        assertNull(runtimeState.activeGroupLabel());
        assertNull(runtimeState.lastActivationMode());
        assertNull(runtimeState.lastError());
        assertEquals(PresenceState.UNKNOWN, runtimeState.presenceState());
        assertEquals(HealthState.UNKNOWN, runtimeState.healthState());
    }

    private static DeviceCatalog loadCatalog() {
        return DeviceCatalog.load(List.of(
                new DeviceDeclaration(DRIVE_LABEL, DeviceLifecycleKind.NORMAL),
                new DeviceDeclaration(PDH_LABEL, DeviceLifecycleKind.SINGLETON)));
    }
}
