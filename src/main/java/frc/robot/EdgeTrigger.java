package frc.robot;

import java.util.HashMap;
import java.util.Map;

/**
 * NAME
 *   EdgeTrigger - Rising-edge detector keyed by action name.
 *
 * DESCRIPTION
 *   Tracks previous boolean states to detect new presses in a periodic loop.
 */
public final class EdgeTrigger {
  private final Map<String, Boolean> last = new HashMap<>();

  /**
   * NAME
   *   pressed - Detect a rising edge for a key.
   *
   * PARAMETERS
   *   key - Logical action name.
   *   now - Current boolean state.
   *
   * RETURNS
   *   True when the state transitions from false to true.
   */
  public boolean pressed(String key, boolean now) {
    boolean prev = last.getOrDefault(key, false);
    last.put(key, now);
    return now && !prev;
  }

  /**
   * NAME
   *   reset - Clear all stored states.
   */
  public void reset() {
    last.clear();
  }
}
