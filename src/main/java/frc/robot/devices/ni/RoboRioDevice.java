package frc.robot.devices.ni;

import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.registry.RegistrationHeader;

/**
 * NAME
 *   RoboRioDevice - Virtual DeviceUnit for the roboRIO controller.
 *
 * DESCRIPTION
 *   Represents the roboRIO in the same manufacturer/device snapshot pipeline
 *   as CAN hardware without allocating a vendor device object.
 */
public final class RoboRioDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "roboRIO",
      "NI",
      "roboRIO",
      "WPILib",
      "Team",
      "2026-04-26",
      "Virtual roboRIO controller entry.");

  private static final String VENDOR = "NI";
  private static final String DEVICE_TYPE = "roboRIO";
  private static final String NOTE_VIRTUAL = "virtual";

  private final int canId;
  private final String label;
  private boolean created;

  /**
   * NAME
   *   RoboRioDevice - Construct a virtual roboRIO device wrapper.
   *
   * PARAMETERS
   *   canId - CAN identity ID.
   *   label - Display label.
   */
  public RoboRioDevice(int canId, String label) {
    this.canId = canId;
    this.label = label;
  }

  @Override
  public int getCanId() {
    return canId;
  }

  @Override
  public String getDeviceType() {
    return DEVICE_TYPE;
  }

  @Override
  public String getLabel() {
    return label;
  }

  @Override
  public RegistrationHeader getHeader() {
    return HEADER;
  }

  @Override
  public boolean isCreated() {
    return created;
  }

  @Override
  public void ensureCreated() {
    created = true;
  }

  @Override
  public void close() {
    created = false;
  }

  @Override
  public void clearFaults() {}

  @Override
  public DeviceSnapshot snapshot() {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = VENDOR;
    snap.deviceType = DEVICE_TYPE;
    snap.canId = canId;
    snap.label = label;
    snap.present = created;
    snap.note = NOTE_VIRTUAL;
    return snap;
  }

  @Override
  public Object readDslSignal(String signalName) {
    return null;
  }

  @Override
  public boolean writeDslSignal(String signalName, double value) {
    return false;
  }

  @Override
  public boolean clearDslSignal(String signalName) {
    return false;
  }

  @Override
  public boolean isDslWritableValueInRange(String signalName, double value) {
    return true;
  }
}
