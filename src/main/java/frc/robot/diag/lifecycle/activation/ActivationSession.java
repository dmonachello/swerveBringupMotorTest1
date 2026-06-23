package frc.robot.diag.lifecycle.activation;

import java.util.List;

/**
 * NAME
 *     ActivationSession - store the current active lifecycle session contract.
 */
public record ActivationSession(
        String sessionId,
        String requestedLabel,
        List<String> requestedDeviceLabels,
        ActivationMode mode) {
    private static final String ERROR_SESSION_ID_BLANK = "Session ID must not be blank";
    private static final String ERROR_REQUESTED_LABEL_BLANK = "Requested label must not be blank";
    private static final String ERROR_REQUESTED_DEVICE_LABELS_NULL =
            "Requested device labels must not be null";
    private static final String ERROR_MODE_NULL = "Activation mode must not be null";

    public ActivationSession {
        if (sessionId == null || sessionId.isBlank()) {
            throw new IllegalArgumentException(ERROR_SESSION_ID_BLANK);
        }
        if (requestedLabel == null || requestedLabel.isBlank()) {
            throw new IllegalArgumentException(ERROR_REQUESTED_LABEL_BLANK);
        }
        if (requestedDeviceLabels == null) {
            throw new IllegalArgumentException(ERROR_REQUESTED_DEVICE_LABELS_NULL);
        }
        if (mode == null) {
            throw new IllegalArgumentException(ERROR_MODE_NULL);
        }
        requestedDeviceLabels = List.copyOf(requestedDeviceLabels);
    }
}
