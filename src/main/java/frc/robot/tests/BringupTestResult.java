package frc.robot.tests;

/**
 * NAME
 *   BringupTestResult - Result states for bringup tests.
 */
public enum BringupTestResult {
  NOT_RUN,
  UNRUNNABLE,
  RUNNING,
  INTERRUPTED,
  PASS_SENSOR_PROVEN,
  PASS,
  FAIL_NO_SENSOR_RESPONSE,
  FAIL_ABORT_CONDITION,
  FAIL_REQUIRE_NOT_MET,
  FAIL_UNTIL_TIMEOUT,
  FAIL_SET_FALLBACK_ACTIVE,
  FAIL_DEVICE_NOT_FOUND,
  FAIL_UNSUPPORTED_SIGNAL,
  FAIL_RUNTIME_COMMUNICATION,
  FAIL_CLEAR_FAULTS,
  FAIL

  ;

  public boolean isPassing() {
    return this == PASS || this == PASS_SENSOR_PROVEN;
  }

  public boolean isInterrupted() {
    return this == INTERRUPTED;
  }

  public boolean isTerminal() {
    return this != NOT_RUN && this != RUNNING;
  }
}
