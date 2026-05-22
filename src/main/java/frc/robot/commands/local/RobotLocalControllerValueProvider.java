package frc.robot.commands.local;

import frc.robot.input.BindingsManager;

/**
 * NAME
 *   RobotLocalControllerValueProvider - Mutable live binding snapshot provider.
 */
public final class RobotLocalControllerValueProvider implements RobotLocalValueProvider {
  private static final String TEXT_EMPTY = "";

  private BindingsManager.BindingState bindingState = new BindingsManager.BindingState();

  public void update(BindingsManager.BindingState bindingState) {
    this.bindingState = bindingState != null ? bindingState : new BindingsManager.BindingState();
  }

  @Override
  public boolean isCommandActive(String commandName) {
    if (commandName == null || commandName.isBlank()) {
      return false;
    }
    return bindingState.held(commandName)
        || bindingState.pressed(commandName)
        || Math.abs(bindingState.axis(commandName)) > 0.0;
  }

  @Override
  public double axisValue(String commandName) {
    return commandName != null && !commandName.equals(TEXT_EMPTY)
        ? bindingState.axis(commandName)
        : 0.0;
  }
}
