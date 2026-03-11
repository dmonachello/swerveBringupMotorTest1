package frc.robot.manufacturers.rev.diag;

import com.revrobotics.spark.SparkBase;
import java.util.List;

/**
 * NAME
 * RevReaderUtil
 *
 * SYNOPSIS
 * REV-specific helpers for extracting fault and warning flags.
 *
 * DESCRIPTION
 * Maps REV fault/warning structures into string lists for reporting.
 */
public final class RevReaderUtil {
  private RevReaderUtil() {}

  /**
   * NAME
   * collectFaultFlags
   *
   * SYNOPSIS
   * Collect active fault flags from a REV faults structure.
   *
   * PARAMETERS
   * faults - fault structure to read.
   * out - list to append active fault names into.
   */
  public static void collectFaultFlags(SparkBase.Faults faults, List<String> out) {
    appendIf(out, "other", faults.other);
    appendIf(out, "motorType", faults.motorType);
    appendIf(out, "sensor", faults.sensor);
    appendIf(out, "can", faults.can);
    appendIf(out, "temperature", faults.temperature);
    appendIf(out, "gateDriver", faults.gateDriver);
    appendIf(out, "escEeprom", faults.escEeprom);
    appendIf(out, "firmware", faults.firmware);
  }

  /**
   * NAME
   * collectWarningFlags
   *
   * SYNOPSIS
   * Collect active warning flags from a REV warnings structure.
   *
   * PARAMETERS
   * warnings - warning structure to read.
   * out - list to append active warning names into.
   */
  public static void collectWarningFlags(SparkBase.Warnings warnings, List<String> out) {
    appendIf(out, "brownout", warnings.brownout);
    appendIf(out, "overcurrent", warnings.overcurrent);
    appendIf(out, "escEeprom", warnings.escEeprom);
    appendIf(out, "extEeprom", warnings.extEeprom);
    appendIf(out, "sensor", warnings.sensor);
    appendIf(out, "stall", warnings.stall);
    appendIf(out, "hasReset", warnings.hasReset);
    appendIf(out, "other", warnings.other);
  }

  /**
   * NAME
   * appendIf
   *
   * SYNOPSIS
   * Append a flag name when it is active.
   */
  private static void appendIf(List<String> out, String name, boolean active) {
    if (!active) {
      return;
    }
    out.add(name);
  }
}
