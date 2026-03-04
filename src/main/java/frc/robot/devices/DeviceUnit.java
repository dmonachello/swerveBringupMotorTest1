package frc.robot.devices;

import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.HasRegistrationHeader;

// Base interface for a single hardware device slot.
public interface DeviceUnit extends HasRegistrationHeader {
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

  default String getMotorModelOverride() {
    return null;
  }

  // Optional hooks for non-motor devices (no-op by default).
  default void activate() {}

  default void deactivate() {}

  // Optional test hook for non-motor devices (no-op by default).
  default boolean hasTest() {
    return false;
  }

  default String getTestName() {
    return "";
  }

  default void runTest() {}

  // Optional encoder position in rotations (internal or external sensor).
  default Double getPositionRotations() {
    return null;
  }

  // Optional encoder position in rotations with source-specific handling.
  default Double getPositionRotations(String encoderSource, Integer countsPerRev) {
    return getPositionRotations();
  }
}
