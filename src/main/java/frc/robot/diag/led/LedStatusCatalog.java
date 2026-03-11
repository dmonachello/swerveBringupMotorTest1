package frc.robot.diag.led;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import edu.wpi.first.wpilibj.Filesystem;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * NAME
 * LedStatusCatalog
 *
 * SYNOPSIS
 * Loads per-vendor LED pattern meanings from deploy JSON files.
 *
 * DESCRIPTION
 * Resolves vendor pattern catalogs from deploy or local paths and caches them
 * for quick lookup during diagnostics.
 */
public final class LedStatusCatalog {
  private static final Gson GSON = new Gson();
  private static final Map<String, VendorCatalog> CACHE = new HashMap<>();

  private LedStatusCatalog() {}

  /**
   * NAME
   * lookup
   *
   * SYNOPSIS
   * Lookup a human-readable meaning for a vendor LED pattern.
   *
   * PARAMETERS
   * vendor - vendor name (e.g., REV, CTRE).
   * deviceType - optional device type key for device-specific patterns.
   * pattern - vendor-reported pattern identifier.
   *
   * RETURNS
   * A meaning string, or empty string when no mapping is available.
   */
  public static String lookup(String vendor, String deviceType, String pattern) {
    if (vendor == null || vendor.isBlank() || pattern == null || pattern.isBlank()) {
      return "";
    }
    VendorCatalog catalog = loadVendor(vendor);
    if (catalog == null) {
      return "";
    }
    if (deviceType != null && !deviceType.isBlank()) {
      Map<String, String> perDevice = catalog.devices.get(deviceType);
      if (perDevice != null && perDevice.containsKey(pattern)) {
        return perDevice.get(pattern);
      }
    }
    String meaning = catalog.patterns.get(pattern);
    return meaning != null ? meaning : "";
  }

  /**
   * NAME
   * loadVendor
   *
   * SYNOPSIS
   * Load or retrieve a cached vendor catalog.
   *
   * PARAMETERS
   * vendor - vendor name to load.
   *
   * RETURNS
   * A vendor catalog (possibly empty).
   */
  private static VendorCatalog loadVendor(String vendor) {
    String key = vendor.trim().toUpperCase();
    if (CACHE.containsKey(key)) {
      return CACHE.get(key);
    }
    VendorCatalog loaded = loadFromFile(key);
    CACHE.put(key, loaded);
    return loaded;
  }

  /**
   * NAME
   * loadFromFile
   *
   * SYNOPSIS
   * Load a vendor catalog from a JSON file.
   *
   * PARAMETERS
   * vendor - vendor name used to pick the catalog file.
   *
   * RETURNS
   * A populated catalog, or an empty catalog on error.
   *
   * ERRORS
   * Swallows parsing and I/O exceptions and returns an empty catalog.
   */
  private static VendorCatalog loadFromFile(String vendor) {
    String fileName;
    if ("REV".equals(vendor)) {
      fileName = "led_status_rev.json";
    } else if ("CTRE".equals(vendor)) {
      fileName = "led_status_ctre.json";
    } else {
      return VendorCatalog.empty();
    }

    Path path = resolvePath(fileName);
    if (path == null || !Files.exists(path)) {
      return VendorCatalog.empty();
    }
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      JsonElement root = GSON.fromJson(reader, JsonElement.class);
      if (root == null || !root.isJsonObject()) {
        return VendorCatalog.empty();
      }
      JsonObject obj = root.getAsJsonObject();
      VendorCatalog catalog = new VendorCatalog();
      JsonObject patterns = obj.has("patterns") && obj.get("patterns").isJsonObject()
          ? obj.getAsJsonObject("patterns")
          : null;
      if (patterns != null) {
        for (Map.Entry<String, JsonElement> entry : patterns.entrySet()) {
          if (entry.getValue().isJsonPrimitive()) {
            catalog.patterns.put(entry.getKey(), entry.getValue().getAsString());
          }
        }
      }
      JsonObject devices = obj.has("devices") && obj.get("devices").isJsonObject()
          ? obj.getAsJsonObject("devices")
          : null;
      if (devices != null) {
        for (Map.Entry<String, JsonElement> deviceEntry : devices.entrySet()) {
          if (!deviceEntry.getValue().isJsonObject()) {
            continue;
          }
          JsonObject devicePatterns = deviceEntry.getValue().getAsJsonObject();
          Map<String, String> map = new HashMap<>();
          for (Map.Entry<String, JsonElement> entry : devicePatterns.entrySet()) {
            if (entry.getValue().isJsonPrimitive()) {
              map.put(entry.getKey(), entry.getValue().getAsString());
            }
          }
          if (!map.isEmpty()) {
            catalog.devices.put(deviceEntry.getKey(), map);
          }
        }
      }
      return catalog;
    } catch (Exception ex) {
      return VendorCatalog.empty();
    }
  }

  /**
   * NAME
   * resolvePath
   *
   * SYNOPSIS
   * Resolve a deploy or development path for a catalog file.
   *
   * PARAMETERS
   * fileName - catalog file name.
   *
   * RETURNS
   * A path candidate, even if it does not exist.
   */
  private static Path resolvePath(String fileName) {
    try {
      Path deployPath = Filesystem.getDeployDirectory().toPath().resolve(fileName);
      if (Files.exists(deployPath)) {
        return deployPath;
      }
    } catch (Exception ex) {
      // Fall through to local dev path.
    }
    Path devPath = Path.of("src", "main", "deploy", fileName);
    if (Files.exists(devPath)) {
      return devPath;
    }
    return Path.of(fileName);
  }

  /**
   * NAME
   * VendorCatalog
   *
   * SYNOPSIS
   * In-memory catalog of vendor and device-specific patterns.
   */
  private static final class VendorCatalog {
    final Map<String, String> patterns = new HashMap<>();
    final Map<String, Map<String, String>> devices = new HashMap<>();

    static VendorCatalog empty() {
      return new VendorCatalog();
    }
  }
}
