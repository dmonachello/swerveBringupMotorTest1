package frc.robot.diag.lifecycle.labels;

import frc.robot.diag.lifecycle.devices.DeviceCatalog;
import frc.robot.diag.lifecycle.groups.GroupCatalog;
import frc.robot.diag.lifecycle.groups.GroupRecord;
import java.util.ArrayList;
import java.util.List;

/**
 * NAME
 *     LabelResolver - resolve a lifecycle label into its ordered device-label target set.
 *
 * DESCRIPTION
 *     Device labels resolve to a single-item list. Group labels resolve to their member device
 *     labels in configured order. The resolver never returns objects.
 */
public final class LabelResolver {
    private static final String ERROR_GROUP_UNKNOWN_MEMBER_PREFIX =
            "Group contains unknown member label: ";
    private static final String ERROR_GROUP_NON_DEVICE_MEMBER_PREFIX =
            "Group contains non-device member label: ";

    private final DeviceCatalog deviceCatalog;
    private final GroupCatalog groupCatalog;

    public LabelResolver(DeviceCatalog deviceCatalog, GroupCatalog groupCatalog) {
        this.deviceCatalog = deviceCatalog;
        this.groupCatalog = groupCatalog;
    }

    /**
     * NAME
     *     resolveToDeviceLabels - resolve a device or group label into ordered device labels.
     *
     * PARAMETERS
     *     label - a registered device or group label.
     *
     * RETURNS
     *     Device labels only, in configured order.
     */
    public List<String> resolveToDeviceLabels(String label) {
        LabelKind labelKind = deviceCatalog.labelRegistry().labelKindOf(label);
        if (labelKind == LabelKind.DEVICE) {
            deviceCatalog.deviceRecord(label);
            return List.of(label);
        }

        GroupRecord groupRecord = groupCatalog.groupRecord(label);
        List<String> resolvedLabels = new ArrayList<>();
        for (String memberLabel : groupRecord.memberDeviceLabels()) {
            LabelKind memberKind;
            try {
                memberKind = deviceCatalog.labelRegistry().labelKindOf(memberLabel);
            } catch (UnknownLabelException exception) {
                throw new IllegalArgumentException(
                        ERROR_GROUP_UNKNOWN_MEMBER_PREFIX + memberLabel, exception);
            }
            if (memberKind != LabelKind.DEVICE) {
                throw new IllegalArgumentException(
                        ERROR_GROUP_NON_DEVICE_MEMBER_PREFIX + memberLabel);
            }
            deviceCatalog.deviceRecord(memberLabel);
            resolvedLabels.add(memberLabel);
        }
        return List.copyOf(resolvedLabels);
    }
}
