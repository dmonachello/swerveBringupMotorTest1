package frc.robot.diag.snapshots;

import java.util.ArrayList;
import java.util.List;

// Plain data snapshot for a single device at a moment in time.
public final class DeviceSnapshot {
  public String vendor = "";
  public String deviceType = "";
  public int canId = -1;
  public boolean present = false;
  public String label = "";
  public String note = "";

  public final List<DeviceAttachment> attachments = new ArrayList<>();

  public void addAttachment(DeviceAttachment attachment) {
    if (attachment != null) {
      attachments.add(attachment);
    }
  }

  public <T extends DeviceAttachment> T getAttachment(Class<T> type) {
    for (DeviceAttachment attachment : attachments) {
      if (type.isInstance(attachment)) {
        return type.cast(attachment);
      }
    }
    return null;
  }

  public DeviceAttachment getAttachment(String type) {
    if (type == null || type.isBlank()) {
      return null;
    }
    for (DeviceAttachment attachment : attachments) {
      if (type.equals(attachment.type)) {
        return attachment;
      }
    }
    return null;
  }
}
