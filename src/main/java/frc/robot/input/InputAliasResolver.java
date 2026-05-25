package frc.robot.input;

import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * NAME
 *   InputAliasResolver - Resolve controller input aliases to canonical keys.
 *
 * DESCRIPTION
 *   Normalizes input identifiers using alias maps from configuration files and
 *   provides helpers to translate controller binding specs into alias keys.
 */
public final class InputAliasResolver {
  public static final String KEY_DRIVER_A = "driver.a";
  public static final String KEY_DRIVER_B = "driver.b";
  public static final String KEY_DRIVER_X = "driver.x";
  public static final String KEY_DRIVER_Y = "driver.y";
  public static final String KEY_DRIVER_LB = "driver.lb";
  public static final String KEY_DRIVER_RB = "driver.rb";
  public static final String KEY_DRIVER_BACK = "driver.back";
  public static final String KEY_DRIVER_START = "driver.start";
  public static final String KEY_DRIVER_LS = "driver.ls";
  public static final String KEY_DRIVER_RS = "driver.rs";
  public static final String KEY_DRIVER_DPAD_UP = "driver.dpad.up";
  public static final String KEY_DRIVER_DPAD_RIGHT = "driver.dpad.right";
  public static final String KEY_DRIVER_DPAD_DOWN = "driver.dpad.down";
  public static final String KEY_DRIVER_DPAD_LEFT = "driver.dpad.left";
  public static final String KEY_DRIVER_LEFT_X = "driver.left.x";
  public static final String KEY_DRIVER_LEFT_Y = "driver.left.y";
  public static final String KEY_DRIVER_RIGHT_X = "driver.right.x";
  public static final String KEY_DRIVER_RIGHT_Y = "driver.right.y";
  public static final String KEY_DRIVER_LEFT_TRIGGER = "driver.left.trigger";
  public static final String KEY_DRIVER_RIGHT_TRIGGER = "driver.right.trigger";

  public static final String KEY_OPERATOR_A = "operator.a";
  public static final String KEY_OPERATOR_B = "operator.b";
  public static final String KEY_OPERATOR_X = "operator.x";
  public static final String KEY_OPERATOR_Y = "operator.y";
  public static final String KEY_OPERATOR_LB = "operator.lb";
  public static final String KEY_OPERATOR_RB = "operator.rb";
  public static final String KEY_OPERATOR_BACK = "operator.back";
  public static final String KEY_OPERATOR_START = "operator.start";
  public static final String KEY_OPERATOR_LS = "operator.ls";
  public static final String KEY_OPERATOR_RS = "operator.rs";
  public static final String KEY_OPERATOR_DPAD_UP = "operator.dpad.up";
  public static final String KEY_OPERATOR_DPAD_RIGHT = "operator.dpad.right";
  public static final String KEY_OPERATOR_DPAD_DOWN = "operator.dpad.down";
  public static final String KEY_OPERATOR_DPAD_LEFT = "operator.dpad.left";
  public static final String KEY_OPERATOR_LEFT_X = "operator.left.x";
  public static final String KEY_OPERATOR_LEFT_Y = "operator.left.y";
  public static final String KEY_OPERATOR_RIGHT_X = "operator.right.x";
  public static final String KEY_OPERATOR_RIGHT_Y = "operator.right.y";
  public static final String KEY_OPERATOR_LEFT_TRIGGER = "operator.left.trigger";
  public static final String KEY_OPERATOR_RIGHT_TRIGGER = "operator.right.trigger";

  public static final String KEY_UI_SLIDER_1 = "ui.slider1";
  public static final String KEY_UI_SLIDER_2 = "ui.slider2";
  public static final String KEY_UI_BUTTON_1 = "ui.button1";
  public static final String KEY_UI_BUTTON_2 = "ui.button2";

  public static final String INPUT_KIND_BUTTON = "button";
  public static final String INPUT_KIND_DPAD = "dpad";
  public static final String INPUT_KIND_COMBO = "combo";
  public static final String INPUT_KIND_AXIS = "axis";

  public static final String AXIS_ID_LEFT_X = "leftX";
  public static final String AXIS_ID_LEFT_Y = "leftY";
  public static final String AXIS_ID_RIGHT_X = "rightX";
  public static final String AXIS_ID_RIGHT_Y = "rightY";
  public static final String AXIS_ID_LEFT_TRIGGER = "leftTrigger";
  public static final String AXIS_ID_RIGHT_TRIGGER = "rightTrigger";

  private static final String SEP = ".";
  private static final String SEG_DPAD = "dpad";
  private static final String SEG_LEFT = "left";
  private static final String SEG_RIGHT = "right";
  private static final String SEG_TRIGGER = "trigger";
  private static final String SEG_X = "x";
  private static final String SEG_Y = "y";
  private static final String EMPTY_STRING = "";

  private InputAliasResolver() {}

  /**
   * NAME
   *   resolve - Resolve an input alias to its canonical key.
   *
   * NOTES
   *   Performs a single alias lookup; chaining is not supported.
   */
  public static String resolve(String input, Map<String, String> aliases) {
    if (input == null || input.isBlank()) {
      return EMPTY_STRING;
    }
    String key = normalize(input);
    if (aliases == null || aliases.isEmpty()) {
      return key;
    }
    String target = aliases.get(key);
    if (target == null || target.isBlank()) {
      return key;
    }
    return normalize(target);
  }

  /**
   * NAME
   *   resolveAll - Resolve a set of input aliases to canonical keys.
   */
  public static Set<String> resolveAll(Iterable<String> inputs, Map<String, String> aliases) {
    if (inputs == null) {
      return Collections.emptySet();
    }
    Set<String> resolved = new HashSet<>();
    for (String input : inputs) {
      String key = resolve(input, aliases);
      if (!key.isBlank() && isSupportedCanonical(key)) {
        resolved.add(key);
      }
    }
    return resolved;
  }

  /**
   * NAME
   *   isSupportedCanonical - Check whether a canonical input key is supported.
   */
  public static boolean isSupportedCanonical(String key) {
    if (key == null || key.isBlank()) {
      return false;
    }
    String norm = normalize(key);
    return norm.equals(KEY_DRIVER_A)
        || norm.equals(KEY_DRIVER_B)
        || norm.equals(KEY_DRIVER_X)
        || norm.equals(KEY_DRIVER_Y)
        || norm.equals(KEY_DRIVER_LB)
        || norm.equals(KEY_DRIVER_RB)
        || norm.equals(KEY_DRIVER_BACK)
        || norm.equals(KEY_DRIVER_START)
        || norm.equals(KEY_DRIVER_LS)
        || norm.equals(KEY_DRIVER_RS)
        || norm.equals(KEY_DRIVER_DPAD_UP)
        || norm.equals(KEY_DRIVER_DPAD_RIGHT)
        || norm.equals(KEY_DRIVER_DPAD_DOWN)
        || norm.equals(KEY_DRIVER_DPAD_LEFT)
        || norm.equals(KEY_DRIVER_LEFT_X)
        || norm.equals(KEY_DRIVER_LEFT_Y)
        || norm.equals(KEY_DRIVER_RIGHT_X)
        || norm.equals(KEY_DRIVER_RIGHT_Y)
        || norm.equals(KEY_DRIVER_LEFT_TRIGGER)
        || norm.equals(KEY_DRIVER_RIGHT_TRIGGER)
        || norm.equals(KEY_OPERATOR_A)
        || norm.equals(KEY_OPERATOR_B)
        || norm.equals(KEY_OPERATOR_X)
        || norm.equals(KEY_OPERATOR_Y)
        || norm.equals(KEY_OPERATOR_LB)
        || norm.equals(KEY_OPERATOR_RB)
        || norm.equals(KEY_OPERATOR_BACK)
        || norm.equals(KEY_OPERATOR_START)
        || norm.equals(KEY_OPERATOR_LS)
        || norm.equals(KEY_OPERATOR_RS)
        || norm.equals(KEY_OPERATOR_DPAD_UP)
        || norm.equals(KEY_OPERATOR_DPAD_RIGHT)
        || norm.equals(KEY_OPERATOR_DPAD_DOWN)
        || norm.equals(KEY_OPERATOR_DPAD_LEFT)
        || norm.equals(KEY_OPERATOR_LEFT_X)
        || norm.equals(KEY_OPERATOR_LEFT_Y)
        || norm.equals(KEY_OPERATOR_RIGHT_X)
        || norm.equals(KEY_OPERATOR_RIGHT_Y)
        || norm.equals(KEY_OPERATOR_LEFT_TRIGGER)
        || norm.equals(KEY_OPERATOR_RIGHT_TRIGGER)
        || norm.equals(KEY_UI_SLIDER_1)
        || norm.equals(KEY_UI_SLIDER_2)
        || norm.equals(KEY_UI_BUTTON_1)
        || norm.equals(KEY_UI_BUTTON_2);
  }

  /**
   * NAME
   *   bindingAliasKey - Build an alias key for a button/dpad binding.
   */
  public static String bindingAliasKey(String controller, String inputKind, String inputId) {
    if (controller == null || inputKind == null || inputId == null) {
      return EMPTY_STRING;
    }
    String controllerKey = normalize(controller);
    String kind = normalize(inputKind);
    if (kind.equals(INPUT_KIND_BUTTON)) {
      return controllerKey + SEP + normalize(inputId);
    }
    if (kind.equals(INPUT_KIND_DPAD)) {
      return controllerKey + SEP + SEG_DPAD + SEP + normalize(inputId);
    }
    if (kind.equals(INPUT_KIND_AXIS)) {
      String axisSuffix = axisAliasSuffix(inputId);
      if (!axisSuffix.isBlank()) {
        return controllerKey + SEP + axisSuffix;
      }
    }
    return EMPTY_STRING;
  }

  /**
   * NAME
   *   axisAliasKey - Build an alias key for an axis binding.
   */
  public static String axisAliasKey(String controller, String axisId) {
    if (controller == null || axisId == null) {
      return EMPTY_STRING;
    }
    String axisSuffix = axisAliasSuffix(axisId);
    if (axisSuffix.isBlank()) {
      return EMPTY_STRING;
    }
    return normalize(controller) + SEP + axisSuffix;
  }

  private static String axisAliasSuffix(String axisId) {
    if (AXIS_ID_LEFT_X.equals(axisId)) {
      return SEG_LEFT + SEP + SEG_X;
    }
    if (AXIS_ID_LEFT_Y.equals(axisId)) {
      return SEG_LEFT + SEP + SEG_Y;
    }
    if (AXIS_ID_RIGHT_X.equals(axisId)) {
      return SEG_RIGHT + SEP + SEG_X;
    }
    if (AXIS_ID_RIGHT_Y.equals(axisId)) {
      return SEG_RIGHT + SEP + SEG_Y;
    }
    if (AXIS_ID_LEFT_TRIGGER.equals(axisId)) {
      return SEG_LEFT + SEP + SEG_TRIGGER;
    }
    if (AXIS_ID_RIGHT_TRIGGER.equals(axisId)) {
      return SEG_RIGHT + SEP + SEG_TRIGGER;
    }
    return EMPTY_STRING;
  }

  private static String normalize(String value) {
    return value == null ? EMPTY_STRING : value.trim().toLowerCase(Locale.ROOT);
  }
}
