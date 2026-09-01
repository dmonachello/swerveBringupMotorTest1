package frc.robot.devices.ctre;

import java.util.function.LongSupplier;

/**
 * NAME
 *   CtreReadFailureCooldown - Track recent CTRE read failures and gate repeated retries.
 *
 * DESCRIPTION
 *   Prevents high-rate retry loops from repeatedly provoking Phoenix/HAL
 *   warning output while a device remains unreachable.
 */
public final class CtreReadFailureCooldown {
  private static final long DEFAULT_COOLDOWN_NS = 30_000_000_000L;
  private static final long NEVER_FAILED_AT_NS = Long.MIN_VALUE;
  private static final String DEFAULT_UNAVAILABLE_MESSAGE = "ctre device read unavailable";
  private static final String ERROR_PREFIX = "cached unavailable: ";

  private final LongSupplier clock;
  private final long cooldownNs;
  private long lastFailureAtNs = NEVER_FAILED_AT_NS;
  private String lastFailureMessage = "";

  /**
   * NAME
   *   CtreReadFailureCooldown - Construct a cooldown tracker using the system monotonic clock.
   */
  public CtreReadFailureCooldown() {
    this(System::nanoTime, DEFAULT_COOLDOWN_NS);
  }

  CtreReadFailureCooldown(LongSupplier clock, long cooldownNs) {
    this.clock = clock != null ? clock : System::nanoTime;
    this.cooldownNs = cooldownNs > 0L ? cooldownNs : DEFAULT_COOLDOWN_NS;
  }

  /**
   * NAME
   *   isActive - Return whether a recent failure still blocks another retry.
   */
  public boolean isActive() {
    return isActiveAt(clock.getAsLong());
  }

  /**
   * NAME
   *   clear - Mark the current device read path healthy again.
   */
  public void clear() {
    lastFailureAtNs = NEVER_FAILED_AT_NS;
    lastFailureMessage = "";
  }

  /**
   * NAME
   *   recordFailure - Remember a failed vendor read and start the cooldown window.
   *
   * PARAMETERS
   *   exception - Failure raised by the vendor API, or null when only a message is known.
   */
  public void recordFailure(RuntimeException exception) {
    recordFailure(exception != null ? exception.getMessage() : "");
  }

  /**
   * NAME
   *   recordFailure - Remember a failed vendor read and start the cooldown window.
   *
   * PARAMETERS
   *   message - Failure detail to surface while the cooldown remains active.
   */
  public void recordFailure(String message) {
    lastFailureAtNs = clock.getAsLong();
    lastFailureMessage = sanitizeMessage(message);
  }

  /**
   * NAME
   *   unavailableNote - Return the caller-facing note for a skipped retry.
   */
  public String unavailableNote() {
    String message = lastFailureMessage;
    if (message.isBlank()) {
      message = DEFAULT_UNAVAILABLE_MESSAGE;
    }
    return ERROR_PREFIX + message;
  }

  private boolean isActiveAt(long nowNs) {
    if (lastFailureAtNs == NEVER_FAILED_AT_NS) {
      return false;
    }
    return nowNs - lastFailureAtNs < cooldownNs;
  }

  private String sanitizeMessage(String message) {
    if (message == null) {
      return "";
    }
    return message.trim();
  }
}
