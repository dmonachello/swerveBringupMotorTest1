package frc.robot.manufacturers;

import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/**
 * NAME
 *   CtreDeviceGroupTest - Regression coverage for CTRE bringup registrations.
 *
 * DESCRIPTION
 *   Verifies newly supported CTRE device types are registered in the runtime
 *   manufacturer group so profile activation can instantiate them.
 */
public class CtreDeviceGroupTest {

  @Test
  void ctreGroupRegistersPigeonDeviceType() {
    CtreDeviceGroup group = new CtreDeviceGroup();

    boolean found =
        group.getDeviceBuckets().stream()
            .map(DeviceTypeBucket::getRegistration)
            .anyMatch(registration -> "Pigeon".equals(registration.deviceType()));

    assertTrue(found, "Expected CTRE group to register Pigeon devices.");
  }
}
