package frc.robot.manufacturers;

import frc.robot.devices.DeviceUnit;

// Result of adding the next device in a bucket.
public record DeviceAddResult(DeviceUnit device, int index, DeviceRegistration registration) {}
