package frc.robot.manufacturers;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Supplier;

/**
 * NAME
 *   ManufacturerRegistry - Static registry for manufacturer group construction.
 *
 * SYNOPSIS
 *   Central list of manufacturer factories used to build device groups.
 *
 * DESCRIPTION
 *   Keeps the "add a manufacturer" edit in one place and produces a fresh
 *   list of ManufacturerGroup instances for each bringup core.
 *
 * NOTES
 *   To add a new manufacturer, append a factory entry in FACTORIES using the
 *   vendor's ManufacturerGroup implementation.
 */
public final class ManufacturerRegistry {
  private static final List<ManufacturerFactory> FACTORIES = List.of(
      new ManufacturerFactory("REV", RevDeviceGroup::new),
      new ManufacturerFactory("CTRE", CtreDeviceGroup::new));

  private ManufacturerRegistry() {
  }

  /**
   * NAME
   *   buildGroups - Construct a fresh list of manufacturer groups.
   *
   * RETURNS
   *   Unmodifiable list of newly constructed groups.
   */
  public static List<ManufacturerGroup> buildGroups() {
    List<ManufacturerGroup> groups = new ArrayList<>(FACTORIES.size());
    for (ManufacturerFactory factory : FACTORIES) {
      groups.add(factory.factory().get());
    }
    return Collections.unmodifiableList(groups);
  }

  /**
   * NAME
   *   indexByVendor - Build a vendor lookup map for groups.
   *
   * PARAMETERS
   *   groups - list of groups to index.
   *
   * RETURNS
   *   Unmodifiable map keyed by lowercase vendor string.
   */
  public static Map<String, ManufacturerGroup> indexByVendor(List<ManufacturerGroup> groups) {
    if (groups == null || groups.isEmpty()) {
      return Collections.emptyMap();
    }
    Map<String, ManufacturerGroup> map = new HashMap<>();
    for (ManufacturerGroup group : groups) {
      if (group == null || group.getHeader() == null) {
        continue;
      }
      String vendor = group.getHeader().vendor();
      if (vendor == null || vendor.isBlank()) {
        continue;
      }
      map.put(vendor.toLowerCase(Locale.ROOT), group);
    }
    return Collections.unmodifiableMap(map);
  }

  /**
   * NAME
   *   ManufacturerFactory - Vendor name and group constructor pairing.
   */
  private record ManufacturerFactory(String vendor, Supplier<ManufacturerGroup> factory) {
  }
}
