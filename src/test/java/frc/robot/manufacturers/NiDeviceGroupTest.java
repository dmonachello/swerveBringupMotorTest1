package frc.robot.manufacturers;

import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/**
 * NAME
 *   NiDeviceGroupTest - Regression coverage for NI bringup registrations.
 *
 * DESCRIPTION
 *   Verifies the NI runtime group registers the shared robot-controller
 *   classifier type so profile activation can instantiate the virtual wrapper.
 */
public class NiDeviceGroupTest {

  @Test
  void niGroupRegistersRobotControllerDeviceType() {
    NiDeviceGroup group = new NiDeviceGroup();

    boolean found =
        group.getDeviceBuckets().stream()
            .map(DeviceTypeBucket::getRegistration)
            .anyMatch(registration -> "robotController".equals(registration.deviceType()));

    assertTrue(found, "Expected NI group to register robotController devices.");
  }
}
