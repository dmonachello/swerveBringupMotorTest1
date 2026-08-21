package frc.robot.devices;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.devices.ni.RoboRioDevice;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.manufacturers.ni.util.RoboRioStatusReader;
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

  @Test
  void roboRioSnapshotAlwaysReportsVirtualPresence() {
    RoboRioDevice device =
        new RoboRioDevice(
            0,
            "roborio",
            new RoboRioStatusReader(new FakeTelemetrySource()));

    DeviceSnapshot snapshot = device.snapshot();

    assertTrue(snapshot.present);
    assertEquals("virtual", snapshot.note);
    assertFalse(device.isCreated());
  }

  private static final class FakeTelemetrySource implements RoboRioStatusReader.TelemetrySource {
    @Override
    public double inputVoltage() {
      return 12.5;
    }

    @Override
    public boolean brownedOut() {
      return false;
    }

    @Override
    public double brownoutVoltage() {
      return 6.3;
    }

    @Override
    public double rail3v3Voltage() {
      return 3.3;
    }

    @Override
    public double rail3v3Current() {
      return 0.1;
    }

    @Override
    public boolean rail3v3Enabled() {
      return true;
    }

    @Override
    public int rail3v3FaultCount() {
      return 0;
    }

    @Override
    public double rail5vVoltage() {
      return 5.0;
    }

    @Override
    public double rail5vCurrent() {
      return 0.2;
    }

    @Override
    public boolean rail5vEnabled() {
      return true;
    }

    @Override
    public int rail5vFaultCount() {
      return 0;
    }

    @Override
    public double rail6vVoltage() {
      return 6.0;
    }

    @Override
    public double rail6vCurrent() {
      return 0.3;
    }

    @Override
    public boolean rail6vEnabled() {
      return true;
    }

    @Override
    public int rail6vFaultCount() {
      return 0;
    }

    @Override
    public double canUtilizationPct() {
      return 0.0;
    }

    @Override
    public int canRxErrorCount() {
      return 0;
    }

    @Override
    public int canTxErrorCount() {
      return 0;
    }

    @Override
    public int canBusOffCount() {
      return 0;
    }

    @Override
    public int canTxFullCount() {
      return 0;
    }
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
