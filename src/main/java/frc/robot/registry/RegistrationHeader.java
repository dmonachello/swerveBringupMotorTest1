package frc.robot.registry;

// Required metadata for any registered manufacturer or device.
public record RegistrationHeader(
    String name,
    String vendor,
    String deviceType,
    String source,
    String owner,
    String lastUpdated,
    String notes) {}
