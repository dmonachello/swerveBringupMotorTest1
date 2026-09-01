package frc.robot.devices.rev;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   RevReadFailureCooldownTest - Unit coverage for REV retry backoff behavior.
 */
class RevReadFailureCooldownTest {
  private static final long COOLDOWN_NS = 1_000L;
  private static final long TIME_START_NS = 10_000L;
  private static final long TIME_DURING_COOLDOWN_NS = 10_500L;
  private static final long TIME_AFTER_COOLDOWN_NS = 11_500L;

  @Test
  void activatesAfterFailureAndExpiresAfterCooldownWindow() {
    AtomicLong clock = new AtomicLong(TIME_START_NS);
    RevReadFailureCooldown cooldown = new RevReadFailureCooldown(clock::get, COOLDOWN_NS);

    assertFalse(cooldown.isActive());
    cooldown.recordFailure("HAL: CAN Receive has Timed Out");
    assertTrue(cooldown.isActive());

    clock.set(TIME_DURING_COOLDOWN_NS);
    assertTrue(cooldown.isActive());

    clock.set(TIME_AFTER_COOLDOWN_NS);
    assertFalse(cooldown.isActive());
  }

  @Test
  void clearImmediatelyEndsCooldown() {
    AtomicLong clock = new AtomicLong(TIME_START_NS);
    RevReadFailureCooldown cooldown = new RevReadFailureCooldown(clock::get, COOLDOWN_NS);

    cooldown.recordFailure("Message not found");
    assertTrue(cooldown.isActive());

    cooldown.clear();
    assertFalse(cooldown.isActive());
  }

  @Test
  void unavailableNoteUsesRecordedFailureMessage() {
    AtomicLong clock = new AtomicLong(TIME_START_NS);
    RevReadFailureCooldown cooldown = new RevReadFailureCooldown(clock::get, COOLDOWN_NS);

    cooldown.recordFailure("HAL: CAN Receive has Timed Out");

    assertTrue(cooldown.unavailableNote().contains("HAL: CAN Receive has Timed Out"));
  }
}
