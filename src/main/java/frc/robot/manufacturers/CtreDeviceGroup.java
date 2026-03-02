package frc.robot.manufacturers;

import frc.robot.BringupHealthFormat;
import frc.robot.BringupUtil;
import frc.robot.BringupUtil.DeviceConfig;
import frc.robot.devices.DeviceUnit;
import frc.robot.devices.ctre.CtreCANCoderDevice;
import frc.robot.devices.ctre.CtreCANdleDevice;
import frc.robot.devices.ctre.CtreTalonFxDevice;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.diag.snapshots.MotorSpecAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.registry.RegistrationHeader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

// Manufacturer layer for CTRE devices: owns device slots and shared logic.
public final class CtreDeviceGroup implements ManufacturerGroup {
  public static final RegistrationHeader HEADER = new RegistrationHeader(
      "CTRE",
      "CTRE",
      "Manufacturer",
      "Phoenix 6",
      "Team",
      "2026-03-02",
      "Vendor-specific diagnostics and motor wrappers.");

  private static final DeviceRegistration KRAKEN_REGISTRATION = new DeviceRegistration(
      CtreTalonFxDevice.HEADER,
      "CTRE",
      "KRAKEN",
      "KRAKEN",
      DeviceRole.MOTOR,
      true,
      config -> new CtreTalonFxDevice(
          config.getId(),
          config.getLabel(),
          config.getMotor(),
          "KRAKEN",
          config.getLimits()));

  private static final DeviceRegistration FALCON_REGISTRATION = new DeviceRegistration(
      CtreTalonFxDevice.HEADER,
      "CTRE",
      "FALCON",
      "FALCON",
      DeviceRole.MOTOR,
      true,
      config -> new CtreTalonFxDevice(
          config.getId(),
          config.getLabel(),
          config.getMotor(),
          "FALCON",
          config.getLimits()));

  private static final DeviceRegistration CANCODER_REGISTRATION = new DeviceRegistration(
      CtreCANCoderDevice.HEADER,
      "CTRE",
      "CANCoder",
      "CANCoder",
      DeviceRole.ENCODER,
      false,
      config -> new CtreCANCoderDevice(
          config.getId(),
          config.getLabel(),
          config.getLimits()));

  private static final DeviceRegistration CANDLE_REGISTRATION = new DeviceRegistration(
      CtreCANdleDevice.HEADER,
      "CTRE",
      "CANdle",
      "CANdle",
      DeviceRole.MISC,
      false,
      config -> new CtreCANdleDevice(
          config.getId(),
          config.getLabel(),
          config.getLimits()));

  private final List<DeviceTypeBucket> buckets = new ArrayList<>();
  private final List<DeviceTypeBucket> motorBuckets = new ArrayList<>();

  public CtreDeviceGroup() {
    register(KRAKEN_REGISTRATION, false);
    register(FALCON_REGISTRATION, false);
    register(CANCODER_REGISTRATION, false);
    register(CANDLE_REGISTRATION, false);
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
    // No CTRE low-current tracking yet.
  }

  @Override
  public List<DeviceUnit> getTestDevices() {
    List<DeviceUnit> devices = new ArrayList<>();
    for (DeviceTypeBucket bucket : buckets) {
      for (DeviceUnit device : bucket.getDevices()) {
        if (device.hasTest()) {
          devices.add(device);
        }
      }
    }
    return devices;
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
      if (bucket.getRegistration().role() == DeviceRole.ENCODER) {
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
        if (bucket.getRegistration().role() == DeviceRole.MOTOR) {
          CtreMotorAttachment ctre = snap.getAttachment(CtreMotorAttachment.class);
          MotorSpecAttachment spec = snap.getAttachment(MotorSpecAttachment.class);
          LimitsAttachment limits = snap.getAttachment(LimitsAttachment.class);
          sb.append(bucket.getRegistration().displayName())
              .append(" index ").append(i)
              .append(" CAN ").append(device.getCanId())
              .append(BringupHealthFormat.formatCtreFaultSummary(ctre))
              .append(BringupHealthFormat.formatMotorSpecNote(spec, ctre != null ? ctre.motorCurrentA : null))
              .append(BringupHealthFormat.formatLimitSummary(limits))
              .append(" busV=").append(String.format("%.2f", BringupHealthFormat.safeDouble(ctre != null ? ctre.busV : null))).append("V")
              .append(" appliedDuty=").append(String.format("%.2f", BringupHealthFormat.safeDouble(ctre != null ? ctre.appliedDuty : null))).append("dc")
              .append(" appliedV=").append(String.format("%.2f", BringupHealthFormat.safeDouble(ctre != null ? ctre.appliedV : null))).append("V")
              .append(" motorCurrentA=").append(String.format("%.4f", BringupHealthFormat.safeDouble(ctre != null ? ctre.motorCurrentA : null))).append("A")
              .append(" tempC=").append(String.format("%.1f", BringupHealthFormat.safeDouble(ctre != null ? ctre.tempC : null))).append("C")
              .append(ctre == null || (ctre.faultStatus.isBlank() && ctre.stickyStatus.isBlank())
                  ? ""
                  : " status=" + ctre.faultStatus + "/" + ctre.stickyStatus)
              .append('\n');
        } else {
          LimitsAttachment limits = snap.getAttachment(LimitsAttachment.class);
          sb.append(bucket.getRegistration().displayName())
              .append(" index ").append(i)
              .append(" CAN ").append(device.getCanId())
              .append(" present=YES")
              .append(BringupHealthFormat.formatLimitSummary(limits))
              .append('\n');
        }
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
      fillSpecForCtre(snap, device.getLabel(), device.getMotorModelOverride());
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

  private void fillSpecForCtre(DeviceSnapshot snap, String label, String modelOverride) {
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
}
