package frc.robot.diag.lifecycle.groups;

import java.util.List;

/**
 * NAME
 *     GroupDeclaration - simple input declaration used to load lifecycle group records.
 *
 * PARAMETERS
 *     label - globally unique group label.
 *     memberDeviceLabels - ordered member device labels.
 */
public record GroupDeclaration(String label, List<String> memberDeviceLabels) {
    private static final String ERROR_LABEL_BLANK = "Group label must not be blank";
    private static final String ERROR_MEMBER_LABELS_NULL = "Group member labels must not be null";

    public GroupDeclaration {
        if (label == null || label.isBlank()) {
            throw new IllegalArgumentException(ERROR_LABEL_BLANK);
        }
        if (memberDeviceLabels == null) {
            throw new IllegalArgumentException(ERROR_MEMBER_LABELS_NULL);
        }
    }
}
