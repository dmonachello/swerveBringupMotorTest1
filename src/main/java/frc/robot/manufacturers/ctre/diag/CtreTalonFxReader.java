package frc.robot.manufacturers.ctre.diag;

import com.ctre.phoenix6.BaseStatusSignal;
import com.ctre.phoenix6.hardware.TalonFX;
import edu.wpi.first.units.Units;
import frc.robot.diag.snapshots.DeviceSnapshot;

// Reader for CTRE TalonFX-based devices (Kraken/Falcon).
public final class CtreTalonFxReader {
  private CtreTalonFxReader() {}

  public static DeviceSnapshot read(TalonFX device, String deviceType, int canId) {
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
    BaseStatusSignal.refreshAll(
        faultSignal,
        stickySignal,
        supplyVoltage,
        dutyCycle,
        supplyCurrent,
        deviceTemp,
        motorVoltage);

    ctre.faultsRaw = faultSignal.getValue();
    ctre.stickyFaultsRaw = stickySignal.getValue();
    ctre.faultStatus = String.valueOf(faultSignal.getStatus());
    ctre.stickyStatus = String.valueOf(stickySignal.getStatus());

    ctre.busV = supplyVoltage.getValue().in(Units.Volts);
    ctre.appliedDuty = dutyCycle.getValue();
    ctre.motorCurrentA = supplyCurrent.getValue().in(Units.Amps);
    ctre.tempC = deviceTemp.getValue().in(Units.Celsius);
    ctre.motorV = motorVoltage.getValue().in(Units.Volts);
    ctre.appliedV = ctre.motorV;

    CtreReaderUtil.collectFaultFlags(device, ctre.faultFlags);
    CtreReaderUtil.collectStickyFaultFlags(device, ctre.stickyFaultFlags);

    snap.addAttachment(ctre);
    return snap;
  }
}
