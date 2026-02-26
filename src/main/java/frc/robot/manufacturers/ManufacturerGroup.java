package frc.robot.manufacturers;

import frc.robot.diag.snapshots.DeviceSnapshot;
import java.util.List;

// Common interface for manufacturer device groups.
public interface ManufacturerGroup {
  void addAll();
  void setDuty(double duty);
  void stopAll();
  void clearFaults();
  void closeAll();
  List<DeviceSnapshot> captureSnapshots();
}
