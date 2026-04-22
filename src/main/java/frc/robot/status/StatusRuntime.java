package frc.robot.status;

import frc.robot.status.generated.StatusCatalogGenerated;
import frc.robot.status.generated.StatusMessagesGenerated;

/**
 * NAME
 *   StatusRuntime - Shared VMS-style status helpers for Java command paths.
 *
 * DESCRIPTION
 *   Provides consistent status labels and status-code selection for UI/TCP
 *   acknowledgements while preserving existing legacy string fields.
 */
public final class StatusRuntime {
  public static final String STATUS_OK = "ok";
  public static final String STATUS_ERROR = "error";

  private StatusRuntime() {}

  /**
   * NAME
   *   ackLabel - Return protocol status label for ACK payloads.
   */
  public static String ackLabel(boolean ok) {
    return ok ? STATUS_OK : STATUS_ERROR;
  }

  /**
   * NAME
   *   ackCode - Return protocol status code for ACK payloads.
   */
  public static int ackCode(boolean ok) {
    if (ok) {
      return StatusCatalogGenerated.SS__EXECUTOR__SUCCESS;
    }
    return StatusCatalogGenerated.SS__EXECUTOR__FAILED;
  }

  /**
   * NAME
   *   messageFor - Resolve status-code message template, if present.
   */
  public static String messageFor(int code) {
    String template = StatusMessagesGenerated.getMessageTemplate(code);
    return template != null ? template : "";
  }
}

