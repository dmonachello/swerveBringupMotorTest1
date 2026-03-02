package frc.robot.manufacturers;

import frc.robot.BringupHealthFormat;
import frc.robot.BringupUtil;
import frc.robot.BringupUtil.DeviceConfig;
import frc.robot.devices.DeviceUnit;
import frc.robot.devices.rev.RevFlexVortexDevice;
import frc.robot.devices.rev.RevSparkMaxNeoDevice;
import frc.robot.devices.rev.RevSparkMaxNeo550Device;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.diag.snapshots.MotorSpecAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
import frc.robot.registry.RegistrationHeader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

// Manufacturer layer for REV devices: owns device slots and shared logic.
public final class RevDeviceGroup implements ManufacturerGroup {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "REV",
      "REV",
      "Manufacturer",
      "REVLib",
      "Team",
      "2026-03-02",
      "Vendor-specific diagnostics and motor wrappers.");

  private static final DeviceRegistration NEO_REGISTRATION = new DeviceRegistration(
      RevSparkMaxNeoDevice.HEADER,
      "REV",
      "NEO",
      "NEO",
      DeviceRole.MOTOR,
      true,
      config -> new RevSparkMaxNeoDevice(
          config.getId(),
          config.getLabel(),
          config.getMotor(),
          config.getLimits()));

  private static final DeviceRegistration NEO550_REGISTRATION = new DeviceRegistration(
      RevSparkMaxNeo550Device.HEADER,
      "REV",
      "NEO 550",
      "NEO 550",
      DeviceRole.MOTOR,
      true,
      config -> new RevSparkMaxNeo550Device(
          config.getId(),
          config.getLabel(),
          config.getMotor(),
          config.getLimits()));

  private static final DeviceRegistration FLEX_REGISTRATION = new DeviceRegistration(
      RevFlexVortexDevice.HEADER,
      "REV",
      "FLEX",
      "FLEX",
      DeviceRole.MOTOR,
      true,
      config -> new RevFlexVortexDevice(
          config.getId(),
          config.getLabel(),
          config.getMotor(),
          config.getLimits()));

  private final List<DeviceTypeBucket> buckets = new ArrayList<>();
  private final List<DeviceTypeBucket> motorBuckets = new ArrayList<>();

  public RevDeviceGroup() {
    register(NEO_REGISTRATION, true);
    register(NEO550_REGISTRATION, true);
    register(FLEX_REGISTRATION, true);
  }

  @Override
  public RegistrationHeader getHeader() {
    return HEADER;
  }

  @Override
  public List<DeviceTypeBucket> getDeviceBuckets() {
    return Collections.unmodifiableList(buckets);
  }

  @Override
  public DeviceAddResult addNextMotor() {
    for (DeviceTypeBucket bucket : motorBuckets) {
      DeviceAddResult result = bucket.addNext();
      if (result != null) {
        return result;
      }
    }
    return null;
  }

  @Override
  public void resetLowCurrentTimers() {
    for (DeviceTypeBucket bucket : motorBuckets) {
      bucket.resetLowCurrentTimers();
    }
  }

  @Override
  public List<DeviceUnit> getTestDevices() {
    return new ArrayList<>();
  }

  @Override
  public void addAll() {
    for (DeviceTypeBucket bucket : buckets) {
      bucket.addAll();
    }
  }

  @Override
  public void setDuty(double duty) {
    for (DeviceTypeBucket bucket : motorBuckets) {
      for (DeviceUnit device : bucket.getDevices()) {
        device.setDuty(duty);
      }
    }
  }

  @Override
  public void stopAll() {
    for (DeviceTypeBucket bucket : motorBuckets) {
      for (DeviceUnit device : bucket.getDevices()) {
        device.stop();
      }
    }
  }

  @Override
  public void clearFaults() {
    for (DeviceTypeBucket bucket : buckets) {
      for (DeviceUnit device : bucket.getDevices()) {
        device.clearFaults();
      }
    }
  }

  @Override
  public void closeAll() {
    for (DeviceTypeBucket bucket : buckets) {
      for (DeviceUnit device : bucket.getDevices()) {
        device.close();
      }
      bucket.resetAddPointer();
    }
  }

  @Override
  public List<DeviceSnapshot> captureSnapshots(double nowSec) {
    List<DeviceSnapshot> devices = new ArrayList<>();
    for (DeviceTypeBucket bucket : buckets) {
      List<DeviceUnit> bucketDevices = bucket.getDevices();
      for (int i = 0; i < bucketDevices.size(); i++) {
        devices.add(snapshotDevice(bucket, i, nowSec));
      }
    }
    return devices;
  }

  public void appendState(StringBuilder sb) {
    for (DeviceTypeBucket bucket : buckets) {
      List<DeviceUnit> bucketDevices = bucket.getDevices();
      if (bucketDevices.isEmpty()) {
        continue;
      }
      sb.append(bucket.getRegistration().displayName()).append(":\n");
      for (int i = 0; i < bucketDevices.size(); i++) {
        DeviceUnit device = bucketDevices.get(i);
        sb.append("  index ").append(i)
            .append(" CAN ").append(device.getCanId())
            .append(device.isCreated() ? " ACTIVE" : " not added")
            .append('\n');
      }
    }
  }

  public void appendHealth(StringBuilder sb, double nowSec) {
    for (DeviceTypeBucket bucket : buckets) {
      if (bucket.getRegistration().role() != DeviceRole.MOTOR) {
        continue;
      }
      List<DeviceUnit> bucketDevices = bucket.getDevices();
      for (int i = 0; i < bucketDevices.size(); i++) {
        DeviceUnit device = bucketDevices.get(i);
        DeviceSnapshot snap = snapshotDevice(bucket, i, nowSec);
        if (!snap.present) {
          sb.append(bucket.getRegistration().displayName())
              .append(" index ").append(i)
              .append(" CAN ").append(device.getCanId())
              .append(" not added\n");
          continue;
        }
        RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
        MotorSpecAttachment spec = snap.getAttachment(MotorSpecAttachment.class);
        LimitsAttachment limits = snap.getAttachment(LimitsAttachment.class);
        sb.append(bucket.getRegistration().displayName())
            .append(" index ").append(i)
            .append(" CAN ").append(device.getCanId())
            .append(BringupHealthFormat.formatRevFaultSummary(rev))
            .append(" lastErr=").append(BringupHealthFormat.safeText(rev != null ? rev.lastError : ""))
            .append(BringupHealthFormat.safeText(rev != null ? rev.healthNote : ""))
            .append(BringupHealthFormat.safeText(rev != null ? rev.lowCurrentNote : ""))
            .append(BringupHealthFormat.formatMotorSpecNote(spec, rev != null ? rev.motorCurrentA : null))
            .append(BringupHealthFormat.formatLimitSummary(limits))
            .append(" busV=").append(String.format("%.2f", BringupHealthFormat.safeDouble(rev != null ? rev.busV : null))).append("V")
            .append(" appliedDuty=").append(String.format("%.2f", BringupHealthFormat.safeDouble(rev != null ? rev.appliedDuty : null))).append("dc")
            .append(" appliedV=").append(String.format("%.2f", BringupHealthFormat.safeDouble(rev != null ? rev.appliedV : null))).append("V")
            .append(" motorCurrentA=").append(String.format("%.4f", BringupHealthFormat.safeDouble(rev != null ? rev.motorCurrentA : null))).append("A")
            .append(" tempC=").append(String.format("%.1f", BringupHealthFormat.safeDouble(rev != null ? rev.tempC : null))).append("C")
            .append(" cmdDuty=").append(String.format("%.2f", BringupHealthFormat.safeDouble(rev != null ? rev.cmdDuty : null))).append("dc")
            .append(" follower=").append(rev != null && rev.follower ? "Y" : "N")
            .append('\n');
      }
    }
  }

  private void register(DeviceRegistration registration, boolean trackLowCurrent) {
    requireRegistrationHeader(registration);
    List<DeviceConfig> configs = BringupUtil.getDeviceConfigs(
        registration.vendor(),
        registration.deviceType());
    List<DeviceUnit> devices = new ArrayList<>();
    for (DeviceConfig config : configs) {
      if (registration.requiresMotorSpec()) {
        warnIfMissingMotorSpec(config.getLabel(), config.getMotor());
      }
      devices.add(registration.factory().create(config));
    }
    DeviceTypeBucket bucket = new DeviceTypeBucket(registration, devices, trackLowCurrent);
    buckets.add(bucket);
    if (registration.role() == DeviceRole.MOTOR) {
      motorBuckets.add(bucket);
    }
  }

  private DeviceSnapshot snapshotDevice(DeviceTypeBucket bucket, int index, double nowSec) {
    DeviceUnit device = bucket.getDevices().get(index);
    DeviceSnapshot snap = device.snapshot();
    if (bucket.getRegistration().role() == DeviceRole.MOTOR) {
      fillSpecForRev(snap, device.getLabel(), device.getMotorModelOverride());
      if (snap.present) {
        RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
        if (rev != null) {
          rev.healthNote = buildRevHealthNote(rev.lastError, BringupHealthFormat.safeDouble(rev.busV));
          if (bucket.tracksLowCurrent()) {
            rev.lowCurrentNote = buildLowCurrentNote(
                bucket.getLowCurrentStartSec(),
                index,
                nowSec,
                BringupHealthFormat.safeDouble(rev.appliedV),
                BringupHealthFormat.safeDouble(rev.motorCurrentA));
          }
        }
      }
    }
    return snap;
  }

  private void requireRegistrationHeader(DeviceRegistration registration) {
    if (registration == null || registration.header() == null) {
      throw new IllegalStateException("Device registration missing required header.");
    }
  }

  private void warnIfMissingMotorSpec(String label, String modelOverride) {
    BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
    if (spec == null) {
      System.out.println("Warning: missing motor spec for " + label);
    }
  }

  private void fillSpecForRev(DeviceSnapshot snap, String label, String modelOverride) {
    snap.label = label;
    BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
    if (spec == null) {
      return;
    }
    MotorSpecAttachment motorSpec = new MotorSpecAttachment();
    motorSpec.model = spec.model;
    motorSpec.nominalV = spec.nominalVoltage;
    motorSpec.freeCurrentA = spec.freeCurrentA;
    motorSpec.stallCurrentA = spec.stallCurrentA;
    snap.addAttachment(motorSpec);
  }

  private String buildRevHealthNote(String lastError, double busVoltage) {
    if (lastError == null || lastError.isBlank()) {
      return "";
    }
    if (!"kOk".equals(lastError) && busVoltage < 7.0) {
      return " lowBusV";
    }
    if (!"kOk".equals(lastError)) {
      return " lastErr=" + lastError;
    }
    return "";
  }

  private String buildLowCurrentNote(
      double[] lowCurrentStart,
      int index,
      double nowSec,
      double appliedVolts,
      double currentA) {
    final double lowCurrentAppliedVMin = 1.0;
    final double lowCurrentAMax = 0.05;
    final double lowCurrentMinSec = 1.0;
    boolean lowCurrentNow =
        Math.abs(appliedVolts) >= lowCurrentAppliedVMin && Math.abs(currentA) <= lowCurrentAMax;
    if (!lowCurrentNow) {
      lowCurrentStart[index] = -1.0;
      return "";
    }
    if (lowCurrentStart[index] < 0.0) {
      lowCurrentStart[index] = nowSec;
      return "";
    }
    if (nowSec - lowCurrentStart[index] < lowCurrentMinSec) {
      return "";
    }
    return " lowCurrent";
  }

  // private double safeDouble(Double value) {
  //   return value == null ? 0.0 : value;
  // }
}
