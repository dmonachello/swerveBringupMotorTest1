package frc.robot.diag.lifecycle.integration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.devices.DeviceActionRequest;
import frc.robot.devices.DeviceLifecycleOwnership;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.lifecycle.devices.DeviceLifecycleKind;
import frc.robot.diag.lifecycle.devices.DeviceRecord;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class DeviceUnitLifecycleFactoryTest {
    private static final String LABEL_DRIVE = "front_left_drive";
    private static final String LABEL_PDH = "pdh";
    private static final String LABEL_MISSING = "missing_device";
    private static final String TYPE_MOTOR = "motor";
    private static final int CAN_ID_DEFAULT = 1;

    @Test
    void createEnsuresRuntimeOwnedWrapperIsCreated() {
        StubDeviceUnit drive = new StubDeviceUnit(LABEL_DRIVE, DeviceLifecycleOwnership.RUNTIME_OWNED_RECREATABLE);
        DeviceUnitLifecycleFactory factory = factoryWith(drive);

        var liveDevice = factory.create(new DeviceRecord(LABEL_DRIVE, DeviceLifecycleKind.NORMAL));

        assertEquals(LABEL_DRIVE, liveDevice.label());
        assertEquals(1, drive.ensureCreatedCount);
        assertTrue(drive.created);
        assertFalse(liveDevice.isClosed());
    }

    @Test
    void createFailsWhenWrapperIsMissing() {
        DeviceUnitLifecycleFactory factory = new DeviceUnitLifecycleFactory(new MapBackedLocator(Map.of()));

        assertThrows(
                IllegalStateException.class,
                () -> factory.create(new DeviceRecord(LABEL_MISSING, DeviceLifecycleKind.NORMAL)));
    }

    @Test
    void createFailsWhenSingletonDeclarationTargetsRuntimeOwnedWrapper() {
        StubDeviceUnit drive = new StubDeviceUnit(LABEL_DRIVE, DeviceLifecycleOwnership.RUNTIME_OWNED_RECREATABLE);
        DeviceUnitLifecycleFactory factory = factoryWith(drive);

        assertThrows(
                IllegalStateException.class,
                () -> factory.create(new DeviceRecord(LABEL_DRIVE, DeviceLifecycleKind.SINGLETON)));
    }

    @Test
    void createFailsWhenNormalDeclarationTargetsSingletonWrapper() {
        StubDeviceUnit pdh = new StubDeviceUnit(LABEL_PDH, DeviceLifecycleOwnership.APP_OWNED_SINGLETON_SERVICE);
        DeviceUnitLifecycleFactory factory = factoryWith(pdh);

        assertThrows(
                IllegalStateException.class,
                () -> factory.create(new DeviceRecord(LABEL_PDH, DeviceLifecycleKind.NORMAL)));
    }

    @Test
    void liveDeviceCloseDelegatesToWrappedDeviceUnit() {
        StubDeviceUnit drive = new StubDeviceUnit(LABEL_DRIVE, DeviceLifecycleOwnership.RUNTIME_OWNED_RECREATABLE);
        DeviceUnitLifecycleFactory factory = factoryWith(drive);

        var liveDevice = factory.create(new DeviceRecord(LABEL_DRIVE, DeviceLifecycleKind.NORMAL));
        liveDevice.close();

        assertEquals(1, drive.closeCount);
        assertTrue(liveDevice.isClosed());
    }

    private static DeviceUnitLifecycleFactory factoryWith(StubDeviceUnit deviceUnit) {
        Map<String, DeviceUnit> devicesByLabel = new LinkedHashMap<>();
        devicesByLabel.put(deviceUnit.getLabel(), deviceUnit);
        return new DeviceUnitLifecycleFactory(new MapBackedLocator(devicesByLabel));
    }

    private static final class MapBackedLocator implements DeviceUnitLocator {
        private final Map<String, DeviceUnit> devicesByLabel;

        private MapBackedLocator(Map<String, DeviceUnit> devicesByLabel) {
            this.devicesByLabel = devicesByLabel;
        }

        @Override
        public DeviceUnit findByLabel(String label) {
            return devicesByLabel.get(label);
        }
    }

    private static final class StubDeviceUnit implements DeviceUnit {
        private final String label;
        private final DeviceLifecycleOwnership ownership;
        private boolean created;
        private int ensureCreatedCount;
        private int closeCount;

        private StubDeviceUnit(String label, DeviceLifecycleOwnership ownership) {
            this.label = label;
            this.ownership = ownership;
        }

        @Override
        public int getCanId() {
            return CAN_ID_DEFAULT;
        }

        @Override
        public String getDeviceType() {
            return TYPE_MOTOR;
        }

        @Override
        public String getLabel() {
            return label;
        }

        @Override
        public boolean isCreated() {
            return created;
        }

        @Override
        public void ensureCreated() {
            ensureCreatedCount++;
            created = true;
        }

        @Override
        public void close() {
            closeCount++;
            created = false;
        }

        @Override
        public void clearFaults() {}

        @Override
        public DeviceLifecycleOwnership getLifecycleOwnership() {
            return ownership;
        }

        @Override
        public DeviceSnapshot snapshot() {
            return new DeviceSnapshot();
        }

        @Override
        public RegistrationHeader getHeader() {
            return new RegistrationHeader(TYPE_MOTOR, TYPE_MOTOR, TYPE_MOTOR, TYPE_MOTOR, TYPE_MOTOR, TYPE_MOTOR, TYPE_MOTOR);
        }

        @Override
        public boolean applyDeviceAction(DeviceActionRequest request) {
            return false;
        }
    }
}
