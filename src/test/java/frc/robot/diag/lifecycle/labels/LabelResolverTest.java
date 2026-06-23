package frc.robot.diag.lifecycle.labels;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import frc.robot.diag.lifecycle.devices.DeviceCatalog;
import frc.robot.diag.lifecycle.devices.DeviceDeclaration;
import frc.robot.diag.lifecycle.devices.DeviceLifecycleKind;
import frc.robot.diag.lifecycle.groups.GroupCatalog;
import frc.robot.diag.lifecycle.groups.GroupDeclaration;
import frc.robot.diag.lifecycle.groups.GroupKind;
import frc.robot.diag.lifecycle.groups.GroupRecord;
import java.lang.reflect.Field;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class LabelResolverTest {
    private static final String DRIVE_LABEL = "front_left_drive";
    private static final String STEER_LABEL = "front_left_steer";
    private static final String ENCODER_LABEL = "front_left_encoder";
    private static final String PDH_LABEL = "pdh";
    private static final String CORNER_GROUP_LABEL = "front_left_corner";
    private static final String STACK_GROUP_LABEL = "front_left_stack";
    private static final String SELECTED_GROUP_LABEL = "selected_devices";
    private static final String MISSING_LABEL = "missing_label";

    @Test
    void resolveDeviceLabel() {
        LabelResolver resolver = loadResolver();

        assertEquals(List.of(DRIVE_LABEL), resolver.resolveToDeviceLabels(DRIVE_LABEL));
    }

    @Test
    void resolveGroupLabel() {
        LabelResolver resolver = loadResolver();

        assertEquals(
                List.of(DRIVE_LABEL, STEER_LABEL),
                resolver.resolveToDeviceLabels(CORNER_GROUP_LABEL));
    }

    @Test
    void resolveUnknownLabelFails() {
        LabelResolver resolver = loadResolver();

        assertThrows(UnknownLabelException.class, () -> resolver.resolveToDeviceLabels(MISSING_LABEL));
    }

    @Test
    void resolvedLabelsPreserveConfiguredOrder() {
        LabelResolver resolver = loadResolver();

        assertEquals(
                List.of(DRIVE_LABEL, STEER_LABEL, ENCODER_LABEL),
                resolver.resolveToDeviceLabels(STACK_GROUP_LABEL));
    }

    @Test
    void groupWithInvalidMemberFails() throws Exception {
        DeviceCatalog devices = loadDevices();
        GroupCatalog groups = GroupCatalog.load(
                devices,
                List.of(new GroupDeclaration(CORNER_GROUP_LABEL, List.of(DRIVE_LABEL))));
        groups.createDynamicGroup(SELECTED_GROUP_LABEL);
        injectGroupRecord(
                groups,
                new GroupRecord(
                        SELECTED_GROUP_LABEL,
                        GroupKind.DYNAMIC,
                        List.of(MISSING_LABEL)));

        LabelResolver resolver = new LabelResolver(devices, groups);

        assertThrows(
                IllegalArgumentException.class,
                () -> resolver.resolveToDeviceLabels(SELECTED_GROUP_LABEL));
    }

    @Test
    void resultContainsDeviceLabelsOnly() {
        LabelResolver resolver = loadResolver();

        List<String> labels = resolver.resolveToDeviceLabels(CORNER_GROUP_LABEL);

        assertEquals(List.of(DRIVE_LABEL, STEER_LABEL), labels);
    }

    private static LabelResolver loadResolver() {
        DeviceCatalog devices = loadDevices();
        GroupCatalog groups = GroupCatalog.load(
                devices,
                List.of(
                        new GroupDeclaration(CORNER_GROUP_LABEL, List.of(DRIVE_LABEL, STEER_LABEL)),
                        new GroupDeclaration(STACK_GROUP_LABEL, List.of(DRIVE_LABEL, STEER_LABEL, ENCODER_LABEL))));
        return new LabelResolver(devices, groups);
    }

    private static DeviceCatalog loadDevices() {
        return DeviceCatalog.load(List.of(
                new DeviceDeclaration(DRIVE_LABEL, DeviceLifecycleKind.NORMAL),
                new DeviceDeclaration(STEER_LABEL, DeviceLifecycleKind.NORMAL),
                new DeviceDeclaration(ENCODER_LABEL, DeviceLifecycleKind.NORMAL),
                new DeviceDeclaration(PDH_LABEL, DeviceLifecycleKind.SINGLETON)));
    }

    /**
     * NAME
     *     injectGroupRecord - install a replacement group record for a malformed test case.
     *
     * PARAMETERS
     *     groups - group catalog under test.
     *     replacement - replacement group record.
     */
    @SuppressWarnings("unchecked")
    private static void injectGroupRecord(GroupCatalog groups, GroupRecord replacement) throws Exception {
        Field field = GroupCatalog.class.getDeclaredField("groupRecordsByLabel");
        field.setAccessible(true);
        Map<String, GroupRecord> records = (Map<String, GroupRecord>) field.get(groups);
        Map<String, GroupRecord> writableRecords = new LinkedHashMap<>(records);
        writableRecords.put(replacement.label(), replacement);
        records.clear();
        records.putAll(writableRecords);
    }
}
