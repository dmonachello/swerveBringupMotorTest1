package frc.robot.diag.lifecycle.groups;

import frc.robot.BridgeGroupManager;
import frc.robot.DeviceLifecycleRegistry;
import frc.robot.diag.lifecycle.runtime.DeviceRuntimeState;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

/**
 * NAME
 *   ResolvedGroupStates - Shared robot-side group-state resolver.
 *
 * DESCRIPTION
 *   Normalizes raw bridge group membership plus current lifecycle/runtime
 *   facts into one shared immutable group-state contract. Robot-side text,
 *   JSON, and future UI payload builders should consume this resolved view
 *   instead of inferring group truth directly from raw member maps.
 */
public final class ResolvedGroupStates {
  private static final String TEXT_EMPTY = "";
  private static final String TEXT_CONTROLLED_ACTIVE = "controlled-active";
  private static final String TEXT_CONTROLLED_INSTANTIATED = "controlled-instantiated";
  private static final String TEXT_INSTANTIATED_PREFIX = "instantiated";
  private static final double RUNTIME_PRESENT_THRESHOLD = 0.5;

  /**
   * NAME
   *   ResolvedGroupMemberState - Shared immutable group-member facts.
   */
  public static final class ResolvedGroupMemberState {
    public final String label;
    public final boolean enabled;
    public final boolean locked;
    public final boolean invalid;
    public final boolean scopeActive;
    public final boolean runtimePresent;
    public final boolean instantiated;
    public final boolean testable;

    private ResolvedGroupMemberState(
        String label,
        boolean enabled,
        boolean locked,
        boolean invalid,
        boolean scopeActive,
        boolean runtimePresent,
        boolean instantiated,
        boolean testable) {
      this.label = label;
      this.enabled = enabled;
      this.locked = locked;
      this.invalid = invalid;
      this.scopeActive = scopeActive;
      this.runtimePresent = runtimePresent;
      this.instantiated = instantiated;
      this.testable = testable;
    }
  }

  /**
   * NAME
   *   ResolvedGroupState - Shared immutable group facts and resolved members.
   */
  public static final class ResolvedGroupState {
    public final String name;
    public final String primaryLabel;
    public final List<ResolvedGroupMemberState> members;
    public final int memberCount;
    public final int enabledMemberCount;
    public final boolean hasMembers;
    public final boolean allEnabledMembersPresent;

    private ResolvedGroupState(
        String name,
        String primaryLabel,
        List<ResolvedGroupMemberState> members,
        int memberCount,
        int enabledMemberCount,
        boolean hasMembers,
        boolean allEnabledMembersPresent) {
      this.name = name;
      this.primaryLabel = primaryLabel;
      this.members = List.copyOf(members);
      this.memberCount = memberCount;
      this.enabledMemberCount = enabledMemberCount;
      this.hasMembers = hasMembers;
      this.allEnabledMembersPresent = allEnabledMembersPresent;
    }
  }

  private ResolvedGroupStates() {}

  /**
   * NAME
   *   resolve - Build one shared resolved group-state view.
   *
   * PARAMETERS
   *   group - Raw bridge group to normalize.
   *   lifecycleForLabel - Lookup for lifecycle view by label.
   *   runtimeForLabel - Lookup for runtime state by label.
   *   locked - Whether the group is presently membership-locked.
   *
   * RETURNS
   *   Shared resolved state, or null when the input group is null.
   */
  public static ResolvedGroupState resolve(
      BridgeGroupManager.Group group,
      Function<String, DeviceLifecycleRegistry.DeviceLifecycleView> lifecycleForLabel,
      Function<String, DeviceRuntimeState> runtimeForLabel,
      boolean locked) {
    if (group == null) {
      return null;
    }
    Function<String, DeviceLifecycleRegistry.DeviceLifecycleView> lifecycleLookup =
        lifecycleForLabel != null ? lifecycleForLabel : label -> null;
    Function<String, DeviceRuntimeState> runtimeLookup =
        runtimeForLabel != null ? runtimeForLabel : label -> null;

    List<ResolvedGroupMemberState> members = new ArrayList<>();
    int enabledMemberCount = 0;
    boolean allEnabledMembersPresent = true;
    for (BridgeGroupManager.MemberState member : group.members.values()) {
      ResolvedGroupMemberState resolved =
          resolveMemberState(member, lifecycleLookup, runtimeLookup, locked);
      if (resolved == null) {
        continue;
      }
      members.add(resolved);
      if (!resolved.enabled) {
        continue;
      }
      enabledMemberCount++;
      if (!resolved.runtimePresent) {
        allEnabledMembersPresent = false;
      }
    }
    if (enabledMemberCount == 0) {
      allEnabledMembersPresent = false;
    }
    return new ResolvedGroupState(
        clean(group.name),
        resolvePrimaryLabel(members),
        members,
        members.size(),
        enabledMemberCount,
        !members.isEmpty(),
        allEnabledMembersPresent);
  }

  private static ResolvedGroupMemberState resolveMemberState(
      BridgeGroupManager.MemberState member,
      Function<String, DeviceLifecycleRegistry.DeviceLifecycleView> lifecycleForLabel,
      Function<String, DeviceRuntimeState> runtimeForLabel,
      boolean locked) {
    if (member == null) {
      return null;
    }
    String label = clean(member.label);
    DeviceLifecycleRegistry.DeviceLifecycleView lifecycle =
        !label.isEmpty() ? lifecycleForLabel.apply(label) : null;
    DeviceRuntimeState runtime = !label.isEmpty() ? runtimeForLabel.apply(label) : null;
    boolean scopeActive = runtime != null && runtime.isActive();
    boolean runtimePresent =
        lifecycle != null && lifecycle.presenceScore >= RUNTIME_PRESENT_THRESHOLD;
    boolean instantiated =
        runtime != null ? runtime.isInstantiated() : lifecycleImpliesInstantiation(lifecycle);
    boolean testable = scopeActive || (lifecycle != null && lifecycle.testable);
    boolean invalid = label.isEmpty() || (lifecycle == null && runtime == null);
    return new ResolvedGroupMemberState(
        label,
        member.enabled,
        locked,
        invalid,
        scopeActive,
        runtimePresent,
        instantiated,
        testable);
  }

  private static String resolvePrimaryLabel(List<ResolvedGroupMemberState> members) {
    if (members == null || members.isEmpty()) {
      return TEXT_EMPTY;
    }
    for (ResolvedGroupMemberState member : members) {
      if (member != null && member.enabled && member.label != null && !member.label.isBlank()) {
        return member.label;
      }
    }
    for (ResolvedGroupMemberState member : members) {
      if (member != null && member.label != null && !member.label.isBlank()) {
        return member.label;
      }
    }
    return TEXT_EMPTY;
  }

  private static boolean lifecycleImpliesInstantiation(
      DeviceLifecycleRegistry.DeviceLifecycleView lifecycle) {
    if (lifecycle == null || lifecycle.lifecycleState == null) {
      return false;
    }
    String state = lifecycle.lifecycleState;
    return state.startsWith(TEXT_INSTANTIATED_PREFIX)
        || TEXT_CONTROLLED_INSTANTIATED.equals(state)
        || TEXT_CONTROLLED_ACTIVE.equals(state);
  }

  private static String clean(String value) {
    return value != null ? value.trim() : TEXT_EMPTY;
  }
}
