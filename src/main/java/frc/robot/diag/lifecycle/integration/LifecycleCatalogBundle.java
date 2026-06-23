package frc.robot.diag.lifecycle.integration;

import frc.robot.diag.lifecycle.devices.DeviceCatalog;
import frc.robot.diag.lifecycle.groups.GroupCatalog;
import frc.robot.diag.lifecycle.labels.LabelResolver;

/**
 * NAME
 *     LifecycleCatalogBundle - passive lifecycle catalog snapshot rebuilt from real profile data.
 *
 * PARAMETERS
 *     profileName - source profile name.
 *     deviceCatalog - resolved lifecycle device catalog.
 *     groupCatalog - resolved lifecycle group catalog.
 *     labelResolver - resolver over the device/group catalogs.
 */
public record LifecycleCatalogBundle(
        String profileName,
        DeviceCatalog deviceCatalog,
        GroupCatalog groupCatalog,
        LabelResolver labelResolver) {}
