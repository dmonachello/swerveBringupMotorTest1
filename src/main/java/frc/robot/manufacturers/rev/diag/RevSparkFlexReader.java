package frc.robot.manufacturers.rev.diag;

import com.revrobotics.REVLibError;
import com.revrobotics.spark.SparkFlex;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.SnapshotDetail;

/**
 * NAME
 * RevSparkFlexReader
 *
 * SYNOPSIS
 * Reader for REV SPARK FLEX (Vortex) devices.
 *
 * DESCRIPTION
 * Samples REV telemetry and packages it into device snapshots.
 */
public final class RevSparkFlexReader {
  private RevSparkFlexReader() {}

  /**
   * NAME
   * read
   *
   * SYNOPSIS
   * Capture a snapshot from a Spark Flex device.
   *
   * PARAMETERS
   * device - Spark Flex instance to read.
   * canId - CAN ID of the device.
   *
   * RETURNS
   * A populated device snapshot with REV motor telemetry.
   */
  public static DeviceSnapshot read(SparkFlex device, int canId) {
    return read(device, canId, SnapshotDetail.FULL);
  }

  /**
   * NAME
   * read
   *
   * SYNOPSIS
   * Capture a snapshot from a Spark Flex device at the requested detail level.
   *
   * PARAMETERS
   * device - Spark Flex instance to read.
   * canId - CAN ID of the device.
   * detail - requested snapshot detail level.
   *
   * RETURNS
   * A populated device snapshot with REV motor telemetry.
   */
  public static DeviceSnapshot read(SparkFlex device, int canId, SnapshotDetail detail) {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.vendor = "REV";
    snap.deviceType = "FLEX";
    snap.canId = canId;
    snap.present = true;

    RevMotorAttachment rev = new RevMotorAttachment();

    rev.velRpm = device.getEncoder().getVelocity();
    rev.positionRot = device.getEncoder().getPosition();

    if (detail == SnapshotDetail.FULL) {
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
      rev.follower = device.isFollower();
    }

    double busV = device.getBusVoltage();
    double appliedDuty = device.getAppliedOutput();
    rev.busV = busV;
    rev.appliedDuty = appliedDuty;
    rev.appliedV = busV * appliedDuty;
    rev.motorCurrentA = device.getOutputCurrent();
    rev.tempC = device.getMotorTemperature();
    rev.cmdDuty = device.get();
    snap.addAttachment(rev);
    return snap;
  }
}
