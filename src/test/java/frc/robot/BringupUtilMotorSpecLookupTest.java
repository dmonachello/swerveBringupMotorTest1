package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import org.junit.jupiter.api.Test;

class BringupUtilMotorSpecLookupTest {

  @Test
  void getMotorSpecForDeviceAcceptsFalcon500AliasOverride() {
    BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice("FALCON 9", "Falcon 500");

    assertNotNull(spec);
    assertEquals("CTRE Falcon 500", spec.model);
  }

  @Test
  void getMotorSpecForDeviceFallsBackToFalconLabelInference() {
    BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice("FALCON 9", "");

    assertNotNull(spec);
    assertEquals("CTRE Falcon 500", spec.model);
  }

  @Test
  void getMotorSpecForDeviceAcceptsCanonicalRevNeoOverride() {
    BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice("REV_MOTORCONTROLLER_25", "REV NEO");

    assertNotNull(spec);
    assertEquals("REV NEO", spec.model);
  }
}
