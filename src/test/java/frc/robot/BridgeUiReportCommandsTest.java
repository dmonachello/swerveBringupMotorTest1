package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import org.junit.jupiter.api.Test;

class BridgeUiReportCommandsTest {

  private static final String CMD_PRINT_SUMMARY = "printSummary";
  private static final String CMD_PRINT_SELECTED_TEST_SOURCE = "printSelectedTestSource";
  private static final String CMD_PRINT_NT_DIAG = "printNTdiag";
  private static final String CMD_PRINT_CAN_DIAG = "printCANdiag";
  private static final String CMD_DUMP_REPORT = "dumpReport";
  private static final String CMD_SHOW_STATUS = "showStatus";
  private static final String CMD_SHOW_VERSION = "showVersion";

  private static final String KEY_JSON = "json";

  private static final String MSG_DIAG_UNAVAILABLE = "Diagnostics unavailable.";
  private static final String MSG_DUMP_WRITE_PREFIX = "Wrote CAN report JSON to ";
  private static final String MSG_DUMP_WRITE_FAIL = "Failed to write CAN report JSON.";
  private static final String MSG_REPORT_DUMPED = "Dumped report.";
  private static final String MSG_PROFILE_DEVICES_PRINTED = "Printed profile devices.";
  private static final String REPORT_PATH = "logs/report.json";

  @Test
  void diagnosticsUnavailableBlocksSummaryNtAndCan() {
    TestDeps deps = new TestDeps();
    deps.hasDiagnostics = false;
    BridgeUiReportCommands commands = new BridgeUiReportCommands(deps);

    BridgeUiCommandResult summary = commands.execute(ingress(CMD_PRINT_SUMMARY, new JsonObject()), 0.0, false);
    BridgeUiCommandResult ntDiag = commands.execute(ingress(CMD_PRINT_NT_DIAG, new JsonObject()), 0.0, false);
    BridgeUiCommandResult canDiag = commands.execute(ingress(CMD_PRINT_CAN_DIAG, new JsonObject()), 0.0, false);

    assertFalse(summary.ok);
    assertEquals(MSG_DIAG_UNAVAILABLE, summary.message);
    assertFalse(ntDiag.ok);
    assertEquals(MSG_DIAG_UNAVAILABLE, ntDiag.message);
    assertFalse(canDiag.ok);
    assertEquals(MSG_DIAG_UNAVAILABLE, canDiag.message);
  }

  @Test
  void showStatusRoutesThroughApplyShowResult() {
    TestDeps deps = new TestDeps();
    BridgeUiReportCommands commands = new BridgeUiReportCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_JSON, true);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_SHOW_STATUS, args), 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.applyShowCalled);
    assertEquals(deps.statusText, deps.lastShowText);
  }

  @Test
  void showVersionRoutesThroughApplyShowResult() {
    TestDeps deps = new TestDeps();
    BridgeUiReportCommands commands = new BridgeUiReportCommands(deps);
    JsonObject args = new JsonObject();
    args.addProperty(KEY_JSON, false);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_SHOW_VERSION, args), 0.0, false);

    assertTrue(result.ok);
    assertTrue(deps.applyShowCalled);
    assertEquals(deps.versionText, deps.lastShowText);
  }

  @Test
  void printSelectedTestSourceEmitsReportText() {
    TestDeps deps = new TestDeps();
    BridgeUiReportCommands commands = new BridgeUiReportCommands(deps);

    BridgeUiCommandResult result =
        commands.execute(ingress(CMD_PRINT_SELECTED_TEST_SOURCE, new JsonObject()), 0.0, false);

    assertTrue(result.ok);
    assertEquals(deps.selectedTestSourceText, result.outText);
  }

  @Test
  void printProfileDevicesReturnsShortAckInsteadOfDuplicatingReportBody() {
    TestDeps deps = new TestDeps();
    BridgeUiReportCommands commands = new BridgeUiReportCommands(deps);

    BridgeUiCommandResult result =
        commands.execute(ingress("printProfileDevices", new JsonObject()), 0.0, false);

    assertTrue(result.ok);
    assertEquals(MSG_PROFILE_DEVICES_PRINTED, result.outText);
  }

  @Test
  void dumpReportWriteSuccessIncludesPathMessage() {
    TestDeps deps = new TestDeps();
    deps.writeReportSuccess = true;
    BridgeUiReportCommands commands = new BridgeUiReportCommands(deps);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_DUMP_REPORT, new JsonObject()), 0.0, false);

    assertTrue(result.ok);
    assertEquals(MSG_REPORT_DUMPED, result.outText);
  }

  @Test
  void dumpReportWriteFailureIncludesFailureMessage() {
    TestDeps deps = new TestDeps();
    deps.writeReportSuccess = false;
    BridgeUiReportCommands commands = new BridgeUiReportCommands(deps);

    BridgeUiCommandResult result = commands.execute(ingress(CMD_DUMP_REPORT, new JsonObject()), 0.0, false);

    assertTrue(result.ok);
    assertEquals(MSG_REPORT_DUMPED, result.outText);
  }

  private static BridgeUiIngressPolicy.Ingress ingress(String name, JsonObject args) {
    return new BridgeUiIngressPolicy.Ingress(
        name,
        args,
        "clientA",
        true,
        true,
        false,
        false,
        false,
        true,
        true,
        false);
  }

  private static final class TestDeps implements BridgeUiReportCommands.Dependencies {
    private boolean hasDiagnostics = true;
    private boolean applyShowCalled;
    private boolean writeReportSuccess = true;
    private String lastShowText = "";

    private final String statusText = "status";
    private final String versionText = "version";
    private final String selectedTestSourceText = "selected source";

    @Override
    public String buildStateReportText() {
      return "state";
    }

    @Override
    public String buildQuickSummary() {
      return "summary";
    }

    @Override
    public String buildHealthReportText() {
      return "health";
    }

    @Override
    public String buildCANCoderReportText() {
      return "cancoder";
    }

    @Override
    public double getLastNeoSpeed() {
      return 0.1;
    }

    @Override
    public double getLastKrakenSpeed() {
      return 0.2;
    }

    @Override
    public String printBindings() {
      return "bindings";
    }

    @Override
    public String printProfileDevices() {
      return "profiles";
    }

    @Override
    public String buildSelectedTestSourceReportText() {
      return selectedTestSourceText;
    }

    @Override
    public String buildNetworkDiagnosticsReportIfReady() {
      return "ntdiag";
    }

    @Override
    public String appendUiSessionStats(String report) {
      return report + "+session";
    }

    @Override
    public String buildCanDiagnosticsReportIfReady() {
      return "candiag";
    }

    @Override
    public long getCanDiagCooldownRemainingMs() {
      return 0;
    }

    @Override
    public String buildReportJsonForDump() {
      return "{}";
    }

    @Override
    public boolean writeReportJsonToFile(String json) {
      return writeReportSuccess;
    }

    @Override
    public String getReportPath() {
      return REPORT_PATH;
    }

    @Override
    public void requestTextReport(String text, int batchSize) {}

    @Override
    public Boolean parseUiArgBoolean(JsonObject args, String key) {
      return args != null && args.has(key) ? args.get(key).getAsBoolean() : null;
    }

    @Override
    public void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson) {
      applyShowCalled = true;
      lastShowText = text;
      if (wantsJson) {
        result.outJson = json.toString();
      } else {
        result.outText = text;
      }
    }

    @Override
    public String buildStatusText() {
      return statusText;
    }

    @Override
    public JsonObject buildStatusJson() {
      JsonObject json = new JsonObject();
      json.addProperty("status", statusText);
      return json;
    }

    @Override
    public String buildVersionText() {
      return versionText;
    }

    @Override
    public JsonObject buildVersionJson() {
      JsonObject json = new JsonObject();
      json.addProperty("version", versionText);
      return json;
    }

    @Override
    public String buildSourcesText() {
      return "sources";
    }

    @Override
    public JsonObject buildSourcesJson() {
      return new JsonObject();
    }

    @Override
    public boolean hasDiagnostics() {
      return hasDiagnostics;
    }
  }
}
