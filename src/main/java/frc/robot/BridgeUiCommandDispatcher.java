package frc.robot;

import java.util.List;

/**
 * NAME
 *   BridgeUiCommandDispatcher - Route validated UI commands to domain families.
 */
final class BridgeUiCommandDispatcher {

  /**
   * NAME
   *   CommandFamily - Execute one command family domain.
   */
  interface CommandFamily {
    boolean handles(String commandName);

    BridgeUiCommandResult execute(
        BridgeUiIngressPolicy.Ingress ingress,
        double cmdTs,
        boolean isTcp);
  }

  private static final String TEXT_UNKNOWN_COMMAND_PREFIX = "Unknown command: ";

  private final List<CommandFamily> families;

  BridgeUiCommandDispatcher(List<CommandFamily> families) {
    this.families = families;
  }

  BridgeUiCommandResult dispatch(BridgeUiIngressPolicy.Ingress ingress, double cmdTs, boolean isTcp) {
    String commandName = ingress != null ? ingress.name : null;
    if (commandName != null) {
      for (CommandFamily family : families) {
        if (family != null && family.handles(commandName)) {
          return family.execute(ingress, cmdTs, isTcp);
        }
      }
    }
    BridgeUiCommandResult result = new BridgeUiCommandResult();
    result.ok = false;
    result.message = TEXT_UNKNOWN_COMMAND_PREFIX + commandName;
    result.outText = result.message;
    return result;
  }
}

