package frc.robot;

import frc.robot.commands.local.RobotLocalCommandContext;
import frc.robot.commands.local.RobotLocalCommandDispatcher;
import frc.robot.input.BindingsManager;

/**
 * NAME
 *   BringupCommandRouter - Compatibility adapter for robot-local command dispatch.
 *
 * DESCRIPTION
 *   Preserves the historical call sites while delegating actual command
 *   ownership to the canonical robot-local command dispatcher.
 */
public final class BringupCommandRouter {
  private static final int REPORT_BATCH_SIZE = 4;
  private static final int DUMP_WRAP_COLUMNS = 120;
  private static final String MESSAGE_REPORT_WRITE_OK_PREFIX = "Wrote CAN report JSON to ";
  private static final String MESSAGE_REPORT_WRITE_FAILED = "Failed to write CAN report JSON.";

  private BringupCommandRouter() {}

  /**
   * NAME
   *   CommonResult - Summary of binding-driven actions.
   */
  public static final class CommonResult {
    public Boolean toggledTestEnabled = null;
    public boolean runTestPressed = false;
    public boolean runAllPressed = false;
  }

  /**
   * NAME
   *   AddAllHandler - Hook for add-all activation behavior.
   */
  public interface AddAllHandler {
    void handleAddAll(boolean addAllNow);
  }

  /**
   * NAME
   *   GenericCmdHandler - Hook for example command activation behavior.
   */
  public interface GenericCmdHandler {
    void handleGenericCmd(boolean genericCmdNow);
  }

  /**
   * NAME
   *   AddMotorHandler - Hook for add-next activation behavior.
   */
  public interface AddMotorHandler {
    void handleAddMotor(boolean addMotorNow);
  }

  /**
   * NAME
   *   applyCommon - Apply registered local commands to the shared runtime.
   */
  public static CommonResult applyCommon(
      BindingsManager.BindingState bind,
      BringupRuntime runtime,
      Runnable printBindings,
      Runnable printTestsInfo,
      Runnable printTestsOverview,
      Runnable toggleProfile,
      Runnable toggleDashboard,
      Runnable printInputs,
      AddAllHandler addAllHandler,
      GenericCmdHandler genericCmdHandler,
      AddMotorHandler addMotorHandler) {
    RobotLocalCommandDispatcher.CommonResult dispatchResult =
        RobotLocalCommandDispatcher.dispatch(
            bind,
            buildRuntimeContext(
                runtime,
                printBindings,
                printTestsInfo,
                printTestsOverview,
                toggleProfile,
                toggleDashboard,
                printInputs,
                addAllHandler,
                genericCmdHandler,
                addMotorHandler));
    return toCommonResult(dispatchResult);
  }

  /**
   * NAME
   *   applyCommon - Apply registered local commands to the legacy core path.
   */
  public static CommonResult applyCommon(
      BindingsManager.BindingState bind,
      BringupCore core,
      DiagnosticsReporter diagnostics,
      Runnable printBindings,
      Runnable printTestsInfo,
      Runnable printTestsOverview,
      Runnable toggleProfile,
      Runnable printInputs,
      AddAllHandler addAllHandler,
      GenericCmdHandler genericCmdHandler,
      AddMotorHandler addMotorHandler) {
    RobotLocalCommandDispatcher.CommonResult dispatchResult =
        RobotLocalCommandDispatcher.dispatch(
            bind,
            buildCoreContext(
                core,
                diagnostics,
                printBindings,
                printTestsInfo,
                printTestsOverview,
                toggleProfile,
                printInputs,
                addAllHandler,
                genericCmdHandler,
                addMotorHandler));
    return toCommonResult(dispatchResult);
  }

  private static CommonResult toCommonResult(
      RobotLocalCommandDispatcher.CommonResult dispatchResult) {
    CommonResult result = new CommonResult();
    result.toggledTestEnabled = dispatchResult.toggledTestEnabled;
    result.runTestPressed = dispatchResult.runTestPressed;
    result.runAllPressed = dispatchResult.runAllPressed;
    return result;
  }

  private static RobotLocalCommandContext buildRuntimeContext(
      BringupRuntime runtime,
      Runnable printBindings,
      Runnable printTestsInfo,
      Runnable printTestsOverview,
      Runnable toggleProfile,
      Runnable toggleDashboard,
      Runnable printInputs,
      AddAllHandler addAllHandler,
      GenericCmdHandler genericCmdHandler,
      AddMotorHandler addMotorHandler) {
    return new RobotLocalCommandContext() {
      @Override
      public void enqueuePrint(String text) {
        BringupPrinter.enqueue(text);
      }

      @Override
      public void handleAddMotor(boolean addMotorNow) {
        if (addMotorHandler != null) {
          addMotorHandler.handleAddMotor(addMotorNow);
        } else {
          runtime.addMotor(addMotorNow);
        }
      }

      @Override
      public void handleAddAll(boolean addAllNow) {
        if (addAllHandler != null) {
          addAllHandler.handleAddAll(addAllNow);
        } else {
          runtime.addAllDevices(addAllNow);
        }
      }

      @Override
      public void handleGenericCmd(boolean genericCmdNow) {
        if (genericCmdHandler != null) {
          genericCmdHandler.handleGenericCmd(genericCmdNow);
        } else {
          runtime.addAllDevices(genericCmdNow);
        }
      }

      @Override
      public void printState() {
        runtime.handlePrint(true);
      }

      @Override
      public void printHealth() {
        runtime.handleHealth(true);
      }

      @Override
      public void printCANCoder() {
        runtime.handleCANCoder(true);
      }

      @Override
      public void selectPreviousTest() {
        runtime.selectPreviousTest();
      }

      @Override
      public void selectNextTest() {
        runtime.selectNextTest();
      }

      @Override
      public Boolean toggleSelectedTestEnabled() {
        return runtime.toggleSelectedTestEnabled();
      }

      @Override
      public void runSelectedTest() {
        runtime.runSelectedTest();
      }

      @Override
      public void runAllTests() {
        runtime.runAllTests();
      }

      @Override
      public void printBindings() {
        if (printBindings != null) {
          printBindings.run();
        }
      }

      @Override
      public void printTestsInfo() {
        if (printTestsInfo != null) {
          printTestsInfo.run();
        }
      }

      @Override
      public void printTestsOverview() {
        if (printTestsOverview != null) {
          printTestsOverview.run();
        }
      }

      @Override
      public void printNextTest() {
        runtime.printNextTestReport();
      }

      @Override
      public void printCanDiagnostics() {
        DiagnosticsReporter diagnostics = runtime.getDiagnostics();
        if (diagnostics == null) {
          return;
        }
        String report = diagnostics.buildCanDiagnosticsReportIfReady();
        if (report != null) {
          runtime.requestTextReport(report, REPORT_BATCH_SIZE);
        }
      }

      @Override
      public void dumpReport() {
        DiagnosticsReporter diagnostics = runtime.getDiagnostics();
        if (diagnostics == null) {
          return;
        }
        String json = diagnostics.buildReportJsonForDump();
        String wrapped = ReportTextUtil.wrapLongLine(json, DUMP_WRAP_COLUMNS);
        runtime.requestTextReport(wrapped, REPORT_BATCH_SIZE);
        if (diagnostics.writeReportJsonToFile(json)) {
          runtime.requestTextReport(
              MESSAGE_REPORT_WRITE_OK_PREFIX + diagnostics.getReportPath(),
              REPORT_BATCH_SIZE);
        } else {
          runtime.requestTextReport(MESSAGE_REPORT_WRITE_FAILED, REPORT_BATCH_SIZE);
        }
      }

      @Override
      public void clearAllFaults() {
        runtime.clearAllFaults();
      }

      @Override
      public void runCanSweep() {
        runtime.runCanPingSweep();
      }

      @Override
      public void toggleProfile() {
        if (toggleProfile != null) {
          toggleProfile.run();
        }
      }

      @Override
      public void toggleDashboard() {
        if (toggleDashboard != null) {
          toggleDashboard.run();
        }
      }

      @Override
      public void printInputs() {
        if (printInputs != null) {
          printInputs.run();
        }
      }

      @Override
      public void updateReportsAndTests(boolean runHeld) {
        runtime.updateReportsAndTests(runHeld);
      }
    };
  }

  private static RobotLocalCommandContext buildCoreContext(
      BringupCore core,
      DiagnosticsReporter diagnostics,
      Runnable printBindings,
      Runnable printTestsInfo,
      Runnable printTestsOverview,
      Runnable toggleProfile,
      Runnable printInputs,
      AddAllHandler addAllHandler,
      GenericCmdHandler genericCmdHandler,
      AddMotorHandler addMotorHandler) {
    return new RobotLocalCommandContext() {
      @Override
      public void enqueuePrint(String text) {
        BringupPrinter.enqueue(text);
      }

      @Override
      public void handleAddMotor(boolean addMotorNow) {
        if (addMotorHandler != null) {
          addMotorHandler.handleAddMotor(addMotorNow);
        } else {
          core.handleAdd(addMotorNow);
        }
      }

      @Override
      public void handleAddAll(boolean addAllNow) {
        if (addAllHandler != null) {
          addAllHandler.handleAddAll(addAllNow);
        } else {
          core.handleAddAll(addAllNow);
        }
      }

      @Override
      public void handleGenericCmd(boolean genericCmdNow) {
        if (genericCmdHandler != null) {
          genericCmdHandler.handleGenericCmd(genericCmdNow);
        } else {
          core.handleAddAll(genericCmdNow);
        }
      }

      @Override
      public void printState() {
        core.handlePrint(true);
      }

      @Override
      public void printHealth() {
        core.handleHealth(true);
      }

      @Override
      public void printCANCoder() {
        core.handleCANCoder(true);
      }

      @Override
      public void selectPreviousTest() {
        core.selectPrevBringupTest();
      }

      @Override
      public void selectNextTest() {
        core.selectNextBringupTest();
      }

      @Override
      public Boolean toggleSelectedTestEnabled() {
        return core.toggleSelectedBringupTestEnabled();
      }

      @Override
      public void runSelectedTest() {
        core.runSelectedBringupTest();
      }

      @Override
      public void runAllTests() {
        core.runAllBringupTests();
      }

      @Override
      public void printBindings() {
        if (printBindings != null) {
          printBindings.run();
        }
      }

      @Override
      public void printTestsInfo() {
        if (printTestsInfo != null) {
          printTestsInfo.run();
        }
      }

      @Override
      public void printTestsOverview() {
        if (printTestsOverview != null) {
          printTestsOverview.run();
        }
      }

      @Override
      public void printNextTest() {
        core.printNextTestReport();
      }

      @Override
      public void printCanDiagnostics() {
        if (diagnostics == null) {
          return;
        }
        String report = diagnostics.buildCanDiagnosticsReportIfReady();
        if (report != null) {
          core.requestTextReport(report, REPORT_BATCH_SIZE);
        }
      }

      @Override
      public void dumpReport() {
        if (diagnostics == null) {
          return;
        }
        String json = diagnostics.buildReportJsonForDump();
        String wrapped = ReportTextUtil.wrapLongLine(json, DUMP_WRAP_COLUMNS);
        core.requestTextReport(wrapped, REPORT_BATCH_SIZE);
        if (diagnostics.writeReportJsonToFile(json)) {
          core.requestTextReport(
              MESSAGE_REPORT_WRITE_OK_PREFIX + diagnostics.getReportPath(),
              REPORT_BATCH_SIZE);
        } else {
          core.requestTextReport(MESSAGE_REPORT_WRITE_FAILED, REPORT_BATCH_SIZE);
        }
      }

      @Override
      public void clearAllFaults() {
        core.clearAllFaults();
      }

      @Override
      public void runCanSweep() {
        core.runCanPingSweep();
      }

      @Override
      public void toggleProfile() {
        if (toggleProfile != null) {
          toggleProfile.run();
        }
      }

      @Override
      public void toggleDashboard() {}

      @Override
      public void printInputs() {
        if (printInputs != null) {
          printInputs.run();
        }
      }

      @Override
      public void updateReportsAndTests(boolean runHeld) {
        core.updateReports();
        core.updateTests(runHeld);
      }
    };
  }
}
