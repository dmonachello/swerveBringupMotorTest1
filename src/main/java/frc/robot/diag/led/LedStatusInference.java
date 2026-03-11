package frc.robot.diag.led;

import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.EncoderAttachment;
import frc.robot.diag.snapshots.LedStatusAttachment;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;

/**
 * NAME
 * LedStatusInference
 *
 * SYNOPSIS
 * Best-effort inference of device status LED meanings.
 *
 * DESCRIPTION
 * Infers likely LED patterns from device telemetry without direct LED reads.
 */
public final class LedStatusInference {
  private static final double DUTY_THRESHOLD = 0.02;

  private LedStatusInference() {}

  /**
   * NAME
   * infer
   *
   * SYNOPSIS
   * Infer a LED status attachment for a device snapshot.
   *
   * PARAMETERS
   * snap - device snapshot containing vendor telemetry.
   *
   * RETURNS
   * A LED status attachment, or null when the device type is not recognized.
   */
  public static LedStatusAttachment infer(DeviceSnapshot snap) {
    if (snap == null || snap.deviceType == null || snap.deviceType.isBlank()) {
      return null;
    }
    String type = snap.deviceType;
    if ("NEO".equals(type) || "NEO 550".equals(type) || "FLEX".equals(type)) {
      return applyMeaning(snap, inferRevMotor(snap));
    }
    if ("KRAKEN".equals(type) || "FALCON".equals(type)) {
      return applyMeaning(snap, inferCtreMotor(snap));
    }
    if ("CANCoder".equals(type)) {
      return applyMeaning(snap, inferCANCoder(snap));
    }
    if ("Pigeon".equals(type) || "Pigeon2".equals(type)) {
      return applyMeaning(snap, inferPigeon(snap));
    }
    return null;
  }

  /**
   * NAME
   * inferRevMotor
   *
   * SYNOPSIS
   * Infer LED patterns for REV motor devices.
   */
  private static LedStatusAttachment inferRevMotor(DeviceSnapshot snap) {
    LedStatusAttachment led = baseAttachment(snap);
    if (!snap.present) {
      setExpected(led, "LED off");
      setLikely(led, "LED off", "HIGH");
      return led;
    }

    RevMotorAttachment rev = snap.getAttachment(RevMotorAttachment.class);
    Double duty = rev != null ? rev.appliedDuty : null;

    if (duty != null) {
      if (Math.abs(duty) < DUTY_THRESHOLD) {
        setExpected(led, "Cyan/Magenta solid");
      } else if (duty > 0) {
        setExpected(led, "Green blink/solid");
      } else {
        setExpected(led, "Red blink/solid");
      }
    } else {
      setExpected(led, "Cyan/Magenta solid");
      led.note = "Telemetry missing; expected state assumes a valid signal.";
    }

    if (rev != null && hasRevFault(rev)) {
      setLikely(led, "Orange/Yellow slow blink", "MEDIUM");
    } else if (duty != null) {
      if (Math.abs(duty) < DUTY_THRESHOLD) {
        setLikely(led, "Cyan/Magenta solid", "MEDIUM");
      } else if (duty > 0) {
        setLikely(led, "Green blink/solid", "HIGH");
      } else {
        setLikely(led, "Red blink/solid", "HIGH");
      }
    } else {
      setLikely(led, "Cyan/Magenta blink", "LOW");
    }

    return led;
  }

  /**
   * NAME
   * hasRevFault
   *
   * SYNOPSIS
   * Determine whether REV telemetry indicates a fault.
   */
  private static boolean hasRevFault(RevMotorAttachment rev) {
    if (rev == null) {
      return false;
    }
    if (rev.faultsRaw != 0 || rev.stickyFaultsRaw != 0
        || rev.warningsRaw != 0 || rev.stickyWarningsRaw != 0) {
      return true;
    }
    return rev.lastError != null && !rev.lastError.isBlank() && !"kOk".equalsIgnoreCase(rev.lastError);
  }

  /**
   * NAME
   * inferCtreMotor
   *
   * SYNOPSIS
   * Infer LED patterns for CTRE motor devices.
   */
  private static LedStatusAttachment inferCtreMotor(DeviceSnapshot snap) {
    LedStatusAttachment led = baseAttachment(snap);
    if (!snap.present) {
      setExpected(led, "LED off");
      setLikely(led, "LED off", "HIGH");
      return led;
    }

    CtreMotorAttachment ctre = snap.getAttachment(CtreMotorAttachment.class);
    Double duty = ctre != null ? ctre.appliedDuty : null;

    if (duty != null) {
      if (Math.abs(duty) < DUTY_THRESHOLD) {
        setExpected(led, "Off/Orange");
      } else if (duty > 0) {
        setExpected(led, "Green blink");
      } else {
        setExpected(led, "Red blink");
      }
    } else {
      setExpected(led, "Off/Orange");
      led.note = "Telemetry missing; expected state assumes neutral output.";
    }

    LimitsAttachment limits = snap.getAttachment(LimitsAttachment.class);
    boolean limitClosed = limits != null && (isClosed(limits.fwdClosed) || isClosed(limits.revClosed));
    if (limitClosed && duty != null && Math.abs(duty) >= DUTY_THRESHOLD) {
      setLikely(led, "Off/Red", "MEDIUM");
      return led;
    }

    if (ctre != null && hasCtreFault(ctre)) {
      setLikely(led, "Red/Orange", "MEDIUM");
    } else if (duty != null) {
      if (Math.abs(duty) < DUTY_THRESHOLD) {
        setLikely(led, "Off/Orange", "MEDIUM");
      } else if (duty > 0) {
        setLikely(led, "Green blink", "HIGH");
      } else {
        setLikely(led, "Red blink", "HIGH");
      }
    } else {
      setLikely(led, "Off/Orange", "LOW");
    }

    return led;
  }

  /**
   * NAME
   * hasCtreFault
   *
   * SYNOPSIS
   * Determine whether CTRE telemetry indicates a fault.
   */
  private static boolean hasCtreFault(CtreMotorAttachment ctre) {
    if (ctre == null) {
      return false;
    }
    if (ctre.faultsRaw != 0 || ctre.stickyFaultsRaw != 0) {
      return true;
    }
    if (ctre.faultStatus != null && !ctre.faultStatus.isBlank()
        && !"OK".equalsIgnoreCase(ctre.faultStatus)) {
      return true;
    }
    return ctre.stickyStatus != null && !ctre.stickyStatus.isBlank()
        && !"OK".equalsIgnoreCase(ctre.stickyStatus);
  }

  /**
   * NAME
   * inferCANCoder
   *
   * SYNOPSIS
   * Infer LED patterns for CTRE CANCoder devices.
   */
  private static LedStatusAttachment inferCANCoder(DeviceSnapshot snap) {
    LedStatusAttachment led = baseAttachment(snap);
    if (!snap.present) {
      setExpected(led, "LED off");
      setLikely(led, "LED off", "HIGH");
      return led;
    }

    EncoderAttachment encoder = snap.getAttachment(EncoderAttachment.class);
    setExpected(led, "Rapid green blink");

    if (encoder != null && encoder.lastError != null
        && !encoder.lastError.isBlank() && !"OK".equalsIgnoreCase(encoder.lastError)
        && !"kOk".equalsIgnoreCase(encoder.lastError)) {
      setLikely(led, "Red blink", "MEDIUM");
    } else {
      setLikely(led, "Rapid green blink", "LOW");
    }
    return led;
  }

  /**
   * NAME
   * inferPigeon
   *
   * SYNOPSIS
   * Infer LED patterns for Pigeon IMU devices.
   */
  private static LedStatusAttachment inferPigeon(DeviceSnapshot snap) {
    LedStatusAttachment led = baseAttachment(snap);
    if (!snap.present) {
      setExpected(led, "LED off");
      setLikely(led, "LED off", "HIGH");
      return led;
    }
    setExpected(led, "Green blink");
    setLikely(led, "Yellow/Green blink", "LOW");
    return led;
  }

  /**
   * NAME
   * baseAttachment
   *
   * SYNOPSIS
   * Create a base LED attachment with common notes.
   */
  private static LedStatusAttachment baseAttachment(DeviceSnapshot snap) {
    LedStatusAttachment led = new LedStatusAttachment();
    led.note = "Best-effort inference from telemetry; not a direct LED read.";
    return led;
  }

  /**
   * NAME
   * setExpected
   *
   * SYNOPSIS
   * Populate expected LED pattern fields.
   */
  private static void setExpected(LedStatusAttachment led, String pattern) {
    led.expectedPattern = safe(pattern);
  }

  /**
   * NAME
   * setLikely
   *
   * SYNOPSIS
   * Populate likely LED pattern fields and confidence.
   */
  private static void setLikely(LedStatusAttachment led, String pattern, String confidence) {
    led.likelyPattern = safe(pattern);
    led.confidence = safe(confidence);
  }

  /**
   * NAME
   * applyMeaning
   *
   * SYNOPSIS
   * Resolve pattern meanings using the vendor catalog.
   */
  private static LedStatusAttachment applyMeaning(DeviceSnapshot snap, LedStatusAttachment led) {
    if (led == null || snap == null) {
      return led;
    }
    String vendor = snap.vendor != null ? snap.vendor : "";
    String deviceType = snap.deviceType != null ? snap.deviceType : "";
    led.expectedMeaning = LedStatusCatalog.lookup(vendor, deviceType, led.expectedPattern);
    led.likelyMeaning = LedStatusCatalog.lookup(vendor, deviceType, led.likelyPattern);
    return led;
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

  /**
   * NAME
   * isClosed
   *
   * SYNOPSIS
   * Interpret a nullable limit switch state.
   */
  private static boolean isClosed(Boolean closed) {
    return closed != null && closed.booleanValue();
  }
}
