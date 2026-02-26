package frc.robot.diag.readers;

import com.revrobotics.spark.SparkBase;
import java.util.List;

// REV-specific helpers for extracting fault/warning flags.
public final class RevReaderUtil {
  private RevReaderUtil() {}

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

  private static void appendIf(List<String> out, String name, boolean active) {
    if (!active) {
      return;
    }
    out.add(name);
  }
}
