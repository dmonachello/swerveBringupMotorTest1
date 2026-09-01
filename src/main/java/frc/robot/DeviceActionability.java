package frc.robot;

/**
 * NAME
 *   DeviceActionability - Shared robot-side readiness contract for device actions.
 *
 * DESCRIPTION
 *   Centralizes the operator-action readiness rules that must stay consistent
 *   between runtime JSON publication, manual duty, and DSL/test execution.
 */
final class DeviceActionability {
  static final String REASON_CODE_READY = "ready";
  static final String REASON_CODE_UNKNOWN = "unknown";
  static final String REASON_CODE_SCOPE_REQUIRED = "scope_required";
  static final String REASON_CODE_NOT_PRESENT = "not_present";
  static final String REASON_CODE_NOT_INSTANTIATED = "not_instantiated";
  static final String REASON_CODE_NOT_IN_SCOPE = "not_in_scope";
  static final String REASON_CODE_OVERRIDE_PENDING = "override_pending";
  static final String REASON_CODE_OVERRIDE_FAILED = "override_failed";
  static final String REASON_CODE_NOT_READY = "not_ready";

  private static final String TEXT_REASON_SCOPE_REQUIRED =
      "Device is outside the active controlled scope membership.";
  private static final String TEXT_REASON_UNKNOWN =
      "Device lifecycle state is unavailable.";
  private static final String TEXT_REASON_TESTABLE = "Testable.";
  private static final String TEXT_REASON_NOT_PRESENT =
      "Presence score below threshold; device is not present.";
  private static final String TEXT_REASON_NOT_INSTANTIATED =
      "Runtime object is not instantiated.";
  private static final String TEXT_REASON_NOT_IN_SCOPE = "Device is not in scope.";
  private static final String TEXT_REASON_OVERRIDE_PENDING =
      "Override instantiation is pending.";
  private static final String TEXT_REASON_OVERRIDE_FAILED =
      "Override instantiation failed. Clear failure before retry.";
  private static final String TEXT_LIFECYCLE_PREFIX_INSTANTIATED = "instantiated";

  private DeviceActionability() {}

  static final class Evaluation {
    final boolean instantiated;
    final boolean testOperable;
    final boolean manualOperable;
    final String blockedReasonCode;
    final String blockedReasonText;

    private Evaluation(
        boolean instantiated,
        boolean testOperable,
        boolean manualOperable,
        String blockedReasonCode,
        String blockedReasonText) {
      this.instantiated = instantiated;
      this.testOperable = testOperable;
      this.manualOperable = manualOperable;
      this.blockedReasonCode = blockedReasonCode;
      this.blockedReasonText = blockedReasonText;
    }
  }

  /**
   * NAME
   *   evaluate - Return one shared readiness decision for a device.
   */
  static Evaluation evaluate(
      DeviceLifecycleRegistry.DeviceLifecycleView lifecycle,
      boolean controlledLifecycleActive,
      boolean controlledDeviceActive) {
    boolean instantiated =
        lifecycle != null
            && lifecycle.lifecycleState != null
            && lifecycle.lifecycleState.startsWith(TEXT_LIFECYCLE_PREFIX_INSTANTIATED);
    if (controlledLifecycleActive && !controlledDeviceActive) {
      return new Evaluation(
          instantiated,
          false,
          false,
          REASON_CODE_SCOPE_REQUIRED,
          TEXT_REASON_SCOPE_REQUIRED);
    }
    if (lifecycle == null) {
      return new Evaluation(
          false,
          false,
          false,
          REASON_CODE_UNKNOWN,
          TEXT_REASON_UNKNOWN);
    }
    if (lifecycle.testable) {
      return new Evaluation(
          instantiated,
          true,
          true,
          REASON_CODE_READY,
          TEXT_REASON_TESTABLE);
    }
    String reasonText =
        lifecycle.notTestableReason != null && !lifecycle.notTestableReason.isBlank()
            ? lifecycle.notTestableReason
            : TEXT_REASON_UNKNOWN;
    return new Evaluation(
        instantiated,
        false,
        false,
        mapReasonCode(reasonText),
        reasonText);
  }

  private static String mapReasonCode(String reasonText) {
    if (TEXT_REASON_NOT_PRESENT.equals(reasonText)) {
      return REASON_CODE_NOT_PRESENT;
    }
    if (TEXT_REASON_NOT_INSTANTIATED.equals(reasonText)) {
      return REASON_CODE_NOT_INSTANTIATED;
    }
    if (TEXT_REASON_NOT_IN_SCOPE.equals(reasonText)) {
      return REASON_CODE_NOT_IN_SCOPE;
    }
    if (TEXT_REASON_OVERRIDE_PENDING.equals(reasonText)) {
      return REASON_CODE_OVERRIDE_PENDING;
    }
    if (TEXT_REASON_OVERRIDE_FAILED.equals(reasonText)) {
      return REASON_CODE_OVERRIDE_FAILED;
    }
    if (TEXT_REASON_TESTABLE.equals(reasonText)) {
      return REASON_CODE_READY;
    }
    return REASON_CODE_NOT_READY;
  }
}
