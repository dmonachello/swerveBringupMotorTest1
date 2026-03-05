package frc.robot.diag.can;

import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.CanSuspicionAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.EncoderAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
import java.util.List;

// Best-effort inference of CAN health issues from device telemetry.
public final class CanSuspicionInference {
  private CanSuspicionInference() {}

  public static CanSuspicionAttachment infer(DeviceSnapshot snap, BusSnapshot bus) {
    if (snap == null || snap.deviceType == null || snap.deviceType.isBlank()) {
      return null;
    }
    String type = snap.deviceType;
    if ("NEO".equals(type) || "NEO 550".equals(type) || "FLEX".equals(type)) {
      return inferRev(snap, bus);
    }
    if ("KRAKEN".equals(type) || "FALCON".equals(type)) {
      return inferCtreMotor(snap, bus);
    }
    if ("CANCoder".equals(type)) {
      return inferCANCoder(snap, bus);
    }
    return null;
  }

  private static CanSuspicionAttachment inferRev(DeviceSnapshot snap, BusSnapshot bus) {
    CanSuspicionAttachment out = baseAttachment();
    setExpected(out, "OK", "No CAN errors expected during normal operation.");
    if (!snap.present) {
      setLikely(out, "NO_DEVICE", "Device not added or no power.", "HIGH");
      return out;
    }
    RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
    if (rev != null && hasAnyFlags(rev.faultFlags, rev.stickyFaultFlags, rev.warningFlags,
        rev.stickyWarningFlags, rev.faultsRaw, rev.stickyFaultsRaw, rev.warningsRaw, rev.stickyWarningsRaw)) {
      setLikely(out, "DEVICE_FAULT", "Device reports faults/warnings.", "HIGH");
      return out;
    }
    if (rev != null && hasNonOk(rev.lastError)) {
      setLikely(out, "CAN_TIMEOUT", "API lastError indicates comms/config issue.", "MEDIUM");
      return out;
    }
    if (hasBusIssues(bus)) {
      setLikely(out, "BUS_HEALTH", "Global CAN controller errors detected.", "LOW");
      return out;
    }
    setLikely(out, "OK", "No CAN issues detected.", "MEDIUM");
    return out;
  }

  private static CanSuspicionAttachment inferCtreMotor(DeviceSnapshot snap, BusSnapshot bus) {
    CanSuspicionAttachment out = baseAttachment();
    setExpected(out, "OK", "No CAN errors expected during normal operation.");
    if (!snap.present) {
      setLikely(out, "NO_DEVICE", "Device not added or no power.", "HIGH");
      return out;
    }
    CtreMotorAttachment ctre = snap.getAttachment(CtreMotorAttachment.class);
    if (ctre != null && hasAnyRaw(ctre.faultsRaw, ctre.stickyFaultsRaw)) {
      setLikely(out, "DEVICE_FAULT", "Device reports faults.", "HIGH");
      return out;
    }
    if (hasBusIssues(bus)) {
      setLikely(out, "BUS_HEALTH", "Global CAN controller errors detected.", "LOW");
      return out;
    }
    setLikely(out, "OK", "No CAN issues detected.", "MEDIUM");
    return out;
  }

  private static CanSuspicionAttachment inferCANCoder(DeviceSnapshot snap, BusSnapshot bus) {
    CanSuspicionAttachment out = baseAttachment();
    setExpected(out, "OK", "No CAN errors expected during normal operation.");
    if (!snap.present) {
      setLikely(out, "NO_DEVICE", "Device not added or no power.", "HIGH");
      return out;
    }
    EncoderAttachment encoder = snap.getAttachment(EncoderAttachment.class);
    if (encoder != null && hasNonOk(encoder.lastError)) {
      setLikely(out, "CAN_OR_MAGNET", "Encoder lastError indicates CAN/magnet issue.", "MEDIUM");
      return out;
    }
    if (hasBusIssues(bus)) {
      setLikely(out, "BUS_HEALTH", "Global CAN controller errors detected.", "LOW");
      return out;
    }
    setLikely(out, "OK", "No CAN issues detected.", "MEDIUM");
    return out;
  }

  private static CanSuspicionAttachment baseAttachment() {
    CanSuspicionAttachment out = new CanSuspicionAttachment();
    out.note = "Best-effort inference from telemetry; not a direct CAN bus read.";
    return out;
  }

  private static void setExpected(CanSuspicionAttachment out, String state, String meaning) {
    out.expectedState = safe(state);
    out.expectedMeaning = safe(meaning);
  }

  private static void setLikely(CanSuspicionAttachment out, String state, String meaning, String confidence) {
    out.likelyState = safe(state);
    out.likelyMeaning = safe(meaning);
    out.confidence = safe(confidence);
  }

  private static boolean hasAnyRaw(int... values) {
    if (values == null) {
      return false;
    }
    for (int value : values) {
      if (value != 0) {
        return true;
      }
    }
    return false;
  }

  @SafeVarargs
  private static boolean hasAnyFlags(List<String>... flags) {
    if (flags == null) {
      return false;
    }
    for (List<String> list : flags) {
      if (list != null && !list.isEmpty()) {
        return true;
      }
    }
    return false;
  }

  private static boolean hasAnyFlags(
      List<String> f1,
      List<String> f2,
      List<String> f3,
      List<String> f4,
      int raw1,
      int raw2,
      int raw3,
      int raw4) {
    return hasAnyFlags(f1, f2, f3, f4) || hasAnyRaw(raw1, raw2, raw3, raw4);
  }

  private static boolean hasNonOk(String value) {
    if (value == null || value.isBlank()) {
      return false;
    }
    return !"OK".equalsIgnoreCase(value) && !"kOk".equalsIgnoreCase(value);
  }

  private static boolean hasBusIssues(BusSnapshot bus) {
    if (bus == null || !bus.valid) {
      return false;
    }
    return bus.busOff > 0 || bus.busOffDelta > 0
        || bus.txFull > 0 || bus.txFullDelta > 0
        || bus.rxDelta > 0 || bus.txDelta > 0;
  }

  private static String safe(String value) {
    return value == null ? "" : value;
  }
}
