package frc.robot.manufacturers.ctre.diag;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.ctre.phoenix6.StatusCode;
import org.junit.jupiter.api.Test;

/**
 * NAME
 * CtreReaderUtilTest
 *
 * SYNOPSIS
 * Narrow regression tests for CTRE detailed fault-read gating.
 *
 * DESCRIPTION
 * Verifies that detailed per-flag CTRE fault expansion is only attempted when
 * the primary fault and sticky-fault aggregate statuses are both fresh. This
 * protects unpowered/stale device cases from driving extra native reads.
 */
class CtreReaderUtilTest {

  @Test
  void allowsDetailedFaultReadsWhenPrimaryStatusesAreOk() {
    assertTrue(CtreReaderUtil.shouldReadDetailedFaultFlags(StatusCode.OK, StatusCode.OK));
  }

  @Test
  void blocksDetailedFaultReadsWhenFaultStatusIsStale() {
    assertFalse(CtreReaderUtil.shouldReadDetailedFaultFlags(StatusCode.RxTimeout, StatusCode.OK));
  }

  @Test
  void blocksDetailedFaultReadsWhenStickyStatusIsStale() {
    assertFalse(CtreReaderUtil.shouldReadDetailedFaultFlags(StatusCode.OK, StatusCode.RxTimeout));
  }
}
