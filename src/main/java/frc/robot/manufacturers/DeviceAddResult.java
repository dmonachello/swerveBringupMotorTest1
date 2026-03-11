package frc.robot.manufacturers;

import frc.robot.devices.DeviceUnit;

/**
 * NAME
 * DeviceAddResult
 *
 * SYNOPSIS
 * Record describing the outcome of adding a device from a bucket.
 *
 * DESCRIPTION
 * Captures the constructed device, its index within the bucket, and the
 * registration that produced it.
 */
public record DeviceAddResult(DeviceUnit device, int index, DeviceRegistration registration) {}
