package frc.robot.diag.lifecycle.activation;

import java.util.List;

/**
 * NAME
 *     DeactivateResult - external proof object for lifecycle deactivation attempts.
 */
public record DeactivateResult(
        boolean success,
        String requestedLabel,
        String sessionId,
        List<String> deactivatedDeviceLabels,
        LifecycleState state,
        String errorCode,
        String errorMessage) {
    public DeactivateResult {
        deactivatedDeviceLabels =
                deactivatedDeviceLabels == null ? List.of() : List.copyOf(deactivatedDeviceLabels);
    }
}
