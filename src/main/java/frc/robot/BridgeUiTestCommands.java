package frc.robot;

import com.google.gson.JsonObject;
import java.util.Set;

/**
 * NAME
 *   BridgeUiTestCommands - Test command family executor.
 */
final class BridgeUiTestCommands implements BridgeUiCommandDispatcher.CommandFamily {

  private static final String CMD_TOGGLE_TEST = "toggleTest";
  private static final String CMD_RUN_TEST = "runTest";
  private static final String CMD_RUN_ALL_TESTS = "runAllTests";
  private static final String CMD_SELECT_TEST_PREV = "selectTestPrev";
  private static final String CMD_SELECT_TEST_NEXT = "selectTestNext";
  private static final String CMD_PRINT_NEXT_TEST = "printNextTest";
  private static final String CMD_PRINT_TESTS_INFO = "printTestsInfo";
  private static final String CMD_PRINT_TESTS_OVERVIEW = "printTestsOverview";
  private static final String CMD_SELECT_TEST_BY_NAME = "selectTestByName";
  private static final String CMD_SHOW_TESTS = "showTests";

  private static final String ARG_NAME = "name";
  private static final String JSON_KEY_JSON = "json";
  private static final String JSON_KEY_RUN_ID = "runId";
  private static final String JSON_KEY_STATE = "state";
  private static final String JSON_KEY_TEST = "test";
  private static final String JSON_KEY_RESULT = "result";
  private static final String JSON_KEY_STATUS = "status";
  private static final String JSON_KEY_MESSAGE = "message";
  private static final String JSON_KEY_STARTED_AT_MS = "startedAtMs";
  private static final String JSON_KEY_FINISHED_AT_MS = "finishedAtMs";
  private static final String JSON_KEY_DETAILS = "details";
  private static final String RUN_STATE_BLOCKED = "blocked";
  private static final String RUN_STATE_ABORTED = "aborted";
  private static final String RUN_STATE_INTERRUPTED = "interrupted";
  private static final String TEXT_EMPTY = "";

  private static final String MESSAGE_RUN_TEST = "Command: runTest (UI)";
  private static final String MESSAGE_RUN_ALL_TESTS = "Command: runAllTests (UI)";
  private static final String MESSAGE_SELECTED_TEST_PREFIX = "Selected test: ";
  private static final String MESSAGE_SELECT_BY_NAME_REQUIRED = "selectTestByName requires args.name.";
  private static final String MESSAGE_TEST_NOT_FOUND_PREFIX = "Test not found: ";

  private static final Set<String> COMMANDS = Set.of(
      CMD_TOGGLE_TEST,
      CMD_RUN_TEST,
      CMD_RUN_ALL_TESTS,
      CMD_SELECT_TEST_PREV,
      CMD_SELECT_TEST_NEXT,
      CMD_PRINT_NEXT_TEST,
      CMD_PRINT_TESTS_INFO,
      CMD_PRINT_TESTS_OVERVIEW,
      CMD_SELECT_TEST_BY_NAME,
      CMD_SHOW_TESTS);

  /**
   * NAME
   *   Dependencies - Narrow dependency contract for test commands.
   */
  interface Dependencies {
    void toggleSelectedBringupTestEnabled();

    String printTestsOverview();

    void enqueuePrint(String text);

    BringupCore.TestRunSnapshot runSelectedBringupTest();

    void runAllBringupTests();

    void selectPrevBringupTest();

    void selectNextBringupTest();

    String getSelectedBringupTestName();

    String buildNextTestReportText();

    void requestTextReport(String text, int batchSize);

    String printTestsInfo();

    String parseUiArgName(JsonObject args);

    boolean selectBringupTestByName(String testName);

    Boolean parseUiArgBoolean(JsonObject args, String key);

    BringupCore.TestsOverview buildTestsOverview();

    String formatTestsOverview(BringupCore.TestsOverview overview);

    JsonObject buildTestsOverviewJson(BringupCore.TestsOverview overview);

    void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson);
  }

  private final Dependencies dependencies;

  BridgeUiTestCommands(Dependencies dependencies) {
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
    JsonObject args = ingress.args;
    switch (commandName) {
      case CMD_TOGGLE_TEST:
        dependencies.toggleSelectedBringupTestEnabled();
        dependencies.printTestsOverview();
        break;
      case CMD_RUN_TEST:
        dependencies.enqueuePrint(MESSAGE_RUN_TEST);
        applyRunSnapshot(result, dependencies.runSelectedBringupTest());
        break;
      case CMD_RUN_ALL_TESTS:
        dependencies.enqueuePrint(MESSAGE_RUN_ALL_TESTS);
        dependencies.runAllBringupTests();
        break;
      case CMD_SELECT_TEST_PREV:
        dependencies.selectPrevBringupTest();
        result.outText = MESSAGE_SELECTED_TEST_PREFIX + dependencies.getSelectedBringupTestName();
        break;
      case CMD_SELECT_TEST_NEXT:
        dependencies.selectNextBringupTest();
        result.outText = MESSAGE_SELECTED_TEST_PREFIX + dependencies.getSelectedBringupTestName();
        break;
      case CMD_PRINT_NEXT_TEST:
        String report = dependencies.buildNextTestReportText();
        dependencies.requestTextReport(report, 4);
        result.outText = report;
        break;
      case CMD_PRINT_TESTS_INFO:
        result.outText = dependencies.printTestsInfo();
        break;
      case CMD_PRINT_TESTS_OVERVIEW:
        result.outText = dependencies.printTestsOverview();
        break;
      case CMD_SELECT_TEST_BY_NAME:
        executeSelectTestByName(args, result);
        break;
      case CMD_SHOW_TESTS:
        executeShowTests(args, result);
        break;
      default:
        result.ok = false;
        result.message = "Unknown command: " + commandName;
        break;
    }
    return result;
  }

  private void executeSelectTestByName(JsonObject args, BridgeUiCommandResult result) {
    String testName = dependencies.parseUiArgName(args);
    if (testName == null || testName.isBlank()) {
      result.ok = false;
      result.message = MESSAGE_SELECT_BY_NAME_REQUIRED;
      return;
    }
    if (!dependencies.selectBringupTestByName(testName)) {
      result.ok = false;
      result.message = MESSAGE_TEST_NOT_FOUND_PREFIX + testName;
      return;
    }
    result.message = MESSAGE_SELECTED_TEST_PREFIX + testName;
    dependencies.printTestsOverview();
  }

  private void executeShowTests(JsonObject args, BridgeUiCommandResult result) {
    boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, JSON_KEY_JSON));
    BringupCore.TestsOverview overview = dependencies.buildTestsOverview();
    dependencies.applyShowResult(
        result,
        dependencies.formatTestsOverview(overview),
        dependencies.buildTestsOverviewJson(overview),
        wantsJson);
  }

  private void applyRunSnapshot(BridgeUiCommandResult result, BringupCore.TestRunSnapshot snapshot) {
    if (snapshot == null) {
      return;
    }
    result.message = snapshot.message != null && !snapshot.message.isBlank()
        ? snapshot.message
        : snapshot.state;
    result.outText = result.message;
    JsonObject obj = new JsonObject();
    obj.addProperty(JSON_KEY_RUN_ID, snapshot.runId);
    obj.addProperty(JSON_KEY_STATE, snapshot.state != null ? snapshot.state : TEXT_EMPTY);
    obj.addProperty(JSON_KEY_TEST, snapshot.test != null ? snapshot.test : TEXT_EMPTY);
    obj.addProperty(JSON_KEY_RESULT, snapshot.result != null ? snapshot.result : TEXT_EMPTY);
    obj.addProperty(JSON_KEY_STATUS, snapshot.status != null ? snapshot.status : TEXT_EMPTY);
    obj.addProperty(JSON_KEY_MESSAGE, snapshot.message != null ? snapshot.message : TEXT_EMPTY);
    obj.addProperty(JSON_KEY_STARTED_AT_MS, snapshot.startedAtMs);
    obj.addProperty(JSON_KEY_FINISHED_AT_MS, snapshot.finishedAtMs);
    obj.add(JSON_KEY_DETAILS, snapshot.details != null ? snapshot.details.deepCopy() : new JsonObject());
    result.outJson = obj.toString();
    if (RUN_STATE_BLOCKED.equals(snapshot.state)
        || RUN_STATE_ABORTED.equals(snapshot.state)
        || RUN_STATE_INTERRUPTED.equals(snapshot.state)) {
      result.ok = false;
    }
  }
}

