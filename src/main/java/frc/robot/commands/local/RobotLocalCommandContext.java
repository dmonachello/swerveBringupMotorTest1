package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalCommandContext - Narrow dependency surface for local command execution.
 *
 * DESCRIPTION
 *   Lets the dispatcher and command-family handlers invoke robot-local
 *   behaviors without reaching directly into Robot or RobotV2 orchestration.
 */
public interface RobotLocalCommandContext {
  void enqueuePrint(String text);

  void handleAddMotor(boolean addMotorNow);

  void handleAddAll(boolean addAllNow);

  void handleGenericCmd(boolean genericCmdNow);

  void printState();

  void printHealth();

  void printCANCoder();

  void selectPreviousTest();

  void selectNextTest();

  Boolean toggleSelectedTestEnabled();

  void runSelectedTest();

  void runAllTests();

  void printBindings();

  void printTestsInfo();

  void printTestsOverview();

  void printNextTest();

  void printCanDiagnostics();

  void dumpReport();

  void clearAllFaults();

  void runCanSweep();

  void toggleProfile();

  void toggleDashboard();

  void printInputs();

  void updateReportsAndTests(boolean runHeld);
}
