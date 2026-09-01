package frc.robot.commands.local;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import java.util.ArrayDeque;
import java.util.Deque;
import org.junit.jupiter.api.Test;

class RobotLocalCommandExecutorTest {

  private static final String CMD_SHOW_DEVICES = "showDevices";
  private static final String CMD_ACTIVE_PRESENCE_PROBE = "activePresenceProbe";
  private static final String CMD_LIFECYCLE_ACTIVATE = "lifecycleActivate";
  private static final String CMD_PRINT_TESTS_OVERVIEW = "printTestsOverview";
  private static final String CMD_PROFILES_APPLY = "profilesApply";
  private static final String CMD_RUN_TEST = "runTest";
  private static final String MESSAGE_ACTIVE_BUSY = "Another command is already active.";
  private static final String MESSAGE_CONTROLLER_HOLD_RELEASED = "controller hold released";
  private static final String MESSAGE_UI_RUN_COMMAND_ENDED = "UI run command ended";

  @Test
  void immediateCompleteCommandClearsActiveSlotBeforeNextSubmit() {
    RobotLocalCommandExecutor executor = new RobotLocalCommandExecutor(new HostStub());

    RobotLocalDispatchResult first =
        executor.submit(request(CMD_SHOW_DEVICES));
    assertEquals(RobotLocalDispatchStatus.ACCEPTED, first.status());
    assertNull(executor.activeCommandName());

    RobotLocalDispatchResult second =
        executor.submit(request(CMD_PROFILES_APPLY));
    assertEquals(RobotLocalDispatchStatus.ACCEPTED, second.status());
    assertNull(executor.activeCommandName());
  }

  @Test
  void secondImmediateCommandIsRejectedWhileLongRunningCommandIsActive() {
    HostStub host = new HostStub();
    host.activeTestRunning = true;
    RobotLocalCommandExecutor executor = new RobotLocalCommandExecutor(host);

    RobotLocalDispatchResult first =
        executor.submit(controllerRequest(CMD_RUN_TEST));
    assertEquals(RobotLocalDispatchStatus.ACCEPTED, first.status());
    assertEquals(CMD_RUN_TEST, executor.activeCommandName());
    assertTrue(first.executionResult().ok());

    RobotLocalDispatchResult second =
        executor.submit(request(CMD_SHOW_DEVICES));
    assertEquals(RobotLocalDispatchStatus.REJECTED, second.status());
    assertEquals(MESSAGE_ACTIVE_BUSY, second.message());
    assertFalse(second.executionResult().ok());
    assertEquals(CMD_RUN_TEST, executor.activeCommandName());
  }

  @Test
  void hostVoidCommandUsesPublicInterfaceMethodForNonPublicHostImplementation() {
    PrivateHostStub host = new PrivateHostStub();
    RobotLocalCommandExecutor executor = new RobotLocalCommandExecutor(host);

    RobotLocalDispatchResult result = executor.submit(request(CMD_PRINT_TESTS_OVERVIEW));

    assertEquals(RobotLocalDispatchStatus.ACCEPTED, result.status());
    assertTrue(result.executionResult().ok());
    assertTrue(host.printTestsOverviewCalled);
  }

  @Test
  void runTestDoesNotRequireLegacyRuntimeActivation() {
    HostStub host = new HostStub();
    RobotLocalCommandExecutor executor = new RobotLocalCommandExecutor(host);

    RobotLocalDispatchResult result = executor.submit(request(CMD_RUN_TEST));

    assertEquals(RobotLocalDispatchStatus.ACCEPTED, result.status());
    assertTrue(result.executionResult().ok());
    assertFalse(host.ensureActiveProfileCalled);
    assertTrue(host.runSelectedTestCalled);
  }

  @Test
  void runTestStillDispatchesWhenLegacyRuntimeEnsureWouldFail() {
    HostStub host = new HostStub();
    host.ensureActiveProfileResult = false;
    RobotLocalCommandExecutor executor = new RobotLocalCommandExecutor(host);

    RobotLocalDispatchResult result = executor.submit(request(CMD_RUN_TEST));

    assertEquals(RobotLocalDispatchStatus.ACCEPTED, result.status());
    assertTrue(result.executionResult().ok());
    assertFalse(host.ensureActiveProfileCalled);
    assertTrue(host.runSelectedTestCalled);
  }

  @Test
  void controllerSourceLossUsesControllerHoldReleasedReason() {
    HostStub host = new HostStub();
    host.activeTestRunning = true;
    host.runSelectedTestResult = RobotLocalExecutionResult.running("runTest active.");
    RobotLocalCommandExecutor executor = new RobotLocalCommandExecutor(host);

    RobotLocalDispatchResult result = executor.submit(controllerRequest(CMD_RUN_TEST));

    assertEquals(RobotLocalDispatchStatus.ACCEPTED, result.status());
    executor.step();
    assertEquals(MESSAGE_CONTROLLER_HOLD_RELEASED, host.lastApplyCommandStopReason);
  }

  @Test
  void hostUiSourceLossUsesUiRunCommandEndedReason() {
    HostStub host = new HostStub();
    host.activeTestRunning = true;
    host.runSelectedTestResult = RobotLocalExecutionResult.running("runTest active.");
    RobotLocalCommandExecutor executor = new RobotLocalCommandExecutor(host);

    RobotLocalDispatchResult result =
        executor.submit(
            new RobotLocalCommandRequest(
                CMD_RUN_TEST,
                RobotLocalCommandSource.HOST_UI,
                RobotLocalDispatchMode.IMMEDIATE,
                new JsonObject(),
                RobotLocalNoopValueProvider.INSTANCE,
                "clientA",
                0.0,
                true));

    assertEquals(RobotLocalDispatchStatus.ACCEPTED, result.status());
    executor.step();
    assertEquals(MESSAGE_UI_RUN_COMMAND_ENDED, host.lastApplyCommandStopReason);
  }

  @Test
  void activePresenceProbeRunsAcrossMultipleExecutorSteps() {
    HostStub host = new HostStub();
    host.stepActivePresenceProbeResults.add(RobotLocalExecutionResult.running("probe step 1"));
    host.stepActivePresenceProbeResults.add(RobotLocalExecutionResult.complete("probe complete"));
    RobotLocalCommandExecutor executor = new RobotLocalCommandExecutor(host);

    RobotLocalDispatchResult result = executor.submit(request(CMD_ACTIVE_PRESENCE_PROBE));

    assertEquals(RobotLocalDispatchStatus.ACCEPTED, result.status());
    assertEquals(CMD_ACTIVE_PRESENCE_PROBE, executor.activeCommandName());
    assertTrue(host.beginActivePresenceProbeCalled);
    assertEquals(1, host.stepActivePresenceProbeCallCount);

    executor.step();
    assertNull(executor.activeCommandName());
    assertEquals(2, host.stepActivePresenceProbeCallCount);
  }

  @Test
  void stopCommandCancelsActivePresenceProbeRun() {
    HostStub host = new HostStub();
    host.stepActivePresenceProbeResults.add(RobotLocalExecutionResult.running("probe step 1"));
    host.stepActivePresenceProbeResults.add(RobotLocalExecutionResult.running("probe step 2"));
    RobotLocalCommandExecutor executor = new RobotLocalCommandExecutor(host);

    RobotLocalDispatchResult start = executor.submit(request(CMD_ACTIVE_PRESENCE_PROBE));
    assertEquals(RobotLocalDispatchStatus.ACCEPTED, start.status());

    RobotLocalDispatchResult stop = executor.submit(request(RobotLocalCommandRegistry.COMMAND_STOP));

    assertEquals(RobotLocalDispatchStatus.INTERRUPTED_AND_ACCEPTED, stop.status());
    assertTrue(host.cancelActivePresenceProbeCalled);
    assertNull(executor.activeCommandName());
  }

  @Test
  void lifecycleActivateRoutesThroughLegacyUiCommandPathWithArgs() {
    HostStub host = new HostStub();
    host.legacyUiResult =
        RobotLocalExecutionResult.complete("Lifecycle activated.", "Lifecycle activated.", "{\"ok\":true}");
    RobotLocalCommandExecutor executor = new RobotLocalCommandExecutor(host);
    JsonObject args = new JsonObject();
    args.addProperty("label", "front_left_drive");
    args.addProperty("mode", "READ_ONLY");

    RobotLocalDispatchResult result =
        executor.submit(
            new RobotLocalCommandRequest(
                CMD_LIFECYCLE_ACTIVATE,
                RobotLocalCommandSource.HOST_UI,
                RobotLocalDispatchMode.IMMEDIATE,
                args,
                RobotLocalNoopValueProvider.INSTANCE,
                "clientA",
                0.0,
                true));

    assertEquals(RobotLocalDispatchStatus.ACCEPTED, result.status());
    assertTrue(result.executionResult().ok());
    assertEquals(CMD_LIFECYCLE_ACTIVATE, host.lastLegacyUiCommandName);
    assertEquals("front_left_drive", host.lastLegacyUiArgs.get("label").getAsString());
    assertEquals("READ_ONLY", host.lastLegacyUiArgs.get("mode").getAsString());
    assertEquals("{\"ok\":true}", result.executionResult().outJson());
  }

  private static RobotLocalCommandRequest request(String name) {
    return new RobotLocalCommandRequest(
        name,
        RobotLocalCommandSource.HOST_UI,
        RobotLocalDispatchMode.IMMEDIATE,
        new JsonObject(),
        RobotLocalNoopValueProvider.INSTANCE,
        "clientA",
        0.0,
        true);
  }

  private static RobotLocalCommandRequest controllerRequest(String name) {
    return new RobotLocalCommandRequest(
        name,
        RobotLocalCommandSource.CONTROLLER,
        RobotLocalDispatchMode.IMMEDIATE,
        new JsonObject(),
        RobotLocalNoopValueProvider.INSTANCE,
        "",
        0.0,
        false);
  }

  private static class HostStub implements RobotLocalCommandHost {
    private boolean activeTestRunning;
    private boolean ensureActiveProfileResult = true;
    private boolean ensureActiveProfileCalled;
    private boolean runSelectedTestCalled;
    private boolean beginActivePresenceProbeCalled;
    private boolean cancelActivePresenceProbeCalled;
    private int stepActivePresenceProbeCallCount;
    private final Deque<RobotLocalExecutionResult> stepActivePresenceProbeResults =
        new ArrayDeque<>();
    private RobotLocalExecutionResult runSelectedTestResult =
        RobotLocalExecutionResult.complete("runSelectedTest");
    private String lastApplyCommandStopReason;
    private String lastLegacyUiCommandName;
    private JsonObject lastLegacyUiArgs;
    private RobotLocalExecutionResult legacyUiResult =
        RobotLocalExecutionResult.complete("legacyUi");

    @Override
    public boolean ensureActiveProfile(String reason) {
      ensureActiveProfileCalled = true;
      return ensureActiveProfileResult;
    }

    @Override
    public void addNextMotorCommand() {}

    @Override
    public void addAllDevicesCommand() {}

    @Override
    public void runGenericCommand() {}

    @Override
    public void clearAllFaults() {}

    @Override
    public void runCanSweep() {}

    @Override
    public void toggleDashboard() {}

    @Override
    public void toggleProfile() {}

    @Override
    public void printState() {}

    @Override
    public void printHealth() {}

    @Override
    public void printCANCoder() {}

    @Override
    public void printCanDiagnostics() {}

    @Override
    public void printBindings() {}

    @Override
    public void printTestsInfo() {}

    @Override
    public void printTestsOverview() {}

    @Override
    public void printSelectedTestSource() {}

    @Override
    public void printNextTest() {}

    @Override
    public void printInputs() {}

    @Override
    public void dumpReport() {}

    @Override
    public RobotLocalExecutionResult beginActivePresenceProbe() {
      beginActivePresenceProbeCalled = true;
      return RobotLocalExecutionResult.running("probe begin");
    }

    @Override
    public RobotLocalExecutionResult stepActivePresenceProbe() {
      stepActivePresenceProbeCallCount++;
      return stepActivePresenceProbeResults.isEmpty()
          ? RobotLocalExecutionResult.complete("activePresenceProbe")
          : stepActivePresenceProbeResults.removeFirst();
    }

    @Override
    public void cancelActivePresenceProbe() {
      cancelActivePresenceProbeCalled = true;
    }

    @Override
    public void selectPreviousTest() {}

    @Override
    public void selectNextTest() {}

    @Override
    public Boolean toggleSelectedTestEnabled() {
      return true;
    }

    @Override
    public RobotLocalExecutionResult runSelectedTest() {
      runSelectedTestCalled = true;
      return runSelectedTestResult;
    }

    @Override
    public RobotLocalExecutionResult runAllTests() {
      return RobotLocalExecutionResult.complete("runAllTests");
    }

    @Override
    public boolean isActiveTestRunning() {
      return activeTestRunning;
    }

    @Override
    public void updateReportsAndTests(boolean runHeld) {}

    @Override
    public boolean clearStopLatch(String reason) {
      return true;
    }

    @Override
    public void applyCommandStop(String reason, boolean latchSafety) {
      lastApplyCommandStopReason = reason;
    }

    @Override
    public RobotLocalExecutionResult executeLegacyUiCommand(
        String commandName,
        JsonObject args,
        String clientId,
        double timestampSec,
        boolean isTcp) {
      lastLegacyUiCommandName = commandName;
      lastLegacyUiArgs = args;
      return legacyUiResult;
    }
  }

  private static final class PrivateHostStub extends HostStub {
    private boolean printTestsOverviewCalled;

    @Override
    public void printTestsOverview() {
      printTestsOverviewCalled = true;
    }
  }
}
