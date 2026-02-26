package frc.robot.diag.readers;

import com.revrobotics.REVLibError;
import com.revrobotics.spark.SparkMax;
import frc.robot.diag.snapshots.DeviceSnapshot;

// Reader for REV SPARK MAX (NEO) devices.
public final class RevSparkMaxReader {
  private RevSparkMaxReader() {}

  public static DeviceSnapshot read(SparkMax device, int canId) {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = "REV";
    snap.deviceType = "NEO";
    snap.canId = canId;
    snap.present = true;

    var faults = device.getFaults();
    var stickyFaults = device.getStickyFaults();
    var warnings = device.getWarnings();
    var stickyWarnings = device.getStickyWarnings();
    REVLibError lastError = device.getLastError();

    snap.faultsRaw = faults.rawBits;
    snap.stickyFaultsRaw = stickyFaults.rawBits;
    snap.warningsRaw = warnings.rawBits;
    snap.stickyWarningsRaw = stickyWarnings.rawBits;
    snap.lastError = String.valueOf(lastError);
    snap.reset = warnings.hasReset || stickyWarnings.hasReset;

    RevReaderUtil.collectFaultFlags(faults, snap.faultFlags);
    RevReaderUtil.collectFaultFlags(stickyFaults, snap.stickyFaultFlags);
    RevReaderUtil.collectWarningFlags(warnings, snap.warningFlags);
    RevReaderUtil.collectWarningFlags(stickyWarnings, snap.stickyWarningFlags);

    double busV = device.getBusVoltage();
    double appliedDuty = device.getAppliedOutput();
    snap.busV = busV;
    snap.appliedDuty = appliedDuty;
    snap.appliedV = busV * appliedDuty;
    snap.motorCurrentA = device.getOutputCurrent();
    snap.tempC = device.getMotorTemperature();
    snap.cmdDuty = device.get();
    snap.follower = device.isFollower();
    return snap;
  }
}
