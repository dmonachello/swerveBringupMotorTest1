package frc.robot.diag.lifecycle.activation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.diag.lifecycle.devices.DeviceCatalog;
import frc.robot.diag.lifecycle.devices.DeviceDeclaration;
import frc.robot.diag.lifecycle.devices.DeviceLifecycleKind;
import frc.robot.diag.lifecycle.factory.FakeDeviceFactory;
import frc.robot.diag.lifecycle.groups.GroupCatalog;
import frc.robot.diag.lifecycle.groups.GroupDeclaration;
import frc.robot.diag.lifecycle.labels.LabelResolver;
import frc.robot.diag.lifecycle.runtime.DeviceRuntimeState;
import frc.robot.diag.lifecycle.runtime.HealthState;
import frc.robot.diag.lifecycle.runtime.PresenceState;
import java.util.List;
import org.junit.jupiter.api.Test;

class ActivationManagerTest {
    private static final String DRIVE_LABEL = "front_left_drive";
    private static final String STEER_LABEL = "front_left_steer";
    private static final String ENCODER_LABEL = "front_left_encoder";
    private static final String PDH_LABEL = "pdh";
    private static final String CORNER_GROUP_LABEL = "front_left_corner";
    private static final String STACK_GROUP_LABEL = "front_left_stack";
    private static final String SINGLETON_AND_DRIVE_GROUP_LABEL = "singleton_and_drive";
    private static final String ACTIVE_GROUP_LABEL = "bringup_active";
    private static final String SESSION_NOT_INACTIVE = "SESSION_NOT_INACTIVE";
    private static final String LABEL_MISMATCH = "LABEL_MISMATCH";
    private static final String EMPTY_GROUP = "EMPTY_GROUP";
    private static final String ACTIVATION_FAILED = "ACTIVATION_FAILED";

    @Test
    void activateSingleDevice() {
        Fixture fixture = fixture();

        ActivationResult result =
                fixture.manager.activate(DRIVE_LABEL, ActivationMode.ACTUATION_ALLOWED);

        assertTrue(result.success());
        assertEquals(DRIVE_LABEL, result.requestedLabel());
        assertEquals(List.of(DRIVE_LABEL), result.requestedDeviceLabels());
        assertEquals(List.of(DRIVE_LABEL), result.instantiatedDeviceLabels());
        assertEquals(ActivationMode.ACTUATION_ALLOWED, result.mode());
        assertNotNull(result.sessionId());
        assertTrue(fixture.manager.getActiveSession().isPresent());
        assertEquals(LifecycleState.ACTIVE, fixture.manager.lifecycleState());
    }

    @Test
    void activateStaticGroup() {
        Fixture fixture = fixture();

        ActivationResult result =
                fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.READ_ONLY);

        assertTrue(result.success());
        assertEquals(List.of(DRIVE_LABEL, STEER_LABEL), result.requestedDeviceLabels());
        assertEquals(List.of(DRIVE_LABEL, STEER_LABEL), result.instantiatedDeviceLabels());
    }

    @Test
    void activateDynamicGroup() {
        Fixture fixture = fixture();
        fixture.groups.createDynamicGroup(ACTIVE_GROUP_LABEL);
        fixture.groups.setDynamicGroupMembers(
                ACTIVE_GROUP_LABEL, List.of(DRIVE_LABEL, ENCODER_LABEL));

        ActivationResult result =
                fixture.manager.activate(ACTIVE_GROUP_LABEL, ActivationMode.PROBE_ONLY);

        assertTrue(result.success());
        assertEquals(List.of(DRIVE_LABEL, ENCODER_LABEL), result.requestedDeviceLabels());
    }

    @Test
    void activateWhileAnotherSessionIsActiveFails() {
        Fixture fixture = fixture();
        fixture.manager.activate(DRIVE_LABEL, ActivationMode.ACTUATION_ALLOWED);

        ActivationResult result =
                fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        assertFalse(result.success());
        assertEquals(SESSION_NOT_INACTIVE, result.errorCode());
        assertEquals(LifecycleState.ACTIVE, fixture.manager.lifecycleState());
    }

    @Test
    void deactivateWrongLabelFails() {
        Fixture fixture = fixture();
        fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        DeactivateResult result = fixture.manager.deactivate(DRIVE_LABEL);

        assertFalse(result.success());
        assertEquals(LABEL_MISMATCH, result.errorCode());
        assertTrue(fixture.manager.getActiveSession().isPresent());
    }

    @Test
    void deactivateActiveSucceeds() {
        Fixture fixture = fixture();
        ActivationResult activation =
                fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        DeactivateResult result = fixture.manager.deactivateActive();

        assertTrue(result.success());
        assertEquals(CORNER_GROUP_LABEL, result.requestedLabel());
        assertEquals(activation.sessionId(), result.sessionId());
        assertEquals(List.of(DRIVE_LABEL, STEER_LABEL), result.deactivatedDeviceLabels());
        assertEquals(LifecycleState.INACTIVE, fixture.manager.lifecycleState());
        assertTrue(fixture.factory.closedLabels().containsAll(result.deactivatedDeviceLabels()));
    }

    @Test
    void activationOfEmptyGroupFails() {
        Fixture fixture = fixture();
        fixture.groups.createDynamicGroup(ACTIVE_GROUP_LABEL);

        ActivationResult result =
                fixture.manager.activate(ACTIVE_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        assertFalse(result.success());
        assertEquals(EMPTY_GROUP, result.errorCode());
        assertEquals(LifecycleState.INACTIVE, fixture.manager.lifecycleState());
        assertTrue(fixture.manager.getActiveSession().isEmpty());
    }

    @Test
    void failedActivationRollsBackAlreadyCreatedDevices() {
        Fixture fixture = fixture();
        fixture.factory.configureFailure(STEER_LABEL);

        ActivationResult result =
                fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        assertFalse(result.success());
        assertEquals(ACTIVATION_FAILED, result.errorCode());
        assertEquals(List.of(), result.instantiatedDeviceLabels());
        assertEquals(List.of(STEER_LABEL), result.failedDeviceLabels());
        assertEquals(List.of(DRIVE_LABEL), fixture.factory.closedLabels());
        assertEquals(0, fixture.factory.activeDeviceCount());
        assertTrue(fixture.manager.getActiveSession().isEmpty());
        assertEquals(LifecycleState.INACTIVE, fixture.manager.lifecycleState());
    }

    @Test
    void successfulSessionStoresRequestedLabel() {
        Fixture fixture = fixture();

        fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        assertEquals(CORNER_GROUP_LABEL, fixture.manager.getActiveSession().orElseThrow().requestedLabel());
    }

    @Test
    void successfulSessionStoresResolvedDeviceLabels() {
        Fixture fixture = fixture();

        fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        assertEquals(
                List.of(DRIVE_LABEL, STEER_LABEL),
                fixture.manager.getActiveSession().orElseThrow().requestedDeviceLabels());
    }

    @Test
    void successfulSessionStoresMode() {
        Fixture fixture = fixture();

        fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.READ_ONLY);

        assertEquals(ActivationMode.READ_ONLY, fixture.manager.getActiveSession().orElseThrow().mode());
    }

    @Test
    void successfulSessionHasSessionId() {
        Fixture fixture = fixture();

        fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.READ_ONLY);

        assertNotNull(fixture.manager.getActiveSession().orElseThrow().sessionId());
    }

    @Test
    void singletonCreatedOnce() {
        Fixture fixture = fixture();

        fixture.manager.activate(PDH_LABEL, ActivationMode.READ_ONLY);
        fixture.manager.deactivateActive();
        fixture.manager.activate(PDH_LABEL, ActivationMode.READ_ONLY);

        assertEquals(1, fixture.factory.creationAttemptsFor(PDH_LABEL));
        assertEquals(List.of(PDH_LABEL), fixture.factory.createdLabels());
    }

    @Test
    void singletonReusedAcrossSessions() {
        Fixture fixture = fixture();

        fixture.manager.activate(PDH_LABEL, ActivationMode.READ_ONLY);
        fixture.manager.deactivateActive();
        ActivationResult secondActivation =
                fixture.manager.activate(SINGLETON_AND_DRIVE_GROUP_LABEL, ActivationMode.READ_ONLY);

        assertTrue(secondActivation.success());
        assertEquals(1, fixture.factory.creationAttemptsFor(PDH_LABEL));
        assertEquals(List.of(PDH_LABEL, DRIVE_LABEL), fixture.factory.createdLabels());
    }

    @Test
    void normalDeviceRecreatedAcrossSessions() {
        Fixture fixture = fixture();

        fixture.manager.activate(DRIVE_LABEL, ActivationMode.ACTUATION_ALLOWED);
        fixture.manager.deactivateActive();
        fixture.manager.activate(DRIVE_LABEL, ActivationMode.ACTUATION_ALLOWED);

        assertEquals(2, fixture.factory.creationAttemptsFor(DRIVE_LABEL));
        assertEquals(List.of(DRIVE_LABEL, DRIVE_LABEL), fixture.factory.createdLabels());
    }

    @Test
    void singletonNotClosedOnDeactivate() {
        Fixture fixture = fixture();

        fixture.manager.activate(PDH_LABEL, ActivationMode.READ_ONLY);
        fixture.manager.deactivateActive();

        assertFalse(fixture.factory.closedLabels().contains(PDH_LABEL));
        assertEquals(List.of(PDH_LABEL), fixture.factory.activeLabels());
    }

    @Test
    void singletonCanStillBePartOfOnlyOneActiveSession() {
        Fixture fixture = fixture();
        fixture.manager.activate(PDH_LABEL, ActivationMode.READ_ONLY);

        ActivationResult result =
                fixture.manager.activate(SINGLETON_AND_DRIVE_GROUP_LABEL, ActivationMode.READ_ONLY);

        assertFalse(result.success());
        assertEquals(SESSION_NOT_INACTIVE, result.errorCode());
    }

    @Test
    void singletonAppearsInInstantiatedResultWhenAttachedSuccessfully() {
        Fixture fixture = fixture();

        ActivationResult result =
                fixture.manager.activate(SINGLETON_AND_DRIVE_GROUP_LABEL, ActivationMode.READ_ONLY);

        assertTrue(result.success());
        assertEquals(List.of(PDH_LABEL, DRIVE_LABEL), result.instantiatedDeviceLabels());
    }

    @Test
    void activeQueryReturnsActiveDeviceLabels() {
        Fixture fixture = fixture();

        fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        assertEquals(List.of(DRIVE_LABEL, STEER_LABEL), fixture.manager.activeDeviceLabels());
    }

    @Test
    void afterDeactivateActiveQueryReturnsEmpty() {
        Fixture fixture = fixture();
        fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        fixture.manager.deactivateActive();

        assertEquals(List.of(), fixture.manager.activeDeviceLabels());
    }

    @Test
    void afterDeactivateInstantiatedIsFalseForNormalDevices() {
        Fixture fixture = fixture();
        fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        fixture.manager.deactivateActive();

        assertFalse(fixture.devices.runtimeState(DRIVE_LABEL).isInstantiated());
        assertFalse(fixture.devices.runtimeState(STEER_LABEL).isInstantiated());
    }

    @Test
    void runtimeRecordsSurviveDeactivate() {
        Fixture fixture = fixture();
        ActivationResult activation =
                fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.READ_ONLY);

        fixture.manager.deactivateActive();

        DeviceRuntimeState driveRuntime = fixture.devices.runtimeState(DRIVE_LABEL);
        assertFalse(driveRuntime.isActive());
        assertFalse(driveRuntime.isInstantiated());
        assertEquals(activation.mode().name(), driveRuntime.lastActivationMode());
    }

    @Test
    void failedActivationLeavesNoActiveDevices() {
        Fixture fixture = fixture();
        fixture.factory.configureFailure(STEER_LABEL);

        fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        assertEquals(List.of(), fixture.manager.activeDeviceLabels());
    }

    @Test
    void failedActivationRecordsErrorState() {
        Fixture fixture = fixture();
        fixture.factory.configureFailure(STEER_LABEL);

        fixture.manager.activate(CORNER_GROUP_LABEL, ActivationMode.ACTUATION_ALLOWED);

        assertEquals(ACTIVATION_FAILED, fixture.devices.runtimeState(DRIVE_LABEL).lastError());
        assertEquals(ACTIVATION_FAILED, fixture.devices.runtimeState(STEER_LABEL).lastError());
        assertFalse(fixture.devices.runtimeState(DRIVE_LABEL).isActive());
        assertFalse(fixture.devices.runtimeState(STEER_LABEL).isActive());
    }

    @Test
    void presenceAndHealthRemainUnknownUntilFutureWork() {
        Fixture fixture = fixture();
        fixture.manager.activate(SINGLETON_AND_DRIVE_GROUP_LABEL, ActivationMode.READ_ONLY);
        fixture.manager.deactivateActive();

        DeviceRuntimeState singletonRuntime = fixture.devices.runtimeState(PDH_LABEL);
        DeviceRuntimeState driveRuntime = fixture.devices.runtimeState(DRIVE_LABEL);

        assertEquals(PresenceState.UNKNOWN, singletonRuntime.presenceState());
        assertEquals(HealthState.UNKNOWN, singletonRuntime.healthState());
        assertEquals(PresenceState.UNKNOWN, driveRuntime.presenceState());
        assertEquals(HealthState.UNKNOWN, driveRuntime.healthState());
    }

    private static Fixture fixture() {
        DeviceCatalog devices = DeviceCatalog.load(List.of(
                new DeviceDeclaration(DRIVE_LABEL, DeviceLifecycleKind.NORMAL),
                new DeviceDeclaration(STEER_LABEL, DeviceLifecycleKind.NORMAL),
                new DeviceDeclaration(ENCODER_LABEL, DeviceLifecycleKind.NORMAL),
                new DeviceDeclaration(PDH_LABEL, DeviceLifecycleKind.SINGLETON)));
        GroupCatalog groups =
                GroupCatalog.load(
                        devices,
                        List.of(
                                new GroupDeclaration(CORNER_GROUP_LABEL, List.of(DRIVE_LABEL, STEER_LABEL)),
                                new GroupDeclaration(STACK_GROUP_LABEL, List.of(DRIVE_LABEL, STEER_LABEL, ENCODER_LABEL)),
                                new GroupDeclaration(SINGLETON_AND_DRIVE_GROUP_LABEL, List.of(PDH_LABEL, DRIVE_LABEL))));
        FakeDeviceFactory factory = new FakeDeviceFactory();
        LabelResolver resolver = new LabelResolver(devices, groups);
        ActivationManager manager = new ActivationManager(devices, resolver, factory);
        return new Fixture(devices, groups, factory, manager);
    }

    private record Fixture(
            DeviceCatalog devices,
            GroupCatalog groups,
            FakeDeviceFactory factory,
            ActivationManager manager) {}
}
