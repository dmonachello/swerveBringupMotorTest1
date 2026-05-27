package frc.robot.commands.local;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import org.junit.jupiter.api.Test;

class RobotLocalCommandExecutorTest {

  private static final String CMD_SHOW_DEVICES = "showDevices";
  private static final String CMD_PROFILES_APPLY = "profilesApply";
  private static final String CMD_RUN_TEST = "runTest";
  private static final String MESSAGE_ACTIVE_BUSY = "Another command is already active.";

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

  private static final class HostStub implements RobotLocalCommandHost {
    private boolean activeTestRunning;

    @Override
    public boolean ensureActiveProfile(String reason) {
      return true;
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
    public void printNtDiagnostics() {}

    @Override
    public void printCanDiagnostics() {}

    @Override
    public void printBindings() {}

    @Override
    public void printTestsInfo() {}

    @Override
    public void printTestsOverview() {}

    @Override
    public void printNextTest() {}

    @Override
    public void printInputs() {}

    @Override
    public void dumpReport() {}

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
      return RobotLocalExecutionResult.complete("runSelectedTest");
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
    public void applyCommandStop(String reason, boolean latchSafety) {}

    @Override
    public RobotLocalExecutionResult executeLegacyUiCommand(
        String commandName,
        JsonObject args,
        String clientId,
        double timestampSec,
        boolean isTcp) {
      return RobotLocalExecutionResult.complete(commandName);
    }
  }
}
