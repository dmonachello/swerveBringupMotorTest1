package frc.robot.diag.lifecycle.groups;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * NAME
 *     GroupRecord - mutable lifecycle group state and membership.
 *
 * DESCRIPTION
 *     GroupRecord stores only device labels and enforces the first-slice immutability rule for
 *     active dynamic groups.
 */
public final class GroupRecord {
    private static final String ERROR_LABEL_BLANK = "Group label must not be blank";
    private static final String ERROR_KIND_NULL = "Group kind must not be null";
    private static final String ERROR_MEMBER_LABELS_NULL = "Group member labels must not be null";
    private static final String ERROR_STATE_NULL = "Group state must not be null";
    private static final String ERROR_ONLY_DYNAMIC_EDITABLE = "Only dynamic groups may be edited";
    private static final String ERROR_ACTIVE_GROUP_IMMUTABLE = "Active group membership is immutable";

    private final String label;
    private final GroupKind kind;
    private GroupState state;
    private List<String> memberDeviceLabels;

    public GroupRecord(String label, GroupKind kind, List<String> memberDeviceLabels) {
        if (label == null || label.isBlank()) {
            throw new IllegalArgumentException(ERROR_LABEL_BLANK);
        }
        if (kind == null) {
            throw new IllegalArgumentException(ERROR_KIND_NULL);
        }
        if (memberDeviceLabels == null) {
            throw new IllegalArgumentException(ERROR_MEMBER_LABELS_NULL);
        }

        this.label = label;
        this.kind = kind;
        this.state = GroupState.INACTIVE;
        this.memberDeviceLabels = List.copyOf(memberDeviceLabels);
    }

    public String label() {
        return label;
    }

    public GroupKind kind() {
        return kind;
    }

    public GroupState state() {
        return state;
    }

    public List<String> memberDeviceLabels() {
        return Collections.unmodifiableList(new ArrayList<>(memberDeviceLabels));
    }

    /**
     * NAME
     *     setMemberDeviceLabels - replace members for an inactive dynamic group.
     *
     * PARAMETERS
     *     memberDeviceLabels - new ordered member device labels.
     *
     * ERRORS
     *     Throws when the group is static or active.
     */
    public void setMemberDeviceLabels(List<String> memberDeviceLabels) {
        if (kind != GroupKind.DYNAMIC) {
            throw new IllegalStateException(ERROR_ONLY_DYNAMIC_EDITABLE);
        }
        if (state != GroupState.INACTIVE) {
            throw new IllegalStateException(ERROR_ACTIVE_GROUP_IMMUTABLE);
        }
        if (memberDeviceLabels == null) {
            throw new IllegalArgumentException(ERROR_MEMBER_LABELS_NULL);
        }
        this.memberDeviceLabels = List.copyOf(memberDeviceLabels);
    }

    public void setState(GroupState state) {
        if (state == null) {
            throw new IllegalArgumentException(ERROR_STATE_NULL);
        }
        this.state = state;
    }
}
