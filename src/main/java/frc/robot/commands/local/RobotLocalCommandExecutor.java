package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalCommandExecutor - Single-active-command executor with no queue.
 */
public final class RobotLocalCommandExecutor {
  private static final String MESSAGE_UNKNOWN_COMMAND_PREFIX = "Unknown command: ";
  private static final String MESSAGE_COMMAND_NOT_ALLOWED_PREFIX = "Command source not allowed: ";
  private static final String MESSAGE_ACTIVE_BUSY = "Another command is already active.";
  private static final String REASON_PREEMPTED = "preempted";
  private static final String REASON_SOURCE_LOSS = "sourceLoss";
  private static final String MESSAGE_CONTROLLER_HOLD_RELEASED = "controller hold released";
  private static final String MESSAGE_UI_RUN_COMMAND_ENDED = "UI run command ended";
  private static final String MESSAGE_HOLD_RELEASED = "hold released";

  private final RobotLocalCommandHost host;
  private ActiveCommand active;

  public RobotLocalCommandExecutor(RobotLocalCommandHost host) {
    this.host = host;
  }

  public RobotLocalDispatchResult submit(RobotLocalCommandRequest request) {
    if (request == null || request.name() == null || request.name().isBlank()) {
      return RobotLocalDispatchResult.rejected(MESSAGE_UNKNOWN_COMMAND_PREFIX + request);
    }
    RobotLocalCommandDefinition definition = RobotLocalCommandRegistry.definition(request.name());
    if (definition == null) {
      return RobotLocalDispatchResult.rejected(MESSAGE_UNKNOWN_COMMAND_PREFIX + request.name());
    }
    if (!definition.isAllowedFor(request.source())) {
      return RobotLocalDispatchResult.rejected(
          MESSAGE_COMMAND_NOT_ALLOWED_PREFIX + definition.wireName());
    }

    if (RobotLocalCommandRegistry.COMMAND_STOP.equals(definition.wireName())) {
      interruptActive(definition, request, true, RobotLocalCommandSource.HOST_UI);
      return RobotLocalDispatchResult.accepted(
          RobotLocalDispatchStatus.INTERRUPTED_AND_ACCEPTED,
          "stopCommand executed.",
          RobotLocalExecutionResult.complete("stopCommand executed."));
    }

    ActiveCommand candidate = new ActiveCommand(definition, request);
    if (active == null) {
      active = candidate;
      RobotLocalExecutionResult executionResult = runActiveOnce(active);
      if (isTerminal(executionResult)) {
        active = null;
      }
      return RobotLocalDispatchResult.accepted(
          RobotLocalDispatchStatus.ACCEPTED,
          executionResult.message(),
          executionResult);
    }

    if (request.dispatchMode() == RobotLocalDispatchMode.INTERRUPT) {
      interruptActive(active.definition, active.request, false, request.source());
      active = candidate;
      RobotLocalExecutionResult executionResult = runActiveOnce(active);
      if (isTerminal(executionResult)) {
        active = null;
      }
      return RobotLocalDispatchResult.accepted(
          RobotLocalDispatchStatus.INTERRUPTED_AND_ACCEPTED,
          executionResult.message(),
          executionResult);
    }
    return RobotLocalDispatchResult.rejected(MESSAGE_ACTIVE_BUSY);
  }

  public void step() {
    if (active == null) {
      return;
    }
    if (active.definition.autoStopOnSourceLoss()
        && !active.request.valueProvider().isCommandActive(active.definition.wireName())) {
      interruptActive(active.definition, active.request, false, active.request.source());
      active = null;
      return;
    }
    RobotLocalExecutionResult result = runActiveOnce(active);
    if (result.state() == RobotLocalExecutionState.COMPLETE
        || result.state() == RobotLocalExecutionState.FAILED
        || result.state() == RobotLocalExecutionState.INTERRUPTED
        || result.state() == RobotLocalExecutionState.REJECTED) {
      active = null;
    }
  }

  public String activeCommandName() {
    return active != null ? active.definition.wireName() : null;
  }

  public boolean isActiveCommand(String commandName) {
    return active != null
        && commandName != null
        && commandName.equals(active.definition.wireName());
  }

  private RobotLocalExecutionResult runActiveOnce(ActiveCommand command) {
    if (command == null) {
      return RobotLocalExecutionResult.complete("");
    }
    RobotLocalCommandParams params =
        new RobotLocalCommandParams(command.definition, command.request, host);
    if (!command.initialized) {
      command.initialized = true;
      RobotLocalExecutionResult initResult = command.definition.command().init(params);
      if (isTerminal(initResult)) {
        command.definition.command().finished(params, initResult);
        return initResult;
      }
    }
    RobotLocalExecutionResult result = command.definition.command().execute(params);
    if (!isTerminal(result) && command.definition.command().isFinished(params)) {
      result = RobotLocalExecutionResult.complete(result.message());
    }
    if (isTerminal(result)) {
      command.definition.command().finished(params, result);
    }
    return result;
  }

  private boolean isTerminal(RobotLocalExecutionResult result) {
    if (result == null) {
      return false;
    }
    return result.state() == RobotLocalExecutionState.COMPLETE
        || result.state() == RobotLocalExecutionState.FAILED
        || result.state() == RobotLocalExecutionState.INTERRUPTED
        || result.state() == RobotLocalExecutionState.REJECTED;
  }

  private void interruptActive(
      RobotLocalCommandDefinition definition,
      RobotLocalCommandRequest request,
      boolean latchSafety,
      RobotLocalCommandSource source) {
    if (active == null) {
      if (latchSafety) {
        host.applyCommandStop(REASON_PREEMPTED, true);
      }
      return;
    }
    RobotLocalCommandParams params =
        new RobotLocalCommandParams(active.definition, active.request, host);
    active.definition.command().interrupt(
        params,
        latchSafety ? active.definition.wireName() : REASON_PREEMPTED);
    host.applyCommandStop(
        latchSafety
            ? active.definition.wireName()
            : resolveOperatorStopReason(source),
        latchSafety);
    active = null;
  }

  private String resolveOperatorStopReason(RobotLocalCommandSource source) {
    if (source == null) {
      return REASON_PREEMPTED;
    }
    return switch (source) {
      case CONTROLLER -> MESSAGE_CONTROLLER_HOLD_RELEASED;
      case HOST_UI -> MESSAGE_UI_RUN_COMMAND_ENDED;
      default -> MESSAGE_HOLD_RELEASED;
    };
  }

  private static final class ActiveCommand {
    private final RobotLocalCommandDefinition definition;
    private final RobotLocalCommandRequest request;
    private boolean initialized;

    private ActiveCommand(
        RobotLocalCommandDefinition definition,
        RobotLocalCommandRequest request) {
      this.definition = definition;
      this.request = request;
      this.initialized = false;
    }
  }
}
