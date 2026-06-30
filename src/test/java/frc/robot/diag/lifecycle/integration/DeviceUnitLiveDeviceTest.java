package frc.robot.diag.lifecycle.integration;

import static org.junit.jupiter.api.Assertions.assertEquals;

import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class DeviceUnitLiveDeviceTest {
  private static final int TEST_CAN_ID = 9;
  private static final String TEST_DEVICE_TYPE = "motor";
  private static final String TEST_LABEL = "FALCON 9";

  @Test
  void closeCallsDeactivateBeforeClose() {
    List<String> events = new ArrayList<>();
    DeviceUnit unit =
        new DeviceUnit() {
          @Override
          public int getCanId() {
            return TEST_CAN_ID;
          }

          @Override
          public String getDeviceType() {
            return TEST_DEVICE_TYPE;
          }

          @Override
          public String getLabel() {
            return TEST_LABEL;
          }

          @Override
          public boolean isCreated() {
            return true;
          }

          @Override
          public void ensureCreated() {}

          @Override
          public void close() {
            events.add("close");
          }

          @Override
          public void deactivate() {
            events.add("deactivate");
          }

          @Override
          public void clearFaults() {}

          @Override
          public DeviceSnapshot snapshot() {
            return new DeviceSnapshot();
          }

          @Override
          public RegistrationHeader getHeader() {
            return new RegistrationHeader(TEST_LABEL, "CTRE", TEST_DEVICE_TYPE, "test", "unit", "", "");
          }
        };

    DeviceUnitLiveDevice liveDevice = new DeviceUnitLiveDevice(unit);
    liveDevice.close();

    assertEquals(List.of("deactivate", "close"), events);
  }
}
