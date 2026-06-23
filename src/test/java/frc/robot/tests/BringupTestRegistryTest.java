package frc.robot.tests;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class BringupTestRegistryTest {

  @Test
  void resolveCurrentProfileNameUsesSelectedProfileWhenRuntimeInactive() {
    assertEquals(
        "test_minimal_25_9",
        BringupTestRegistry.resolveCurrentProfileName(
            false,
            "",
            "test_minimal_25_9"));
  }

  @Test
  void resolveCurrentProfileNameUsesActiveProfileWhenRuntimeActive() {
    assertEquals(
        "robot_2026_swerve",
        BringupTestRegistry.resolveCurrentProfileName(
            true,
            "robot_2026_swerve",
            "test_minimal_25_9"));
  }

  @Test
  void resolveCurrentProfileNameFallsBackToSelectedWhenActiveNameMissing() {
    assertEquals(
        "test_minimal_25_9",
        BringupTestRegistry.resolveCurrentProfileName(
            true,
            "",
            "test_minimal_25_9"));
  }
}
