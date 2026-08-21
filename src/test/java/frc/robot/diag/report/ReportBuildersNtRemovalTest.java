package frc.robot.diag.report;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.MotorSpecAttachment;
import frc.robot.diag.snapshots.RobotControllerBusAttachment;
import frc.robot.diag.snapshots.RobotControllerPowerAttachment;
import frc.robot.diag.snapshots.RobotControllerRailsAttachment;
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

  @Test
  void canDiagnosticsReportIncludesSharedRobotControllerTelemetry() {
    SnapshotBundle bundle = new SnapshotBundle();
    bundle.bus = validBus();
    bundle.devices.add(robotControllerSnapshot());

    String report = new ReportTextBuilder().buildCanDiagnosticsReport(bundle);

    assertTrue(report.contains("robotController CAN 0: present=YES (virtual) inputV=12.30V"));
    assertTrue(report.contains("brownout=NO brownoutV=6.80V canUtil=17.5%"));
    assertTrue(report.contains("rails: 3v3=3.31V current=0.20A en=YES faults=0"));
    assertTrue(report.contains("5v=5.02V current=0.40A en=YES faults=1"));
    assertTrue(report.contains("6v=6.01V current=0.60A en=NO faults=2"));
  }

  @Test
  void reportJsonIncludesStructuredRobotControllerSummary() {
    SnapshotBundle bundle = new SnapshotBundle();
    bundle.bus = validBus();
    bundle.devices.add(robotControllerSnapshot());

    String jsonText = new ReportJsonBuilder().buildReportJson(bundle);
    JsonObject json = JsonParser.parseString(jsonText).getAsJsonObject();
    JsonArray devices = json.getAsJsonArray("devices");
    JsonObject device = devices.get(0).getAsJsonObject();

    assertTrue(device.has("attachments"));
    assertTrue(device.has("family"));
    assertTrue(device.has("robotController"));
    assertTrue("robotController".equals(device.get("family").getAsString()));
    JsonObject controller = device.getAsJsonObject("robotController");
    assertTrue(controller.getAsJsonObject("power").get("inputVoltage").getAsDouble() == 12.3);
    assertTrue(controller.getAsJsonObject("bus").get("canUtilizationPct").getAsDouble() == 17.5);
    assertTrue(controller.getAsJsonObject("rails").getAsJsonObject("rail6v").get("faultCount").getAsInt() == 2);
  }

  @Test
  void canDiagnosticsReportIncludesMissingMotorSpecWarning() {
    SnapshotBundle bundle = new SnapshotBundle();
    bundle.bus = validBus();
    bundle.devices.add(revMotorSnapshotWithMissingSpec());

    String report = new ReportTextBuilder().buildCanDiagnosticsReport(bundle);

    assertTrue(report.contains("specMissing=YES"));
    assertTrue(report.contains("requestedModel=Unknown Motor"));
  }

  @Test
  void reportJsonIncludesMissingMotorSpecAttachmentState() {
    SnapshotBundle bundle = new SnapshotBundle();
    bundle.bus = validBus();
    bundle.devices.add(revMotorSnapshotWithMissingSpec());

    String jsonText = new ReportJsonBuilder().buildReportJson(bundle);
    JsonObject json = JsonParser.parseString(jsonText).getAsJsonObject();
    JsonArray devices = json.getAsJsonArray("devices");
    JsonObject device = devices.get(0).getAsJsonObject();
    JsonArray attachments = device.getAsJsonArray("attachments");
    JsonObject spec = attachments.get(1).getAsJsonObject();

    assertTrue("motorSpec".equals(spec.get("type").getAsString()));
    assertTrue(!spec.get("matched").getAsBoolean());
    assertTrue("Unknown Motor".equals(spec.get("requestedModel").getAsString()));
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

  private static DeviceSnapshot robotControllerSnapshot() {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.deviceType = "robotController";
    snap.canId = 0;
    snap.present = true;
    snap.note = "virtual";

    RobotControllerPowerAttachment power = new RobotControllerPowerAttachment();
    power.inputVoltage = 12.3;
    power.brownout = false;
    power.brownoutVoltage = 6.8;
    snap.addAttachment(power);

    RobotControllerBusAttachment bus = new RobotControllerBusAttachment();
    bus.canUtilizationPct = 17.5;
    bus.canRxErrorCount = 1;
    bus.canTxErrorCount = 2;
    bus.canBusOffCount = 3;
    bus.canTxFullCount = 4;
    snap.addAttachment(bus);

    RobotControllerRailsAttachment rails = new RobotControllerRailsAttachment();
    rails.rail3v3Voltage = 3.31;
    rails.rail3v3Current = 0.2;
    rails.rail3v3Enabled = true;
    rails.rail3v3FaultCount = 0;
    rails.rail5vVoltage = 5.02;
    rails.rail5vCurrent = 0.4;
    rails.rail5vEnabled = true;
    rails.rail5vFaultCount = 1;
    rails.rail6vVoltage = 6.01;
    rails.rail6vCurrent = 0.6;
    rails.rail6vEnabled = false;
    rails.rail6vFaultCount = 2;
    snap.addAttachment(rails);
    return snap;
  }

  private static DeviceSnapshot revMotorSnapshotWithMissingSpec() {
    DeviceSnapshot snap = new DeviceSnapshot();
    snap.deviceType = "NEO";
    snap.canId = 9;
    snap.present = true;

    frc.robot.manufacturers.rev.diag.RevMotorAttachment rev =
        new frc.robot.manufacturers.rev.diag.RevMotorAttachment();
    rev.busV = 12.0;
    rev.appliedV = 2.4;
    rev.motorCurrentA = 3.2;
    rev.tempC = 29.0;
    snap.addAttachment(rev);

    MotorSpecAttachment spec = new MotorSpecAttachment();
    spec.requestedModel = "Unknown Motor";
    snap.addAttachment(spec);
    return snap;
  }
}
