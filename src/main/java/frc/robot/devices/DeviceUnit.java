package frc.robot.devices;

import frc.robot.diag.snapshots.DeviceSnapshot;

// Base interface for a single hardware device slot.
public interface DeviceUnit {
  int getCanId();
  String getDeviceType();
  String getLabel();
  boolean isCreated();
  void ensureCreated();
  void close();
  void clearFaults();
  DeviceSnapshot snapshot();

  default void setDuty(double duty) {}

  default void stop() {}
}
