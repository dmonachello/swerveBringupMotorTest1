package frc.robot;

import frc.robot.input.BindingsManager;

public final class BringupCommandRouter {
  private BringupCommandRouter() {}

  public static void applyCommon(
      BindingsManager.BindingState bind,
      BringupCore core,
      DiagnosticsReporter diagnostics,
      Runnable printBindings,
      boolean runHeld) {

    core.handleAdd(bind.pressed("addMotor"));
    core.handleAddAll(bind.pressed("addAll"));
    core.handlePrint(bind.pressed("printState"));
    core.handleHealth(bind.pressed("printHealth"));
    core.handleCANCoder(runHeld ? false : bind.pressed("printCANcoder"));

    if (bind.pressed("selectTestPrev")) {
      core.selectPrevBringupTest();
    }
    if (bind.pressed("selectTestNext")) {
      core.selectNextBringupTest();
    }
    if (bind.pressed("toggleTest")) {
      core.toggleSelectedBringupTestEnabled();
    }
    if (bind.pressed("runTest")) {
      core.runSelectedBringupTest();
    }
    if (bind.pressed("runAllTests")) {
      core.runAllBringupTests();
    }

    if (bind.pressed("printBindings") && printBindings != null) {
      printBindings.run();
    }

    if (diagnostics != null) {
      if (bind.pressed("printNTdiag")) {
        diagnostics.printNetworkDiagnostics();
      }
      if (bind.pressed("printCANdiag")) {
        diagnostics.printCanDiagnosticsReport();
      }
      if (bind.pressed("dumpReport")) {
        diagnostics.dumpReportJsonToConsoleAndFile();
      }
    }

    if (bind.pressed("clearFaults")) {
      core.clearAllFaults();
      BringupPrinter.enqueue("Cleared device faults (current + sticky).");
    }

    core.updateTests(runHeld || bind.held("runTest"));
  }
}
