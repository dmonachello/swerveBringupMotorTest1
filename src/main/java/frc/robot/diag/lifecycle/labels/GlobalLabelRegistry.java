package frc.robot.diag.lifecycle.labels;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *     GlobalLabelRegistry - own the shared namespace for lifecycle device and group labels.
 *
 * DESCRIPTION
 *     This registry enforces one global namespace shared by device labels and group labels.
 *     It is the first guard against ambiguous activation targets.
 */
public final class GlobalLabelRegistry {
    private static final String ERROR_LABEL_BLANK = "Label must not be blank";

    private final Map<String, LabelKind> labelsByName = new LinkedHashMap<>();

    /**
     * NAME
     *     registerDeviceLabel - register a device label in the global namespace.
     *
     * PARAMETERS
     *     label - the device label to register.
     *
     * ERRORS
     *     Throws DuplicateLabelException when the label already exists.
     */
    public void registerDeviceLabel(String label) {
        register(label, LabelKind.DEVICE);
    }

    /**
     * NAME
     *     registerGroupLabel - register a group label in the global namespace.
     *
     * PARAMETERS
     *     label - the group label to register.
     *
     * ERRORS
     *     Throws DuplicateLabelException when the label already exists.
     */
    public void registerGroupLabel(String label) {
        register(label, LabelKind.GROUP);
    }

    /**
     * NAME
     *     unregisterLabel - remove one label from the shared namespace.
     *
     * PARAMETERS
     *     label - the label to remove.
     *
     * NOTES
     *     Missing labels are ignored so dynamic-group sync can converge on the current runtime
     *     state without requiring a separate existence check.
     */
    public void unregisterLabel(String label) {
        if (label == null || label.isBlank()) {
            throw new IllegalArgumentException(ERROR_LABEL_BLANK);
        }
        labelsByName.remove(label);
    }

    /**
     * NAME
     *     labelKindOf - resolve the kind of a registered global label.
     *
     * PARAMETERS
     *     label - the label to inspect.
     *
     * RETURNS
     *     The registered label kind.
     *
     * ERRORS
     *     Throws UnknownLabelException when the label does not exist.
     */
    public LabelKind labelKindOf(String label) {
        LabelKind kind = labelsByName.get(label);
        if (kind == null) {
            throw new UnknownLabelException(label);
        }
        return kind;
    }

    /**
     * NAME
     *     register - store a label-kind pair after validation.
     *
     * PARAMETERS
     *     label - the label to register.
     *     kind - the lifecycle label kind.
     */
    private void register(String label, LabelKind kind) {
        if (label == null || label.isBlank()) {
            throw new IllegalArgumentException(ERROR_LABEL_BLANK);
        }
        if (labelsByName.containsKey(label)) {
            throw new DuplicateLabelException(label);
        }
        labelsByName.put(label, kind);
    }
}
