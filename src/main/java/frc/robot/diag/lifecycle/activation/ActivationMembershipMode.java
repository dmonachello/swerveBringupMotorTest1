package frc.robot.diag.lifecycle.activation;

/**
 * NAME
 *     ActivationMembershipMode - requested membership-selection policy for lifecycle activation.
 *
 * DESCRIPTION
 *     Separates "which devices should be attempted" from session access mode. Strict requires all
 *     requested members to be runnable, partial skips members that are currently not runnable, and
 *     force attempts all requested members regardless of current evidence.
 */
public enum ActivationMembershipMode {
    STRICT,
    PARTIAL,
    FORCE
}
