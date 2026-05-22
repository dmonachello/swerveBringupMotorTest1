package frc.robot.input;

import frc.robot.BringupPrinter;
import com.google.gson.Gson;
import com.google.gson.JsonParseException;
import edu.wpi.first.wpilibj.Filesystem;
import edu.wpi.first.wpilibj.XboxController;
import frc.robot.EdgeTrigger;
import frc.robot.commands.local.RobotLocalCommandRegistry;
import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * NAME
 *   BindingsManager - Load and evaluate controller bindings.
 *
 * DESCRIPTION
 *   Parses bringup_bindings.json and provides runtime sampling of buttons
 *   and axes into named commands. Missing or invalid config results in an
 *   empty binding set instead of code-defined controller defaults.
 */
public final class BindingsManager {
  private static final String BINDINGS_FILE = "bringup_bindings.json";
  private static final String JSON_KEY_INPUT_ALIASES = "inputAliases";
  private static final String MESSAGE_BINDINGS_CONFIG_MISSING_FORMAT =
      "Warning: bindings config not found: %s. Robot will run with no controller bindings.";
  private static final String MESSAGE_BINDINGS_CONFIG_EMPTY_FORMAT =
      "Warning: bindings config root was empty: %s. Robot will run with no controller bindings.";
  private static final String MESSAGE_BINDINGS_CONFIG_INVALID_FORMAT =
      "Warning: failed to load bindings config %s: %s. Robot will run with no controller bindings.";
  private static final Gson GSON = new Gson();

  private final List<BindingSpec> bindings = new ArrayList<>();
  private final List<AxisSpec> axes = new ArrayList<>();
  private Map<String, String> inputAliases = new HashMap<>();

  /**
   * NAME
   *   BindingsManager - Construct and load bindings.
   */
  public BindingsManager() {
    loadBindings();
  }

  /**
   * NAME
   *   sample - Sample controller inputs into a BindingState.
   *
   * PARAMETERS
   *   controllers - Named Xbox controller map.
   *   edge - EdgeTrigger for rising-edge detection.
   *
   * RETURNS
   *   BindingState snapshot for this cycle.
   */
  public BindingState sample(Map<String, XboxController> controllers, EdgeTrigger edge) {
    return sample(controllers, edge, Collections.emptySet(), inputAliases);
  }

  /**
   * NAME
   *   sample - Sample controller inputs into a BindingState with local overrides.
   *
   * PARAMETERS
   *   controllers - Named Xbox controller map.
   *   edge - EdgeTrigger for rising-edge detection.
   *   localOverrides - Local binding inputs that should suppress globals.
   *   aliases - Alias map for input resolution.
   *
   * RETURNS
   *   BindingState snapshot for this cycle.
   */
  public BindingState sample(
      Map<String, XboxController> controllers,
      EdgeTrigger edge,
      Set<String> localOverrides,
      Map<String, String> aliases) {
    Set<String> overrides = InputAliasResolver.resolveAll(localOverrides, aliases);
    BindingState state = new BindingState();
    for (int i = 0; i < bindings.size(); i++) {
      BindingSpec spec = bindings.get(i);
      XboxController controller = resolveController(spec.controller, controllers);
      if (controller == null) {
        continue;
      }
      boolean active = isActive(controller, spec);
      String key = "bind_" + i + "_" + spec.command;
      boolean pressed = edge.pressed(key, active);
      if (isBindingSuppressed(spec, overrides, aliases)) {
        continue;
      }
      boolean hold = active;
      if (spec.isHoldMode()) {
        state.holds.put(spec.command, hold);
        if (pressed) {
          state.pressed.put(spec.command, true);
        }
      } else {
        if (pressed) {
          state.pressed.put(spec.command, true);
        }
      }
    }

    for (AxisSpec spec : axes) {
      XboxController controller = resolveController(spec.controller, controllers);
      if (controller == null) {
        continue;
      }
      if (isAxisSuppressed(spec, overrides, aliases)) {
        continue;
      }
      double value = readAxis(controller, spec.id);
      if (spec.invert) {
        value = -value;
      }
      if (Math.abs(value) < spec.deadband) {
        value = 0.0;
      }
      state.axes.put(spec.command, value);
    }
    return state;
  }

  /**
   * NAME
   *   getInputAliases - Return configured input alias mapping.
   */
  public Map<String, String> getInputAliases() {
    return Collections.unmodifiableMap(inputAliases);
  }

  /**
   * NAME
   *   describeBindings - Return human-readable binding descriptions.
   */
  public List<String> describeBindings() {
    List<String> lines = new ArrayList<>();
    for (BindingSpec spec : bindings) {
      String mode = spec.mode != null ? spec.mode : "edge";
      lines.add(spec.command + ": " + spec.controller + " " + spec.input + " " + spec.id + " (" + mode + ")");
    }
    return lines;
  }

  /**
   * NAME
   *   describeAxes - Return human-readable axis descriptions.
   */
  public List<String> describeAxes() {
    List<String> lines = new ArrayList<>();
    for (AxisSpec spec : axes) {
      lines.add(spec.command + ": " + spec.controller + " axis " + spec.id + " (invert=" + spec.invert + ", deadband=" + spec.deadband + ")");
    }
    return lines;
  }

  /**
   * NAME
   *   describeBinding - Return a human-readable binding for a command.
   *
   * PARAMETERS
   *   command - Logical command name to resolve.
   *
   * RETURNS
   *   Binding description, or "(unbound)" if not found.
   */
  public String describeBinding(String command) {
    if (command == null || command.isBlank()) {
      return "(unbound)";
    }
    for (BindingSpec spec : bindings) {
      if (!command.equals(spec.command)) {
        continue;
      }
      String mode = spec.mode != null ? spec.mode : "edge";
      return spec.controller + " " + spec.input + " " + spec.id + " (" + mode + ")";
    }
    return "(unbound)";
  }

  private boolean isBindingSuppressed(
      BindingSpec spec,
      Set<String> overrides,
      Map<String, String> aliases) {
    if (spec == null || overrides == null || overrides.isEmpty()) {
      return false;
    }
    String aliasKey = InputAliasResolver.bindingAliasKey(
        spec.controller, spec.input, spec.id);
    if (aliasKey.isBlank()) {
      return false;
    }
    String canonical = InputAliasResolver.resolve(aliasKey, aliases);
    if (canonical.isBlank()) {
      return false;
    }
    return overrides.contains(canonical);
  }

  private boolean isAxisSuppressed(
      AxisSpec spec,
      Set<String> overrides,
      Map<String, String> aliases) {
    if (spec == null || overrides == null || overrides.isEmpty()) {
      return false;
    }
    String aliasKey = InputAliasResolver.axisAliasKey(spec.controller, spec.id);
    if (aliasKey.isBlank()) {
      return false;
    }
    String canonical = InputAliasResolver.resolve(aliasKey, aliases);
    if (canonical.isBlank()) {
      return false;
    }
    return overrides.contains(canonical);
  }

  private void loadBindings() {
    clearLoadedBindings();
    Path path = resolvePath();
    if (path == null || !Files.exists(path)) {
      loadEmptyBindings(String.format(MESSAGE_BINDINGS_CONFIG_MISSING_FORMAT, path));
      return;
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      BindingRoot root = GSON.fromJson(reader, BindingRoot.class);
      if (root == null) {
        loadEmptyBindings(String.format(MESSAGE_BINDINGS_CONFIG_EMPTY_FORMAT, path));
        return;
      }
      if (root.bindings != null) {
        bindings.addAll(root.bindings);
      }
      if (root.axes != null) {
        axes.addAll(root.axes);
      }
      if (root.inputAliases != null) {
        inputAliases = new HashMap<>(root.inputAliases);
      } else {
        inputAliases = new HashMap<>();
      }
      validateBindings();
    } catch (IOException | JsonParseException ex) {
      loadEmptyBindings(String.format(
          MESSAGE_BINDINGS_CONFIG_INVALID_FORMAT,
          path,
          ex.getMessage()));
    }
  }

  private void clearLoadedBindings() {
    bindings.clear();
    axes.clear();
    inputAliases = new HashMap<>();
  }

  private void loadEmptyBindings(String warningText) {
    clearLoadedBindings();
    if (warningText != null && !warningText.isBlank()) {
      BringupPrinter.enqueue(warningText);
    }
  }

  private void validateBindings() {
    Map<String, Integer> bindingCounts = new HashMap<>();
    for (BindingSpec spec : bindings) {
      if (spec == null || spec.command == null) {
        continue;
      }
      String command = spec.command.trim();
      bindingCounts.put(command, bindingCounts.getOrDefault(command, 0) + 1);
      if (!RobotLocalCommandRegistry.isKnownCommand(command)) {
        BringupPrinter.enqueue("Warning: unknown binding command '" + command + "'.");
      }
    }
    for (Map.Entry<String, Integer> entry : bindingCounts.entrySet()) {
      if (entry.getValue() > 1) {
        BringupPrinter.enqueue("Warning: duplicate binding for command '" + entry.getKey() + "'.");
      }
    }
    for (AxisSpec axis : axes) {
      if (axis == null || axis.command == null) {
        continue;
      }
      String command = axis.command.trim();
      if (!RobotLocalCommandRegistry.isKnownAxisCommand(command)) {
        BringupPrinter.enqueue("Warning: unknown axis command '" + command + "'.");
      }
    }
  }

  private boolean isActive(XboxController controller, BindingSpec spec) {
    if (spec == null || spec.input == null || spec.id == null) {
      return false;
    }
    String input = spec.input.trim().toLowerCase(Locale.ROOT);
    String id = spec.id.trim().toUpperCase(Locale.ROOT);
    if (InputAliasResolver.INPUT_KIND_BUTTON.equals(input)) {
      return isButtonPressed(controller, id);
    }
    if (InputAliasResolver.INPUT_KIND_DPAD.equals(input)) {
      return isDpadPressed(controller, id);
    }
    if (InputAliasResolver.INPUT_KIND_COMBO.equals(input)) {
      return isComboPressed(controller, id);
    }
    return false;
  }

  private boolean isButtonPressed(XboxController controller, String id) {
    return switch (id) {
      case "A" -> controller.getAButton();
      case "B" -> controller.getBButton();
      case "X" -> controller.getXButton();
      case "Y" -> controller.getYButton();
      case "LB" -> controller.getLeftBumperButton();
      case "RB" -> controller.getRightBumperButton();
      case "BACK" -> controller.getBackButton();
      case "START" -> controller.getStartButton();
      case "LS" -> controller.getLeftStickButton();
      case "RS" -> controller.getRightStickButton();
      default -> false;
    };
  }

  private boolean isDpadPressed(XboxController controller, String id) {
    int pov = controller.getPOV();
    return switch (id) {
      case "UP" -> pov == 0;
      case "RIGHT" -> pov == 90;
      case "DOWN" -> pov == 180;
      case "LEFT" -> pov == 270;
      default -> false;
    };
  }

  private boolean isComboPressed(XboxController controller, String id) {
    String[] parts = id.split("\\+");
    for (String part : parts) {
      String token = part.trim().toUpperCase(Locale.ROOT);
      if (token.startsWith("DPAD_")) {
        if (!isDpadPressed(controller, token.substring("DPAD_".length()))) {
          return false;
        }
      } else if (!isButtonPressed(controller, token)) {
        return false;
      }
    }
    return true;
  }

  private double readAxis(XboxController controller, String id) {
    if (id == null) {
      return 0.0;
    }
    return switch (id) {
      case InputAliasResolver.AXIS_ID_LEFT_X -> controller.getLeftX();
      case InputAliasResolver.AXIS_ID_LEFT_Y -> controller.getLeftY();
      case InputAliasResolver.AXIS_ID_RIGHT_X -> controller.getRightX();
      case InputAliasResolver.AXIS_ID_RIGHT_Y -> controller.getRightY();
      case InputAliasResolver.AXIS_ID_LEFT_TRIGGER -> controller.getLeftTriggerAxis();
      case InputAliasResolver.AXIS_ID_RIGHT_TRIGGER -> controller.getRightTriggerAxis();
      default -> 0.0;
    };
  }

  private XboxController resolveController(String name, Map<String, XboxController> controllers) {
    if (name == null || controllers == null) {
      return null;
    }
    return controllers.get(name);
  }

  private Path resolvePath() {
    try {
      Path deployPath = Filesystem.getDeployDirectory().toPath().resolve(BINDINGS_FILE);
      if (Files.exists(deployPath)) {
        return deployPath;
      }
    } catch (Exception ex) {
      // Fall through to local dev path.
    }
    Path devPath = Paths.get("src", "main", "deploy", BINDINGS_FILE);
    if (Files.exists(devPath)) {
      return devPath;
    }
    return Paths.get(BINDINGS_FILE);
  }

  /**
   * NAME
   *   BindingState - Snapshot of button/axis states.
   */
  public static final class BindingState {
    private final Map<String, Boolean> pressed = new HashMap<>();
    private final Map<String, Boolean> holds = new HashMap<>();
    private final Map<String, Double> axes = new HashMap<>();

    /**
     * NAME
     *   pressed - Return rising-edge state for a command.
     */
    public boolean pressed(String command) {
      return pressed.getOrDefault(command, false);
    }

    /**
     * NAME
     *   held - Return current held state for a command.
     */
    public boolean held(String command) {
      return holds.getOrDefault(command, false);
    }

    /**
     * NAME
     *   axis - Return axis value for a command.
     */
    public double axis(String command) {
      return axes.getOrDefault(command, 0.0);
    }

    /**
     * NAME
     *   hasAxis - Return whether an axis binding exists for a command.
     */
    public boolean hasAxis(String command) {
      return axes.containsKey(command);
    }
  }

  private static final class BindingRoot {
    List<BindingSpec> bindings = Collections.emptyList();
    List<AxisSpec> axes = Collections.emptyList();
    @com.google.gson.annotations.SerializedName(JSON_KEY_INPUT_ALIASES)
    Map<String, String> inputAliases = Collections.emptyMap();
  }

  /**
   * NAME
   *   BindingSpec - JSON binding specification.
   */
  public static final class BindingSpec {
    String command;
    String controller;
    String input;
    String id;
    String mode;

    boolean isHoldMode() {
      return mode != null && mode.trim().equalsIgnoreCase("hold");
    }
  }

  /**
   * NAME
   *   AxisSpec - JSON axis specification.
   */
  public static final class AxisSpec {
    String command;
    String controller;
    String id;
    boolean invert = false;
    double deadband = 0.0;
  }

}
