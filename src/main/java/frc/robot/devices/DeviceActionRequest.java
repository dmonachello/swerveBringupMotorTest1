package frc.robot.devices;

/**
 * NAME
 *   DeviceActionRequest - Device action payload for non-motor tests.
 *
 * DESCRIPTION
 *   Carries a parsed action request (such as LED commands) to device units
 *   that support device-specific actions.
 */
public final class DeviceActionRequest {
  public static final String ACTION_TOGGLE_LED = "toggle_led";
  public static final String ACTION_SET_COLOR = "set_color";
  public static final String PATTERN_SOLID = "solid";
  public static final String COLOR_PREFIX = "#";
  public static final int COLOR_HEX_LENGTH = 7;
  public static final int COLOR_HEX_BODY_START = 1;
  public static final int COLOR_RADIX = 16;
  public static final int COLOR_SHIFT_RED = 16;
  public static final int COLOR_SHIFT_GREEN = 8;
  public static final int COLOR_SHIFT_BLUE = 0;
  public static final int COLOR_MASK = 0xFF;
  public static final int INT_ZERO = 0;
  public static final int INT_MAX = 255;
  public static final double BRIGHTNESS_MIN = 0.0;
  public static final double BRIGHTNESS_MAX = 1.0;
  public static final double BRIGHTNESS_DEFAULT = 1.0;

  public final String action;
  public final RgbColor color;
  public final String pattern;
  public final double brightness;
  public final Double durationSec;

  /**
   * NAME
   *   DeviceActionRequest - Construct a parsed device action request.
   */
  public DeviceActionRequest(
      String action,
      RgbColor color,
      String pattern,
      Double brightness,
      Double durationSec) {
    this.action = action;
    this.color = color;
    this.pattern = pattern;
    this.brightness = normalizeBrightness(brightness);
    this.durationSec = durationSec;
  }

  /**
   * NAME
   *   isAction - Compare against a known action string.
   */
  public boolean isAction(String expected) {
    if (expected == null || action == null) {
      return false;
    }
    return expected.equalsIgnoreCase(action);
  }

  /**
   * NAME
   *   isSolidPattern - Check for solid/empty pattern.
   */
  public boolean isSolidPattern() {
    if (pattern == null || pattern.isBlank()) {
      return true;
    }
    return PATTERN_SOLID.equalsIgnoreCase(pattern.trim());
  }

  /**
   * NAME
   *   normalizeBrightness - Clamp brightness to [0, 1].
   */
  public static double normalizeBrightness(Double value) {
    if (value == null) {
      return BRIGHTNESS_DEFAULT;
    }
    double raw = value.doubleValue();
    if (raw < BRIGHTNESS_MIN) {
      return BRIGHTNESS_MIN;
    }
    if (raw > BRIGHTNESS_MAX) {
      return BRIGHTNESS_MAX;
    }
    return raw;
  }

  /**
   * NAME
   *   parseColor - Parse #RRGGBB into RGB components.
   */
  public static RgbColor parseColor(String value) {
    if (value == null || value.isBlank()) {
      return null;
    }
    String trimmed = value.trim();
    if (!trimmed.startsWith(COLOR_PREFIX) || trimmed.length() != COLOR_HEX_LENGTH) {
      return null;
    }
    String hex = trimmed.substring(COLOR_HEX_BODY_START);
    int packed;
    try {
      packed = Integer.parseInt(hex, COLOR_RADIX);
    } catch (NumberFormatException ex) {
      return null;
    }
    int red = (packed >> COLOR_SHIFT_RED) & COLOR_MASK;
    int green = (packed >> COLOR_SHIFT_GREEN) & COLOR_MASK;
    int blue = (packed >> COLOR_SHIFT_BLUE) & COLOR_MASK;
    if (!isComponentValid(red) || !isComponentValid(green) || !isComponentValid(blue)) {
      return null;
    }
    return new RgbColor(red, green, blue);
  }

  /**
   * NAME
   *   scaleComponent - Apply brightness scaling to a color component.
   */
  public static int scaleComponent(int component, double brightness) {
    double scaled = component * brightness;
    if (scaled < INT_ZERO) {
      return INT_ZERO;
    }
    if (scaled > INT_MAX) {
      return INT_MAX;
    }
    return (int) Math.round(scaled);
  }

  private static boolean isComponentValid(int value) {
    return value >= INT_ZERO && value <= INT_MAX;
  }

  /**
   * NAME
   *   RgbColor - Simple RGB tuple.
   */
  public static final class RgbColor {
    public final int red;
    public final int green;
    public final int blue;

    public RgbColor(int red, int green, int blue) {
      this.red = red;
      this.green = green;
      this.blue = blue;
    }
  }
}
