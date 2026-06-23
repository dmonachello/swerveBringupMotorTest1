package frc.robot.diag.lifecycle.groups;

import frc.robot.diag.lifecycle.devices.DeviceCatalog;
import frc.robot.diag.lifecycle.labels.LabelKind;
import frc.robot.diag.lifecycle.labels.UnknownLabelException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * NAME
 *     GroupCatalog - load and manage lifecycle group records.
 *
 * DESCRIPTION
 *     GroupCatalog validates that group membership contains device labels only and enforces the
 *     dynamic-group mutation rules for the current model slice.
 */
public final class GroupCatalog {
    private static final String ERROR_UNKNOWN_GROUP_PREFIX = "Unknown group label: ";
    private static final String ERROR_UNKNOWN_DEVICE_PREFIX = "Unknown device label: ";
    private static final String ERROR_MEMBERS_MUST_BE_DEVICES_PREFIX =
            "Group members must be device labels only: ";
    private static final String ERROR_ONLY_DYNAMIC_EDITABLE = "Only dynamic groups may be edited";
    private static final String ERROR_ACTIVE_GROUP_IMMUTABLE = "Active group membership is immutable";

    private final DeviceCatalog deviceCatalog;
    private final Map<String, GroupRecord> groupRecordsByLabel;

    private GroupCatalog(DeviceCatalog deviceCatalog, Map<String, GroupRecord> groupRecordsByLabel) {
        this.deviceCatalog = deviceCatalog;
        this.groupRecordsByLabel = groupRecordsByLabel;
    }

    public static GroupCatalog load(DeviceCatalog deviceCatalog, Iterable<GroupDeclaration> declarations) {
        Map<String, GroupRecord> groupRecordsByLabel = new LinkedHashMap<>();

        for (GroupDeclaration declaration : declarations) {
            validateMemberDeviceLabels(deviceCatalog, declaration.memberDeviceLabels());
            deviceCatalog.labelRegistry().registerGroupLabel(declaration.label());
            groupRecordsByLabel.put(
                    declaration.label(),
                    new GroupRecord(
                            declaration.label(), GroupKind.STATIC, declaration.memberDeviceLabels()));
        }

        return new GroupCatalog(deviceCatalog, groupRecordsByLabel);
    }

    public GroupRecord createDynamicGroup(String label) {
        deviceCatalog.labelRegistry().registerGroupLabel(label);
        GroupRecord groupRecord = new GroupRecord(label, GroupKind.DYNAMIC, List.of());
        groupRecordsByLabel.put(label, groupRecord);
        return groupRecord;
    }

    public void setDynamicGroupMembers(String label, List<String> memberDeviceLabels) {
        validateMemberDeviceLabels(deviceCatalog, memberDeviceLabels);
        groupRecord(label).setMemberDeviceLabels(memberDeviceLabels);
    }

    public GroupRecord groupRecord(String label) {
        GroupRecord record = groupRecordsByLabel.get(label);
        if (record == null) {
            throw new IllegalArgumentException(ERROR_UNKNOWN_GROUP_PREFIX + label);
        }
        return record;
    }

    public boolean hasGroupLabel(String label) {
        return groupRecordsByLabel.containsKey(label);
    }

    public List<GroupRecord> groupRecords() {
        return new ArrayList<>(groupRecordsByLabel.values());
    }

    public void deleteDynamicGroup(String label) {
        GroupRecord record = groupRecord(label);
        if (record.kind() != GroupKind.DYNAMIC) {
            throw new IllegalStateException(ERROR_ONLY_DYNAMIC_EDITABLE);
        }
        if (record.state() != GroupState.INACTIVE) {
            throw new IllegalStateException(ERROR_ACTIVE_GROUP_IMMUTABLE);
        }
        groupRecordsByLabel.remove(label);
        deviceCatalog.labelRegistry().unregisterLabel(label);
    }

    private static void validateMemberDeviceLabels(
            DeviceCatalog deviceCatalog, List<String> memberDeviceLabels) {
        for (String memberLabel : memberDeviceLabels) {
            LabelKind labelKind;
            try {
                labelKind = deviceCatalog.labelRegistry().labelKindOf(memberLabel);
            } catch (UnknownLabelException exception) {
                throw new IllegalArgumentException(ERROR_UNKNOWN_DEVICE_PREFIX + memberLabel, exception);
            }
            if (labelKind != LabelKind.DEVICE) {
                throw new IllegalArgumentException(ERROR_MEMBERS_MUST_BE_DEVICES_PREFIX + memberLabel);
            }
        }
    }
}
