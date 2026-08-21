package frc.robot.diag.report;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.DeviceAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.RobotControllerBusAttachment;
import frc.robot.diag.snapshots.RobotControllerPowerAttachment;
import frc.robot.diag.snapshots.RobotControllerRailsAttachment;
import frc.robot.diag.snapshots.SnapshotBundle;
import java.util.List;

/**
 * NAME
 *   ReportJsonBuilder - Build machine-readable JSON reports.
 *
 * DESCRIPTION
 *   Formats snapshot bundles into the bringup diagnostics JSON structure.
 */
public final class ReportJsonBuilder {
  private static final Gson GSON = new Gson();
  private static final String KEY_FAMILY = "family";
  private static final String KEY_ROBOT_CONTROLLER = "robotController";
  private static final String KEY_POWER = "power";
  private static final String KEY_BUS = "bus";
  private static final String KEY_RAILS = "rails";
  private static final String KEY_INPUT_VOLTAGE = "inputVoltage";
  private static final String KEY_BROWNOUT = "brownout";
  private static final String KEY_BROWNOUT_VOLTAGE = "brownoutVoltage";
  private static final String KEY_CAN_UTILIZATION_PCT = "canUtilizationPct";
  private static final String KEY_CAN_RX_ERROR_COUNT = "canRxErrorCount";
  private static final String KEY_CAN_TX_ERROR_COUNT = "canTxErrorCount";
  private static final String KEY_CAN_BUS_OFF_COUNT = "canBusOffCount";
  private static final String KEY_CAN_TX_FULL_COUNT = "canTxFullCount";
  private static final String KEY_RAIL_3V3 = "rail3v3";
  private static final String KEY_RAIL_5V = "rail5v";
  private static final String KEY_RAIL_6V = "rail6v";
  private static final String KEY_VOLTAGE = "voltage";
  private static final String KEY_CURRENT = "current";
  private static final String KEY_ENABLED = "enabled";
  private static final String KEY_FAULT_COUNT = "faultCount";
  private static final String VALUE_FAMILY_ROBOT_CONTROLLER = "robotController";

  /**
   * NAME
   *   buildReportJson - Serialize a SnapshotBundle to JSON.
   *
   * PARAMETERS
   *   bundle - Snapshot data to serialize.
   *
   * RETURNS
   *   JSON string.
   */
  public String buildReportJson(SnapshotBundle bundle) {
    JsonObject root = new JsonObject();
    root.addProperty("timestamp", bundle != null ? bundle.timestampSec : 0.0);
    root.add("bus", buildBusJson(bundle != null ? bundle.bus : null));
    root.add("devices", buildDevicesJson(bundle != null ? bundle.devices : null));
    return GSON.toJson(root);
  }

  /**
   * NAME
   *   buildBusJson - Build the bus section JSON.
   */
  private JsonObject buildBusJson(BusSnapshot bus) {
    JsonObject out = new JsonObject();
    if (bus == null || !bus.valid) {
      out.addProperty("valid", false);
      return out;
    }
    out.addProperty("valid", true);
    out.addProperty("utilizationPct", bus.utilizationPct);
    out.addProperty("rxErrors", bus.rxErrors);
    out.addProperty("txErrors", bus.txErrors);
    out.addProperty("rxDelta", bus.rxDelta);
    out.addProperty("txDelta", bus.txDelta);
    out.addProperty("txFull", bus.txFull);
    out.addProperty("txFullDelta", bus.txFullDelta);
    out.addProperty("busOff", bus.busOff);
    out.addProperty("busOffDelta", bus.busOffDelta);
    out.addProperty("sampleAgeSec", bus.sampleAgeSec);
    return out;
  }

  /**
   * NAME
   *   buildDevicesJson - Build the devices array JSON.
   */
  private JsonArray buildDevicesJson(List<DeviceSnapshot> devices) {
    JsonArray out = new JsonArray();
    if (devices == null) {
      return out;
    }
    for (DeviceSnapshot snap : devices) {
      JsonObject entry = new JsonObject();
      entry.addProperty("type", snap.deviceType);
      entry.addProperty("id", snap.canId);
      if (snap.label != null && !snap.label.isBlank()) {
        entry.addProperty("label", snap.label);
      }
      if (!snap.present) {
        entry.addProperty("present", false);
        if (snap.note != null && !snap.note.isBlank()) {
          entry.addProperty("note", snap.note);
        }
        appendAttachments(entry, snap.attachments);
        out.add(entry);
        continue;
      }

      entry.addProperty("present", true);
      if (snap.note != null && !snap.note.isBlank()) {
        entry.addProperty("note", snap.note);
      }
      appendAttachments(entry, snap.attachments);
      appendRobotControllerJson(entry, snap);
      out.add(entry);
    }
    return out;
  }

  /**
   * NAME
   *   appendAttachments - Append attachment array to a device entry.
   */
  private void appendAttachments(JsonObject entry, List<DeviceAttachment> attachments) {
    if (attachments == null || attachments.isEmpty()) {
      return;
    }
    JsonArray array = new JsonArray();
    for (DeviceAttachment attachment : attachments) {
      array.add(GSON.toJsonTree(attachment));
    }
    entry.add("attachments", array);
  }

  /**
   * NAME
   *   appendRobotControllerJson - Append additive controller-family summary fields.
   */
  private void appendRobotControllerJson(JsonObject entry, DeviceSnapshot snap) {
    RobotControllerPowerAttachment power = snap.getAttachment(RobotControllerPowerAttachment.class);
    RobotControllerBusAttachment bus = snap.getAttachment(RobotControllerBusAttachment.class);
    RobotControllerRailsAttachment rails = snap.getAttachment(RobotControllerRailsAttachment.class);
    if (power == null && bus == null && rails == null) {
      return;
    }
    entry.addProperty(KEY_FAMILY, VALUE_FAMILY_ROBOT_CONTROLLER);
    JsonObject controller = new JsonObject();
    if (power != null) {
      JsonObject powerJson = new JsonObject();
      powerJson.addProperty(KEY_INPUT_VOLTAGE, power.inputVoltage);
      powerJson.addProperty(KEY_BROWNOUT, power.brownout);
      powerJson.addProperty(KEY_BROWNOUT_VOLTAGE, power.brownoutVoltage);
      controller.add(KEY_POWER, powerJson);
    }
    if (bus != null) {
      JsonObject busJson = new JsonObject();
      busJson.addProperty(KEY_CAN_UTILIZATION_PCT, bus.canUtilizationPct);
      busJson.addProperty(KEY_CAN_RX_ERROR_COUNT, bus.canRxErrorCount);
      busJson.addProperty(KEY_CAN_TX_ERROR_COUNT, bus.canTxErrorCount);
      busJson.addProperty(KEY_CAN_BUS_OFF_COUNT, bus.canBusOffCount);
      busJson.addProperty(KEY_CAN_TX_FULL_COUNT, bus.canTxFullCount);
      controller.add(KEY_BUS, busJson);
    }
    if (rails != null) {
      JsonObject railsJson = new JsonObject();
      railsJson.add(KEY_RAIL_3V3, buildRailJson(
          rails.rail3v3Voltage,
          rails.rail3v3Current,
          rails.rail3v3Enabled,
          rails.rail3v3FaultCount));
      railsJson.add(KEY_RAIL_5V, buildRailJson(
          rails.rail5vVoltage,
          rails.rail5vCurrent,
          rails.rail5vEnabled,
          rails.rail5vFaultCount));
      railsJson.add(KEY_RAIL_6V, buildRailJson(
          rails.rail6vVoltage,
          rails.rail6vCurrent,
          rails.rail6vEnabled,
          rails.rail6vFaultCount));
      controller.add(KEY_RAILS, railsJson);
    }
    entry.add(KEY_ROBOT_CONTROLLER, controller);
  }

  /**
   * NAME
   *   buildRailJson - Build one controller rail summary object.
   */
  private JsonObject buildRailJson(
      double voltage,
      double current,
      boolean enabled,
      int faultCount) {
    JsonObject rail = new JsonObject();
    rail.addProperty(KEY_VOLTAGE, voltage);
    rail.addProperty(KEY_CURRENT, current);
    rail.addProperty(KEY_ENABLED, enabled);
    rail.addProperty(KEY_FAULT_COUNT, faultCount);
    return rail;
  }

  // private double safeDouble(Double value) {
  //   return value == null ? 0.0 : value;
  // }
}
