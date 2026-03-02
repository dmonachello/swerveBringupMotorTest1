package frc.robot.manufacturers.rev.diag;

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

    RevMotorAttachment rev = new RevMotorAttachment();

    var faults = device.getFaults();
    var stickyFaults = device.getStickyFaults();
    var warnings = device.getWarnings();
    var stickyWarnings = device.getStickyWarnings();
    REVLibError lastError = device.getLastError();

    rev.faultsRaw = faults.rawBits;
    rev.stickyFaultsRaw = stickyFaults.rawBits;
    rev.warningsRaw = warnings.rawBits;
    rev.stickyWarningsRaw = stickyWarnings.rawBits;
    rev.lastError = String.valueOf(lastError);
    rev.reset = warnings.hasReset || stickyWarnings.hasReset;

    RevReaderUtil.collectFaultFlags(faults, rev.faultFlags);
    RevReaderUtil.collectFaultFlags(stickyFaults, rev.stickyFaultFlags);
    RevReaderUtil.collectWarningFlags(warnings, rev.warningFlags);
    RevReaderUtil.collectWarningFlags(stickyWarnings, rev.stickyWarningFlags);

    double busV = device.getBusVoltage();
    double appliedDuty = device.getAppliedOutput();
    rev.busV = busV;
    rev.appliedDuty = appliedDuty;
    rev.appliedV = busV * appliedDuty;
    rev.motorCurrentA = device.getOutputCurrent();
    rev.tempC = device.getMotorTemperature();
    rev.cmdDuty = device.get();
    rev.follower = device.isFollower();
    snap.addAttachment(rev);
    return snap;
  }
}
