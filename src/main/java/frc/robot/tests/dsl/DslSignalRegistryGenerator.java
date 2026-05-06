package frc.robot.tests.dsl;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * NAME
 *   DslSignalRegistryGenerator - Emit the host-side generated signal metadata artifact.
 *
 * SYNOPSIS
 *   java frc.robot.tests.dsl.DslSignalRegistryGenerator tools/common/generated/robot_test_dsl_signals.json
 */
public final class DslSignalRegistryGenerator {
  private DslSignalRegistryGenerator() {}

  public static void main(String[] args) throws IOException {
    if (args.length != 1) {
      throw new IllegalArgumentException("Usage: DslSignalRegistryGenerator <output-json-path>");
    }
    Path output = Paths.get(args[0]);
    Files.createDirectories(output.getParent());
    Files.writeString(output, DslSignalRegistry.exportJson().toString() + System.lineSeparator(), StandardCharsets.UTF_8);
  }
}
