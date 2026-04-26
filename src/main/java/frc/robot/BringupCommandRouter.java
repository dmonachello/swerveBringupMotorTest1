package frc.robot;

import frc.robot.input.BindingsManager;

/**
 * NAME
 *   BringupCommandRouter - Map bindings to bringup actions.
 *
 * DESCRIPTION
 *   Applies controller bindings to runtime actions, report requests, and
 *   diagnostics outputs.
 */
public final class BringupCommandRouter {
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
   *   AddMotorHandler - Hook for add-next activation behavior.
   */
  public interface AddMotorHandler {
    void handleAddMotor(boolean addMotorNow);
  }

  /**
   * NAME
   *   applyCommon - Apply common binding-driven actions.
   *
   * PARAMETERS
   *   bind - Current binding state snapshot.
   *   runtime - Shared runtime/action owner.
   *   printBindings - Callback to print bindings.
   *   printTestsInfo - Callback to print tests info.
   *   printTestsOverview - Callback to print tests overview.
   *   runHeld - Whether run is currently held.
   *
   * SIDE EFFECTS
   *   Enqueues prints, triggers device actions, and updates reports/tests.
   *
   * RETURNS
   *   Summary of binding-driven actions for downstream safety handling.
   */
  public static CommonResult applyCommon(
      BindingsManager.BindingState bind,
      BringupRuntime runtime,
      Runnable printBindings,
      Runnable printTestsInfo,
      Runnable printTestsOverview,
      boolean runHeld,
      AddAllHandler addAllHandler,
      AddMotorHandler addMotorHandler) {
    CommonResult result = new CommonResult();

    if (bind.pressed("addMotor")) {
      BringupPrinter.enqueue("Command: addMotor");
      if (addMotorHandler != null) {
        addMotorHandler.handleAddMotor(true);
      } else {
        runtime.addMotor(true);
      }
    } else {
      if (addMotorHandler != null) {
        addMotorHandler.handleAddMotor(false);
      } else {
        runtime.addMotor(false);
      }
    }
    if (bind.pressed("addAll")) {
      BringupPrinter.enqueue("Command: addAll");
      if (addAllHandler != null) {
        addAllHandler.handleAddAll(true);
      } else {
        runtime.addAllDevices(true);
      }
    } else {
      if (addAllHandler != null) {
        addAllHandler.handleAddAll(false);
      } else {
        runtime.addAllDevices(false);
      }
    }
    DiagnosticsReporter diagnostics = runtime.getDiagnostics();
    runtime.handlePrint(bind.pressed("printState"));
    runtime.handleHealth(bind.pressed("printHealth"));
    runtime.handleCANCoder(runHeld ? false : bind.pressed("printCANcoder"));

    if (bind.pressed("selectTestPrev")) {
      runtime.selectPreviousTest();
      if (printTestsOverview != null) {
        printTestsOverview.run();
      }
    }
    if (bind.pressed("selectTestNext")) {
      runtime.selectNextTest();
      if (printTestsOverview != null) {
        printTestsOverview.run();
      }
    }
    if (bind.pressed("toggleTest")) {
      result.toggledTestEnabled = runtime.toggleSelectedTestEnabled();
      if (printTestsOverview != null) {
        printTestsOverview.run();
      }
    }
    if (bind.pressed("runTest")) {
      BringupPrinter.enqueue("Command: runTest");
      runtime.runSelectedTest();
      result.runTestPressed = true;
    }
    if (bind.pressed("runAllTests")) {
      BringupPrinter.enqueue("Command: runAllTests");
      runtime.runAllTests();
      result.runAllPressed = true;
    }

    if (bind.pressed("printBindings") && printBindings != null) {
      printBindings.run();
    }
    if (bind.pressed("printTestsInfo") && printTestsInfo != null) {
      printTestsInfo.run();
    }
    if (bind.pressed("printTestsOverview") && printTestsOverview != null) {
      printTestsOverview.run();
    }
    if (bind.pressed("printNextTest")) {
      runtime.printNextTestReport();
    }

    if (diagnostics != null) {
      if (bind.pressed("printNTdiag")) {
        String report = diagnostics.buildNetworkDiagnosticsReportIfReady();
        if (report != null) {
          runtime.requestTextReport(report, 4);
        }
      }
      if (bind.pressed("printCANdiag")) {
        String report = diagnostics.buildCanDiagnosticsReportIfReady();
        if (report != null) {
          runtime.requestTextReport(report, 4);
        }
      }
      if (bind.pressed("dumpReport")) {
        String json = diagnostics.buildReportJsonForDump();
        String wrapped = ReportTextUtil.wrapLongLine(json, 120);
        runtime.requestTextReport(wrapped, 4);
        if (diagnostics.writeReportJsonToFile(json)) {
          runtime.requestTextReport("Wrote CAN report JSON to " + diagnostics.getReportPath(), 4);
        } else {
          runtime.requestTextReport("Failed to write CAN report JSON.", 4);
        }
      }
    }

    if (bind.pressed("clearFaults")) {
      BringupPrinter.enqueue("Command: clearFaults");
      runtime.clearAllFaults();
      BringupPrinter.enqueue("Cleared device faults (current + sticky).");
    }
    if (bind.pressed("canSweep")) {
      BringupPrinter.enqueue("Command: canSweep");
      runtime.runCanPingSweep();
    }

    runtime.updateReportsAndTests(runHeld || bind.held("runTest"));
    return result;
  }

  /**
   * NAME
   *   applyCommon - Legacy core-based compatibility path.
   *
   * DESCRIPTION
   *   Supports the older Robot entry point. RobotV2 and UI/CLI paths use the
   *   BringupRuntime overload so they share current runtime ownership.
   */
  public static CommonResult applyCommon(
      BindingsManager.BindingState bind,
      BringupCore core,
      DiagnosticsReporter diagnostics,
      Runnable printBindings,
      Runnable printTestsInfo,
      Runnable printTestsOverview,
      boolean runHeld,
      AddAllHandler addAllHandler,
      AddMotorHandler addMotorHandler) {
    CommonResult result = new CommonResult();

    if (bind.pressed("addMotor")) {
      BringupPrinter.enqueue("Command: addMotor");
      if (addMotorHandler != null) {
        addMotorHandler.handleAddMotor(true);
      } else {
        core.handleAdd(true);
      }
    } else if (addMotorHandler != null) {
      addMotorHandler.handleAddMotor(false);
    } else {
      core.handleAdd(false);
    }
    if (bind.pressed("addAll")) {
      BringupPrinter.enqueue("Command: addAll");
      if (addAllHandler != null) {
        addAllHandler.handleAddAll(true);
      } else {
        core.handleAddAll(true);
      }
    } else if (addAllHandler != null) {
      addAllHandler.handleAddAll(false);
    } else {
      core.handleAddAll(false);
    }
    core.handlePrint(bind.pressed("printState"));
    core.handleHealth(bind.pressed("printHealth"));
    core.handleCANCoder(runHeld ? false : bind.pressed("printCANcoder"));

    if (bind.pressed("selectTestPrev")) {
      core.selectPrevBringupTest();
      if (printTestsOverview != null) {
        printTestsOverview.run();
      }
    }
    if (bind.pressed("selectTestNext")) {
      core.selectNextBringupTest();
      if (printTestsOverview != null) {
        printTestsOverview.run();
      }
    }
    if (bind.pressed("toggleTest")) {
      result.toggledTestEnabled = core.toggleSelectedBringupTestEnabled();
      if (printTestsOverview != null) {
        printTestsOverview.run();
      }
    }
    if (bind.pressed("runTest")) {
      BringupPrinter.enqueue("Command: runTest");
      core.runSelectedBringupTest();
      result.runTestPressed = true;
    }
    if (bind.pressed("runAllTests")) {
      BringupPrinter.enqueue("Command: runAllTests");
      core.runAllBringupTests();
      result.runAllPressed = true;
    }

    if (bind.pressed("printBindings") && printBindings != null) {
      printBindings.run();
    }
    if (bind.pressed("printTestsInfo") && printTestsInfo != null) {
      printTestsInfo.run();
    }
    if (bind.pressed("printTestsOverview") && printTestsOverview != null) {
      printTestsOverview.run();
    }
    if (bind.pressed("printNextTest")) {
      core.printNextTestReport();
    }

    if (diagnostics != null) {
      if (bind.pressed("printNTdiag")) {
        String report = diagnostics.buildNetworkDiagnosticsReportIfReady();
        if (report != null) {
          core.requestTextReport(report, 4);
        }
      }
      if (bind.pressed("printCANdiag")) {
        String report = diagnostics.buildCanDiagnosticsReportIfReady();
        if (report != null) {
          core.requestTextReport(report, 4);
        }
      }
      if (bind.pressed("dumpReport")) {
        String json = diagnostics.buildReportJsonForDump();
        String wrapped = ReportTextUtil.wrapLongLine(json, 120);
        core.requestTextReport(wrapped, 4);
        if (diagnostics.writeReportJsonToFile(json)) {
          core.requestTextReport("Wrote CAN report JSON to " + diagnostics.getReportPath(), 4);
        } else {
          core.requestTextReport("Failed to write CAN report JSON.", 4);
        }
      }
    }

    if (bind.pressed("clearFaults")) {
      BringupPrinter.enqueue("Command: clearFaults");
      core.clearAllFaults();
      BringupPrinter.enqueue("Cleared device faults (current + sticky).");
    }
    if (bind.pressed("canSweep")) {
      BringupPrinter.enqueue("Command: canSweep");
      core.runCanPingSweep();
    }

    core.updateReports();
    core.updateTests(runHeld || bind.held("runTest"));
    return result;
  }
}
