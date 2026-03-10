package frc.robot.input;

import com.google.gson.Gson;
import com.google.gson.JsonParseException;
import edu.wpi.first.wpilibj.Filesystem;
import edu.wpi.first.wpilibj.XboxController;
import frc.robot.EdgeTrigger;
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

public final class BindingsManager {
  private static final String BINDINGS_FILE = "bringup_bindings.json";
  private static final Gson GSON = new Gson();

  private final List<BindingSpec> bindings = new ArrayList<>();
  private final List<AxisSpec> axes = new ArrayList<>();

  public BindingsManager() {
    loadBindings();
  }

  public BindingState sample(XboxController primary, XboxController secondary, EdgeTrigger edge) {
    BindingState state = new BindingState();
    for (int i = 0; i < bindings.size(); i++) {
      BindingSpec spec = bindings.get(i);
      XboxController controller = resolveController(spec.controller, primary, secondary);
      if (controller == null) {
        continue;
      }
      boolean active = isActive(controller, spec);
      String key = "bind_" + i + "_" + spec.command;
      boolean pressed = edge.pressed(key, active);
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
      XboxController controller = resolveController(spec.controller, primary, secondary);
      if (controller == null) {
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

  public List<String> describeBindings() {
    List<String> lines = new ArrayList<>();
    for (BindingSpec spec : bindings) {
      String mode = spec.mode != null ? spec.mode : "edge";
      lines.add(spec.command + ": " + spec.controller + " " + spec.input + " " + spec.id + " (" + mode + ")");
    }
    return lines;
  }

  public List<String> describeAxes() {
    List<String> lines = new ArrayList<>();
    for (AxisSpec spec : axes) {
      lines.add(spec.command + ": " + spec.controller + " axis " + spec.id + " (invert=" + spec.invert + ", deadband=" + spec.deadband + ")");
    }
    return lines;
  }

  private void loadBindings() {
    bindings.clear();
    axes.clear();
    Path path = resolvePath();
    if (path == null || !Files.exists(path)) {
      loadDefaultBindings();
      return;
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      BindingRoot root = GSON.fromJson(reader, BindingRoot.class);
      if (root == null) {
        loadDefaultBindings();
        return;
      }
      if (root.bindings != null) {
        bindings.addAll(root.bindings);
      }
      if (root.axes != null) {
        axes.addAll(root.axes);
      }
      if (bindings.isEmpty() && axes.isEmpty()) {
        loadDefaultBindings();
      }
      validateBindings();
    } catch (IOException | JsonParseException ex) {
      loadDefaultBindings();
    }
  }

  private void loadDefaultBindings() {
    bindings.clear();
    axes.clear();

    bindings.add(BindingSpec.edge("addMotor", "primary", "button", "A"));
    bindings.add(BindingSpec.edge("addAll", "primary", "button", "START"));
    bindings.add(BindingSpec.edge("printState", "primary", "button", "B"));
    bindings.add(BindingSpec.edge("printHealth", "primary", "dpad", "LEFT"));
    bindings.add(BindingSpec.edge("printCANcoder", "primary", "button", "RB"));
    bindings.add(BindingSpec.edge("printNTdiag", "primary", "dpad", "DOWN"));
    bindings.add(BindingSpec.edge("printCANdiag", "primary", "dpad", "UP"));
    bindings.add(BindingSpec.edge("printInputs", "primary", "dpad", "RIGHT"));
    bindings.add(BindingSpec.edge("printBindings", "primary", "button", "LB"));
    bindings.add(BindingSpec.edge("printTestsInfo", "primary", "combo", "LB+RB"));
    bindings.add(BindingSpec.edge("printTestsOverview", "primary", "button", "LS"));
    bindings.add(BindingSpec.edge("clearFaults", "primary", "button", "RS"));
    bindings.add(BindingSpec.edge("dumpReport", "primary", "button", "X"));
    bindings.add(BindingSpec.edge("toggleDashboard", "primary", "button", "Y"));
    bindings.add(BindingSpec.edge("profileToggle", "primary", "button", "BACK"));

    bindings.add(BindingSpec.edge("canSweep", "secondary", "button", "Y"));

    bindings.add(BindingSpec.edge("selectTestPrev", "secondary", "button", "LB"));
    bindings.add(BindingSpec.edge("selectTestNext", "secondary", "button", "RB"));
    bindings.add(BindingSpec.edge("toggleTest", "secondary", "button", "X"));
    bindings.add(BindingSpec.hold("runTest", "secondary", "button", "A"));
    bindings.add(BindingSpec.edge("runAllTests", "secondary", "button", "B"));

    bindings.add(BindingSpec.hold("fixedSpeed25", "secondary", "dpad", "UP"));
    bindings.add(BindingSpec.hold("fixedSpeed50", "secondary", "dpad", "RIGHT"));
    bindings.add(BindingSpec.hold("fixedSpeed75", "secondary", "dpad", "DOWN"));
    bindings.add(BindingSpec.hold("fixedSpeed100", "secondary", "dpad", "LEFT"));

    axes.add(AxisSpec.axis("leftDrive", "primary", "LY", true, 0.12));
    axes.add(AxisSpec.axis("rightDrive", "primary", "RY", true, 0.12));
  }

  private void validateBindings() {
    List<String> knownCommands = List.of(
        "addMotor",
        "addAll",
        "printState",
        "printHealth",
        "printCANcoder",
        "printNTdiag",
        "printCANdiag",
        "printInputs",
        "printBindings",
        "printTestsInfo",
        "printTestsOverview",
        "clearFaults",
        "dumpReport",
        "toggleDashboard",
        "profileToggle",
        "canSweep",
        "selectTestPrev",
        "selectTestNext",
        "toggleTest",
        "runTest",
        "runAllTests",
        "fixedSpeed25",
        "fixedSpeed50",
        "fixedSpeed75",
        "fixedSpeed100"
    );
    Map<String, Integer> bindingCounts = new HashMap<>();
    for (BindingSpec spec : bindings) {
      if (spec == null || spec.command == null) {
        continue;
      }
      String command = spec.command.trim();
      bindingCounts.put(command, bindingCounts.getOrDefault(command, 0) + 1);
      if (!knownCommands.contains(command)) {
        System.out.println("Warning: unknown binding command '" + command + "'.");
      }
    }
    for (Map.Entry<String, Integer> entry : bindingCounts.entrySet()) {
      if (entry.getValue() > 1) {
        System.out.println("Warning: duplicate binding for command '" + entry.getKey() + "'.");
      }
    }
    for (AxisSpec axis : axes) {
      if (axis == null || axis.command == null) {
        continue;
      }
      String command = axis.command.trim();
      if (!List.of("leftDrive", "rightDrive").contains(command)) {
        System.out.println("Warning: unknown axis command '" + command + "'.");
      }
    }
  }

  private boolean isActive(XboxController controller, BindingSpec spec) {
    if (spec == null || spec.input == null || spec.id == null) {
      return false;
    }
    String input = spec.input.trim().toLowerCase(Locale.ROOT);
    String id = spec.id.trim().toUpperCase(Locale.ROOT);
    if ("button".equals(input)) {
      return isButtonPressed(controller, id);
    }
    if ("dpad".equals(input)) {
      return isDpadPressed(controller, id);
    }
    if ("combo".equals(input)) {
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
    return switch (id) {
      case "LX" -> controller.getLeftX();
      case "LY" -> controller.getLeftY();
      case "RX" -> controller.getRightX();
      case "RY" -> controller.getRightY();
      default -> 0.0;
    };
  }

  private XboxController resolveController(String role, XboxController primary, XboxController secondary) {
    if (role == null) {
      return primary;
    }
    String normalized = role.trim().toLowerCase(Locale.ROOT);
    if ("secondary".equals(normalized)) {
      return secondary;
    }
    return primary;
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

  public static final class BindingState {
    private final Map<String, Boolean> pressed = new HashMap<>();
    private final Map<String, Boolean> holds = new HashMap<>();
    private final Map<String, Double> axes = new HashMap<>();

    public boolean pressed(String command) {
      return pressed.getOrDefault(command, false);
    }

    public boolean held(String command) {
      return holds.getOrDefault(command, false);
    }

    public double axis(String command) {
      return axes.getOrDefault(command, 0.0);
    }

    public boolean hasAxis(String command) {
      return axes.containsKey(command);
    }
  }

  private static final class BindingRoot {
    List<BindingSpec> bindings = Collections.emptyList();
    List<AxisSpec> axes = Collections.emptyList();
  }

  public static final class BindingSpec {
    String command;
    String controller;
    String input;
    String id;
    String mode;

    static BindingSpec edge(String command, String controller, String input, String id) {
      BindingSpec spec = new BindingSpec();
      spec.command = command;
      spec.controller = controller;
      spec.input = input;
      spec.id = id;
      spec.mode = "edge";
      return spec;
    }

    static BindingSpec hold(String command, String controller, String input, String id) {
      BindingSpec spec = new BindingSpec();
      spec.command = command;
      spec.controller = controller;
      spec.input = input;
      spec.id = id;
      spec.mode = "hold";
      return spec;
    }

    boolean isHoldMode() {
      return mode != null && mode.trim().equalsIgnoreCase("hold");
    }
  }

  public static final class AxisSpec {
    String command;
    String controller;
    String id;
    boolean invert = false;
    double deadband = 0.0;

    static AxisSpec axis(String command, String controller, String id, boolean invert, double deadband) {
      AxisSpec spec = new AxisSpec();
      spec.command = command;
      spec.controller = controller;
      spec.id = id;
      spec.invert = invert;
      spec.deadband = deadband;
      return spec;
    }
  }
}
