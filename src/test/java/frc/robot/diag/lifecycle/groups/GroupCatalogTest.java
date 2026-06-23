package frc.robot.diag.lifecycle.groups;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import frc.robot.diag.lifecycle.devices.DeviceCatalog;
import frc.robot.diag.lifecycle.devices.DeviceDeclaration;
import frc.robot.diag.lifecycle.devices.DeviceLifecycleKind;
import java.util.List;
import org.junit.jupiter.api.Test;

class GroupCatalogTest {
    private static final String DRIVE_LABEL = "front_left_drive";
    private static final String STEER_LABEL = "front_left_steer";
    private static final String PDH_LABEL = "pdh";
    private static final String CORNER_GROUP_LABEL = "front_left_corner";
    private static final String ACTIVE_GROUP_LABEL = "bringup_active";
    private static final String SELECTED_GROUP_LABEL = "selected_devices";
    private static final String MISSING_DEVICE_LABEL = "missing_device";

    @Test
    void staticGroupResolvesToConfiguredDeviceLabels() {
        GroupCatalog groups = loadGroups();

        assertEquals(
                List.of(DRIVE_LABEL, STEER_LABEL),
                groups.groupRecord(CORNER_GROUP_LABEL).memberDeviceLabels());
    }

    @Test
    void dynamicGroupCanBeCreated() {
        GroupCatalog groups = loadGroups();

        GroupRecord dynamicGroup = groups.createDynamicGroup(ACTIVE_GROUP_LABEL);

        assertEquals(GroupKind.DYNAMIC, dynamicGroup.kind());
        assertEquals(GroupState.INACTIVE, dynamicGroup.state());
        assertEquals(List.of(), dynamicGroup.memberDeviceLabels());
    }

    @Test
    void dynamicGroupCanBeEditedWhileInactive() {
        GroupCatalog groups = loadGroups();
        groups.createDynamicGroup(ACTIVE_GROUP_LABEL);

        groups.setDynamicGroupMembers(ACTIVE_GROUP_LABEL, List.of(DRIVE_LABEL, STEER_LABEL));

        assertEquals(
                List.of(DRIVE_LABEL, STEER_LABEL),
                groups.groupRecord(ACTIVE_GROUP_LABEL).memberDeviceLabels());
    }

    @Test
    void editingActiveGroupFails() {
        GroupCatalog groups = loadGroups();
        GroupRecord dynamicGroup = groups.createDynamicGroup(ACTIVE_GROUP_LABEL);
        dynamicGroup.setState(GroupState.ACTIVE);

        assertThrows(
                IllegalStateException.class,
                () -> groups.setDynamicGroupMembers(ACTIVE_GROUP_LABEL, List.of(DRIVE_LABEL)));
    }

    @Test
    void groupContainingUnknownDeviceLabelFails() {
        DeviceCatalog devices = loadDevices();

        assertThrows(
                IllegalArgumentException.class,
                () -> GroupCatalog.load(
                        devices,
                        List.of(new GroupDeclaration(
                                CORNER_GROUP_LABEL,
                                List.of(DRIVE_LABEL, MISSING_DEVICE_LABEL)))));
    }

    @Test
    void groupContainingGroupLabelFails() {
        DeviceCatalog devices = loadDevices();

        assertThrows(
                IllegalArgumentException.class,
                () -> GroupCatalog.load(
                        devices,
                        List.of(
                                new GroupDeclaration(CORNER_GROUP_LABEL, List.of(DRIVE_LABEL)),
                                new GroupDeclaration(SELECTED_GROUP_LABEL, List.of(CORNER_GROUP_LABEL)))));
    }

    @Test
    void emptyDynamicGroupIsAllowedWhileInactive() {
        GroupCatalog groups = loadGroups();
        GroupRecord dynamicGroup = groups.createDynamicGroup(SELECTED_GROUP_LABEL);

        groups.setDynamicGroupMembers(SELECTED_GROUP_LABEL, List.of());

        assertEquals(List.of(), dynamicGroup.memberDeviceLabels());
        assertEquals(GroupState.INACTIVE, dynamicGroup.state());
    }

    private static GroupCatalog loadGroups() {
        return GroupCatalog.load(
                loadDevices(),
                List.of(new GroupDeclaration(CORNER_GROUP_LABEL, List.of(DRIVE_LABEL, STEER_LABEL))));
    }

    private static DeviceCatalog loadDevices() {
        return DeviceCatalog.load(List.of(
                new DeviceDeclaration(DRIVE_LABEL, DeviceLifecycleKind.NORMAL),
                new DeviceDeclaration(STEER_LABEL, DeviceLifecycleKind.NORMAL),
                new DeviceDeclaration(PDH_LABEL, DeviceLifecycleKind.SINGLETON)));
    }
}
