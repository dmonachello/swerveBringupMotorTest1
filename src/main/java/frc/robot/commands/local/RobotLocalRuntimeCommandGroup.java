package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalRuntimeCommandGroup - Runtime/system command source file.
 *
 * DESCRIPTION
 *   Owns the Java command behavior for runtime-oriented robot-local commands.
 *   The central registry references these commands but does not own their
 *   behavior directly.
 */
final class RobotLocalRuntimeCommandGroup {
  private static final String REASON_PROFILE_ACTIVATE = "robotLocalCommand";
  private static final String MESSAGE_PROFILE_INACTIVE_ADD =
      "Profile inactive. Activate a profile before adding devices.";

  RobotLocalCommand addMotor() {
    return new RobotLocalHostVoidCommand(
        true,
        REASON_PROFILE_ACTIVATE,
        MESSAGE_PROFILE_INACTIVE_ADD,
        "addNextMotorCommand",
        "Add motor.");
  }

  RobotLocalCommand addAll() {
    return new RobotLocalHostVoidCommand(
        true,
        REASON_PROFILE_ACTIVATE,
        MESSAGE_PROFILE_INACTIVE_ADD,
        "addAllDevicesCommand",
        "Instantiated all configured devices.");
  }

  RobotLocalCommand genericCmd() {
    return new RobotLocalHostVoidCommand(
        true,
        REASON_PROFILE_ACTIVATE,
        MESSAGE_PROFILE_INACTIVE_ADD,
        "runGenericCommand",
        "Ran genericCmd.");
  }

  RobotLocalCommand clearFaults() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "clearAllFaults",
        "Cleared device faults (current + sticky).");
  }

  RobotLocalCommand clearStopLatch() {
    return new RobotLocalClearStopLatchCommand();
  }

  RobotLocalCommand canSweep() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "runCanSweep",
        "Command: canSweep");
  }

  RobotLocalCommand toggleDashboard() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "toggleDashboard",
        "Toggled dashboard updates.");
  }

  RobotLocalCommand profileToggle() {
    return new RobotLocalHostVoidCommand(
        false,
        "",
        "",
        "toggleProfile",
        "Selected next profile.");
  }

  RobotLocalCommand stop() {
    return new RobotLocalLegacyUiCommandGroup();
  }
}
