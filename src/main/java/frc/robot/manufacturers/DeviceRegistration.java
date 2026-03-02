package frc.robot.manufacturers;

import frc.robot.registry.RegistrationHeader;

// Defines a device type registration within a manufacturer.
public record DeviceRegistration(
    RegistrationHeader header,
    String vendor,
    String deviceType,
    String displayName,
    DeviceRole role,
    boolean requiresMotorSpec,
    DeviceFactory factory) {}
