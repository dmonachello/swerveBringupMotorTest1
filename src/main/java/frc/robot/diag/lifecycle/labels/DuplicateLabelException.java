package frc.robot.diag.lifecycle.labels;

/**
 * NAME
 *     DuplicateLabelException - report a duplicate global lifecycle label registration.
 */
public final class DuplicateLabelException extends RuntimeException {
    private static final String MESSAGE_PREFIX = "Label already registered: ";

    /**
     * NAME
     *     DuplicateLabelException - build the duplicate-label failure.
     *
     * PARAMETERS
     *     label - the duplicate label value.
     */
    public DuplicateLabelException(String label) {
        super(MESSAGE_PREFIX + label);
    }
}
