package frc.robot;

import java.util.HashMap;
import java.util.Map;

// Simple rising-edge detector keyed by action name.
final class EdgeTrigger {
  private final Map<String, Boolean> last = new HashMap<>();

  boolean pressed(String key, boolean now) {
    boolean prev = last.getOrDefault(key, false);
    last.put(key, now);
    return now && !prev;
  }

  void reset() {
    last.clear();
  }
}
