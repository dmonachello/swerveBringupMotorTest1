package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalReportCommandGroup - Report/diagnostic command source file.
 *
 * DESCRIPTION
 *   Owns the Java command behavior for the direct report commands that simply
 *   call host-side report emitters.
 */
final class RobotLocalReportCommandGroup {
  RobotLocalCommand printState() {
    return new RobotLocalHostVoidCommand(false, "", "", "printState", "Printed state.");
  }

  RobotLocalCommand printHealth() {
    return new RobotLocalHostVoidCommand(false, "", "", "printHealth", "Printed health.");
  }

  RobotLocalCommand printCANcoder() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "printCANCoder",
        "Printed CANcoder report.");
  }

  RobotLocalCommand printInputs() {
    return new RobotLocalHostVoidCommand(false, "", "", "printInputs", "Printed inputs.");
  }

  RobotLocalCommand printBindings() {
    return new RobotLocalHostVoidCommand(false, "", "", "printBindings", "Printed bindings.");
  }

  RobotLocalCommand printTestsInfo() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "printTestsInfo",
        "Printed tests info.");
  }

  RobotLocalCommand printTestsOverview() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "printTestsOverview",
        "Printed tests overview.");
  }

  RobotLocalCommand printSelectedTestSource() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "printSelectedTestSource",
        "Printed selected test source.");
  }

  RobotLocalCommand printNextTest() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "printNextTest",
        "Printed next test.");
  }

  RobotLocalCommand printNtDiagnostics() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "printNtDiagnostics",
        "Printed NT diagnostics.");
  }

  RobotLocalCommand printCanDiagnostics() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "printCanDiagnostics",
        "Printed CAN diagnostics.");
  }

  RobotLocalCommand activePresenceProbe() {
    return new RobotLocalCommand() {
      private static final String MESSAGE_RUNTIME_INACTIVE =
          "Runtime inactive. Click Runtime Activate.";

      @Override
      public RobotLocalExecutionResult execute(RobotLocalCommandParams params) {
        RobotLocalExecutionResult result = params.host().runActivePresenceProbe();
        if (result != null) {
          return result;
        }
        return RobotLocalExecutionResult.failed(MESSAGE_RUNTIME_INACTIVE);
      }
    };
  }

  RobotLocalCommand dumpReport() {
    return new RobotLocalHostVoidCommand(false, "", "", "dumpReport", "Dumped report.");
  }
}
