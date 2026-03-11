package frc.robot.manufacturers;

import frc.robot.registry.RegistrationHeader;

/**
 * NAME
 * DeviceRegistration
 *
 * SYNOPSIS
 * Record describing a registered device type for a manufacturer.
 *
 * DESCRIPTION
 * Captures the header metadata, device identifiers, role, and factory needed
 * to instantiate a device during bringup.
 */
public record DeviceRegistration(
    RegistrationHeader header,
    String vendor,
    String deviceType,
    String displayName,
    DeviceRole role,
    boolean requiresMotorSpec,
    DeviceFactory factory) {}
