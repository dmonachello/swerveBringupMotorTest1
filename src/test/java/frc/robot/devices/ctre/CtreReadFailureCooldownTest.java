package frc.robot.devices.ctre;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   CtreReadFailureCooldownTest - Unit coverage for CTRE retry backoff behavior.
 */
class CtreReadFailureCooldownTest {
  private static final long COOLDOWN_NS = 1_000L;
  private static final long TIME_START_NS = 10_000L;
  private static final long TIME_DURING_COOLDOWN_NS = 10_500L;
  private static final long TIME_AFTER_COOLDOWN_NS = 11_500L;

  @Test
  void activatesAfterFailureAndExpiresAfterCooldownWindow() {
    AtomicLong clock = new AtomicLong(TIME_START_NS);
    CtreReadFailureCooldown cooldown = new CtreReadFailureCooldown(clock::get, COOLDOWN_NS);

    assertFalse(cooldown.isActive());
    cooldown.recordFailure("CAN frame not received/too-stale");
    assertTrue(cooldown.isActive());

    clock.set(TIME_DURING_COOLDOWN_NS);
    assertTrue(cooldown.isActive());

    clock.set(TIME_AFTER_COOLDOWN_NS);
    assertFalse(cooldown.isActive());
  }

  @Test
  void clearImmediatelyEndsCooldown() {
    AtomicLong clock = new AtomicLong(TIME_START_NS);
    CtreReadFailureCooldown cooldown = new CtreReadFailureCooldown(clock::get, COOLDOWN_NS);

    cooldown.recordFailure("CAN: Message not found");
    assertTrue(cooldown.isActive());

    cooldown.clear();
    assertFalse(cooldown.isActive());
  }
}
