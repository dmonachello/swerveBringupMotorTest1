package frc.robot.diag.lifecycle.factory;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.diag.lifecycle.devices.DeviceLifecycleKind;
import frc.robot.diag.lifecycle.devices.DeviceRecord;
import org.junit.jupiter.api.Test;

class FakeDeviceFactoryTest {
    private static final String DRIVE_LABEL = "front_left_drive";
    private static final String STEER_LABEL = "front_left_steer";
    private static final int ZERO_COUNT = 0;
    private static final int ONE_COUNT = 1;
    private static final int TWO_COUNT = 2;
    private static final int THREE_COUNT = 3;

    @Test
    void factoryCreatesLiveDeviceOnlyWhenAsked() {
        FakeDeviceFactory factory = new FakeDeviceFactory();

        assertEquals(ZERO_COUNT, factory.activeDeviceCount());
        assertEquals(ZERO_COUNT, factory.totalCreationAttempts());

        LiveDevice liveDevice = factory.create(normalDevice(DRIVE_LABEL));

        assertEquals(DRIVE_LABEL, liveDevice.label());
        assertFalse(liveDevice.isClosed());
        assertEquals(ONE_COUNT, factory.activeDeviceCount());
        assertEquals(ONE_COUNT, factory.totalCreationAttempts());
        assertEquals(ONE_COUNT, factory.creationAttemptsFor(DRIVE_LABEL));
        assertEquals(ONE_COUNT, factory.createdLabels().size());
    }

    @Test
    void normalDeviceIsClosedWhenClosedExplicitly() {
        FakeDeviceFactory factory = new FakeDeviceFactory();
        LiveDevice liveDevice = factory.create(normalDevice(DRIVE_LABEL));

        liveDevice.close();

        assertTrue(liveDevice.isClosed());
        assertEquals(ZERO_COUNT, factory.activeDeviceCount());
        assertEquals(ONE_COUNT, factory.closedLabels().size());
        assertEquals(DRIVE_LABEL, factory.closedLabels().get(0));
    }

    @Test
    void failedFakeConstructionIsReported() {
        FakeDeviceFactory factory = new FakeDeviceFactory();
        factory.configureFailure(DRIVE_LABEL);

        assertThrows(
                FakeDeviceConstructionException.class,
                () -> factory.create(normalDevice(DRIVE_LABEL)));
        assertEquals(ZERO_COUNT, factory.activeDeviceCount());
        assertEquals(ONE_COUNT, factory.totalCreationAttempts());
    }

    @Test
    void fakeConstructionCountersAreCorrect() {
        FakeDeviceFactory factory = new FakeDeviceFactory();

        LiveDevice drive = factory.create(normalDevice(DRIVE_LABEL));
        LiveDevice steer = factory.create(normalDevice(STEER_LABEL));
        drive.close();
        factory.configureFailure(DRIVE_LABEL);
        assertThrows(
                FakeDeviceConstructionException.class,
                () -> factory.create(normalDevice(DRIVE_LABEL)));

        assertEquals(THREE_COUNT, factory.totalCreationAttempts());
        assertEquals(TWO_COUNT, factory.creationAttemptsFor(DRIVE_LABEL));
        assertEquals(ONE_COUNT, factory.creationAttemptsFor(STEER_LABEL));
        assertEquals(TWO_COUNT, factory.createdLabels().size());
        assertEquals(ONE_COUNT, factory.closedLabels().size());
        assertEquals(ONE_COUNT, factory.activeDeviceCount());
        assertEquals(STEER_LABEL, factory.activeLabels().get(0));

        steer.close();
    }

    private static DeviceRecord normalDevice(String label) {
        return new DeviceRecord(label, DeviceLifecycleKind.NORMAL);
    }
}
