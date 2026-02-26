package frc.robot.diag.readers;

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

    snap.faultsRaw = faultSignal.getValue();
    snap.stickyFaultsRaw = stickySignal.getValue();
    snap.faultStatus = String.valueOf(faultSignal.getStatus());
    snap.stickyStatus = String.valueOf(stickySignal.getStatus());

    snap.busV = supplyVoltage.getValue().in(Units.Volts);
    snap.appliedDuty = dutyCycle.getValue();
    snap.motorCurrentA = supplyCurrent.getValue().in(Units.Amps);
    snap.tempC = deviceTemp.getValue().in(Units.Celsius);
    snap.motorV = motorVoltage.getValue().in(Units.Volts);
    snap.appliedV = snap.motorV;

    CtreReaderUtil.collectFaultFlags(device, snap.faultFlags);
    CtreReaderUtil.collectStickyFaultFlags(device, snap.stickyFaultFlags);

    return snap;
  }
}
