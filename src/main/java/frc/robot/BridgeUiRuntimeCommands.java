package frc.robot;

import java.util.Set;

/**
 * NAME
 *   BridgeUiRuntimeCommands - Runtime/system command family executor.
 */
final class BridgeUiRuntimeCommands implements BridgeUiCommandDispatcher.CommandFamily {

  private static final String CMD_ADD_MOTOR = "addMotor";
  private static final String CMD_ADD_ALL = "addAll";
  private static final String CMD_TOGGLE_DASHBOARD = "toggleDashboard";
  private static final String CMD_CLEAR_FAULTS = "clearFaults";
  private static final String CMD_CLEAR_STOP_LATCH = "clearStopLatch";
  private static final String CMD_CAN_SWEEP = "canSweep";

  private static final Set<String> COMMANDS = Set.of(
      CMD_ADD_MOTOR,
      CMD_ADD_ALL,
      CMD_TOGGLE_DASHBOARD,
      CMD_CLEAR_FAULTS,
      CMD_CLEAR_STOP_LATCH,
      CMD_CAN_SWEEP);

  private static final String MESSAGE_PROFILE_INACTIVE_ADD =
      "Profile inactive. Use profileActivate before adding motors.";
  private static final String MESSAGE_PROFILE_STAGE_FAILED_PREFIX =
      "Failed to stage selected profile for incremental bringup: ";
  private static final String MESSAGE_ADD_ALL =
      "Instantiated enabled active-group devices only.";
  private static final String MESSAGE_CLEAR_FAULTS = "Cleared device faults (current + sticky).";
  private static final String MESSAGE_STOP_LATCH_CLEARED = "Stop latch cleared.";
  private static final String MESSAGE_STOP_LATCH_NOT_ACTIVE = "Stop latch not active.";
  private static final String MESSAGE_CAN_SWEEP = "Command: canSweep (UI)";
  private static final String MESSAGE_DASHBOARD_FMT = "Dashboard/Shuffleboard updates: %s";
  private static final String TEXT_ON = "ON";
  private static final String TEXT_OFF = "OFF";

  /**
   * NAME
   *   Dependencies - Narrow dependency contract for runtime commands.
   */
  interface Dependencies {
    String stageSelectedProfileForBringup();

    boolean isProfileActive();

    void addNextMotorCommand();

    void addAllDevicesCommand();

    void setDashboardUpdatesEnabled(boolean enabled);

    boolean isDashboardUpdatesEnabled();

    void applyDashboardUpdateState();

    void enqueuePrint(String text);

    void clearAllFaults();

    boolean clearStopLatchFromUi(String reason);

    String buildCanPingSweepReportText();

    void requestTextReport(String text, int batchSize);
  }

  private final Dependencies dependencies;

  BridgeUiRuntimeCommands(Dependencies dependencies) {
    this.dependencies = dependencies;
  }

  @Override
  public boolean handles(String commandName) {
    return COMMANDS.contains(commandName);
  }

  @Override
  public BridgeUiCommandResult execute(
      BridgeUiIngressPolicy.Ingress ingress,
      double cmdTs,
      boolean isTcp) {
    BridgeUiCommandResult result = new BridgeUiCommandResult();
    String commandName = ingress.name;
    switch (commandName) {
      case CMD_ADD_MOTOR:
        ensureBringupProfileStaged(result);
        if (!result.ok) {
          break;
        }
        dependencies.addNextMotorCommand();
        result.message = "Add motor.";
        break;
      case CMD_ADD_ALL:
        ensureBringupProfileStaged(result);
        if (!result.ok) {
          break;
        }
        dependencies.addAllDevicesCommand();
        result.message = MESSAGE_ADD_ALL;
        break;
      case CMD_TOGGLE_DASHBOARD:
        dependencies.setDashboardUpdatesEnabled(!dependencies.isDashboardUpdatesEnabled());
        dependencies.applyDashboardUpdateState();
        dependencies.enqueuePrint(String.format(
            MESSAGE_DASHBOARD_FMT,
            dependencies.isDashboardUpdatesEnabled() ? TEXT_ON : TEXT_OFF));
        break;
      case CMD_CLEAR_FAULTS:
        dependencies.clearAllFaults();
        dependencies.enqueuePrint(MESSAGE_CLEAR_FAULTS);
        break;
      case CMD_CLEAR_STOP_LATCH:
        result.message = dependencies.clearStopLatchFromUi("uiClear")
            ? MESSAGE_STOP_LATCH_CLEARED
            : MESSAGE_STOP_LATCH_NOT_ACTIVE;
        result.outText = result.message;
        break;
      case CMD_CAN_SWEEP:
        dependencies.enqueuePrint(MESSAGE_CAN_SWEEP);
        String sweepReport = dependencies.buildCanPingSweepReportText();
        dependencies.requestTextReport(sweepReport, 6);
        result.outText = sweepReport;
        break;
      default:
        result.ok = false;
        result.message = "Unknown command: " + commandName;
        break;
    }
    return result;
  }

  private void ensureBringupProfileStaged(BridgeUiCommandResult result) {
    if (!dependencies.isProfileActive()) {
      String error = dependencies.stageSelectedProfileForBringup();
      if (error != null && !error.isBlank()) {
        result.ok = false;
        result.message = MESSAGE_PROFILE_STAGE_FAILED_PREFIX + error;
        result.outText = result.message;
        return;
      }
    }
  }
}
