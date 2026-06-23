package frc.robot.diag.lifecycle.devices;

/**
 * NAME
 *     DeviceDeclaration - simple input declaration used to load lifecycle device records.
 *
 * PARAMETERS
 *     label - globally unique device label.
 *     lifecycleKind - normal or singleton lifecycle policy.
 */
public record DeviceDeclaration(String label, DeviceLifecycleKind lifecycleKind) {
    /**
     * NAME
     *     toRecord - convert the declaration into an immutable runtime-independent record.
     *
     * RETURNS
     *     A validated DeviceRecord.
     */
    public DeviceRecord toRecord() {
        return new DeviceRecord(label, lifecycleKind);
    }
}
