package frc.robot;

import java.util.HashMap;
import java.util.Map;

// Simple rising-edge detector keyed by action name.
public final class EdgeTrigger {
  private final Map<String, Boolean> last = new HashMap<>();

  public boolean pressed(String key, boolean now) {
    boolean prev = last.getOrDefault(key, false);
    last.put(key, now);
    return now && !prev;
  }

  public void reset() {
    last.clear();
  }
}
