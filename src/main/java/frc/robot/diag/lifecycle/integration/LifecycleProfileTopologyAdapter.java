package frc.robot.diag.lifecycle.integration;

import frc.robot.BridgeGroupManager;
import frc.robot.BringupUtil;
import frc.robot.diag.lifecycle.devices.DeviceCatalog;
import frc.robot.diag.lifecycle.devices.DeviceDeclaration;
import frc.robot.diag.lifecycle.devices.DeviceLifecycleKind;
import frc.robot.diag.lifecycle.groups.GroupCatalog;
import frc.robot.diag.lifecycle.groups.GroupDeclaration;
import frc.robot.diag.lifecycle.groups.GroupKind;
import frc.robot.diag.lifecycle.groups.GroupRecord;
import frc.robot.diag.lifecycle.labels.LabelResolver;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * NAME
 *     LifecycleProfileTopologyAdapter - adapt real bringup profile data into lifecycle catalogs.
 *
 * DESCRIPTION
 *     This adapter is the integration seam between existing BringupUtil profile/config data and
 *     the new lifecycle model. It merges static profile groups with runtime-only bridge groups and
 *     intentionally performs no activation or hardware work.
 */
public final class LifecycleProfileTopologyAdapter {
    private static final String GROUP_ACTIVE = "active-group";
    private static final String TYPE_PDH = "PDH";
    private static final String TYPE_PDP = "PDP";
    private static final String TYPE_ROBORIO = "robotController";
    private static final String TYPE_XBOX_CONTROLLER = "xboxController";

    private LifecycleProfileTopologyAdapter() {}

    /**
     * NAME
     *     build - create lifecycle catalogs from one profile's current devices and bridge groups.
     *
     * PARAMETERS
     *     profileName - source profile name.
     *     deviceEntries - current profile device entries.
     *     bridgeConfig - current profile bridge-group configuration.
     *
     * RETURNS
     *     A passive lifecycle catalog bundle derived from the supplied profile data.
     */
    public static LifecycleCatalogBundle build(
            String profileName,
            List<BringupUtil.DeviceEntry> deviceEntries,
            BringupUtil.BridgeProfileRuntimeConfig bridgeConfig) {
        return build(profileName, deviceEntries, bridgeConfig, List.of());
    }

    /**
     * NAME
     *     build - create lifecycle catalogs from one profile's devices, static groups, and
     *     runtime-only dynamic groups.
     *
     * PARAMETERS
     *     profileName - source profile name.
     *     deviceEntries - current profile device entries.
     *     bridgeConfig - current profile bridge-group configuration.
     *     runtimeGroups - current runtime-only bridge groups.
     *
     * RETURNS
     *     A passive lifecycle catalog bundle derived from the supplied profile data.
     */
    public static LifecycleCatalogBundle build(
            String profileName,
            List<BringupUtil.DeviceEntry> deviceEntries,
            BringupUtil.BridgeProfileRuntimeConfig bridgeConfig,
            List<BridgeGroupManager.Group> runtimeGroups) {
        List<DeviceDeclaration> deviceDeclarations = buildDeviceDeclarations(deviceEntries);
        DeviceCatalog deviceCatalog = DeviceCatalog.load(deviceDeclarations);
        List<GroupDeclaration> configuredGroupDeclarations = buildConfiguredGroupDeclarations(bridgeConfig);
        GroupCatalog groupCatalog = GroupCatalog.load(deviceCatalog, configuredGroupDeclarations);
        syncRuntimeGroups(groupCatalog, runtimeGroups);
        LabelResolver labelResolver = new LabelResolver(deviceCatalog, groupCatalog);
        return new LifecycleCatalogBundle(profileName, deviceCatalog, groupCatalog, labelResolver);
    }

    static List<DeviceDeclaration> buildDeviceDeclarations(List<BringupUtil.DeviceEntry> deviceEntries) {
        List<DeviceDeclaration> declarations = new ArrayList<>();
        if (deviceEntries == null) {
            return declarations;
        }
        for (BringupUtil.DeviceEntry entry : deviceEntries) {
            if (entry == null || entry.label == null || entry.label.isBlank()) {
                continue;
            }
            declarations.add(new DeviceDeclaration(entry.label, lifecycleKindFor(entry)));
        }
        return declarations;
    }

    static List<GroupDeclaration> buildConfiguredGroupDeclarations(
            BringupUtil.BridgeProfileRuntimeConfig bridgeConfig) {
        List<GroupDeclaration> declarations = new ArrayList<>();
        if (bridgeConfig == null || bridgeConfig.groups == null) {
            return declarations;
        }
        for (BringupUtil.BridgeProfileGroupConfig group : bridgeConfig.groups) {
            if (group == null || group.name == null || group.name.isBlank()) {
                continue;
            }
            if (GROUP_ACTIVE.equalsIgnoreCase(group.name.trim())) {
                continue;
            }
            List<String> memberLabels = new ArrayList<>();
            if (group.members != null) {
                for (BringupUtil.BridgeProfileMemberConfig member : group.members) {
                    if (member == null || !member.enabled || member.label == null || member.label.isBlank()) {
                        continue;
                    }
                    memberLabels.add(member.label);
                }
            }
            declarations.add(new GroupDeclaration(group.name, memberLabels));
        }
        return declarations;
    }

    public static void syncRuntimeGroups(
            GroupCatalog groupCatalog, List<BridgeGroupManager.Group> runtimeGroups) {
        syncRuntimeGroups(groupCatalog, runtimeGroups, List.of());
    }

    public static void syncRuntimeGroups(
            GroupCatalog groupCatalog,
            List<BridgeGroupManager.Group> runtimeGroups,
            List<String> preservedDynamicLabels) {
        if (groupCatalog == null) {
            return;
        }
        Set<String> runtimeLabels = new LinkedHashSet<>();
        Set<String> preservedLabels = new LinkedHashSet<>();
        if (preservedDynamicLabels != null) {
            preservedLabels.addAll(preservedDynamicLabels);
        }
        if (runtimeGroups != null) {
            for (BridgeGroupManager.Group runtimeGroup : runtimeGroups) {
                if (runtimeGroup == null
                        || runtimeGroup.name == null
                        || runtimeGroup.name.isBlank()) {
                    continue;
                }
                String groupLabel = runtimeGroup.name;
                runtimeLabels.add(groupLabel);
                List<String> memberLabels = buildRuntimeMemberLabels(runtimeGroup);
                if (!groupCatalog.hasGroupLabel(groupLabel)) {
                    groupCatalog.createDynamicGroup(groupLabel);
                }
                GroupRecord groupRecord = groupCatalog.groupRecord(groupLabel);
                if (groupRecord.kind() == GroupKind.DYNAMIC) {
                    groupCatalog.setDynamicGroupMembers(groupLabel, memberLabels);
                }
            }
        }

        for (GroupRecord groupRecord : groupCatalog.groupRecords()) {
            if (groupRecord.kind() != GroupKind.DYNAMIC) {
                continue;
            }
            if (preservedLabels.contains(groupRecord.label())) {
                continue;
            }
            if (!runtimeLabels.contains(groupRecord.label())) {
                groupCatalog.deleteDynamicGroup(groupRecord.label());
            }
        }
    }

    private static List<String> buildRuntimeMemberLabels(BridgeGroupManager.Group runtimeGroup) {
        List<String> memberLabels = new ArrayList<>();
        if (runtimeGroup.members == null) {
            return memberLabels;
        }
        for (BridgeGroupManager.MemberState memberState : runtimeGroup.members.values()) {
            if (memberState == null
                    || !memberState.enabled
                    || memberState.label == null
                    || memberState.label.isBlank()) {
                continue;
            }
            memberLabels.add(memberState.label);
        }
        return memberLabels;
    }

    private static DeviceLifecycleKind lifecycleKindFor(BringupUtil.DeviceEntry entry) {
        if (BringupUtil.isSingletonLifecycleEntry(entry)) {
            return DeviceLifecycleKind.SINGLETON;
        }
        return DeviceLifecycleKind.NORMAL;
    }
}
