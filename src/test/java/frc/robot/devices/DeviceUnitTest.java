package frc.robot.devices;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.devices.ni.RoboRioDevice;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.manufacturers.microsoft.XboxControllerDevice;
import org.junit.jupiter.api.Test;

class DeviceUnitTest {

  @Test
  void shutdownClosesRuntimeOwnedDevices() {
    FakeDevice device = new FakeDevice(DeviceLifecycleOwnership.RUNTIME_OWNED_RECREATABLE);

    device.shutdown();

    assertEquals(1, device.deactivateCalls);
    assertEquals(1, device.closeCalls);
  }

  @Test
  void shutdownPreservesAppOwnedSingletonDevices() {
    FakeDevice device = new FakeDevice(DeviceLifecycleOwnership.APP_OWNED_SINGLETON_SERVICE);

    device.shutdown();

    assertEquals(1, device.deactivateCalls);
    assertEquals(0, device.closeCalls);
  }

  @Test
  void xboxControllerSingletonRemainsCreatedAcrossWrapperReplacement() {
    XboxControllerDevice first = new XboxControllerDevice(9100, "controller0-test");

    first.ensureCreated();
    first.close();

    XboxControllerDevice replacement = new XboxControllerDevice(9100, "controller0-test");

    assertTrue(first.isCreated());
    assertTrue(replacement.isCreated());
  }

  @Test
  void roboRioSingletonRemainsCreatedAcrossWrapperReplacement() {
    RoboRioDevice first = new RoboRioDevice(9101, "roborio-test");

    first.ensureCreated();
    first.close();

    RoboRioDevice replacement = new RoboRioDevice(9101, "roborio-test");

    assertTrue(first.isCreated());
    assertTrue(replacement.isCreated());
  }

  private static final class FakeDevice implements DeviceUnit {
    private final DeviceLifecycleOwnership ownership;
    private int deactivateCalls;
    private int closeCalls;

    FakeDevice(DeviceLifecycleOwnership ownership) {
      this.ownership = ownership;
    }

    @Override
    public int getCanId() {
      return 0;
    }

    @Override
    public String getDeviceType() {
      return "fake";
    }

    @Override
    public String getLabel() {
      return "fake";
    }

    @Override
    public boolean isCreated() {
      return false;
    }

    @Override
    public void ensureCreated() {}

    @Override
    public void close() {
      closeCalls++;
    }

    @Override
    public void clearFaults() {}

    @Override
    public DeviceSnapshot snapshot() {
      return new DeviceSnapshot();
    }

    @Override
    public void deactivate() {
      deactivateCalls++;
    }

    @Override
    public DeviceLifecycleOwnership getLifecycleOwnership() {
      return ownership;
    }

    @Override
    public frc.robot.registry.RegistrationHeader getHeader() {
      return new frc.robot.registry.RegistrationHeader(
          "fake",
          "fake",
          "fake",
          "fake",
          "fake",
          "2026-07-26",
          "fake");
    }
  }
}
