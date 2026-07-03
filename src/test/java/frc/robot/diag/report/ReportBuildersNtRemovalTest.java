package frc.robot.diag.report;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.SnapshotBundle;
import org.junit.jupiter.api.Test;

class ReportBuildersNtRemovalTest {

  @Test
  void canDiagnosticsReportIsRobotLocalOnly() {
    SnapshotBundle bundle = new SnapshotBundle();
    bundle.bus = validBus();
    bundle.devices.add(new DeviceSnapshot());

    String report = new ReportTextBuilder().buildCanDiagnosticsReport(bundle);

    assertTrue(report.contains("Summary: bus=OK"));
    assertFalse(report.contains(" pc="));
    assertFalse(report.contains("PC Tool:"));
  }

  @Test
  void reportJsonOmitsPcSection() {
    SnapshotBundle bundle = new SnapshotBundle();
    bundle.timestampSec = 1.23;
    bundle.bus = validBus();

    String jsonText = new ReportJsonBuilder().buildReportJson(bundle);
    JsonObject json = JsonParser.parseString(jsonText).getAsJsonObject();

    assertTrue(json.has("bus"));
    assertTrue(json.has("devices"));
    assertFalse(json.has("pc"));
  }

  private static BusSnapshot validBus() {
    BusSnapshot bus = new BusSnapshot();
    bus.valid = true;
    bus.utilizationPct = 12.5;
    bus.rxErrors = 0;
    bus.txErrors = 0;
    bus.busOff = 0;
    return bus;
  }
}
