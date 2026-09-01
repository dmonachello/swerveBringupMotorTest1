package frc.robot;

import frc.robot.diag.snapshots.ActivePresenceProbeAttachment;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.DevicePresenceCheckAttachment;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * NAME
 *   DeviceLifecycleRegistry - Robot-owned lifecycle FSM for profile-defined devices.
 *
 * DESCRIPTION
 *   Maintains one event-driven lifecycle state per configured device and
 *   publishes a single authoritative path to testability. This FSM does not
 *   decide usable/degraded/failed health; it only decides whether a device is
 *   presently testable based on scope, presence evidence, instantiation, and
 *   operator override provenance.
 */
public final class DeviceLifecycleRegistry {
  private static final String TEXT_EMPTY = "";
  private static final String STATE_UNKNOWN = "unknown";
  private static final String STATE_UNKNOWN_PRESENT = "unknown-present";
  private static final String STATE_UNKNOWN_STALE = "unknown-stale";
  private static final String STATE_DEFINED = "defined";
  private static final String STATE_DEFINED_PRESENT = "defined-present";
  private static final String STATE_DEFINED_STALE = "defined-stale";
  private static final String STATE_IN_SCOPE = "in-scope";
  private static final String STATE_IN_SCOPE_PRESENT = "in-scope-present";
  private static final String STATE_IN_SCOPE_STALE = "in-scope-stale";
  private static final String STATE_OVERRIDE_INSTANTIATION_PENDING =
      "override-instantiation-pending";
  private static final String STATE_OVERRIDE_INSTANTIATION_FAILED =
      "override-instantiation-failed";
  private static final String STATE_INSTANTIATED_PRESENT = "instantiated-present";
  private static final String STATE_INSTANTIATED_NOT_PRESENT =
      "instantiated-not-present";
  private static final String STATE_INSTANTIATED_NOT_PRESENT_OVERRIDE =
      "instantiated-not-present-override";
  private static final String STATE_INSTANTIATED_PRESENT_OVERRIDE =
      "instantiated-present-override";

  private static final String EVENT_DEFINE = "define";
  private static final String EVENT_DISCOVER = "discover";
  private static final String EVENT_LOST_PRESENCE = "lost-presence";
  private static final String EVENT_ENTER_SCOPE = "enter-scope";
  private static final String EVENT_EXIT_SCOPE = "exit-scope";
  private static final String EVENT_INSTANTIATE = "instantiate";
  private static final String EVENT_INSTANTIATE_AND_DISCOVER =
      "instantiate-and-discover";
  private static final String EVENT_INSTANTIATE_FAILED = "instantiate-failed";
  private static final String EVENT_MANUAL_OVERRIDE_INSTANTIATE =
      "manual-override-instantiate";
  private static final String EVENT_MANUAL_OVERRIDE_CLEAR =
      "manual-override-clear";
  private static final String EVENT_REFRESH = "refresh";

  private static final String REASON_NOT_IN_SCOPE = "Device is not in scope.";
  private static final String REASON_NO_PRESENCE =
      "Presence score below threshold; device is not present.";
  private static final String REASON_NOT_INSTANTIATED =
      "Runtime object is not instantiated.";
  private static final String REASON_NOT_INSTANTIABLE =
      "Device is not eligible for instantiation in the current lifecycle state.";
  private static final String REASON_OVERRIDE_PENDING =
      "Override instantiation is pending.";
  private static final String REASON_OVERRIDE_FAILED =
      "Override instantiation failed. Clear failure before retry.";
  private static final String REASON_TESTABLE = "Testable.";
  private static final String REASON_OVERRIDE_PROVENANCE =
      "Testable via override-originated runtime instance.";

  /**
   * NAME
   *   DeviceLifecycleView - Published robot-owned lifecycle contract for one device.
   */
  public static final class DeviceLifecycleView {
    public final String label;
    public final String lifecycleState;
    public final double presenceScore;
    public final boolean testable;
    public final boolean overrideActive;
    public final boolean overrideOriginated;
    public final boolean overrideFailure;
    public final String lastEvent;
    public final long lastTransitionTimeMs;
    public final String notTestableReason;

    private DeviceLifecycleView(
        String label,
        String lifecycleState,
        double presenceScore,
        boolean testable,
        boolean overrideActive,
        boolean overrideOriginated,
        boolean overrideFailure,
        String lastEvent,
        long lastTransitionTimeMs,
        String notTestableReason) {
      this.label = label;
      this.lifecycleState = lifecycleState;
      this.presenceScore = presenceScore;
      this.testable = testable;
      this.overrideActive = overrideActive;
      this.overrideOriginated = overrideOriginated;
      this.overrideFailure = overrideFailure;
      this.lastEvent = lastEvent;
      this.lastTransitionTimeMs = lastTransitionTimeMs;
      this.notTestableReason = notTestableReason;
    }
  }

  private final Map<String, MutableState> states = new LinkedHashMap<>();
  private String profileName = TEXT_EMPTY;
  private double discoverThreshold = BringupUtil.DEFAULT_DISCOVER_THRESHOLD;
  private double lostPresenceThreshold = BringupUtil.DEFAULT_LOST_PRESENCE_THRESHOLD;

  /**
   * NAME
   *   resetForProfile - Rebuild lifecycle state for the current profile definition set.
   *
   * PARAMETERS
   *   nextProfileName - Active or selected profile name.
   *   entries - Profile-defined device entries.
   *   nowMs - Timestamp of the rebuild.
   */
  public void resetForProfile(
      String nextProfileName,
      List<BringupUtil.DeviceEntry> entries,
      long nowMs) {
    profileName = nextProfileName != null ? nextProfileName : TEXT_EMPTY;
    discoverThreshold = BringupUtil.getProfileDiscoverThreshold(profileName);
    lostPresenceThreshold = BringupUtil.getProfileLostPresenceThreshold(profileName);
    states.clear();
    if (entries == null) {
      return;
    }
    for (BringupUtil.DeviceEntry entry : entries) {
      if (entry == null || entry.label == null || entry.label.isBlank()) {
        continue;
      }
      String key = normalize(entry.label);
      MutableState state = new MutableState(entry.label.trim());
      state.lifecycleState = STATE_DEFINED;
      state.lastEvent = EVENT_DEFINE;
      state.lastTransitionTimeMs = nowMs;
      states.put(key, state);
    }
  }

  /**
   * NAME
   *   refresh - Recompute lifecycle states from current snapshots and instantiation data.
   *
   * PARAMETERS
   *   entries - Profile-defined device entries.
   *   snapshotsByLabel - Current local snapshots keyed by normalized label.
   *   instantiatedByLabel - Created-state map keyed by normalized label.
   *   nowMs - Current timestamp.
   */
  public void refresh(
      List<BringupUtil.DeviceEntry> entries,
      Map<String, DeviceSnapshot> snapshotsByLabel,
      Map<String, Boolean> instantiatedByLabel,
      Map<String, Boolean> inScopeByLabel,
      long nowMs) {
    if (entries == null) {
      entries = new ArrayList<>();
    }
    ensureEntriesPresent(entries, nowMs);
    for (BringupUtil.DeviceEntry entry : entries) {
      if (entry == null || entry.label == null || entry.label.isBlank()) {
        continue;
      }
      String key = normalize(entry.label);
      MutableState state = states.get(key);
      if (state == null) {
        continue;
      }
      DeviceSnapshot snapshot = snapshotsByLabel != null ? snapshotsByLabel.get(key) : null;
      boolean instantiated = instantiatedByLabel != null
          && Boolean.TRUE.equals(instantiatedByLabel.get(key));
      boolean inScope = inScopeByLabel != null
          && Boolean.TRUE.equals(inScopeByLabel.get(key));
      double score = resolvePresenceScore(state, snapshot, instantiated, inScope);
      boolean present = resolvePresent(state, snapshot, instantiated, inScope, score);
      boolean stale = resolveStale(state, snapshot, instantiated, inScope, score);
      String previous = state.lifecycleState;
      String next = resolveState(state, inScope, instantiated, present, stale);
      String event = inferRefreshEvent(state, previous, next, instantiated, present, stale);
      applyResolvedState(state, next, score, event, nowMs);
    }
  }

  private double resolvePresenceScore(
      MutableState state,
      DeviceSnapshot snapshot,
      boolean instantiated,
      boolean inScope) {
    if (snapshot != null) {
      return presenceScore(snapshot);
    }
    if (state != null && instantiated && inScope) {
      return state.presenceScore;
    }
    return 0.0;
  }

  private boolean resolvePresent(
      MutableState state,
      DeviceSnapshot snapshot,
      boolean instantiated,
      boolean inScope,
      double score) {
    if (snapshot != null) {
      return score >= discoverThreshold;
    }
    if (state != null && instantiated && inScope) {
      return state.presentNow;
    }
    return score >= discoverThreshold;
  }

  private boolean resolveStale(
      MutableState state,
      DeviceSnapshot snapshot,
      boolean instantiated,
      boolean inScope,
      double score) {
    if (snapshot != null) {
      return score < lostPresenceThreshold;
    }
    if (state != null && instantiated && inScope) {
      return state.wasPresent && !state.presentNow;
    }
    return score < lostPresenceThreshold;
  }

  /**
   * NAME
   *   markOverrideInstantiationPending - Record an explicit operator override attempt.
   *
   * PARAMETERS
   *   label - Target device label.
   *   nowMs - Event timestamp.
   *
   * RETURNS
   *   Published view after the transition, or null when the label is unknown.
   */
  public DeviceLifecycleView markOverrideInstantiationPending(String label, long nowMs) {
    MutableState state = stateForLabel(label);
    if (state == null) {
      return null;
    }
    state.overrideActive = true;
    state.overrideOriginated = false;
    state.overrideFailure = false;
    state.lifecycleState = STATE_OVERRIDE_INSTANTIATION_PENDING;
    state.lastEvent = EVENT_MANUAL_OVERRIDE_INSTANTIATE;
    state.lastTransitionTimeMs = nowMs;
    return view(state);
  }

  /**
   * NAME
   *   markOverrideInstantiationFailed - Record an explicit override failure state.
   *
   * PARAMETERS
   *   label - Target device label.
   *   nowMs - Event timestamp.
   *
   * RETURNS
   *   Published view after the transition, or null when the label is unknown.
   */
  public DeviceLifecycleView markOverrideInstantiationFailed(String label, long nowMs) {
    MutableState state = stateForLabel(label);
    if (state == null) {
      return null;
    }
    state.overrideActive = true;
    state.overrideFailure = true;
    state.overrideOriginated = false;
    state.lifecycleState = STATE_OVERRIDE_INSTANTIATION_FAILED;
    state.lastEvent = EVENT_INSTANTIATE_FAILED;
    state.lastTransitionTimeMs = nowMs;
    return view(state);
  }

  /**
   * NAME
   *   clearOverrideFailure - Clear explicit override failure state.
   *
   * PARAMETERS
   *   label - Target device label.
   *   nowMs - Event timestamp.
   *
   * RETURNS
   *   Published view after the transition, or null when the label is unknown.
   */
  public DeviceLifecycleView clearOverrideFailure(String label, long nowMs) {
    MutableState state = stateForLabel(label);
    if (state == null) {
      return null;
    }
    state.overrideActive = false;
    state.overrideFailure = false;
    state.overrideOriginated = false;
    state.lastEvent = EVENT_MANUAL_OVERRIDE_CLEAR;
    state.lastTransitionTimeMs = nowMs;
    state.lifecycleState = state.wasPresent ? STATE_IN_SCOPE_STALE : STATE_IN_SCOPE;
    return view(state);
  }

  /**
   * NAME
   *   viewForLabel - Return one published lifecycle view.
   *
   * PARAMETERS
   *   label - Target device label.
   *
   * RETURNS
   *   Published view, or null when the label is not part of the current profile.
   */
  public DeviceLifecycleView viewForLabel(String label) {
    MutableState state = stateForLabel(label);
    return state != null ? view(state) : null;
  }

  /**
   * NAME
   *   isInstantiationAllowed - Return whether one device may be instantiated now.
   *
   * PARAMETERS
   *   label - Target device label.
   *
   * RETURNS
   *   True when the lifecycle state permits instantiation or already reflects
   *   an instantiated runtime object.
   */
  public boolean isInstantiationAllowed(String label) {
    MutableState state = stateForLabel(label);
    return state != null && isInstantiationAllowedState(state.lifecycleState);
  }

  /**
   * NAME
   *   isSnapshotAllowed - Return whether one device may be sampled/snapshotted now.
   *
   * PARAMETERS
   *   label - Target device label.
   *
   * RETURNS
   *   True when the lifecycle currently reflects an instantiated runtime path.
   */
  public boolean isSnapshotAllowed(String label) {
    MutableState state = stateForLabel(label);
    return state != null && isInstantiatedState(state.lifecycleState);
  }

  /**
   * NAME
   *   isOperationAllowed - Return whether one device may be actively operated now.
   *
   * PARAMETERS
   *   label - Target device label.
   *
   * RETURNS
   *   True when the device is currently testable.
   */
  public boolean isOperationAllowed(String label) {
    MutableState state = stateForLabel(label);
    return state != null && isTestableState(state.lifecycleState);
  }

  /**
   * NAME
   *   instantiationReasonForLabel - Return a short reason string for instantiation gating.
   *
   * PARAMETERS
   *   label - Target device label.
   *
   * RETURNS
   *   Short operator-facing reason string.
   */
  public String instantiationReasonForLabel(String label) {
    MutableState state = stateForLabel(label);
    if (state == null) {
      return REASON_NOT_IN_SCOPE;
    }
    if (state.overrideFailure) {
      return REASON_OVERRIDE_FAILED;
    }
    if (STATE_OVERRIDE_INSTANTIATION_PENDING.equals(state.lifecycleState)) {
      return REASON_OVERRIDE_PENDING;
    }
    if (isInstantiationAllowedState(state.lifecycleState)) {
      return REASON_NOT_INSTANTIATED;
    }
    return REASON_NOT_INSTANTIABLE;
  }

  private void ensureEntriesPresent(List<BringupUtil.DeviceEntry> entries, long nowMs) {
    for (BringupUtil.DeviceEntry entry : entries) {
      if (entry == null || entry.label == null || entry.label.isBlank()) {
        continue;
      }
      String key = normalize(entry.label);
      if (states.containsKey(key)) {
        continue;
      }
      MutableState state = new MutableState(entry.label.trim());
      state.lifecycleState = STATE_DEFINED;
      state.lastEvent = EVENT_DEFINE;
      state.lastTransitionTimeMs = nowMs;
      states.put(key, state);
    }
  }

  private MutableState stateForLabel(String label) {
    if (label == null || label.isBlank()) {
      return null;
    }
    return states.get(normalize(label));
  }

  private String resolveState(
      MutableState state,
      boolean inScope,
      boolean instantiated,
      boolean present,
      boolean stale) {
    if (!inScope) {
      if (present) {
        return STATE_DEFINED_PRESENT;
      }
      return STATE_DEFINED;
    }
    if (state.overrideFailure) {
      return STATE_OVERRIDE_INSTANTIATION_FAILED;
    }
    if (state.overrideActive && !instantiated && !state.overrideOriginated) {
      return STATE_OVERRIDE_INSTANTIATION_PENDING;
    }
    if (instantiated) {
      if (state.overrideActive || state.overrideOriginated) {
        return present
            ? STATE_INSTANTIATED_PRESENT_OVERRIDE
            : STATE_INSTANTIATED_NOT_PRESENT_OVERRIDE;
      }
      return present ? STATE_INSTANTIATED_PRESENT : STATE_INSTANTIATED_NOT_PRESENT;
    }
    if (present) {
      return STATE_IN_SCOPE_PRESENT;
    }
    if (state.wasPresent || stale) {
      return STATE_IN_SCOPE_STALE;
    }
    return STATE_IN_SCOPE;
  }

  private String inferRefreshEvent(
      MutableState state,
      String previous,
      String next,
      boolean instantiated,
      boolean present,
      boolean stale) {
    if (STATE_OVERRIDE_INSTANTIATION_FAILED.equals(next)) {
      return EVENT_INSTANTIATE_FAILED;
    }
    if (STATE_OVERRIDE_INSTANTIATION_PENDING.equals(next)) {
      return EVENT_MANUAL_OVERRIDE_INSTANTIATE;
    }
    if (!previous.equals(next)) {
      if (present && !state.presentNow) {
        if (instantiated && state.overrideActive) {
          return EVENT_INSTANTIATE_AND_DISCOVER;
        }
        return EVENT_DISCOVER;
      }
      if (stale && state.presentNow) {
        return EVENT_LOST_PRESENCE;
      }
      if (instantiated && !state.instantiatedNow) {
        if (present) {
          return state.overrideActive ? EVENT_INSTANTIATE_AND_DISCOVER : EVENT_INSTANTIATE;
        }
        return EVENT_INSTANTIATE;
      }
      if (!instantiated && state.instantiatedNow) {
        return EVENT_EXIT_SCOPE;
      }
    }
    return EVENT_REFRESH;
  }

  private void applyResolvedState(
      MutableState state,
      String next,
      double score,
      String event,
      long nowMs) {
    boolean changed = !next.equals(state.lifecycleState);
    state.lifecycleState = next;
    state.presenceScore = score;
    state.presentNow = score >= discoverThreshold;
    state.instantiatedNow = next.startsWith("instantiated");
    if (state.presentNow) {
      state.wasPresent = true;
    }
    if (state.instantiatedNow && state.overrideActive) {
      state.overrideOriginated = true;
    }
    if (changed || !event.equals(state.lastEvent)) {
      state.lastEvent = event;
      state.lastTransitionTimeMs = nowMs;
    }
    if (STATE_INSTANTIATED_PRESENT.equals(next)) {
      state.overrideActive = false;
      state.overrideFailure = false;
      state.overrideOriginated = false;
    } else if (STATE_INSTANTIATED_PRESENT_OVERRIDE.equals(next)
        || STATE_INSTANTIATED_NOT_PRESENT_OVERRIDE.equals(next)
        || STATE_OVERRIDE_INSTANTIATION_PENDING.equals(next)) {
      state.overrideActive = true;
    } else if (!STATE_OVERRIDE_INSTANTIATION_FAILED.equals(next)) {
      state.overrideFailure = false;
    }
  }

  private DeviceLifecycleView view(MutableState state) {
    String lifecycleState = state.lifecycleState != null ? state.lifecycleState : STATE_UNKNOWN;
    boolean testable = isTestableState(lifecycleState);
    boolean overrideActive = state.overrideActive || state.overrideFailure;
    boolean overrideOriginated = state.overrideOriginated;
    boolean overrideFailure = state.overrideFailure;
    String reason;
    if (testable) {
      reason = overrideOriginated ? REASON_OVERRIDE_PROVENANCE : REASON_TESTABLE;
    } else if (STATE_OVERRIDE_INSTANTIATION_FAILED.equals(lifecycleState)) {
      reason = REASON_OVERRIDE_FAILED;
    } else if (STATE_OVERRIDE_INSTANTIATION_PENDING.equals(lifecycleState)) {
      reason = REASON_OVERRIDE_PENDING;
    } else if (STATE_DEFINED.equals(lifecycleState)
        || STATE_DEFINED_PRESENT.equals(lifecycleState)
        || STATE_DEFINED_STALE.equals(lifecycleState)) {
      reason = REASON_NOT_IN_SCOPE;
    } else if (STATE_IN_SCOPE.equals(lifecycleState)) {
      reason = REASON_NO_PRESENCE;
    } else if (STATE_IN_SCOPE_STALE.equals(lifecycleState) || STATE_DEFINED_STALE.equals(lifecycleState)) {
      reason = REASON_NO_PRESENCE;
    } else if (STATE_IN_SCOPE_PRESENT.equals(lifecycleState) || STATE_DEFINED_PRESENT.equals(lifecycleState)) {
      reason = REASON_NOT_INSTANTIATED;
    } else {
      reason = REASON_NOT_INSTANTIATED;
    }
    return new DeviceLifecycleView(
        state.label,
        lifecycleState,
        state.presenceScore,
        testable,
        overrideActive,
        overrideOriginated,
        overrideFailure,
        state.lastEvent,
        state.lastTransitionTimeMs,
        reason);
  }

  private double presenceScore(DeviceSnapshot snapshot) {
    if (snapshot == null) {
      return 0.0;
    }
    DevicePresenceCheckAttachment presenceCheck =
        snapshot.getAttachment(DevicePresenceCheckAttachment.class);
    if (presenceCheck != null && presenceCheck.maxScore > 0) {
      return Math.max(
          0.0,
          Math.min(1.0, ((double) presenceCheck.score) / ((double) presenceCheck.maxScore)));
    }
    ActivePresenceProbeAttachment probe =
        snapshot.getAttachment(ActivePresenceProbeAttachment.class);
    if (probe != null && probe.maxScore > 0) {
      return Math.max(
          0.0,
          Math.min(1.0, ((double) probe.score) / ((double) probe.maxScore)));
    }
    return snapshot.present ? 1.0 : 0.0;
  }

  private String normalize(String label) {
    return label != null ? label.trim().toLowerCase() : TEXT_EMPTY;
  }

  private boolean isInstantiationAllowedState(String lifecycleState) {
    return STATE_IN_SCOPE.equals(lifecycleState)
        || STATE_IN_SCOPE_PRESENT.equals(lifecycleState)
        || STATE_IN_SCOPE_STALE.equals(lifecycleState)
        || STATE_OVERRIDE_INSTANTIATION_PENDING.equals(lifecycleState)
        || isInstantiatedState(lifecycleState);
  }

  private boolean isInstantiatedState(String lifecycleState) {
    return STATE_INSTANTIATED_PRESENT.equals(lifecycleState)
        || STATE_INSTANTIATED_NOT_PRESENT.equals(lifecycleState)
        || STATE_INSTANTIATED_NOT_PRESENT_OVERRIDE.equals(lifecycleState)
        || STATE_INSTANTIATED_PRESENT_OVERRIDE.equals(lifecycleState);
  }

  private boolean isTestableState(String lifecycleState) {
    return STATE_INSTANTIATED_PRESENT.equals(lifecycleState)
        || STATE_INSTANTIATED_PRESENT_OVERRIDE.equals(lifecycleState);
  }

  private static final class MutableState {
    private final String label;
    private String lifecycleState = STATE_UNKNOWN;
    private double presenceScore;
    private boolean presentNow;
    private boolean instantiatedNow;
    private boolean wasPresent;
    private boolean overrideActive;
    private boolean overrideOriginated;
    private boolean overrideFailure;
    private String lastEvent = EVENT_DEFINE;
    private long lastTransitionTimeMs;

    private MutableState(String label) {
      this.label = label;
    }
  }
}
