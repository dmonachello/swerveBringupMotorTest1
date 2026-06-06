package frc.robot.manufacturers.ctre.diag;

import com.ctre.phoenix6.BaseStatusSignal;
import com.ctre.phoenix6.hardware.TalonFX;
import edu.wpi.first.units.Units;
import frc.robot.diag.snapshots.DeviceSnapshot;

/**
 * NAME
 * CtreTalonFxReader
 *
 * SYNOPSIS
 * Reader for CTRE TalonFX-based devices (Kraken/Falcon).
 *
 * DESCRIPTION
 * Samples Phoenix status signals and packages telemetry into snapshots.
 */
public final class CtreTalonFxReader {
  private static final double RPM_PER_RPS = 60.0;

  private CtreTalonFxReader() {}

  /**
   * NAME
   * read
   *
   * SYNOPSIS
   * Capture a snapshot from a TalonFX device.
   *
   * PARAMETERS
   * device - TalonFX instance to read.
   * deviceType - device type token (e.g., KRAKEN/FALCON).
   * canId - CAN ID of the device.
   *
   * RETURNS
   * A populated device snapshot with CTRE motor telemetry.
   *
   * SIDE EFFECTS
   * Refreshes Phoenix status signals.
   */
  public static DeviceSnapshot read(
      TalonFX device,
      String deviceType,
      int canId,
      Double commandedDuty) {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = "CTRE";
    snap.deviceType = deviceType;
    snap.canId = canId;
    snap.present = true;

    CtreMotorAttachment ctre = new CtreMotorAttachment();

    var faultSignal = device.getFaultField();
    var stickySignal = device.getStickyFaultField();
    var supplyVoltage = device.getSupplyVoltage();
    var dutyCycle = device.getDutyCycle();
    var supplyCurrent = device.getSupplyCurrent();
    var deviceTemp = device.getDeviceTemp();
    var motorVoltage = device.getMotorVoltage();
    var rotorVelocity = device.getRotorVelocity();
    var rotorPosition = device.getPosition();
    BaseStatusSignal.refreshAll(
        faultSignal,
        stickySignal,
        supplyVoltage,
        dutyCycle,
        supplyCurrent,
        deviceTemp,
        motorVoltage,
        rotorVelocity,
        rotorPosition);

    ctre.faultsRaw = faultSignal.getValue();
    ctre.stickyFaultsRaw = stickySignal.getValue();
    ctre.faultStatus = String.valueOf(faultSignal.getStatus());
    ctre.stickyStatus = String.valueOf(stickySignal.getStatus());

    ctre.busV = supplyVoltage.getValue().in(Units.Volts);
    ctre.cmdDuty = commandedDuty;
    ctre.appliedDuty = dutyCycle.getValue();
    ctre.motorCurrentA = supplyCurrent.getValue().in(Units.Amps);
    ctre.tempC = deviceTemp.getValue().in(Units.Celsius);
    ctre.motorV = motorVoltage.getValue().in(Units.Volts);
    ctre.appliedV = ctre.motorV;
    ctre.velRpm = rotorVelocity.getValue().in(Units.RotationsPerSecond) * RPM_PER_RPS;
    ctre.positionRot = rotorPosition.getValue().in(Units.Rotations);

    CtreReaderUtil.collectFaultFlags(device, ctre.faultFlags);
    CtreReaderUtil.collectStickyFaultFlags(device, ctre.stickyFaultFlags);

    snap.addAttachment(ctre);
    return snap;
  }
}
