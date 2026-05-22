package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalLegacyUiCommandGroup - Adapter to the existing UI command families.
 *
 * DESCRIPTION
 *   Keeps the executor/lookup path unified while broader UI command families
 *   are still implemented by the existing BridgeUi* command owners.
 */
final class RobotLocalLegacyUiCommandGroup implements RobotLocalCommand {
  @Override
  public RobotLocalExecutionResult execute(RobotLocalCommandParams params) {
    return params.host().executeLegacyUiCommand(
        params.definition().wireName(),
        params.request().args(),
        params.request().clientId(),
        params.request().timestampSec(),
        params.request().tcp());
  }
}
