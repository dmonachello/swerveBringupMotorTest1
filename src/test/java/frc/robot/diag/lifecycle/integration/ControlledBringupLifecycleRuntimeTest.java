package frc.robot.diag.lifecycle.integration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.devices.DeviceActionRequest;
import frc.robot.devices.DeviceLifecycleOwnership;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.lifecycle.activation.ActivationMode;
import frc.robot.diag.lifecycle.devices.DeviceDeclaration;
import frc.robot.diag.lifecycle.devices.DeviceLifecycleKind;
import frc.robot.diag.lifecycle.devices.DeviceRecord;
import frc.robot.diag.lifecycle.devices.DeviceCatalog;
import frc.robot.diag.lifecycle.groups.GroupCatalog;
import frc.robot.diag.lifecycle.groups.GroupDeclaration;
import frc.robot.diag.lifecycle.labels.LabelResolver;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ControlledBringupLifecycleRuntimeTest {
    private static final String PROFILE_NAME = "test_profile";
    private static final String LABEL_DRIVE = "front_left_drive";
    private static final String LABEL_PDH = "pdh";
    private static final String LABEL_GROUP = "drive_and_power";
    private static final String TYPE_MOTOR = "motor";
    private static final int CAN_ID_DEFAULT = 1;

    @Test
    void activationManagerBuiltFromDeviceUnitFactoryPreservesSingletonCloseSemantics() {
        StubDeviceUnit drive =
                new StubDeviceUnit(LABEL_DRIVE, DeviceLifecycleOwnership.RUNTIME_OWNED_RECREATABLE);
        StubDeviceUnit pdh =
                new StubDeviceUnit(LABEL_PDH, DeviceLifecycleOwnership.APP_OWNED_SINGLETON_SERVICE);
        ControlledBringupLifecycleRuntime runtime =
                new ControlledBringupLifecycleRuntime(
                        bundle(),
                        new frc.robot.diag.lifecycle.activation.ActivationManager(
                                bundle().deviceCatalog(),
                                bundle().labelResolver(),
                                new DeviceUnitLifecycleFactory(
                                        new MapBackedLocator(mapOf(drive, pdh)))));

        var activation =
                runtime.activationManager().activate(LABEL_GROUP, ActivationMode.READ_ONLY);
        assertTrue(activation.success());

        var deactivation = runtime.activationManager().deactivateActive();
        assertTrue(deactivation.success());
        assertEquals(1, drive.closeCount);
        assertEquals(0, pdh.closeCount);
        assertFalse(drive.isCreated());
        assertTrue(pdh.isCreated());
    }

    private static LifecycleCatalogBundle bundle() {
        DeviceCatalog deviceCatalog =
                DeviceCatalog.load(
                        List.of(
                                new DeviceDeclaration(LABEL_DRIVE, DeviceLifecycleKind.NORMAL),
                                new DeviceDeclaration(LABEL_PDH, DeviceLifecycleKind.SINGLETON)));
        GroupCatalog groupCatalog =
                GroupCatalog.load(
                        deviceCatalog,
                        List.of(new GroupDeclaration(LABEL_GROUP, List.of(LABEL_DRIVE, LABEL_PDH))));
        return new LifecycleCatalogBundle(
                PROFILE_NAME, deviceCatalog, groupCatalog, new LabelResolver(deviceCatalog, groupCatalog));
    }

    private static Map<String, DeviceUnit> mapOf(StubDeviceUnit... devices) {
        Map<String, DeviceUnit> devicesByLabel = new LinkedHashMap<>();
        for (StubDeviceUnit device : devices) {
            devicesByLabel.put(device.getLabel(), device);
        }
        return devicesByLabel;
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
