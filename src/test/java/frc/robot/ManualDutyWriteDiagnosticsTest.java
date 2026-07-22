package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class ManualDutyWriteDiagnosticsTest {
  private static final String DEVICE_LABEL = "FALCON 9";
  private static final String OWNER_SOURCE = "manual-group:active-group";
  private static final String FOREIGN_SOURCE = "bridge-binding:motors";
  private static final double REQUESTED_DUTY = 0.296;
  private static final double FOREIGN_DUTY = 0.0;
  private static final String EXPECTED_MESSAGE =
      "Manual duty overwrite diag: label=FALCON 9 requested=0.296 written=0.0"
          + " source=bridge-binding:motors owner=manual-group:active-group";

  @Test
  void recordWriteReportsForeignOverwriteAgainstWatchedManualDuty() {
    ManualDutyWriteDiagnostics diagnostics = new ManualDutyWriteDiagnostics();

    diagnostics.watch(DEVICE_LABEL, REQUESTED_DUTY, OWNER_SOURCE);

    String message = diagnostics.recordWrite(DEVICE_LABEL, FOREIGN_DUTY, FOREIGN_SOURCE);

    assertEquals(EXPECTED_MESSAGE, message);
  }

  @Test
  void recordWriteSuppressesDuplicateConflictSignature() {
    ManualDutyWriteDiagnostics diagnostics = new ManualDutyWriteDiagnostics();

    diagnostics.watch(DEVICE_LABEL, REQUESTED_DUTY, OWNER_SOURCE);

    String first = diagnostics.recordWrite(DEVICE_LABEL, FOREIGN_DUTY, FOREIGN_SOURCE);
    String second = diagnostics.recordWrite(DEVICE_LABEL, FOREIGN_DUTY, FOREIGN_SOURCE);

    assertEquals(EXPECTED_MESSAGE, first);
    assertTrue(second.isEmpty());
  }

  @Test
  void recordWriteIgnoresOwnerWritesAndAllowsFutureForeignConflict() {
    ManualDutyWriteDiagnostics diagnostics = new ManualDutyWriteDiagnostics();

    diagnostics.watch(DEVICE_LABEL, REQUESTED_DUTY, OWNER_SOURCE);

    String ownerWrite = diagnostics.recordWrite(DEVICE_LABEL, REQUESTED_DUTY, OWNER_SOURCE);
    String foreignWrite = diagnostics.recordWrite(DEVICE_LABEL, FOREIGN_DUTY, FOREIGN_SOURCE);

    assertTrue(ownerWrite.isEmpty());
    assertEquals(EXPECTED_MESSAGE, foreignWrite);
  }
}
