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
  private static final String CMD_FIXED_SPEED_25 = "fixedSpeed25";
  private static final String CMD_FIXED_SPEED_50 = "fixedSpeed50";
  private static final String CMD_FIXED_SPEED_75 = "fixedSpeed75";
  private static final String CMD_FIXED_SPEED_100 = "fixedSpeed100";

  private static final Set<String> COMMANDS = Set.of(
      CMD_ADD_MOTOR,
      CMD_ADD_ALL,
      CMD_TOGGLE_DASHBOARD,
      CMD_CLEAR_FAULTS,
      CMD_CLEAR_STOP_LATCH,
      CMD_CAN_SWEEP,
      CMD_FIXED_SPEED_25,
      CMD_FIXED_SPEED_50,
      CMD_FIXED_SPEED_75,
      CMD_FIXED_SPEED_100);

  private static final String MESSAGE_PROFILE_INACTIVE_ADD =
      "Profile inactive. Use profileActivate before adding motors.";
  private static final String MESSAGE_ADD_ALL =
      "Instantiated all configured devices. Use active add to populate active-group.";
  private static final String MESSAGE_CLEAR_FAULTS = "Cleared device faults (current + sticky).";
  private static final String MESSAGE_STOP_LATCH_CLEARED = "Stop latch cleared.";
  private static final String MESSAGE_STOP_LATCH_NOT_ACTIVE = "Stop latch not active.";
  private static final String MESSAGE_CAN_SWEEP = "Command: canSweep (UI)";
  private static final String MESSAGE_DASHBOARD_FMT = "Dashboard/Shuffleboard updates: %s";
  private static final String TEXT_ON = "ON";
  private static final String TEXT_OFF = "OFF";
  private static final String MESSAGE_FIXED_SPEED_OFF = "Fixed speed: OFF.";
  private static final String MESSAGE_FIXED_SPEED_FMT = "Fixed speed: %.2f";

  private static final double SPEED_25 = 0.25;
  private static final double SPEED_50 = 0.50;
  private static final double SPEED_75 = 0.75;
  private static final double SPEED_100 = 1.00;
  private static final double TOGGLE_EPSILON = 1e-6;

  /**
   * NAME
   *   Dependencies - Narrow dependency contract for runtime commands.
   */
  interface Dependencies {
    void prepareActivationForSelectedProfile();

    void activateSelectedProfile();

    boolean isProfileActive();

    void runProfileActivateAction();

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

    double getUiFixedSpeed();

    void setUiFixedSpeed(double speed);
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
        ensureActiveProfile(result);
        if (!result.ok) {
          break;
        }
        dependencies.addNextMotorCommand();
        result.message = "Add motor.";
        break;
      case CMD_ADD_ALL:
        ensureActiveProfile(result);
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
      case CMD_FIXED_SPEED_25:
        applyFixedSpeed(SPEED_25, result);
        break;
      case CMD_FIXED_SPEED_50:
        applyFixedSpeed(SPEED_50, result);
        break;
      case CMD_FIXED_SPEED_75:
        applyFixedSpeed(SPEED_75, result);
        break;
      case CMD_FIXED_SPEED_100:
        applyFixedSpeed(SPEED_100, result);
        break;
      default:
        result.ok = false;
        result.message = "Unknown command: " + commandName;
        break;
    }
    return result;
  }

  private void ensureActiveProfile(BridgeUiCommandResult result) {
    if (!dependencies.isProfileActive()) {
      dependencies.prepareActivationForSelectedProfile();
      dependencies.activateSelectedProfile();
      if (dependencies.isProfileActive()) {
        dependencies.runProfileActivateAction();
      }
    }
    if (!dependencies.isProfileActive()) {
      result.ok = false;
      result.message = MESSAGE_PROFILE_INACTIVE_ADD;
      result.outText = result.message;
    }
  }

  private void applyFixedSpeed(double speed, BridgeUiCommandResult result) {
    double updated = toggleFixedSpeed(dependencies.getUiFixedSpeed(), speed);
    dependencies.setUiFixedSpeed(updated);
    result.message = buildFixedSpeedMessage(updated);
  }

  private double toggleFixedSpeed(double current, double requested) {
    if (Double.isNaN(current)) {
      return requested;
    }
    if (Math.abs(current - requested) < TOGGLE_EPSILON) {
      return Double.NaN;
    }
    return requested;
  }

  private String buildFixedSpeedMessage(double speed) {
    if (Double.isNaN(speed)) {
      return MESSAGE_FIXED_SPEED_OFF;
    }
    return String.format(MESSAGE_FIXED_SPEED_FMT, speed);
  }
}
