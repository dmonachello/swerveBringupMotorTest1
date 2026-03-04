package frc.robot.input;

import com.google.gson.Gson;
import com.google.gson.JsonParseException;
import edu.wpi.first.wpilibj.Filesystem;
import edu.wpi.first.wpilibj.XboxController;
import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class ControllerManager {
  private static final String CONTROLLERS_FILE = "bringup_controllers.json";
  private static final Gson GSON = new Gson();

  private final List<ControllerSpec> specs = new ArrayList<>();
  private final List<XboxController> xboxControllers = new ArrayList<>();

  public ControllerManager() {
    loadSpecs();
    initControllers();
  }

  public XboxController getXbox(int index) {
    if (index < 0 || index >= xboxControllers.size()) {
      return null;
    }
    return xboxControllers.get(index);
  }

  public List<ControllerSpec> getSpecs() {
    return Collections.unmodifiableList(specs);
  }

  private void loadSpecs() {
    specs.clear();
    Path path = resolvePath();
    if (path == null || !Files.exists(path)) {
      addDefaultSpecs();
      return;
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      ControllerRoot root = GSON.fromJson(reader, ControllerRoot.class);
      if (root == null || root.controllers == null || root.controllers.isEmpty()) {
        addDefaultSpecs();
        return;
      }
      specs.addAll(root.controllers);
    } catch (IOException | JsonParseException ex) {
      addDefaultSpecs();
    }
  }

  private void addDefaultSpecs() {
    ControllerSpec primary = new ControllerSpec();
    primary.type = ControllerType.XBOX;
    primary.port = 0;
    primary.role = "primary";
    ControllerSpec secondary = new ControllerSpec();
    secondary.type = ControllerType.XBOX;
    secondary.port = 1;
    secondary.role = "secondary";
    specs.add(primary);
    specs.add(secondary);
  }

  private void initControllers() {
    xboxControllers.clear();
    for (ControllerSpec spec : specs) {
      if (spec == null || spec.type == null) {
        continue;
      }
      if (spec.type == ControllerType.XBOX) {
        xboxControllers.add(new XboxController(spec.port));
      }
    }
  }

  private Path resolvePath() {
    try {
      Path deployPath = Filesystem.getDeployDirectory().toPath().resolve(CONTROLLERS_FILE);
      if (Files.exists(deployPath)) {
        return deployPath;
      }
    } catch (Exception ex) {
      // Fall through to local dev path.
    }
    Path devPath = Paths.get("src", "main", "deploy", CONTROLLERS_FILE);
    if (Files.exists(devPath)) {
      return devPath;
    }
    return Paths.get(CONTROLLERS_FILE);
  }

  private static final class ControllerRoot {
    List<ControllerSpec> controllers = Collections.emptyList();
  }
}
