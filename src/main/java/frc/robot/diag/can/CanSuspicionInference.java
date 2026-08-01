package frc.robot.diag.can;

import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.CanSuspicionAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.EncoderAttachment;
import frc.robot.diag.snapshots.ImuAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
import java.util.List;

/**
 * NAME
 * CanSuspicionInference
 *
 * SYNOPSIS
 * Best-effort inference of CAN health issues from device telemetry.
 *
 * DESCRIPTION
 * Infers likely CAN-related problems using device-specific diagnostics and
 * bus-level counters, without direct CAN bus reads.
 */
public final class CanSuspicionInference {
  private static final String TYPE_NEO = "NEO";
  private static final String TYPE_NEO_550 = "NEO 550";
  private static final String TYPE_FLEX = "FLEX";
  private static final String TYPE_KRAKEN = "KRAKEN";
  private static final String TYPE_FALCON = "FALCON";
  private static final String TYPE_CANCODER = "CANCoder";
  private static final String TYPE_PIGEON = "Pigeon";
  private static final String STATE_OK = "OK";
  private static final String STATE_NO_DEVICE = "NO_DEVICE";
  private static final String STATE_CAN_TIMEOUT = "CAN_TIMEOUT";
  private static final String STATE_BUS_HEALTH = "BUS_HEALTH";
  private static final String STATE_ACTIVE_FAULT = "ACTIVE_FAULT";
  private static final String STATE_STICKY_FAULT = "STICKY_FAULT";
  private static final String STATE_ACTIVE_WARNING = "ACTIVE_WARNING";
  private static final String STATE_STICKY_WARNING = "STICKY_WARNING";
  private static final String STATE_CAN_OR_MAGNET = "CAN_OR_MAGNET";
  private static final String CONFIDENCE_HIGH = "HIGH";
  private static final String CONFIDENCE_MEDIUM = "MEDIUM";
  private static final String CONFIDENCE_LOW = "LOW";
  private static final String MEANING_EXPECTED_OK =
      "No CAN errors expected during normal operation.";
  private static final String MEANING_NO_DEVICE = "Device not added or no power.";
  private static final String MEANING_ACTIVE_FAULT = "Device reports active faults.";
  private static final String MEANING_STICKY_FAULT = "Device reports sticky faults.";
  private static final String MEANING_ACTIVE_WARNING = "Device reports active warnings.";
  private static final String MEANING_STICKY_WARNING = "Device reports sticky warnings.";
  private static final String MEANING_CAN_TIMEOUT =
      "API lastError indicates comms/config issue.";
  private static final String MEANING_BUS_HEALTH =
      "Global CAN controller errors detected.";
  private static final String MEANING_CAN_OR_MAGNET =
      "Encoder lastError indicates CAN/magnet issue.";
  private static final String MEANING_OK = "No CAN issues detected.";
  private static final String NOTE_BEST_EFFORT =
      "Best-effort inference from telemetry; not a direct CAN bus read.";

  private CanSuspicionInference() {}

  /**
   * NAME
   * infer
   *
   * SYNOPSIS
   * Infer a CAN suspicion attachment for a device snapshot.
   *
   * PARAMETERS
   * snap - device snapshot containing vendor telemetry.
   * bus - bus snapshot with controller health counters.
   *
   * RETURNS
   * A suspicion attachment, or null when the device type is not recognized.
   */
  public static CanSuspicionAttachment infer(DeviceSnapshot snap, BusSnapshot bus) {
    if (snap == null || snap.deviceType == null || snap.deviceType.isBlank()) {
      return null;
    }
    String type = snap.deviceType;
    if (TYPE_NEO.equals(type) || TYPE_NEO_550.equals(type) || TYPE_FLEX.equals(type)) {
      return inferRev(snap, bus);
    }
    if (TYPE_KRAKEN.equals(type) || TYPE_FALCON.equals(type)) {
      return inferCtreMotor(snap, bus);
    }
    if (TYPE_CANCODER.equals(type)) {
      return inferCANCoder(snap, bus);
    }
    if (TYPE_PIGEON.equals(type)) {
      return inferPigeon(snap, bus);
    }
    return null;
  }

  /**
   * NAME
   * inferRev
   *
   * SYNOPSIS
   * Infer CAN suspicion state for REV motor devices.
   */
  private static CanSuspicionAttachment inferRev(DeviceSnapshot snap, BusSnapshot bus) {
    CanSuspicionAttachment out = baseAttachment();
    setExpected(out, STATE_OK, MEANING_EXPECTED_OK);
    if (!snap.present) {
      setLikely(out, STATE_NO_DEVICE, MEANING_NO_DEVICE, CONFIDENCE_HIGH);
      return out;
    }
    RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
    if (rev != null) {
      if (hasAnyFlags(rev.faultFlags) || rev.faultsRaw != 0) {
        setLikely(out, STATE_ACTIVE_FAULT, MEANING_ACTIVE_FAULT, CONFIDENCE_HIGH);
        return out;
      }
      if (hasAnyFlags(rev.warningFlags) || rev.warningsRaw != 0) {
        setLikely(out, STATE_ACTIVE_WARNING, MEANING_ACTIVE_WARNING, CONFIDENCE_HIGH);
        return out;
      }
      if (hasAnyFlags(rev.stickyFaultFlags) || rev.stickyFaultsRaw != 0) {
        setLikely(out, STATE_STICKY_FAULT, MEANING_STICKY_FAULT, CONFIDENCE_HIGH);
        return out;
      }
      if (hasAnyFlags(rev.stickyWarningFlags) || rev.stickyWarningsRaw != 0) {
        setLikely(out, STATE_STICKY_WARNING, MEANING_STICKY_WARNING, CONFIDENCE_HIGH);
        return out;
      }
    }
    if (rev != null && hasNonOk(rev.lastError)) {
      setLikely(out, STATE_CAN_TIMEOUT, MEANING_CAN_TIMEOUT, CONFIDENCE_MEDIUM);
      return out;
    }
    if (hasBusIssues(bus)) {
      setLikely(out, STATE_BUS_HEALTH, MEANING_BUS_HEALTH, CONFIDENCE_LOW);
      return out;
    }
    setLikely(out, STATE_OK, MEANING_OK, CONFIDENCE_MEDIUM);
    return out;
  }

  /**
   * NAME
   * inferCtreMotor
   *
   * SYNOPSIS
   * Infer CAN suspicion state for CTRE motor devices.
   */
  private static CanSuspicionAttachment inferCtreMotor(DeviceSnapshot snap, BusSnapshot bus) {
    CanSuspicionAttachment out = baseAttachment();
    setExpected(out, STATE_OK, MEANING_EXPECTED_OK);
    if (!snap.present) {
      setLikely(out, STATE_NO_DEVICE, MEANING_NO_DEVICE, CONFIDENCE_HIGH);
      return out;
    }
    CtreMotorAttachment ctre = snap.getAttachment(CtreMotorAttachment.class);
    if (ctre != null) {
      if (ctre.faultsRaw != 0 || hasAnyFlags(ctre.faultFlags)) {
        setLikely(out, STATE_ACTIVE_FAULT, MEANING_ACTIVE_FAULT, CONFIDENCE_HIGH);
        return out;
      }
      if (ctre.stickyFaultsRaw != 0 || hasAnyFlags(ctre.stickyFaultFlags)) {
        setLikely(out, STATE_STICKY_FAULT, MEANING_STICKY_FAULT, CONFIDENCE_HIGH);
        return out;
      }
    }
    if (hasBusIssues(bus)) {
      setLikely(out, STATE_BUS_HEALTH, MEANING_BUS_HEALTH, CONFIDENCE_LOW);
      return out;
    }
    setLikely(out, STATE_OK, MEANING_OK, CONFIDENCE_MEDIUM);
    return out;
  }

  /**
   * NAME
   * inferCANCoder
   *
   * SYNOPSIS
   * Infer CAN suspicion state for CTRE CANCoder devices.
   */
  private static CanSuspicionAttachment inferCANCoder(DeviceSnapshot snap, BusSnapshot bus) {
    CanSuspicionAttachment out = baseAttachment();
    setExpected(out, STATE_OK, MEANING_EXPECTED_OK);
    if (!snap.present) {
      setLikely(out, STATE_NO_DEVICE, MEANING_NO_DEVICE, CONFIDENCE_HIGH);
      return out;
    }
    EncoderAttachment encoder = snap.getAttachment(EncoderAttachment.class);
    if (encoder != null && hasNonOk(encoder.lastError)) {
      setLikely(out, STATE_CAN_OR_MAGNET, MEANING_CAN_OR_MAGNET, CONFIDENCE_MEDIUM);
      return out;
    }
    if (hasBusIssues(bus)) {
      setLikely(out, STATE_BUS_HEALTH, MEANING_BUS_HEALTH, CONFIDENCE_LOW);
      return out;
    }
    setLikely(out, STATE_OK, MEANING_OK, CONFIDENCE_MEDIUM);
    return out;
  }

  /**
   * NAME
   * inferPigeon
   *
   * SYNOPSIS
   * Infer CAN suspicion state for CTRE Pigeon devices.
   */
  private static CanSuspicionAttachment inferPigeon(DeviceSnapshot snap, BusSnapshot bus) {
    CanSuspicionAttachment out = baseAttachment();
    setExpected(out, STATE_OK, MEANING_EXPECTED_OK);
    if (!snap.present) {
      setLikely(out, STATE_NO_DEVICE, MEANING_NO_DEVICE, CONFIDENCE_HIGH);
      return out;
    }
    ImuAttachment imu = snap.getAttachment(ImuAttachment.class);
    if (imu != null) {
      if (imu.faultsRaw != null && imu.faultsRaw != 0) {
        setLikely(out, STATE_ACTIVE_FAULT, MEANING_ACTIVE_FAULT, CONFIDENCE_HIGH);
        return out;
      }
      if (imu.stickyFaultsRaw != null && imu.stickyFaultsRaw != 0) {
        setLikely(out, STATE_STICKY_FAULT, MEANING_STICKY_FAULT, CONFIDENCE_HIGH);
        return out;
      }
    }
    if (hasBusIssues(bus)) {
      setLikely(out, STATE_BUS_HEALTH, MEANING_BUS_HEALTH, CONFIDENCE_LOW);
      return out;
    }
    setLikely(out, STATE_OK, MEANING_OK, CONFIDENCE_MEDIUM);
    return out;
  }

  /**
   * NAME
   * baseAttachment
   *
   * SYNOPSIS
   * Create a base attachment with common notes.
   *
   * RETURNS
   * A new attachment with shared metadata filled in.
   */
  private static CanSuspicionAttachment baseAttachment() {
    CanSuspicionAttachment out = new CanSuspicionAttachment();
    out.note = NOTE_BEST_EFFORT;
    return out;
  }

  /**
   * NAME
   * setExpected
   *
   * SYNOPSIS
   * Populate expected state fields.
   */
  private static void setExpected(CanSuspicionAttachment out, String state, String meaning) {
    out.expectedState = safe(state);
    out.expectedMeaning = safe(meaning);
  }

  /**
   * NAME
   * setLikely
   *
   * SYNOPSIS
   * Populate likely state fields and confidence.
   */
  private static void setLikely(CanSuspicionAttachment out, String state, String meaning, String confidence) {
    out.likelyState = safe(state);
    out.likelyMeaning = safe(meaning);
    out.confidence = safe(confidence);
  }

  /**
   * NAME
   * hasAnyRaw
   *
   * SYNOPSIS
   * Check whether any raw fault counters are non-zero.
   */
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

  /**
   * NAME
   * hasAnyFlags
   *
   * SYNOPSIS
   * Check whether any fault/warning flag lists are non-empty.
   */
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

  /**
   * NAME
   * hasAnyFlags
   *
   * SYNOPSIS
   * Check whether any flag lists or raw counters indicate faults.
   */
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

  /**
   * NAME
   * hasNonOk
   *
   * SYNOPSIS
   * Determine whether a vendor status string indicates an error.
   */
  private static boolean hasNonOk(String value) {
    if (value == null || value.isBlank()) {
      return false;
    }
    return !"OK".equalsIgnoreCase(value) && !"kOk".equalsIgnoreCase(value);
  }

  /**
   * NAME
   * hasBusIssues
   *
   * SYNOPSIS
   * Detect bus-level health counter activity.
   */
  private static boolean hasBusIssues(BusSnapshot bus) {
    if (bus == null || !bus.valid) {
      return false;
    }
    return bus.busOff > 0 || bus.busOffDelta > 0
        || bus.txFull > 0 || bus.txFullDelta > 0
        || bus.rxDelta > 0 || bus.txDelta > 0;
  }

  /**
   * NAME
   * safe
   *
   * SYNOPSIS
   * Normalize null strings to empty strings.
   */
  private static String safe(String value) {
    return value == null ? "" : value;
  }
}
