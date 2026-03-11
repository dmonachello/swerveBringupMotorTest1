package frc.robot.tests;

/**
 * NAME
 *   BringupTest - Interface for bringup test state machines.
 *
 * DESCRIPTION
 *   Defines lifecycle hooks and metadata required by the bringup test runner.
 */
public interface BringupTest {
  /**
   * NAME
   *   getName - Return the test name.
   */
  String getName();

  /**
   * NAME
   *   isEnabled - Return whether the test is enabled.
   */
  boolean isEnabled();

  /**
   * NAME
   *   setEnabled - Enable or disable the test.
   */
  default void setEnabled(boolean enabled) {}

  /**
   * NAME
   *   isRunning - Return whether the test is currently active.
   */
  boolean isRunning();

  /**
   * NAME
   *   isFinished - Return whether the test has completed.
   */
  boolean isFinished();

  /**
   * NAME
   *   getResult - Return the final test result.
   */
  BringupTestResult getResult();

  /**
   * NAME
   *   getStatus - Return a human-readable status string.
   */
  String getStatus();

  /**
   * NAME
   *   start - Start the test.
   *
   * PARAMETERS
   *   context - Test context with device access.
   *   nowSec - Current time in seconds.
   *
   * RETURNS
   *   True if the test started successfully.
   */
  boolean start(BringupTestContext context, double nowSec);

  /**
   * NAME
   *   update - Update the test state.
   *
   * PARAMETERS
   *   context - Test context with device access.
   *   nowSec - Current time in seconds.
   */
  void update(BringupTestContext context, double nowSec);

  /**
   * NAME
   *   stop - Stop the test and clean up.
   *
   * PARAMETERS
   *   context - Test context with device access.
   */
  void stop(BringupTestContext context);

  /**
   * NAME
   *   onHoldSignal - Inform the test of hold-to-run input.
   */
  default void onHoldSignal(boolean held) {}

  /**
   * NAME
   *   getMotorKeys - Return motor keys used by the test.
   */
  default java.util.List<String> getMotorKeys() {
    return java.util.Collections.emptyList();
  }

  /**
   * NAME
   *   getDisplayName - Return a user-facing display name.
   */
  default String getDisplayName() {
    return getName();
  }
}
