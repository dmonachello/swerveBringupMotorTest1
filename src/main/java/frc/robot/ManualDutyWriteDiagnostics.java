package frc.robot;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * NAME
 *   ManualDutyWriteDiagnostics - Track manual-duty expectations versus later writes.
 *
 * DESCRIPTION
 *   Records the requested duty for labels currently controlled by a manual
 *   popup and emits a concise diagnostic when some other runtime writer later
 *   commands a materially different duty. This is additive instrumentation only
 *   and must not affect motor control behavior.
 */
final class ManualDutyWriteDiagnostics {
  static final String SOURCE_UNSPECIFIED = "core-unspecified";
  private static final String TEXT_EMPTY = "";
  private static final String TEXT_FIELD_LABEL = " label=";
  private static final String TEXT_FIELD_REQUESTED = " requested=";
  private static final String TEXT_FIELD_WRITTEN = " written=";
  private static final String TEXT_FIELD_SOURCE = " source=";
  private static final String TEXT_FIELD_OWNER = " owner=";
  private static final String TEXT_PREFIX = "Manual duty overwrite diag:";
  private static final double DUTY_DIAG_ACTIVE_THRESHOLD = 0.05;
  private static final double DUTY_DIAG_MATCH_EPSILON = 0.02;
  private static final int DUTY_FMT_THOUSANDTHS = 1000;

  private final Map<String, WatchState> watchedByLabel = new HashMap<>();

  /**
   * NAME
   *   watch - Track one label as manual-duty owned.
   *
   * PARAMETERS
   *   label - Runtime device label.
   *   requestedDuty - Latest requested manual duty.
   *   ownerSource - Human-readable writer/source tag for the manual owner.
   */
  void watch(String label, double requestedDuty, String ownerSource) {
    String key = normalize(label);
    if (key.isEmpty()) {
      return;
    }
    WatchState state = watchedByLabel.computeIfAbsent(key, ignored -> new WatchState());
    state.label = label != null ? label.trim() : TEXT_EMPTY;
    state.requestedDuty = requestedDuty;
    state.ownerSource = ownerSource != null && !ownerSource.isBlank()
        ? ownerSource.trim()
        : SOURCE_UNSPECIFIED;
    state.lastConflictSignature = TEXT_EMPTY;
  }

  /**
   * NAME
   *   clear - Stop tracking one label.
   *
   * PARAMETERS
   *   label - Runtime device label.
   */
  void clear(String label) {
    String key = normalize(label);
    if (key.isEmpty()) {
      return;
    }
    watchedByLabel.remove(key);
  }

  /**
   * NAME
   *   clearAll - Stop tracking every label.
   */
  void clearAll() {
    watchedByLabel.clear();
  }

  /**
   * NAME
   *   recordWrite - Compare one actual duty write against any tracked manual request.
   *
   * PARAMETERS
   *   label - Runtime device label.
   *   writtenDuty - Duty command being sent now.
   *   source - Human-readable writer/source tag.
   *
   * RETURNS
   *   Diagnostic text when a foreign writer conflicts with the tracked manual
   *   request, or an empty string when there is no conflict to report.
   */
  String recordWrite(String label, double writtenDuty, String source) {
    String key = normalize(label);
    if (key.isEmpty()) {
      return TEXT_EMPTY;
    }
    WatchState state = watchedByLabel.get(key);
    if (state == null) {
      return TEXT_EMPTY;
    }
    String normalizedSource = source != null && !source.isBlank()
        ? source.trim()
        : SOURCE_UNSPECIFIED;
    if (Math.abs(state.requestedDuty) < DUTY_DIAG_ACTIVE_THRESHOLD) {
      state.lastConflictSignature = TEXT_EMPTY;
      return TEXT_EMPTY;
    }
    if (sameSource(state.ownerSource, normalizedSource)) {
      state.lastConflictSignature = TEXT_EMPTY;
      return TEXT_EMPTY;
    }
    if (Math.abs(writtenDuty - state.requestedDuty) <= DUTY_DIAG_MATCH_EPSILON) {
      state.lastConflictSignature = TEXT_EMPTY;
      return TEXT_EMPTY;
    }
    String signature =
        state.ownerSource
            + '|'
            + normalizedSource
            + '|'
            + formatDuty(state.requestedDuty)
            + '|'
            + formatDuty(writtenDuty);
    if (signature.equals(state.lastConflictSignature)) {
      return TEXT_EMPTY;
    }
    state.lastConflictSignature = signature;
    return TEXT_PREFIX
        + TEXT_FIELD_LABEL + state.label
        + TEXT_FIELD_REQUESTED + formatDuty(state.requestedDuty)
        + TEXT_FIELD_WRITTEN + formatDuty(writtenDuty)
        + TEXT_FIELD_SOURCE + normalizedSource
        + TEXT_FIELD_OWNER + state.ownerSource;
  }

  /**
   * NAME
   *   formatDuty - Render duty values consistently for compact diagnostics.
   */
  static String formatDuty(double duty) {
    double rounded = Math.rint(duty * DUTY_FMT_THOUSANDTHS) / DUTY_FMT_THOUSANDTHS;
    return Double.toString(rounded);
  }

  private static boolean sameSource(String first, String second) {
    if (first == null || second == null) {
      return false;
    }
    return first.equalsIgnoreCase(second);
  }

  private static String normalize(String label) {
    if (label == null) {
      return TEXT_EMPTY;
    }
    return label.trim().toLowerCase(Locale.ROOT);
  }

  /**
   * NAME
   *   WatchState - Tracked requested-duty state for one label.
   */
  private static final class WatchState {
    String label = TEXT_EMPTY;
    double requestedDuty = 0.0;
    String ownerSource = SOURCE_UNSPECIFIED;
    String lastConflictSignature = TEXT_EMPTY;
  }
}
