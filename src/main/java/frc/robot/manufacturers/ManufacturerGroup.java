package frc.robot.manufacturers;

import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.devices.DeviceUnit;
import frc.robot.registry.RegistrationHeader;
import java.util.List;

// Common interface for manufacturer device groups.
public interface ManufacturerGroup {
  RegistrationHeader getHeader();
  List<DeviceTypeBucket> getDeviceBuckets();
  DeviceAddResult addNextMotor();
  void resetLowCurrentTimers();
  List<DeviceUnit> getTestDevices();
  void addAll();
  void setDuty(double duty);
  void stopAll();
  void clearFaults();
  void closeAll();
  List<DeviceSnapshot> captureSnapshots(double nowSec);
}
