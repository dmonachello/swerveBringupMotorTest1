package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;

import frc.robot.telemetry.SampledTelemetrySampler;
import frc.robot.tests.BringupTest;
import frc.robot.tests.BringupTestContext;
import frc.robot.tests.BringupTestResult;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   BringupCoreSelectedTestTest - Tests for selected-test preservation during runtime rebuilds.
 */
class BringupCoreSelectedTestTest {

  @Test
  void resolveSelectedTestIndexPreservesMatchingRawName() {
    List<BringupTest> tests =
        List.of(
            fakeTest("test_minimal_25_9_spark25_leftY"),
            fakeTest("falcon9_move_150_rotations"),
            fakeTest("newTests_123"));

    assertEquals(2, BringupCore.resolveSelectedTestIndex(tests, "newTests_123"));
  }

  @Test
  void resolveSelectedTestIndexFallsBackToFirstWhenSelectionMissing() {
    List<BringupTest> tests =
        List.of(
            fakeTest("test_minimal_25_9_spark25_leftY"),
            fakeTest("falcon9_move_150_rotations"),
            fakeTest("newTests_123"));

    assertEquals(0, BringupCore.resolveSelectedTestIndex(tests, "missing_test"));
  }

  @Test
  void resolveSelectedTestIndexPreservesFallbackIndexWhenSelectionMissing() {
    List<BringupTest> tests =
        List.of(
            fakeTest("test_minimal_25_9_spark25_leftY"),
            fakeTest("falcon9_move_150_rotations"),
            fakeTest("newTests_123"));

    assertEquals(2, BringupCore.resolveSelectedTestIndex(tests, "missing_test", 2));
  }

  @Test
  void resolveSelectedTestIndexReturnsMissingWhenNoTestsExist() {
    assertEquals(-1, BringupCore.resolveSelectedTestIndex(List.of(), "newTests_123"));
  }

  @Test
  void resetStatePreservesSelectedBringupTestName() throws Exception {
    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    List<BringupTest> tests =
        List.of(
            fakeTest("test_minimal_25_9_spark25_leftY"),
            fakeTest("falcon9_move_150_rotations"),
            fakeTest("newTests_123"));

    Field bringupTestsField = BringupCore.class.getDeclaredField("bringupTests");
    bringupTestsField.setAccessible(true);
    @SuppressWarnings("unchecked")
    List<BringupTest> bringupTests = (List<BringupTest>) bringupTestsField.get(core);
    bringupTests.clear();
    bringupTests.addAll(tests);

    Field selectedTestIndexField = BringupCore.class.getDeclaredField("selectedTestIndex");
    selectedTestIndexField.setAccessible(true);
    selectedTestIndexField.setInt(core, 2);

    core.resetState("test-reset");

    assertEquals("newTests_123", core.getSelectedBringupTestName());
  }

  @Test
  void refreshSelectableTestsFallsBackToStoredSelectionHint() throws Exception {
    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    List<BringupTest> tests =
        List.of(
            fakeTest("test_minimal_25_9_spark25_leftY"),
            fakeTest("falcon9_move_150_rotations"),
            fakeTest("newTests_123"));

    Field bringupTestsField = BringupCore.class.getDeclaredField("bringupTests");
    bringupTestsField.setAccessible(true);
    @SuppressWarnings("unchecked")
    List<BringupTest> bringupTests = (List<BringupTest>) bringupTestsField.get(core);
    bringupTests.clear();
    bringupTests.addAll(tests);

    Field selectableTestsField = BringupCore.class.getDeclaredField("selectableTests");
    selectableTestsField.setAccessible(true);
    @SuppressWarnings("unchecked")
    List<BringupTest> selectableTests = (List<BringupTest>) selectableTestsField.get(core);
    selectableTests.clear();

    Field selectedTestIndexField = BringupCore.class.getDeclaredField("selectedTestIndex");
    selectedTestIndexField.setAccessible(true);
    selectedTestIndexField.setInt(core, -1);

    Field selectedTestNameHintField = BringupCore.class.getDeclaredField("selectedTestNameHint");
    selectedTestNameHintField.setAccessible(true);
    selectedTestNameHintField.set(core, "newTests_123");

    Method refreshSelectableTests =
        BringupCore.class.getDeclaredMethod("refreshSelectableTests", String.class);
    refreshSelectableTests.setAccessible(true);
    refreshSelectableTests.invoke(core, "");

    assertEquals("newTests_123", core.getSelectedBringupTestName());
  }

  @Test
  void refreshSelectableTestsPreservesCurrentIndexWhenPreferredSelectionMissing() throws Exception {
    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    List<BringupTest> tests =
        List.of(
            fakeTest("test_minimal_25_9_spark25_leftY"),
            fakeTest("falcon9_move_150_rotations"),
            fakeTest("newTests_123"));

    Field bringupTestsField = BringupCore.class.getDeclaredField("bringupTests");
    bringupTestsField.setAccessible(true);
    @SuppressWarnings("unchecked")
    List<BringupTest> bringupTests = (List<BringupTest>) bringupTestsField.get(core);
    bringupTests.clear();
    bringupTests.addAll(tests);

    Field selectedTestIndexField = BringupCore.class.getDeclaredField("selectedTestIndex");
    selectedTestIndexField.setAccessible(true);
    selectedTestIndexField.setInt(core, 2);

    Field selectedTestNameHintField = BringupCore.class.getDeclaredField("selectedTestNameHint");
    selectedTestNameHintField.setAccessible(true);
    selectedTestNameHintField.set(core, "");

    Method refreshSelectableTests =
        BringupCore.class.getDeclaredMethod("refreshSelectableTests", String.class);
    refreshSelectableTests.setAccessible(true);
    refreshSelectableTests.invoke(core, "missing_test");

    assertEquals("newTests_123", core.getSelectedBringupTestName());
  }

  private static BringupTest fakeTest(String name) {
    return new BringupTest() {
      @Override
      public String getName() {
        return name;
      }

      @Override
      public boolean isEnabled() {
        return true;
      }

      @Override
      public boolean isRunning() {
        return false;
      }

      @Override
      public boolean isFinished() {
        return false;
      }

      @Override
      public BringupTestResult getResult() {
        return BringupTestResult.PASS;
      }

      @Override
      public String getStatus() {
        return "";
      }

      @Override
      public boolean start(BringupTestContext context, double nowSec) {
        return false;
      }

      @Override
      public void update(BringupTestContext context, double nowSec) {}

      @Override
      public void stop(BringupTestContext context) {}

      @Override
      public List<String> getRequiredDeviceKeys() {
        return List.of();
      }
    };
  }
}
