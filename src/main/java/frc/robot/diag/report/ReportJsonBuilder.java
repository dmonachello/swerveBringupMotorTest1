package frc.robot.diag.report;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import frc.robot.diag.snapshots.BusSnapshot;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.PcSnapshot;
import frc.robot.diag.snapshots.SnapshotBundle;
import java.util.List;

// Formats snapshot bundles into the machine-readable JSON report.
public final class ReportJsonBuilder {
  private static final Gson GSON = new Gson();

  public String buildReportJson(SnapshotBundle bundle) {
    JsonObject root = new JsonObject();
    root.addProperty("timestamp", bundle != null ? bundle.timestampSec : 0.0);
    root.add("bus", buildBusJson(bundle != null ? bundle.bus : null));
    root.add("pc", buildPcJson(bundle != null ? bundle.pc : null));
    root.add("devices", buildDevicesJson(bundle != null ? bundle.devices : null));
    return GSON.toJson(root);
  }

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

  private JsonObject buildPcJson(PcSnapshot pc) {
    JsonObject out = new JsonObject();
    if (pc == null) {
      out.addProperty("heartbeatAgeSec", -1.0);
      out.addProperty("openOk", false);
      out.addProperty("framesPerSec", Double.NaN);
      out.addProperty("framesTotal", Double.NaN);
      out.addProperty("readErrors", Double.NaN);
      out.addProperty("lastFrameAgeSec", Double.NaN);
      JsonObject summary = new JsonObject();
      summary.addProperty("missingCount", 0);
      summary.addProperty("totalCount", 0);
      summary.addProperty("flappingCount", 0);
      summary.add("seenNotLocal", new JsonArray());
      out.add("deviceSummary", summary);
      return out;
    }
    out.addProperty("heartbeatAgeSec", pc.heartbeatAgeSec);
    out.addProperty("openOk", pc.openOk);
    out.addProperty("framesPerSec", pc.framesPerSec);
    out.addProperty("framesTotal", pc.framesTotal);
    out.addProperty("readErrors", pc.readErrors);
    out.addProperty("lastFrameAgeSec", pc.lastFrameAgeSec);

    JsonObject summary = new JsonObject();
    summary.addProperty("missingCount", pc.missingCount);
    summary.addProperty("totalCount", pc.totalCount);
    summary.addProperty("flappingCount", pc.flappingCount);
    JsonArray seenNotLocal = new JsonArray();
    for (PcSnapshot.SeenNotLocalEntry entry : pc.seenNotLocal) {
      JsonObject obj = new JsonObject();
      obj.addProperty("key", entry.key);
      if (entry.ageSec != null) {
        obj.addProperty("ageSec", entry.ageSec);
      }
      seenNotLocal.add(obj);
    }
    JsonArray profileMismatch = new JsonArray();
    for (PcSnapshot.ProfileMismatchEntry entry : pc.profileMismatch) {
      JsonObject obj = new JsonObject();
      obj.addProperty("expected", entry.expected);
      JsonArray ids = new JsonArray();
      for (Integer id : entry.seenIds) {
        ids.add(id);
      }
      obj.add("seenIds", ids);
      profileMismatch.add(obj);
    }
    JsonArray staleDevices = new JsonArray();
    for (PcSnapshot.StaleDeviceEntry entry : pc.staleDevices) {
      JsonObject obj = new JsonObject();
      obj.addProperty("key", entry.key);
      if (entry.ageSec != null) {
        obj.addProperty("ageSec", entry.ageSec);
      }
      staleDevices.add(obj);
    }
    summary.add("seenNotLocal", seenNotLocal);
    summary.add("profileMismatch", profileMismatch);
    summary.add("staleDevices", staleDevices);
    out.add("deviceSummary", summary);
    return out;
  }

  private JsonArray buildDevicesJson(List<DeviceSnapshot> devices) {
    JsonArray out = new JsonArray();
    if (devices == null) {
      return out;
    }
    for (DeviceSnapshot snap : devices) {
      JsonObject entry = new JsonObject();
      entry.addProperty("type", snap.deviceType);
      entry.addProperty("id", snap.canId);
      if (!snap.present) {
        entry.addProperty("present", false);
        if (snap.note != null && !snap.note.isBlank()) {
          entry.addProperty("note", snap.note);
        }
        out.add(entry);
        continue;
      }

      entry.addProperty("present", true);
      if (snap.note != null && !snap.note.isBlank()) {
        entry.addProperty("note", snap.note);
      }
      boolean isRev = "NEO".equals(snap.deviceType) || "FLEX".equals(snap.deviceType);
      boolean isCtre = "KRAKEN".equals(snap.deviceType) || "FALCON".equals(snap.deviceType);
      if (isRev || isCtre) {
        entry.addProperty("faultsRaw", snap.faultsRaw);
        entry.addProperty("stickyFaultsRaw", snap.stickyFaultsRaw);
      }
      if (isRev) {
        entry.addProperty("warningsRaw", snap.warningsRaw);
        entry.addProperty("stickyWarningsRaw", snap.stickyWarningsRaw);
        entry.addProperty("lastError", snap.lastError == null ? "" : snap.lastError);
        entry.addProperty("reset", snap.reset);
      }
      if (isCtre) {
        entry.addProperty("faultStatus", snap.faultStatus == null ? "" : snap.faultStatus);
        entry.addProperty("stickyStatus", snap.stickyStatus == null ? "" : snap.stickyStatus);
      }
      if (snap.model != null && !snap.model.isBlank()) {
        entry.addProperty("specModel", snap.model);
      }
      if (snap.specNominalV != null) {
        entry.addProperty("specNominalV", snap.specNominalV);
      }
      if (snap.specFreeA != null) {
        entry.addProperty("specFreeA", snap.specFreeA);
      }
      if (snap.specStallA != null) {
        entry.addProperty("specStallA", snap.specStallA);
      }
      if (isRev || isCtre) {
        entry.addProperty("busV", safeDouble(snap.busV));
        entry.addProperty("appliedDuty", safeDouble(snap.appliedDuty));
        entry.addProperty("appliedV", safeDouble(snap.appliedV));
        entry.addProperty("motorCurrentA", safeDouble(snap.motorCurrentA));
        entry.addProperty("tempC", safeDouble(snap.tempC));
      }
      if (isRev) {
        entry.addProperty("cmdDuty", safeDouble(snap.cmdDuty));
      }
      if (isCtre) {
        entry.addProperty("motorV", safeDouble(snap.motorV));
      }
      if ("CANCoder".equals(snap.deviceType)) {
        entry.addProperty("absDeg", safeDouble(snap.absDeg));
        entry.addProperty("lastError", snap.lastError == null ? "" : snap.lastError);
      }
      if ("CANdle".equals(snap.deviceType)) {
        // No additional fields yet beyond presence.
      }
      out.add(entry);
    }
    return out;
  }

  private double safeDouble(Double value) {
    return value == null ? 0.0 : value;
  }
}
