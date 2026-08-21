package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.diag.snapshots.MotorSpecAttachment;
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

  @Test
  void buildMotorSpecAttachmentMarksMatchedSpec() {
    MotorSpecAttachment attachment = BringupUtil.buildMotorSpecAttachment("FALCON 9", "Falcon 500");

    assertNotNull(attachment);
    assertTrue(attachment.matched);
    assertEquals("Falcon 500", attachment.requestedModel);
    assertEquals("CTRE Falcon 500", attachment.model);
  }

  @Test
  void buildMotorSpecAttachmentCarriesMissingSpecRequest() {
    MotorSpecAttachment attachment = BringupUtil.buildMotorSpecAttachment("FALCON 9", "Unknown Motor");

    assertNotNull(attachment);
    assertFalse(attachment.matched);
    assertEquals("Unknown Motor", attachment.requestedModel);
    assertEquals("", attachment.model);
  }
}
