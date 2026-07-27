package frc.robot.devices.ctre;

import frc.robot.BringupUtil;
import frc.robot.devices.DeviceDslSupport;
import frc.robot.devices.DeviceLifecycleOwnership;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.manufacturers.ctre.diag.PdpStatusAttachment;
import frc.robot.manufacturers.ctre.util.PdpStatusReader;
import frc.robot.registry.RegistrationHeader;

/**
 * NAME
 *   CtrePdpDevice - DeviceUnit wrapper for CTRE PDP status.
 *
 * DESCRIPTION
 *   Attaches to an app-owned singleton PowerDistribution reader so runtime
 *   teardown can detach wrappers without reallocating the PDP in-process.
 */
public final class CtrePdpDevice implements DeviceUnit {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "PDP",
      "CTRE",
      "PDP",
      "WPILib",
      "Team",
      "2026-04-26",
      "CTRE power distribution panel status reader.");

  private static final String VENDOR = "CTRE";
  private static final String DEVICE_TYPE = "PDP";
  private static final String NOTE_NOT_ADDED = "not added";
  private static final String NOTE_READ_FAIL_PREFIX = "PDP read failed: ";

  private final int canId;
  private final String label;
  private PdpStatusReader reader;

  /**
   * NAME
   *   CtrePdpDevice - Construct a CTRE PDP device wrapper.
   *
   * PARAMETERS
   *   canId - CAN module ID.
   *   label - Display label.
   */
  public CtrePdpDevice(int canId, String label) {
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

  /**
   * NAME
   *   getActiveReaderForProbe - Return the current runtime-owned PDP reader.
   *
   * RETURNS
   *   Active PdpStatusReader instance, or null when the runtime has not attached it.
   */
  public PdpStatusReader getActiveReaderForProbe() {
    if (reader == null) {
      reader = BringupUtil.peekAppSingletonService(this, PdpStatusReader.class);
    }
    return reader;
  }

  @Override
  public boolean isCreated() {
    return getActiveReaderForProbe() != null;
  }

  @Override
  public void ensureCreated() {
    if (getActiveReaderForProbe() != null) {
      return;
    }
    reader = BringupUtil.acquireAppSingletonService(this, PdpStatusReader.class, () -> new PdpStatusReader(canId));
  }

  @Override
  public void close() {
    reader = getActiveReaderForProbe();
  }

  @Override
  public void clearFaults() {
    PdpStatusReader activeReader = getActiveReaderForProbe();
    if (activeReader != null) {
      activeReader.clearStickyFaults();
    }
  }

  @Override
  public DeviceSnapshot snapshot() {
    DeviceSnapshot snap = baseSnapshot();
    PdpStatusReader activeReader = getActiveReaderForProbe();
    if (activeReader == null) {
      snap.present = false;
      snap.note = NOTE_NOT_ADDED;
      return snap;
    }
    try {
      PdpStatusAttachment status = activeReader.snapshot();
      snap.present = true;
      snap.addAttachment(status);
    } catch (RuntimeException ex) {
      snap.present = false;
      snap.note = NOTE_READ_FAIL_PREFIX + ex.getMessage();
    }
    return snap;
  }

  private DeviceSnapshot baseSnapshot() {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = VENDOR;
    snap.deviceType = DEVICE_TYPE;
    snap.canId = canId;
    snap.label = label;
    return snap;
  }

  @Override
  public DeviceLifecycleOwnership getLifecycleOwnership() {
    return DeviceLifecycleOwnership.APP_OWNED_SINGLETON_SERVICE;
  }

  @Override
  public Object readDslSignal(String signalName) {
    return DeviceDslSupport.readPowerDistributionSignal(this, signalName);
  }

  @Override
  public boolean clearDslSignal(String signalName) {
    return DeviceDslSupport.clearFaultSignal(this, signalName);
  }
}
