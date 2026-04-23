package frc.robot;

import frc.robot.status.StatusRuntime;

/**
 * NAME
 *   BridgeUiCommandResult - Shared result payload for UI command execution.
 */
final class BridgeUiCommandResult {
  boolean ok = true;
  int code = StatusRuntime.ackCode(true);
  String message = "OK";
  String outText = "OK";
  String outJson = "";
}

