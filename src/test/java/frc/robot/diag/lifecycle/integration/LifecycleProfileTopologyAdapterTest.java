package frc.robot.diag.lifecycle.integration;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertEquals;

import frc.robot.BridgeGroupManager;
import frc.robot.BringupUtil;
import frc.robot.diag.lifecycle.devices.DeviceLifecycleKind;
import frc.robot.diag.lifecycle.groups.GroupKind;
import java.util.List;
import org.junit.jupiter.api.Test;

class LifecycleProfileTopologyAdapterTest {
    private static final int ID_DRIVE = 9;
    private static final int ID_STEER = 25;
    private static final int ID_PDH = 1;
    private static final int MFG_CTRE = 4;
    private static final int MFG_REV = 5;
    private static final int DEVTYPE_MOTOR = 2;
    private static final int DEVTYPE_POWER = 8;
    private static final String INTERFACE_CAN = "CAN";
    private static final String TYPE_FALCON = "FALCON";
    private static final String TYPE_NEO = "NEO";
    private static final String TYPE_PDH = "PDH";
    private static final String TYPE_ROBORIO = "roboRIO";
    private static final String TYPE_XBOX_CONTROLLER = "xboxController";
    private static final String LABEL_DRIVE = "front_left_drive";
    private static final String LABEL_STEER = "front_left_steer";
    private static final String LABEL_PDH = "pdh";
    private static final String LABEL_ROBORIO = "roborio";
    private static final String LABEL_CONTROLLER = "controller0";
    private static final String GROUP_CORNER = "front_left_corner";
    private static final String GROUP_DISABLED_MEMBER = "disabled_member_group";
    private static final String GROUP_ACTIVE = "active-group";

    @Test
    void buildMapsPowerDistributionDevicesToSingletonLifecycle() {
        LifecycleCatalogBundle bundle =
                LifecycleProfileTopologyAdapter.build(
                        "test_profile",
                        List.of(
                                deviceEntry(ID_DRIVE, MFG_CTRE, DEVTYPE_MOTOR, TYPE_FALCON, LABEL_DRIVE),
                                deviceEntry(ID_PDH, MFG_REV, DEVTYPE_POWER, TYPE_PDH, LABEL_PDH)),
                        BringupUtil.BridgeProfileRuntimeConfig.empty());

        assertEquals(DeviceLifecycleKind.NORMAL, bundle.deviceCatalog().deviceRecord(LABEL_DRIVE).lifecycleKind());
        assertEquals(DeviceLifecycleKind.SINGLETON, bundle.deviceCatalog().deviceRecord(LABEL_PDH).lifecycleKind());
    }

    @Test
    void buildMapsVirtualRuntimeDevicesToSingletonLifecycle() {
        LifecycleCatalogBundle bundle =
                LifecycleProfileTopologyAdapter.build(
                        "test_profile",
                        List.of(
                                deviceEntry(ID_DRIVE, MFG_CTRE, DEVTYPE_MOTOR, TYPE_FALCON, LABEL_DRIVE),
                                deviceEntry(0, 0, 0, TYPE_ROBORIO, LABEL_ROBORIO),
                                deviceEntry(0, 0, 0, TYPE_XBOX_CONTROLLER, LABEL_CONTROLLER)),
                        BringupUtil.BridgeProfileRuntimeConfig.empty());

        assertEquals(DeviceLifecycleKind.SINGLETON, bundle.deviceCatalog().deviceRecord(LABEL_ROBORIO).lifecycleKind());
        assertEquals(DeviceLifecycleKind.SINGLETON, bundle.deviceCatalog().deviceRecord(LABEL_CONTROLLER).lifecycleKind());
    }

    @Test
    void buildMapsBridgeGroupsIntoLifecycleGroupDeclarations() {
        LifecycleCatalogBundle bundle =
                LifecycleProfileTopologyAdapter.build(
                        "test_profile",
                        List.of(
                                deviceEntry(ID_DRIVE, MFG_CTRE, DEVTYPE_MOTOR, TYPE_FALCON, LABEL_DRIVE),
                                deviceEntry(ID_STEER, MFG_REV, DEVTYPE_MOTOR, TYPE_NEO, LABEL_STEER)),
                        new BringupUtil.BridgeProfileRuntimeConfig(
                                List.of(
                                        new BringupUtil.BridgeProfileGroupConfig(
                                                GROUP_CORNER,
                                                true,
                                                List.of(
                                                        new BringupUtil.BridgeProfileMemberConfig(LABEL_DRIVE, true),
                                                        new BringupUtil.BridgeProfileMemberConfig(LABEL_STEER, true)),
                                                List.of())),
                                new BringupUtil.BridgeProfileSelectedDeviceConfig("", false)));

        assertEquals(
                List.of(LABEL_DRIVE, LABEL_STEER),
                bundle.groupCatalog().groupRecord(GROUP_CORNER).memberDeviceLabels());
        assertEquals(
                List.of(LABEL_DRIVE, LABEL_STEER),
                bundle.labelResolver().resolveToDeviceLabels(GROUP_CORNER));
    }

    @Test
    void buildDropsDisabledBridgeMembersFromLifecycleGroups() {
        LifecycleCatalogBundle bundle =
                LifecycleProfileTopologyAdapter.build(
                        "test_profile",
                        List.of(
                                deviceEntry(ID_DRIVE, MFG_CTRE, DEVTYPE_MOTOR, TYPE_FALCON, LABEL_DRIVE),
                                deviceEntry(ID_STEER, MFG_REV, DEVTYPE_MOTOR, TYPE_NEO, LABEL_STEER)),
                        new BringupUtil.BridgeProfileRuntimeConfig(
                                List.of(
                                        new BringupUtil.BridgeProfileGroupConfig(
                                                GROUP_DISABLED_MEMBER,
                                                true,
                                                List.of(
                                                        new BringupUtil.BridgeProfileMemberConfig(LABEL_DRIVE, true),
                                                        new BringupUtil.BridgeProfileMemberConfig(LABEL_STEER, false)),
                                                List.of())),
                                new BringupUtil.BridgeProfileSelectedDeviceConfig("", false)));

        assertEquals(
                List.of(LABEL_DRIVE),
                bundle.groupCatalog().groupRecord(GROUP_DISABLED_MEMBER).memberDeviceLabels());
    }

    @Test
    void buildMapsRuntimeActiveGroupIntoDynamicLifecycleGroup() {
        BridgeGroupManager runtimeGroups = new BridgeGroupManager();
        runtimeGroups.createGroup(GROUP_ACTIVE);
        runtimeGroups.addDevice(GROUP_ACTIVE, LABEL_DRIVE, false);
        runtimeGroups.addDevice(GROUP_ACTIVE, LABEL_STEER, false);
        runtimeGroups.setMemberEnabled(GROUP_ACTIVE, LABEL_STEER, false);

        LifecycleCatalogBundle bundle =
                LifecycleProfileTopologyAdapter.build(
                        "test_profile",
                        List.of(
                                deviceEntry(ID_DRIVE, MFG_CTRE, DEVTYPE_MOTOR, TYPE_FALCON, LABEL_DRIVE),
                                deviceEntry(ID_STEER, MFG_REV, DEVTYPE_MOTOR, TYPE_NEO, LABEL_STEER)),
                        BringupUtil.BridgeProfileRuntimeConfig.empty(),
                        runtimeGroups.getGroups());

        assertEquals(GroupKind.DYNAMIC, bundle.groupCatalog().groupRecord(GROUP_ACTIVE).kind());
        assertEquals(
                List.of(LABEL_DRIVE),
                bundle.groupCatalog().groupRecord(GROUP_ACTIVE).memberDeviceLabels());
        assertEquals(
                List.of(LABEL_DRIVE),
                bundle.labelResolver().resolveToDeviceLabels(GROUP_ACTIVE));
    }

    @Test
    void buildIgnoresConfiguredActiveGroupAndUsesRuntimeActiveGroupMembers() {
        BridgeGroupManager runtimeGroups = new BridgeGroupManager();
        runtimeGroups.createGroup(GROUP_ACTIVE);
        runtimeGroups.addDevice(GROUP_ACTIVE, LABEL_DRIVE, false);
        runtimeGroups.addDevice(GROUP_ACTIVE, LABEL_STEER, false);

        LifecycleCatalogBundle bundle =
                LifecycleProfileTopologyAdapter.build(
                        "test_profile",
                        List.of(
                                deviceEntry(ID_DRIVE, MFG_CTRE, DEVTYPE_MOTOR, TYPE_FALCON, LABEL_DRIVE),
                                deviceEntry(ID_STEER, MFG_REV, DEVTYPE_MOTOR, TYPE_NEO, LABEL_STEER)),
                        new BringupUtil.BridgeProfileRuntimeConfig(
                                List.of(
                                        new BringupUtil.BridgeProfileGroupConfig(
                                                GROUP_ACTIVE,
                                                true,
                                                List.of(),
                                                List.of())),
                                new BringupUtil.BridgeProfileSelectedDeviceConfig("", false)),
                        runtimeGroups.getGroups());

        assertEquals(GroupKind.DYNAMIC, bundle.groupCatalog().groupRecord(GROUP_ACTIVE).kind());
        assertEquals(
                List.of(LABEL_DRIVE, LABEL_STEER),
                bundle.groupCatalog().groupRecord(GROUP_ACTIVE).memberDeviceLabels());
        assertEquals(
                List.of(LABEL_DRIVE, LABEL_STEER),
                bundle.labelResolver().resolveToDeviceLabels(GROUP_ACTIVE));
    }

    @Test
    void syncRuntimeGroupsRemovesDeletedDynamicGroups() {
        BridgeGroupManager runtimeGroups = new BridgeGroupManager();
        runtimeGroups.createGroup(GROUP_ACTIVE);
        runtimeGroups.addDevice(GROUP_ACTIVE, LABEL_DRIVE, false);

        LifecycleCatalogBundle bundle =
                LifecycleProfileTopologyAdapter.build(
                        "test_profile",
                        List.of(deviceEntry(ID_DRIVE, MFG_CTRE, DEVTYPE_MOTOR, TYPE_FALCON, LABEL_DRIVE)),
                        BringupUtil.BridgeProfileRuntimeConfig.empty(),
                        runtimeGroups.getGroups());

        runtimeGroups.deleteGroup(GROUP_ACTIVE);
        LifecycleProfileTopologyAdapter.syncRuntimeGroups(
                bundle.groupCatalog(), runtimeGroups.getGroups());

        assertFalse(bundle.groupCatalog().hasGroupLabel(GROUP_ACTIVE));
    }

    private static BringupUtil.DeviceEntry deviceEntry(
            int id, int manufacturer, int deviceType, String type, String label) {
        return new BringupUtil.DeviceEntry(
                id,
                manufacturer,
                deviceType,
                INTERFACE_CAN,
                type,
                type,
                label,
                "",
                new BringupUtil.LimitConfig(),
                List.of(),
                false);
    }
}
