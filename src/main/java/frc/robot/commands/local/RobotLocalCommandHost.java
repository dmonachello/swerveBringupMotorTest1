package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalCommandHost - Runtime services exposed to local command handlers.
 */
public interface RobotLocalCommandHost {
  boolean ensureActiveProfile(String reason);

  void addNextMotorCommand();

  void addAllDevicesCommand();

  void runGenericCommand();

  void clearAllFaults();

  void runCanSweep();

  void toggleDashboard();

  void toggleProfile();

  void printState();

  void printHealth();

  void printCANCoder();

  void printNtDiagnostics();

  void printCanDiagnostics();

  void printBindings();

  void printTestsInfo();

  void printTestsOverview();

  void printSelectedTestSource();

  void printNextTest();

  void printInputs();

  void dumpReport();

  RobotLocalExecutionResult runActivePresenceProbe();

  void selectPreviousTest();

  void selectNextTest();

  Boolean toggleSelectedTestEnabled();

  RobotLocalExecutionResult runSelectedTest();

  RobotLocalExecutionResult runAllTests();

  boolean isActiveTestRunning();

  void updateReportsAndTests(boolean runHeld);

  boolean clearStopLatch(String reason);

  void applyCommandStop(String reason, boolean latchSafety);

  RobotLocalExecutionResult executeLegacyUiCommand(
      String commandName,
      com.google.gson.JsonObject args,
      String clientId,
      double timestampSec,
      boolean isTcp);
}
