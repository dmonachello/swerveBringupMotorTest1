package frc.robot.commands.local;

import com.google.gson.JsonObject;
import frc.robot.input.BindingsManager;

/**
 * NAME
 *   RobotLocalControllerGateway - Convert binding edges into executor requests.
 */
public final class RobotLocalControllerGateway {
  private static final JsonObject JSON_EMPTY = new JsonObject();

  private final RobotLocalCommandExecutor executor;
  private final RobotLocalControllerValueProvider valueProvider;

  public RobotLocalControllerGateway(
      RobotLocalCommandExecutor executor,
      RobotLocalControllerValueProvider valueProvider) {
    this.executor = executor;
    this.valueProvider = valueProvider;
  }

  public void submitFromBindings(BindingsManager.BindingState bindingState) {
    valueProvider.update(bindingState);
    for (String commandName : RobotLocalCommandRegistry.commandNames()) {
      RobotLocalCommandDefinition definition = RobotLocalCommandRegistry.definition(commandName);
      if (definition == null || !definition.controllerAllowed()) {
        continue;
      }
      if (definition.invocationKind() == RobotLocalInvocationKind.AXIS_VALUE) {
        continue;
      }
      if (!bindingState.pressed(commandName)) {
        continue;
      }
      executor.submit(new RobotLocalCommandRequest(
          commandName,
          RobotLocalCommandSource.CONTROLLER,
          RobotLocalDispatchMode.IMMEDIATE,
          JSON_EMPTY,
          valueProvider,
          "",
          0.0,
          false));
    }
  }
}
