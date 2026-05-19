package frc.robot.tests.dsl.signals;

import java.util.Map;

/**
 * NAME
 *   DslDeviceSignalProvider - Device-type owner for DSL signal declarations.
 *
 * DESCRIPTION
 *   Each provider returns the signal metadata for one DSL device type. The
 *   central registry aggregates these explicit providers into one stable export.
 */
public interface DslDeviceSignalProvider {
  String deviceType();

  Map<String, DslSignalMeta> signals();
}
