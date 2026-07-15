package frc.robot.diag.lifecycle.activation;

import java.util.List;

/**
 * NAME
 *     ActivationResult - external proof object for lifecycle activation attempts.
 */
public record ActivationResult(
        boolean success,
        String requestedLabel,
        String sessionId,
        ActivationMode mode,
        ActivationMembershipMode membershipMode,
        List<String> requestedDeviceLabels,
        List<String> instantiatedDeviceLabels,
        List<String> failedDeviceLabels,
        List<String> skippedDeviceLabels,
        LifecycleState state,
        String errorCode,
        String errorMessage) {
    public ActivationResult {
        requestedDeviceLabels = requestedDeviceLabels == null ? List.of() : List.copyOf(requestedDeviceLabels);
        instantiatedDeviceLabels =
                instantiatedDeviceLabels == null ? List.of() : List.copyOf(instantiatedDeviceLabels);
        failedDeviceLabels = failedDeviceLabels == null ? List.of() : List.copyOf(failedDeviceLabels);
        skippedDeviceLabels = skippedDeviceLabels == null ? List.of() : List.copyOf(skippedDeviceLabels);
    }
}
