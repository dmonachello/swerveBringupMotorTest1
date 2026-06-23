package frc.robot.diag.lifecycle.runtime;

/**
 * NAME
 *     DeviceRuntimeState - store mutable lifecycle runtime facts for one declared device.
 *
 * DESCRIPTION
 *     This state is independent from live vendor objects. It survives deactivate and leaves
 *     room for future presence and health evidence without conflating those concepts with
 *     instantiation.
 */
public final class DeviceRuntimeState {
    private boolean instantiated;
    private boolean active;
    private String activeSessionId;
    private String activeGroupLabel;
    private String lastActivationMode;
    private String lastError;
    private PresenceState presenceState;
    private HealthState healthState;

    /**
     * NAME
     *     DeviceRuntimeState - initialize an inactive, unknown runtime state.
     */
    public DeviceRuntimeState() {
        this.instantiated = false;
        this.active = false;
        this.activeSessionId = null;
        this.activeGroupLabel = null;
        this.lastActivationMode = null;
        this.lastError = null;
        this.presenceState = PresenceState.UNKNOWN;
        this.healthState = HealthState.UNKNOWN;
    }

    public boolean isInstantiated() {
        return instantiated;
    }

    public boolean isActive() {
        return active;
    }

    public String activeSessionId() {
        return activeSessionId;
    }

    public String activeGroupLabel() {
        return activeGroupLabel;
    }

    public String lastActivationMode() {
        return lastActivationMode;
    }

    public String lastError() {
        return lastError;
    }

    public PresenceState presenceState() {
        return presenceState;
    }

    public HealthState healthState() {
        return healthState;
    }

    /**
     * NAME
     *     markActivated - record a successful activation for this device.
     *
     * PARAMETERS
     *     sessionId - owning session identifier.
     *     groupLabel - requested activation label.
     *     activationMode - string name of the activation mode.
     */
    public void markActivated(String sessionId, String groupLabel, String activationMode) {
        this.instantiated = true;
        this.active = true;
        this.activeSessionId = sessionId;
        this.activeGroupLabel = groupLabel;
        this.lastActivationMode = activationMode;
        this.lastError = null;
    }

    /**
     * NAME
     *     markDeactivated - record a deactivation while preserving singleton state when needed.
     *
     * PARAMETERS
     *     keepInstantiated - true when the device remains instantiated after deactivate.
     */
    public void markDeactivated(boolean keepInstantiated) {
        this.active = false;
        this.activeSessionId = null;
        this.activeGroupLabel = null;
        this.instantiated = keepInstantiated;
    }

    /**
     * NAME
     *     markActivationFailed - record an activation failure for this device.
     *
     * PARAMETERS
     *     error - compact lifecycle error code.
     */
    public void markActivationFailed(String error) {
        this.active = false;
        this.instantiated = false;
        this.activeSessionId = null;
        this.activeGroupLabel = null;
        this.lastError = error;
    }
}
