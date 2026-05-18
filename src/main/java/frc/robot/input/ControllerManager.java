package frc.robot.input;

import com.google.gson.Gson;
import com.google.gson.JsonParseException;
import edu.wpi.first.wpilibj.Filesystem;
import edu.wpi.first.wpilibj.XboxController;
import frc.robot.BringupPrinter;
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
import java.util.Map;

/**
 * NAME
 *   ControllerManager - Load controller specs and instantiate devices.
 *
 * DESCRIPTION
 *   Reads controller configuration from deploy JSON and builds controller
 *   instances for use in bindings.
 */
public final class ControllerManager {
  private static final String CONTROLLERS_FILE = "bringup_controllers.json";
  private static final String BINDINGS_FILE = "bringup_bindings.json";
  private static final String DEFAULT_CONTROLLER_PREFIX = "controller";
  private static final String MESSAGE_NO_CONTROLLER_CONFIG =
      "Warning: no controller configuration loaded; robot will run with no configured Xbox controllers.";
  private static final String MESSAGE_INVALID_CONTROLLER_CONFIG_FORMAT =
      "Warning: failed to load controller config %s: %s";
  private static final String MESSAGE_DROPPED_CONTROLLER_SPEC_FORMAT =
      "Warning: dropped invalid controller spec from %s at index %d: %s";
  private static final Gson GSON = new Gson();

  private final List<ControllerSpec> specs = new ArrayList<>();
  private final List<XboxController> xboxControllers = new ArrayList<>();
  private final Map<String, XboxController> xboxByName = new HashMap<>();

  /**
   * NAME
   *   ControllerManager - Construct and load controller specs.
   */
  public ControllerManager() {
    loadSpecs();
    initControllers();
  }

  /**
   * NAME
   *   getXbox - Return the Xbox controller at index.
   *
   * RETURNS
   *   XboxController or null if out of range.
   */
  public XboxController getXbox(int index) {
    if (index < 0 || index >= xboxControllers.size()) {
      return null;
    }
    return xboxControllers.get(index);
  }

  /**
   * NAME
   *   getXboxControllers - Return Xbox controllers by name.
   */
  public Map<String, XboxController> getXboxControllers() {
    return Collections.unmodifiableMap(xboxByName);
  }

  /**
   * NAME
   *   getSpecs - Return the configured controller specs.
   */
  public List<ControllerSpec> getSpecs() {
    return Collections.unmodifiableList(specs);
  }

  /**
   * NAME
   *   loadSpecs - Load controller specs from bindings/controllers JSON.
   */
  private void loadSpecs() {
    specs.clear();
    List<ControllerSpec> fromBindings = loadControllersFromBindings();
    if (!fromBindings.isEmpty()) {
      specs.addAll(fromBindings);
      normalizeSpecNames();
      return;
    }
    List<ControllerSpec> fromControllers = loadControllersFromFile();
    if (!fromControllers.isEmpty()) {
      specs.addAll(fromControllers);
      normalizeSpecNames();
      return;
    }
    BringupPrinter.enqueue(MESSAGE_NO_CONTROLLER_CONFIG);
  }

  /**
   * NAME
   *   initControllers - Instantiate controller objects from specs.
   */
  private void initControllers() {
    xboxControllers.clear();
    xboxByName.clear();
    for (ControllerSpec spec : specs) {
      if (spec == null || spec.type == null || spec.port == null) {
        continue;
      }
      if (spec.type == ControllerType.XBOX) {
        XboxController controller = new XboxController(spec.port);
        xboxControllers.add(controller);
        if (spec.name != null && !spec.name.isBlank()) {
          xboxByName.put(spec.name, controller);
        }
      }
    }
  }

  /**
   * NAME
   *   loadControllersFromBindings - Load controller specs from bindings JSON.
   */
  private List<ControllerSpec> loadControllersFromBindings() {
    Path path = resolvePath(BINDINGS_FILE);
    if (path == null || !Files.exists(path)) {
      return Collections.emptyList();
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      BindingRoot root = GSON.fromJson(reader, BindingRoot.class);
      if (root == null || root.controllers == null || root.controllers.isEmpty()) {
        return Collections.emptyList();
      }
      return sanitizeSpecs(root.controllers, path.toString());
    } catch (IOException | JsonParseException ex) {
      BringupPrinter.enqueue(String.format(
          MESSAGE_INVALID_CONTROLLER_CONFIG_FORMAT,
          path,
          ex.getMessage()));
      return Collections.emptyList();
    }
  }

  /**
   * NAME
   *   loadControllersFromFile - Load controller specs from controllers JSON.
   */
  private List<ControllerSpec> loadControllersFromFile() {
    Path path = resolvePath(CONTROLLERS_FILE);
    if (path == null || !Files.exists(path)) {
      return Collections.emptyList();
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      ControllerRoot root = GSON.fromJson(reader, ControllerRoot.class);
      if (root == null || root.controllers == null || root.controllers.isEmpty()) {
        return Collections.emptyList();
      }
      return sanitizeSpecs(root.controllers, path.toString());
    } catch (IOException | JsonParseException ex) {
      BringupPrinter.enqueue(String.format(
          MESSAGE_INVALID_CONTROLLER_CONFIG_FORMAT,
          path,
          ex.getMessage()));
      return Collections.emptyList();
    }
  }

  private List<ControllerSpec> sanitizeSpecs(List<ControllerSpec> rawSpecs, String sourceLabel) {
    List<ControllerSpec> sanitized = new ArrayList<>();
    for (int index = 0; index < rawSpecs.size(); index++) {
      ControllerSpec spec = rawSpecs.get(index);
      String reason = getInvalidSpecReason(spec);
      if (reason != null) {
        BringupPrinter.enqueue(String.format(
            MESSAGE_DROPPED_CONTROLLER_SPEC_FORMAT,
            sourceLabel,
            index,
            reason));
        continue;
      }
      sanitized.add(spec);
    }
    return sanitized;
  }

  private String getInvalidSpecReason(ControllerSpec spec) {
    if (spec == null) {
      return "entry was null";
    }
    if (spec.type == null) {
      return "missing type";
    }
    if (spec.port == null) {
      return "missing port";
    }
    if (spec.port < 0) {
      return "negative port";
    }
    return null;
  }

  private void normalizeSpecNames() {
    for (ControllerSpec spec : specs) {
      if (spec == null) {
        continue;
      }
      if ((spec.name == null || spec.name.isBlank()) && spec.port != null && spec.port >= 0) {
        spec.name = DEFAULT_CONTROLLER_PREFIX + spec.port;
      }
    }
  }

  /**
   * NAME
   *   resolvePath - Resolve deploy path with dev fallback.
   */
  private Path resolvePath(String fileName) {
    try {
      Path deployPath = Filesystem.getDeployDirectory().toPath().resolve(fileName);
      if (Files.exists(deployPath)) {
        return deployPath;
      }
    } catch (Exception ex) {
      // Fall through to local dev path.
    }
    Path devPath = Paths.get("src", "main", "deploy", fileName);
    if (Files.exists(devPath)) {
      return devPath;
    }
    return Paths.get(fileName);
  }

  /**
   * NAME
   *   ControllerRoot - JSON root for controller file.
   */
  private static final class ControllerRoot {
    List<ControllerSpec> controllers = Collections.emptyList();
  }

  /**
   * NAME
   *   BindingRoot - JSON root for bindings file.
   */
  private static final class BindingRoot {
    List<ControllerSpec> controllers = Collections.emptyList();
  }
}
