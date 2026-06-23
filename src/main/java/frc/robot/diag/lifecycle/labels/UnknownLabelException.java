package frc.robot.diag.lifecycle.labels;

/**
 * NAME
 *     UnknownLabelException - report an unresolved global lifecycle label.
 */
public final class UnknownLabelException extends RuntimeException {
    private static final String MESSAGE_PREFIX = "Unknown label: ";

    /**
     * NAME
     *     UnknownLabelException - build the unknown-label failure.
     *
     * PARAMETERS
     *     label - the missing label value.
     */
    public UnknownLabelException(String label) {
        super(MESSAGE_PREFIX + label);
    }
}
