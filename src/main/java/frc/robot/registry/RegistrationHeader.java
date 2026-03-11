package frc.robot.registry;

/**
 * NAME
 *   RegistrationHeader - Metadata for registered manufacturers/devices.
 */
public record RegistrationHeader(
    String name,
    String vendor,
    String deviceType,
    String source,
    String owner,
    String lastUpdated,
    String notes) {}
