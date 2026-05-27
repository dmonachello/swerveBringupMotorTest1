package frc.robot.input;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.Collections;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   InputAliasResolverTest - Coverage for built-in controller alias defaults.
 */
class InputAliasResolverTest {

  @Test
  void resolvePreservesCanonicalControllerZeroInputs() {
    assertEquals(
        "controller0.right.y",
        InputAliasResolver.resolve("controller0.rightY", Collections.emptyMap()));
    assertEquals(
        "controller0.left.trigger",
        InputAliasResolver.resolve("controller0.leftTrigger", Collections.emptyMap()));
  }

  @Test
  void resolveMapsDriverAndOperatorAliasesToControllerNames() {
    assertEquals(
        "controller1.left.y",
        InputAliasResolver.resolve("operator.left.y", Collections.emptyMap()));
    assertEquals(
        "controller0.a",
        InputAliasResolver.resolve("driver.a", Collections.emptyMap()));
  }
}
