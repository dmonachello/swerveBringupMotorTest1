package frc.robot.manufacturers.ni.util;

import edu.wpi.first.wpilibj.RobotController;
import frc.robot.diag.snapshots.RobotControllerBusAttachment;
import frc.robot.diag.snapshots.RobotControllerPowerAttachment;
import frc.robot.diag.snapshots.RobotControllerRailsAttachment;
import frc.robot.manufacturers.ni.diag.RoboRioPowerAttachment;
import frc.robot.manufacturers.ni.diag.RoboRioRailsAttachment;

/**
 * NAME
 *   RoboRioStatusReader - Read roboRIO controller telemetry into attachments.
 *
 * DESCRIPTION
 *   Centralizes roboRIO controller reads behind a small seam so the current
 *   NI implementation can produce structured controller attachments now and
 *   later share the same contract shape with SystemCore.
 */
public final class RoboRioStatusReader {
  private final TelemetrySource source;

  /**
   * NAME
   *   RoboRioStatusReader - Construct using live WPILib controller telemetry.
   */
  public RoboRioStatusReader() {
    this(new WpiTelemetrySource());
  }

  /**
   * NAME
   *   RoboRioStatusReader - Construct using a supplied telemetry source.
   *
   * PARAMETERS
   *   source - abstraction over controller telemetry reads.
   */
  public RoboRioStatusReader(TelemetrySource source) {
    this.source = source != null ? source : new WpiTelemetrySource();
  }

  /**
   * NAME
   *   readPowerAttachment - Build the roboRIO power-health attachment.
   *
   * RETURNS
   *   Structured power-health attachment for the active controller.
   */
  public RoboRioPowerAttachment readPowerAttachment() {
    RoboRioPowerAttachment attachment = new RoboRioPowerAttachment();
    RobotControllerPowerAttachment shared = readSharedPowerAttachment();
    attachment.inputVoltage = shared.inputVoltage;
    attachment.brownedOut = shared.brownout;
    attachment.brownoutVoltage = shared.brownoutVoltage;
    return attachment;
  }

  /**
   * NAME
   *   readRailsAttachment - Build the roboRIO user-rails attachment.
   *
   * RETURNS
   *   Structured rail-health attachment for the active controller.
   */
  public RoboRioRailsAttachment readRailsAttachment() {
    RoboRioRailsAttachment attachment = new RoboRioRailsAttachment();
    RobotControllerRailsAttachment shared = readSharedRailsAttachment();
    attachment.rail3v3Voltage = shared.rail3v3Voltage;
    attachment.rail3v3Current = shared.rail3v3Current;
    attachment.rail3v3Enabled = shared.rail3v3Enabled;
    attachment.rail3v3FaultCount = shared.rail3v3FaultCount;
    attachment.rail5vVoltage = shared.rail5vVoltage;
    attachment.rail5vCurrent = shared.rail5vCurrent;
    attachment.rail5vEnabled = shared.rail5vEnabled;
    attachment.rail5vFaultCount = shared.rail5vFaultCount;
    attachment.rail6vVoltage = shared.rail6vVoltage;
    attachment.rail6vCurrent = shared.rail6vCurrent;
    attachment.rail6vEnabled = shared.rail6vEnabled;
    attachment.rail6vFaultCount = shared.rail6vFaultCount;
    return attachment;
  }

  /**
   * NAME
   *   readSharedPowerAttachment - Build the shared controller-family power attachment.
   *
   * RETURNS
   *   Shared power-health attachment for the active controller.
   */
  public RobotControllerPowerAttachment readSharedPowerAttachment() {
    RobotControllerPowerAttachment attachment = new RobotControllerPowerAttachment();
    attachment.inputVoltage = source.inputVoltage();
    attachment.brownout = source.brownedOut();
    attachment.brownoutVoltage = source.brownoutVoltage();
    return attachment;
  }

  /**
   * NAME
   *   readSharedRailsAttachment - Build the shared controller-family rails attachment.
   *
   * RETURNS
   *   Shared rail-health attachment for the active controller.
   */
  public RobotControllerRailsAttachment readSharedRailsAttachment() {
    RobotControllerRailsAttachment attachment = new RobotControllerRailsAttachment();
    attachment.rail3v3Voltage = source.rail3v3Voltage();
    attachment.rail3v3Current = source.rail3v3Current();
    attachment.rail3v3Enabled = source.rail3v3Enabled();
    attachment.rail3v3FaultCount = source.rail3v3FaultCount();
    attachment.rail5vVoltage = source.rail5vVoltage();
    attachment.rail5vCurrent = source.rail5vCurrent();
    attachment.rail5vEnabled = source.rail5vEnabled();
    attachment.rail5vFaultCount = source.rail5vFaultCount();
    attachment.rail6vVoltage = source.rail6vVoltage();
    attachment.rail6vCurrent = source.rail6vCurrent();
    attachment.rail6vEnabled = source.rail6vEnabled();
    attachment.rail6vFaultCount = source.rail6vFaultCount();
    return attachment;
  }

  /**
   * NAME
   *   readSharedBusAttachment - Build the shared controller-family CAN-bus attachment.
   *
   * RETURNS
   *   Shared bus-health attachment for the active controller.
   */
  public RobotControllerBusAttachment readSharedBusAttachment() {
    RobotControllerBusAttachment attachment = new RobotControllerBusAttachment();
    attachment.canUtilizationPct = source.canUtilizationPct();
    attachment.canRxErrorCount = source.canRxErrorCount();
    attachment.canTxErrorCount = source.canTxErrorCount();
    attachment.canBusOffCount = source.canBusOffCount();
    attachment.canTxFullCount = source.canTxFullCount();
    return attachment;
  }

  /**
   * NAME
   *   TelemetrySource - Abstract roboRIO controller telemetry provider.
   */
  public interface TelemetrySource {
    double inputVoltage();

    boolean brownedOut();

    double brownoutVoltage();

    double rail3v3Voltage();

    double rail3v3Current();

    boolean rail3v3Enabled();

    int rail3v3FaultCount();

    double rail5vVoltage();

    double rail5vCurrent();

    boolean rail5vEnabled();

    int rail5vFaultCount();

    double rail6vVoltage();

    double rail6vCurrent();

    boolean rail6vEnabled();

    int rail6vFaultCount();

    double canUtilizationPct();

    int canRxErrorCount();

    int canTxErrorCount();

    int canBusOffCount();

    int canTxFullCount();
  }

  /**
   * NAME
   *   WpiTelemetrySource - Live RobotController-backed telemetry source.
   */
  private static final class WpiTelemetrySource implements TelemetrySource {
    @Override
    public double inputVoltage() {
      return RobotController.getInputVoltage();
    }

    @Override
    public boolean brownedOut() {
      return RobotController.isBrownedOut();
    }

    @Override
    public double brownoutVoltage() {
      return RobotController.getBrownoutVoltage();
    }

    @Override
    public double rail3v3Voltage() {
      return RobotController.getVoltage3V3();
    }

    @Override
    public double rail3v3Current() {
      return RobotController.getCurrent3V3();
    }

    @Override
    public boolean rail3v3Enabled() {
      return RobotController.getEnabled3V3();
    }

    @Override
    public int rail3v3FaultCount() {
      return RobotController.getFaultCount3V3();
    }

    @Override
    public double rail5vVoltage() {
      return RobotController.getVoltage5V();
    }

    @Override
    public double rail5vCurrent() {
      return RobotController.getCurrent5V();
    }

    @Override
    public boolean rail5vEnabled() {
      return RobotController.getEnabled5V();
    }

    @Override
    public int rail5vFaultCount() {
      return RobotController.getFaultCount5V();
    }

    @Override
    public double rail6vVoltage() {
      return RobotController.getVoltage6V();
    }

    @Override
    public double rail6vCurrent() {
      return RobotController.getCurrent6V();
    }

    @Override
    public boolean rail6vEnabled() {
      return RobotController.getEnabled6V();
    }

    @Override
    public int rail6vFaultCount() {
      return RobotController.getFaultCount6V();
    }

    @Override
    public double canUtilizationPct() {
      return RobotController.getCANStatus().percentBusUtilization * 100.0;
    }

    @Override
    public int canRxErrorCount() {
      return RobotController.getCANStatus().receiveErrorCount;
    }

    @Override
    public int canTxErrorCount() {
      return RobotController.getCANStatus().transmitErrorCount;
    }

    @Override
    public int canBusOffCount() {
      return RobotController.getCANStatus().busOffCount;
    }

    @Override
    public int canTxFullCount() {
      return RobotController.getCANStatus().txFullCount;
    }
  }
}
