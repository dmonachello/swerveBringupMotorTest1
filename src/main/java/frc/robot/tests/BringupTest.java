package frc.robot.tests;

public interface BringupTest {
  String getName();
  boolean isEnabled();
  default void setEnabled(boolean enabled) {}
  boolean isRunning();
  boolean isFinished();
  BringupTestResult getResult();
  String getStatus();
  boolean start(BringupTestContext context, double nowSec);
  void update(BringupTestContext context, double nowSec);
  void stop(BringupTestContext context);

  default void onHoldSignal(boolean held) {}

  default java.util.List<String> getMotorKeys() {
    return java.util.Collections.emptyList();
  }

  default String getDisplayName() {
    return getName();
  }
}
