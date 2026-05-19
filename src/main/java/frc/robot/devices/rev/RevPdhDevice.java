package frc.robot.devices.rev;

import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.manufacturers.rev.diag.PdhStatusAttachment;
import frc.robot.manufacturers.rev.util.PdhStatusReader;
import frc.robot.registry.RegistrationHeader;

/**
 * NAME
 *   RevPdhDevice - DeviceUnit wrapper for REV PDH status.
 *
 * DESCRIPTION
 *   Owns the WPILib PowerDistribution allocation through the same lifecycle
 *   used by motor and sensor devices.
 */
public final class RevPdhDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "PDH",
      "REV",
      "PDH",
      "WPILib",
      "Team",
      "2026-04-26",
      "REV power distribution hub status reader.");

  private static final String VENDOR = "REV";
  private static final String DEVICE_TYPE = "PDH";
  private static final String NOTE_NOT_ADDED = "not added";
  private static final String NOTE_READ_FAIL_PREFIX = "PDH read failed: ";

  private final int canId;
  private final String label;
  private PdhStatusReader reader;

  /**
   * NAME
   *   RevPdhDevice - Construct a REV PDH device wrapper.
   *
   * PARAMETERS
   *   canId - CAN module ID.
   *   label - Display label.
   */
  public RevPdhDevice(int canId, String label) {
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
    return reader != null;
  }

  @Override
  public void ensureCreated() {
    if (reader == null) {
      reader = new PdhStatusReader(canId);
    }
  }

  @Override
  public void close() {
    if (reader != null) {
      reader.close();
      reader = null;
    }
  }

  @Override
  public void clearFaults() {
    if (reader != null) {
      reader.clearStickyFaults();
    }
  }

  @Override
  public DeviceSnapshot snapshot() {
    DeviceSnapshot snap = baseSnapshot();
    if (reader == null) {
      snap.present = false;
      snap.note = NOTE_NOT_ADDED;
      return snap;
    }
    try {
      PdhStatusAttachment status = reader.snapshot();
      snap.present = true;
      snap.addAttachment(status);
    } catch (RuntimeException ex) {
      snap.present = false;
      snap.note = NOTE_READ_FAIL_PREFIX + ex.getMessage();
    }
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

  private DeviceSnapshot baseSnapshot() {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = VENDOR;
    snap.deviceType = DEVICE_TYPE;
    snap.canId = canId;
    snap.label = label;
    return snap;
  }
}
