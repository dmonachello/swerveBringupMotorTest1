package frc.robot.manufacturers;

import frc.robot.BringupUtil;
import frc.robot.devices.rev.RevFlexVortexDevice;
import frc.robot.devices.rev.RevSparkMaxNeoDevice;
import frc.robot.devices.rev.RevSparkMaxNeo550Device;
import frc.robot.diag.snapshots.DeviceSnapshot;
import java.util.ArrayList;
import java.util.List;

// Manufacturer layer for REV devices: owns device slots and shared logic.
public final class RevDeviceGroup implements ManufacturerGroup {
  private final RevSparkMaxNeoDevice[] neos;
  private final RevSparkMaxNeo550Device[] neo550s;
  private final RevFlexVortexDevice[] flexes;
  private final double[] neoLowCurrentStartSec;
  private final double[] neo550LowCurrentStartSec;
  private final double[] flexLowCurrentStartSec;
  private int nextNeo = 0;
  private int nextNeo550 = 0;
  private int nextFlex = 0;

  public RevDeviceGroup() {
    int[] neoIds = BringupUtil.filterCanIds(BringupUtil.NEO_CAN_IDS);
    int[] neo550Ids = BringupUtil.filterCanIds(BringupUtil.NEO550_CAN_IDS);
    int[] flexIds = BringupUtil.filterCanIds(BringupUtil.FLEX_CAN_IDS);

    neos = new RevSparkMaxNeoDevice[neoIds.length];
    for (int i = 0; i < neoIds.length; i++) {
      neos[i] = new RevSparkMaxNeoDevice(
          neoIds[i],
          BringupUtil.getNeoLabel(i),
          BringupUtil.getNeoMotorModel(i));
    }

    neo550s = new RevSparkMaxNeo550Device[neo550Ids.length];
    for (int i = 0; i < neo550Ids.length; i++) {
      neo550s[i] = new RevSparkMaxNeo550Device(
          neo550Ids[i],
          BringupUtil.getNeo550Label(i),
          BringupUtil.getNeo550MotorModel(i));
    }

    flexes = new RevFlexVortexDevice[flexIds.length];
    for (int i = 0; i < flexIds.length; i++) {
      flexes[i] = new RevFlexVortexDevice(
          flexIds[i],
          BringupUtil.getFlexLabel(i),
          BringupUtil.getFlexMotorModel(i));
    }

    neoLowCurrentStartSec = new double[neoIds.length];
    neo550LowCurrentStartSec = new double[neo550Ids.length];
    flexLowCurrentStartSec = new double[flexIds.length];
    initLowCurrentTimers();
  }

  public void initLowCurrentTimers() {
    for (int i = 0; i < neoLowCurrentStartSec.length; i++) {
      neoLowCurrentStartSec[i] = -1.0;
    }
    for (int i = 0; i < neo550LowCurrentStartSec.length; i++) {
      neo550LowCurrentStartSec[i] = -1.0;
    }
    for (int i = 0; i < flexLowCurrentStartSec.length; i++) {
      flexLowCurrentStartSec[i] = -1.0;
    }
  }

  public int addNextNeo() {
    if (nextNeo < neos.length && !neos[nextNeo].isCreated()) {
      int index = nextNeo;
      neos[nextNeo].ensureCreated();
      nextNeo++;
      return index;
    }
    return -1;
  }

  public int addNextNeo550() {
    if (nextNeo550 < neo550s.length && !neo550s[nextNeo550].isCreated()) {
      int index = nextNeo550;
      neo550s[nextNeo550].ensureCreated();
      nextNeo550++;
      return index;
    }
    return -1;
  }

  public int addNextFlex() {
    if (nextFlex < flexes.length && !flexes[nextFlex].isCreated()) {
      int index = nextFlex;
      flexes[nextFlex].ensureCreated();
      nextFlex++;
      return index;
    }
    return -1;
  }

  @Override
  public void addAll() {
    for (RevSparkMaxNeoDevice neo : neos) {
      neo.ensureCreated();
    }
    for (RevSparkMaxNeo550Device neo550 : neo550s) {
      neo550.ensureCreated();
    }
    for (RevFlexVortexDevice flex : flexes) {
      flex.ensureCreated();
    }
    nextNeo = neos.length;
    nextNeo550 = neo550s.length;
    nextFlex = flexes.length;
  }

  @Override
  public void setDuty(double duty) {
    for (RevSparkMaxNeoDevice neo : neos) {
      neo.setDuty(duty);
    }
    for (RevSparkMaxNeo550Device neo550 : neo550s) {
      neo550.setDuty(duty);
    }
    for (RevFlexVortexDevice flex : flexes) {
      flex.setDuty(duty);
    }
  }

  @Override
  public void stopAll() {
    for (RevSparkMaxNeoDevice neo : neos) {
      neo.stop();
    }
    for (RevSparkMaxNeo550Device neo550 : neo550s) {
      neo550.stop();
    }
    for (RevFlexVortexDevice flex : flexes) {
      flex.stop();
    }
  }

  @Override
  public void clearFaults() {
    for (RevSparkMaxNeoDevice neo : neos) {
      neo.clearFaults();
    }
    for (RevSparkMaxNeo550Device neo550 : neo550s) {
      neo550.clearFaults();
    }
    for (RevFlexVortexDevice flex : flexes) {
      flex.clearFaults();
    }
  }

  @Override
  public void closeAll() {
    for (RevSparkMaxNeoDevice neo : neos) {
      neo.close();
    }
    for (RevSparkMaxNeo550Device neo550 : neo550s) {
      neo550.close();
    }
    for (RevFlexVortexDevice flex : flexes) {
      flex.close();
    }
    nextNeo = 0;
    nextNeo550 = 0;
    nextFlex = 0;
  }

  public List<DeviceSnapshot> captureSnapshots(double nowSec) {
    List<DeviceSnapshot> devices = new ArrayList<>();
    for (int i = 0; i < neos.length; i++) {
      devices.add(snapshotNeo(i, nowSec));
    }
    for (int i = 0; i < neo550s.length; i++) {
      devices.add(snapshotNeo550(i, nowSec));
    }
    for (int i = 0; i < flexes.length; i++) {
      devices.add(snapshotFlex(i, nowSec));
    }
    return devices;
  }

  @Override
  public List<DeviceSnapshot> captureSnapshots() {
    return captureSnapshots(edu.wpi.first.wpilibj.Timer.getFPGATimestamp());
  }

  public DeviceSnapshot snapshotNeo(int index, double nowSec) {
    DeviceSnapshot snap = neos[index].snapshot();
    fillSpecForRev(snap, neos[index].getLabel(), neos[index].getMotorModelOverride());
    if (snap.present) {
      snap.healthNote = buildRevHealthNote(snap.lastError, safeDouble(snap.busV));
      snap.lowCurrentNote = buildLowCurrentNote(
          neoLowCurrentStartSec,
          index,
          nowSec,
          safeDouble(snap.appliedV),
          safeDouble(snap.motorCurrentA));
    }
    return snap;
  }

  public DeviceSnapshot snapshotNeo550(int index, double nowSec) {
    DeviceSnapshot snap = neo550s[index].snapshot();
    fillSpecForRev(snap, neo550s[index].getLabel(), neo550s[index].getMotorModelOverride());
    if (snap.present) {
      snap.healthNote = buildRevHealthNote(snap.lastError, safeDouble(snap.busV));
      snap.lowCurrentNote = buildLowCurrentNote(
          neo550LowCurrentStartSec,
          index,
          nowSec,
          safeDouble(snap.appliedV),
          safeDouble(snap.motorCurrentA));
    }
    return snap;
  }

  public DeviceSnapshot snapshotFlex(int index, double nowSec) {
    DeviceSnapshot snap = flexes[index].snapshot();
    fillSpecForRev(snap, flexes[index].getLabel(), flexes[index].getMotorModelOverride());
    if (snap.present) {
      snap.healthNote = buildRevHealthNote(snap.lastError, safeDouble(snap.busV));
      snap.lowCurrentNote = buildLowCurrentNote(
          flexLowCurrentStartSec,
          index,
          nowSec,
          safeDouble(snap.appliedV),
          safeDouble(snap.motorCurrentA));
    }
    return snap;
  }

  public boolean isNeoInstantiated(int deviceId) {
    for (RevSparkMaxNeoDevice neo : neos) {
      if (neo.getCanId() == deviceId) {
        return neo.isCreated();
      }
    }
    return false;
  }

  public boolean isNeo550Instantiated(int deviceId) {
    for (RevSparkMaxNeo550Device neo : neo550s) {
      if (neo.getCanId() == deviceId) {
        return neo.isCreated();
      }
    }
    return false;
  }

  public boolean isFlexInstantiated(int deviceId) {
    for (RevFlexVortexDevice flex : flexes) {
      if (flex.getCanId() == deviceId) {
        return flex.isCreated();
      }
    }
    return false;
  }

  public RevSparkMaxNeoDevice[] getNeos() {
    return neos;
  }

  public RevSparkMaxNeo550Device[] getNeo550s() {
    return neo550s;
  }

  public RevFlexVortexDevice[] getFlexes() {
    return flexes;
  }

  private void fillSpecForRev(DeviceSnapshot snap, String label, String modelOverride) {
    snap.label = label;
    BringupUtil.MotorSpec spec = BringupUtil.getMotorSpecForDevice(label, modelOverride);
    if (spec == null) {
      return;
    }
    snap.model = spec.model;
    snap.specNominalV = spec.nominalVoltage;
    snap.specFreeA = spec.freeCurrentA;
    snap.specStallA = spec.stallCurrentA;
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

  private double safeDouble(Double value) {
    return value == null ? 0.0 : value;
  }
}

