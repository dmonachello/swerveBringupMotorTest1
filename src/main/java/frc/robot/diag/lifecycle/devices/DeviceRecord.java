package frc.robot.diag.lifecycle.devices;

/**
 * NAME
 *     DeviceRecord - immutable declared facts for a lifecycle-managed device.
 *
 * PARAMETERS
 *     label - globally unique device label.
 *     lifecycleKind - normal or singleton lifecycle policy.
 */
public record DeviceRecord(String label, DeviceLifecycleKind lifecycleKind) {
    private static final String ERROR_LABEL_BLANK = "Device label must not be blank";
    private static final String ERROR_LIFECYCLE_NULL = "Device lifecycle kind must not be null";

    public DeviceRecord {
        if (label == null || label.isBlank()) {
            throw new IllegalArgumentException(ERROR_LABEL_BLANK);
        }
        if (lifecycleKind == null) {
            throw new IllegalArgumentException(ERROR_LIFECYCLE_NULL);
        }
    }
}
