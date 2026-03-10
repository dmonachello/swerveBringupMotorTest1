package frc.robot;

import frc.robot.input.BindingsManager;
import frc.robot.diag.report.ReportTextUtil;

public final class BringupCommandRouter {
  private BringupCommandRouter() {}

  public static void applyCommon(
      BindingsManager.BindingState bind,
      BringupCore core,
      DiagnosticsReporter diagnostics,
      Runnable printBindings,
      Runnable printTestsInfo,
      Runnable printTestsOverview,
      boolean runHeld) {

    if (bind.pressed("addMotor")) {
      BringupPrinter.enqueue("Command: addMotor");
      core.handleAdd(true);
    } else {
      core.handleAdd(false);
    }
    if (bind.pressed("addAll")) {
      BringupPrinter.enqueue("Command: addAll");
      core.handleAddAll(true);
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
      core.toggleSelectedBringupTestEnabled();
      if (printTestsOverview != null) {
        printTestsOverview.run();
      }
    }
    if (bind.pressed("runTest")) {
      BringupPrinter.enqueue("Command: runTest");
      core.runSelectedBringupTest();
    }
    if (bind.pressed("runAllTests")) {
      BringupPrinter.enqueue("Command: runAllTests");
      core.runAllBringupTests();
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
  }
}
