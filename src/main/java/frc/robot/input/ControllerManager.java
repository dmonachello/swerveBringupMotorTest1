package frc.robot.input;

import frc.robot.BringupUtil;
import edu.wpi.first.wpilibj.XboxController;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
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
  private static final String DEFAULT_CONTROLLER_PREFIX = "controller";

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
   *   loadSpecs - Load controller specs from unified profile devices.
   */
  private void loadSpecs() {
    specs.clear();
    List<ControllerSpec> fromProfiles = loadControllersFromProfiles();
    if (!fromProfiles.isEmpty()) {
      specs.addAll(fromProfiles);
      normalizeSpecNames();
      return;
    }
  }

  /**
   * NAME
   *   initControllers - Instantiate controller objects from specs.
   */
  private void initControllers() {
    xboxControllers.clear();
    xboxByName.clear();
    for (ControllerSpec spec : specs) {
      if (spec == null || spec.type == null) {
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
   *   loadControllersFromProfiles - Load controller specs from bringup_system.json.
   */
  private List<ControllerSpec> loadControllersFromProfiles() {
    Map<String, Integer> configured = new LinkedHashMap<>(BringupUtil.getConfiguredControllerPorts());
    if (configured.isEmpty()) {
      return Collections.emptyList();
    }
    List<ControllerSpec> loaded = new ArrayList<>();
    for (Map.Entry<String, Integer> entry : configured.entrySet()) {
      ControllerSpec spec = new ControllerSpec();
      spec.type = ControllerType.XBOX;
      spec.name = entry.getKey();
      spec.port = entry.getValue();
      loaded.add(spec);
    }
    return loaded;
  }

  private void normalizeSpecNames() {
    for (ControllerSpec spec : specs) {
      if (spec == null) {
        continue;
      }
      if (spec.name == null || spec.name.isBlank()) {
        spec.name = DEFAULT_CONTROLLER_PREFIX + spec.port;
      }
    }
  }

}
