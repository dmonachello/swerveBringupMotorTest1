package frc.robot.diag.report;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.DeviceAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
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

  // private double safeDouble(Double value) {
  //   return value == null ? 0.0 : value;
  // }
}
