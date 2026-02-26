package frc.robot.manufacturers;

import frc.robot.BringupUtil;
import frc.robot.devices.ctre.CtreCANCoderDevice;
import frc.robot.devices.ctre.CtreCANdleDevice;
import frc.robot.devices.ctre.CtreTalonFxDevice;
import frc.robot.diag.snapshots.DeviceSnapshot;
import java.util.ArrayList;
import java.util.List;

// Manufacturer layer for CTRE devices: owns device slots and shared logic.
public final class CtreDeviceGroup implements ManufacturerGroup {
  private final CtreTalonFxDevice[] krakens;
  private final CtreTalonFxDevice[] falcons;
  private final CtreCANCoderDevice[] cancoders;
  private final CtreCANdleDevice[] candles;
  private int nextKraken = 0;
  private int nextFalcon = 0;

  public CtreDeviceGroup() {
    int[] krakenIds = BringupUtil.filterCanIds(BringupUtil.KRAKEN_CAN_IDS);
    int[] falconIds = BringupUtil.filterCanIds(BringupUtil.FALCON_CAN_IDS);
    int[] cancoderIds = BringupUtil.filterCanIds(BringupUtil.CANCODER_CAN_IDS);
    int[] candleIds = BringupUtil.filterCanIds(BringupUtil.CANDLE_CAN_IDS);

    krakens = new CtreTalonFxDevice[krakenIds.length];
    for (int i = 0; i < krakenIds.length; i++) {
      krakens[i] = new CtreTalonFxDevice(
          krakenIds[i],
          BringupUtil.getKrakenLabel(i),
          BringupUtil.getKrakenMotorModel(i),
          "KRAKEN");
    }

    falcons = new CtreTalonFxDevice[falconIds.length];
    for (int i = 0; i < falconIds.length; i++) {
      falcons[i] = new CtreTalonFxDevice(
          falconIds[i],
          BringupUtil.getFalconLabel(i),
          BringupUtil.getFalconMotorModel(i),
          "FALCON");
    }

    cancoders = new CtreCANCoderDevice[cancoderIds.length];
    for (int i = 0; i < cancoderIds.length; i++) {
      cancoders[i] = new CtreCANCoderDevice(cancoderIds[i], BringupUtil.getCANCoderLabel(i));
    }

    candles = new CtreCANdleDevice[candleIds.length];
    for (int i = 0; i < candleIds.length; i++) {
      candles[i] = new CtreCANdleDevice(candleIds[i], BringupUtil.getCandleLabel(i));
    }
  }

  public int addNextKraken() {
    if (nextKraken < krakens.length && !krakens[nextKraken].isCreated()) {
      int index = nextKraken;
      krakens[nextKraken].ensureCreated();
      nextKraken++;
      return index;
    }
    return -1;
  }

  public int addNextFalcon() {
    if (nextFalcon < falcons.length && !falcons[nextFalcon].isCreated()) {
      int index = nextFalcon;
      falcons[nextFalcon].ensureCreated();
      nextFalcon++;
      return index;
    }
    return -1;
  }

  @Override
  public void addAll() {
    for (CtreTalonFxDevice kraken : krakens) {
      kraken.ensureCreated();
    }
    for (CtreTalonFxDevice falcon : falcons) {
      falcon.ensureCreated();
    }
    for (CtreCANCoderDevice cancoder : cancoders) {
      cancoder.ensureCreated();
    }
    for (CtreCANdleDevice candle : candles) {
      candle.ensureCreated();
    }
    nextKraken = krakens.length;
    nextFalcon = falcons.length;
  }

  @Override
  public void setDuty(double duty) {
    for (CtreTalonFxDevice kraken : krakens) {
      kraken.setDuty(duty);
    }
    for (CtreTalonFxDevice falcon : falcons) {
      falcon.setDuty(duty);
    }
  }

  @Override
  public void stopAll() {
    for (CtreTalonFxDevice kraken : krakens) {
      kraken.stop();
    }
    for (CtreTalonFxDevice falcon : falcons) {
      falcon.stop();
    }
  }

  @Override
  public void clearFaults() {
    for (CtreTalonFxDevice kraken : krakens) {
      kraken.clearFaults();
    }
    for (CtreTalonFxDevice falcon : falcons) {
      falcon.clearFaults();
    }
    for (CtreCANCoderDevice cancoder : cancoders) {
      cancoder.clearFaults();
    }
    for (CtreCANdleDevice candle : candles) {
      candle.clearFaults();
    }
  }

  @Override
  public void closeAll() {
    for (CtreTalonFxDevice kraken : krakens) {
      kraken.close();
    }
    for (CtreTalonFxDevice falcon : falcons) {
      falcon.close();
    }
    for (CtreCANCoderDevice cancoder : cancoders) {
      cancoder.close();
    }
    for (CtreCANdleDevice candle : candles) {
      candle.close();
    }
    nextKraken = 0;
    nextFalcon = 0;
  }

  @Override
  public List<DeviceSnapshot> captureSnapshots() {
    List<DeviceSnapshot> devices = new ArrayList<>();
    for (int i = 0; i < krakens.length; i++) {
      devices.add(snapshotKraken(i));
    }
    for (int i = 0; i < falcons.length; i++) {
      devices.add(snapshotFalcon(i));
    }
    for (int i = 0; i < cancoders.length; i++) {
      devices.add(snapshotCANCoder(i));
    }
    for (int i = 0; i < candles.length; i++) {
      devices.add(snapshotCANdle(i));
    }
    return devices;
  }

  public DeviceSnapshot snapshotKraken(int index) {
    DeviceSnapshot snap = krakens[index].snapshot();
    fillSpecForCtre(snap, krakens[index].getLabel(), krakens[index].getMotorModelOverride());
    return snap;
  }

  public DeviceSnapshot snapshotFalcon(int index) {
    DeviceSnapshot snap = falcons[index].snapshot();
    fillSpecForCtre(snap, falcons[index].getLabel(), falcons[index].getMotorModelOverride());
    return snap;
  }

  public DeviceSnapshot snapshotCANCoder(int index) {
    return cancoders[index].snapshot();
  }

  public DeviceSnapshot snapshotCANdle(int index) {
    return candles[index].snapshot();
  }

  public boolean isKrakenInstantiated(int deviceId) {
    for (CtreTalonFxDevice kraken : krakens) {
      if (kraken.getCanId() == deviceId) {
        return kraken.isCreated();
      }
    }
    return false;
  }

  public boolean isFalconInstantiated(int deviceId) {
    for (CtreTalonFxDevice falcon : falcons) {
      if (falcon.getCanId() == deviceId) {
        return falcon.isCreated();
      }
    }
    return false;
  }

  public boolean isCANCoderInstantiated(int deviceId) {
    for (CtreCANCoderDevice cancoder : cancoders) {
      if (cancoder.getCanId() == deviceId) {
        return cancoder.isCreated();
      }
    }
    return false;
  }

  public boolean isCANdleInstantiated(int deviceId) {
    for (CtreCANdleDevice candle : candles) {
      if (candle.getCanId() == deviceId) {
        return candle.isCreated();
      }
    }
    return false;
  }

  public CtreTalonFxDevice[] getKrakens() {
    return krakens;
  }

  public CtreTalonFxDevice[] getFalcons() {
    return falcons;
  }

  public CtreCANCoderDevice[] getCANCoders() {
    return cancoders;
  }

  public CtreCANdleDevice[] getCANdles() {
    return candles;
  }

  private void fillSpecForCtre(DeviceSnapshot snap, String label, String modelOverride) {
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
}
