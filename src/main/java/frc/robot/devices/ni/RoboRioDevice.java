package frc.robot.devices.ni;

import frc.robot.BringupUtil;
import frc.robot.devices.DeviceLifecycleOwnership;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.manufacturers.ni.util.RoboRioStatusReader;
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
      "robotController",
      "WPILib",
      "Team",
      "2026-04-26",
      "Virtual roboRIO controller entry.");

  private static final String VENDOR = "NI";
  private static final String DEVICE_TYPE = "robotController";
  private static final String NOTE_VIRTUAL = "virtual";

  private final int canId;
  private final String label;
  private final RoboRioStatusReader statusReader;
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
    this(canId, label, new RoboRioStatusReader());
  }

  /**
   * NAME
   *   RoboRioDevice - Construct a roboRIO wrapper with an injected status reader.
   *
   * PARAMETERS
   *   canId - CAN identity ID.
   *   label - Display label.
   *   statusReader - controller telemetry reader used for snapshot attachments.
   */
  public RoboRioDevice(int canId, String label, RoboRioStatusReader statusReader) {
    this.canId = canId;
    this.label = label;
    this.statusReader = statusReader;
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
    return created || BringupUtil.hasAppSingletonService(this);
  }

  @Override
  public void ensureCreated() {
    BringupUtil.markAppSingletonAllocated(this);
    created = true;
  }

  @Override
  public void close() {
    created = isCreated();
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
    snap.present = true;
    snap.note = NOTE_VIRTUAL;
    snap.addAttachment(statusReader.readSharedPowerAttachment());
    snap.addAttachment(statusReader.readSharedRailsAttachment());
    snap.addAttachment(statusReader.readSharedBusAttachment());
    snap.addAttachment(statusReader.readPowerAttachment());
    snap.addAttachment(statusReader.readRailsAttachment());
    return snap;
  }

  @Override
  public Object readDslSignal(String signalName) {
    return frc.robot.devices.DeviceDslSupport.readRobotControllerSignal(this, signalName);
  }

  @Override
  public DeviceLifecycleOwnership getLifecycleOwnership() {
    return DeviceLifecycleOwnership.APP_OWNED_SINGLETON_SERVICE;
  }
}
