package frc.robot;

import com.google.gson.JsonObject;
import java.util.Set;

/**
 * NAME
 *   BridgeUiReportCommands - Report/diagnostic command family executor.
 */
final class BridgeUiReportCommands implements BridgeUiCommandDispatcher.CommandFamily {

  private static final String CMD_PRINT_STATE = "printState";
  private static final String CMD_PRINT_SUMMARY = "printSummary";
  private static final String CMD_PRINT_HEALTH = "printHealth";
  private static final String CMD_PRINT_CANCODER = "printCANcoder";
  private static final String CMD_PRINT_INPUTS = "printInputs";
  private static final String CMD_PRINT_BINDINGS = "printBindings";
  private static final String CMD_PRINT_PROFILE_DEVICES = "printProfileDevices";
  private static final String CMD_PRINT_SELECTED_TEST_SOURCE = "printSelectedTestSource";
  private static final String CMD_PRINT_CAN_DIAG = "printCANdiag";
  private static final String CMD_DUMP_REPORT = "dumpReport";
  private static final String CMD_SHOW_STATUS = "showStatus";
  private static final String CMD_SHOW_VERSION = "showVersion";
  private static final String CMD_SHOW_SOURCES = "showSources";

  private static final String JSON_KEY_JSON = "json";
  private static final String MESSAGE_DIAGNOSTICS_UNAVAILABLE = "Diagnostics unavailable.";

  private static final Set<String> COMMANDS = Set.of(
      CMD_PRINT_STATE,
      CMD_PRINT_SUMMARY,
      CMD_PRINT_HEALTH,
      CMD_PRINT_CANCODER,
      CMD_PRINT_INPUTS,
      CMD_PRINT_BINDINGS,
      CMD_PRINT_PROFILE_DEVICES,
      CMD_PRINT_SELECTED_TEST_SOURCE,
      CMD_PRINT_CAN_DIAG,
      CMD_DUMP_REPORT,
      CMD_SHOW_STATUS,
      CMD_SHOW_VERSION,
      CMD_SHOW_SOURCES);

  /**
   * NAME
   *   Dependencies - Narrow dependency contract for report commands.
   */
  interface Dependencies {
    String buildStateReportText();

    String buildQuickSummary();

    String buildHealthReportText();

    String buildCANCoderReportText();

    String buildInputsReportText();

    String printBindings();

    String printProfileDevices();

    String buildSelectedTestSourceReportText();

    String buildCanDiagnosticsReportIfReady();

    long getCanDiagCooldownRemainingMs();

    String buildReportJsonForDump();

    boolean writeReportJsonToFile(String json);

    String getReportPath();

    void requestTextReport(String text, int batchSize);

    Boolean parseUiArgBoolean(JsonObject args, String key);

    void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson);

    String buildStatusText();

    JsonObject buildStatusJson();

    String buildVersionText();

    JsonObject buildVersionJson();

    String buildSourcesText();

    JsonObject buildSourcesJson();

    boolean hasDiagnostics();
  }

  private final Dependencies dependencies;

  BridgeUiReportCommands(Dependencies dependencies) {
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
      case CMD_PRINT_STATE:
        result.outText = emitReport(dependencies.buildStateReportText(), 4);
        break;
      case CMD_PRINT_SUMMARY:
        if (dependencies.hasDiagnostics()) {
          result.outText = emitReport(dependencies.buildQuickSummary(), 4);
        } else {
          result.ok = false;
          result.message = MESSAGE_DIAGNOSTICS_UNAVAILABLE;
        }
        break;
      case CMD_PRINT_HEALTH:
        result.outText = emitReport(dependencies.buildHealthReportText(), 4);
        break;
      case CMD_PRINT_CANCODER:
        result.outText = emitReport(dependencies.buildCANCoderReportText(), 4);
        break;
      case CMD_PRINT_INPUTS:
        result.outText = emitReport(dependencies.buildInputsReportText(), 4);
        break;
      case CMD_PRINT_BINDINGS:
        result.outText = dependencies.printBindings();
        break;
      case CMD_PRINT_PROFILE_DEVICES:
        result.outText = dependencies.printProfileDevices();
        break;
      case CMD_PRINT_SELECTED_TEST_SOURCE:
        result.outText = emitReport(dependencies.buildSelectedTestSourceReportText(), 4);
        break;
      case CMD_PRINT_CAN_DIAG:
        executePrintCanDiag(result);
        break;
      case CMD_DUMP_REPORT:
        executeDumpReport(result);
        break;
      case CMD_SHOW_STATUS:
        executeShow(result, args, dependencies.buildStatusText(), dependencies.buildStatusJson());
        break;
      case CMD_SHOW_VERSION:
        executeShow(result, args, dependencies.buildVersionText(), dependencies.buildVersionJson());
        break;
      case CMD_SHOW_SOURCES:
        executeShow(result, args, dependencies.buildSourcesText(), dependencies.buildSourcesJson());
        break;
      default:
        result.ok = false;
        result.message = "Unknown command: " + commandName;
        break;
    }
    return result;
  }

  private String emitReport(String text, int batchSize) {
    dependencies.requestTextReport(text, batchSize);
    return text;
  }

  private void executePrintCanDiag(BridgeUiCommandResult result) {
    if (!dependencies.hasDiagnostics()) {
      result.ok = false;
      result.message = MESSAGE_DIAGNOSTICS_UNAVAILABLE;
      return;
    }
    String report = dependencies.buildCanDiagnosticsReportIfReady();
    if (report != null) {
      dependencies.requestTextReport(report, 4);
      result.outText = report;
      return;
    }
    long remainingMs = dependencies.getCanDiagCooldownRemainingMs();
    String message;
    if (remainingMs > 0) {
      double remainingSec = remainingMs / 1000.0;
      message = String.format("CAN diagnostics rate-limited, try again in %.1fs.", remainingSec);
    } else {
      message = "CAN diagnostics not ready yet.";
    }
    dependencies.requestTextReport(message, 4);
    result.outText = message;
  }

  private void executeDumpReport(BridgeUiCommandResult result) {
    if (!dependencies.hasDiagnostics()) {
      result.ok = false;
      result.message = MESSAGE_DIAGNOSTICS_UNAVAILABLE;
      return;
    }
    String json = dependencies.buildReportJsonForDump();
    String wrapped = ReportTextUtil.wrapLongLine(json, 120);
    dependencies.requestTextReport(wrapped, 4);
    StringBuilder dumpOut = new StringBuilder(wrapped);
    if (dependencies.writeReportJsonToFile(json)) {
      String message = "Wrote CAN report JSON to " + dependencies.getReportPath();
      dependencies.requestTextReport(message, 4);
      dumpOut.append('\n').append(message);
    } else {
      String message = "Failed to write CAN report JSON.";
      dependencies.requestTextReport(message, 4);
      dumpOut.append('\n').append(message);
    }
    result.outText = dumpOut.toString();
  }

  private void executeShow(
      BridgeUiCommandResult result,
      JsonObject args,
      String text,
      JsonObject json) {
    boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, JSON_KEY_JSON));
    dependencies.applyShowResult(result, text, json, wantsJson);
  }
}
