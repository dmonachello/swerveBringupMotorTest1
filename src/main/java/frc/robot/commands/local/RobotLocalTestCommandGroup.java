package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalTestCommandGroup - Direct bringup-test command handlers.
 */
final class RobotLocalTestCommandGroup implements RobotLocalCommand {
  private static final String REASON_RUN_TEST = "xboxRun";
  private static final String REASON_RUN_ALL_TESTS = "runAllTests";
  private static final String MESSAGE_TEST_RUNTIME_NOT_READY =
      "Active profile runtime is not ready for tests. Use Runtime Activate.";

  @Override
  public RobotLocalExecutionResult init(RobotLocalCommandParams params) {
    String wireName = params.definition().wireName();
    RobotLocalCommandHost host = params.host();
    switch (wireName) {
      case RobotLocalCommandRegistry.COMMAND_RUN_TEST:
        if (!host.ensureActiveProfile(REASON_RUN_TEST)) {
          return RobotLocalExecutionResult.failed(MESSAGE_TEST_RUNTIME_NOT_READY);
        }
        host.clearStopLatch(REASON_RUN_TEST);
        RobotLocalExecutionResult runResult = host.runSelectedTest();
        if (params.request().source() == RobotLocalCommandSource.HOST_UI) {
          return runResult;
        }
        return RobotLocalExecutionResult.running(runResult.message());
      case RobotLocalCommandRegistry.COMMAND_RUN_ALL_TESTS:
        if (!host.ensureActiveProfile(REASON_RUN_ALL_TESTS)) {
          return RobotLocalExecutionResult.failed(MESSAGE_TEST_RUNTIME_NOT_READY);
        }
        host.clearStopLatch(REASON_RUN_TEST);
        return host.runAllTests();
      default:
        return RobotLocalExecutionResult.running();
    }
  }

  @Override
  public RobotLocalExecutionResult execute(RobotLocalCommandParams params) {
    RobotLocalCommandHost host = params.host();
    switch (params.definition().wireName()) {
      case RobotLocalCommandRegistry.COMMAND_SELECT_TEST_PREV:
        host.selectPreviousTest();
        host.printTestsOverview();
        return RobotLocalExecutionResult.complete("Selected previous test.");
      case RobotLocalCommandRegistry.COMMAND_SELECT_TEST_NEXT:
        host.selectNextTest();
        host.printTestsOverview();
        return RobotLocalExecutionResult.complete("Selected next test.");
      case RobotLocalCommandRegistry.COMMAND_TOGGLE_TEST:
        host.toggleSelectedTestEnabled();
        host.printTestsOverview();
        return RobotLocalExecutionResult.complete("Toggled selected test.");
      case RobotLocalCommandRegistry.COMMAND_RUN_TEST:
        return RobotLocalExecutionResult.running("runTest active.");
      case RobotLocalCommandRegistry.COMMAND_RUN_ALL_TESTS:
        return RobotLocalExecutionResult.complete("runAllTests requested.");
      default:
        return host.executeLegacyUiCommand(
            params.definition().wireName(),
            params.request().args(),
            params.request().clientId(),
            params.request().timestampSec(),
            params.request().tcp());
    }
  }

  @Override
  public boolean isFinished(RobotLocalCommandParams params) {
    return switch (params.definition().wireName()) {
      case RobotLocalCommandRegistry.COMMAND_RUN_TEST -> !params.host().isActiveTestRunning();
      default -> true;
    };
  }
}
