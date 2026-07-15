package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.diag.lifecycle.activation.ActivationMembershipMode;
import frc.robot.diag.lifecycle.runtime.DeviceRuntimeState;
import java.lang.reflect.Constructor;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   BringupRuntimeLifecycleSelectionTest - Tests for lifecycle profile fallback resolution.
 */
class BringupRuntimeLifecycleSelectionTest {
  private static final String TEXT_EMPTY = "";
  private static final String TEXT_NONE = "(none)";
  private static final String PROFILE_ACTIVE = "activeProfile";
  private static final String PROFILE_SELECTED = "selectedProfile";
  private static final String PROFILE_DEFAULT = "defaultProfile";

  @Test
  void resolveLifecycleProfileNameUsesActiveProfileFirst() {
    assertEquals(
        PROFILE_ACTIVE,
        BringupRuntime.resolveLifecycleProfileName(
            true,
            PROFILE_ACTIVE,
            PROFILE_SELECTED,
            PROFILE_DEFAULT));
  }

  @Test
  void resolveLifecycleProfileNameFallsBackToSelectedWhenInactive() {
    assertEquals(
        PROFILE_SELECTED,
        BringupRuntime.resolveLifecycleProfileName(
            false,
            PROFILE_ACTIVE,
            PROFILE_SELECTED,
            PROFILE_DEFAULT));
  }

  @Test
  void resolveLifecycleProfileNameFallsBackToDefaultWhenSelectedMissing() {
    assertEquals(
        PROFILE_DEFAULT,
        BringupRuntime.resolveLifecycleProfileName(
            false,
            TEXT_EMPTY,
            TEXT_EMPTY,
            PROFILE_DEFAULT));
  }

  @Test
  void resolveLifecycleProfileNameTreatsDisplayNoneAsMissing() {
    assertEquals(
        PROFILE_DEFAULT,
        BringupRuntime.resolveLifecycleProfileName(
            false,
            TEXT_EMPTY,
            TEXT_NONE,
            PROFILE_DEFAULT));
  }

  @Test
  void resolveLifecycleDeviceInScopeUsesControlledActiveScopeWhenLifecycleActive() {
    DeviceRuntimeState controlledState = new DeviceRuntimeState();
    controlledState.markActivated("session-1", "active-group", "READ_ONLY");

    assertTrue(
        BringupRuntime.resolveLifecycleDeviceInScope(
            false,
            true,
            controlledState));
    assertFalse(
        BringupRuntime.resolveLifecycleDeviceInScope(
            false,
            true,
            new DeviceRuntimeState()));
  }

  @Test
  void resolveLifecycleDeviceInScopeFallsBackToLegacyRuntimeWhenLifecycleInactive() {
    assertTrue(
        BringupRuntime.resolveLifecycleDeviceInScope(
            true,
            false,
            new DeviceRuntimeState()));
    assertFalse(
        BringupRuntime.resolveLifecycleDeviceInScope(
            false,
            false,
            null));
  }

  @Test
  void shouldCaptureLifecycleSnapshotRequiresControlledActiveDeviceWhenLifecycleActive() {
    DeviceRuntimeState controlledState = new DeviceRuntimeState();
    controlledState.markActivated("session-1", "active-group", "READ_ONLY");

    assertTrue(
        BringupRuntime.shouldCaptureLifecycleSnapshot(
            false,
            true,
            true,
            controlledState));
    assertFalse(
        BringupRuntime.shouldCaptureLifecycleSnapshot(
            false,
            true,
            true,
            new DeviceRuntimeState()));
    assertFalse(
        BringupRuntime.shouldCaptureLifecycleSnapshot(
            false,
            true,
            false,
            controlledState));
  }

  @Test
  void shouldInstantiateLifecycleSingletonRequiresActiveScope() {
    DeviceRuntimeState controlledState = new DeviceRuntimeState();
    controlledState.markActivated("session-1", "active-group", "READ_ONLY");

    assertFalse(
        BringupRuntime.shouldInstantiateLifecycleSingleton(
            false,
            false,
            null));
    assertTrue(
        BringupRuntime.shouldInstantiateLifecycleSingleton(
            true,
            false,
            null));
    assertTrue(
        BringupRuntime.shouldInstantiateLifecycleSingleton(
            false,
            true,
            controlledState));
    assertFalse(
        BringupRuntime.shouldInstantiateLifecycleSingleton(
            false,
            true,
            new DeviceRuntimeState()));
  }

  @Test
  void synchronizeBridgeRuntimeConfigLoadsProfileDefinedGroups() {
    BridgeGroupManager groups = new BridgeGroupManager();
    BridgeGroupManager.SelectedState selected = new BridgeGroupManager.SelectedState();
    BringupUtil.BridgeProfileRuntimeConfig config =
        new BringupUtil.BridgeProfileRuntimeConfig(
            List.of(
                new BringupUtil.BridgeProfileGroupConfig(
                    "motors",
                    true,
                    List.of(
                        new BringupUtil.BridgeProfileMemberConfig("FALCON 9", true),
                        new BringupUtil.BridgeProfileMemberConfig("SPARKMAX/NEO 25", true)),
                    List.of())),
            new BringupUtil.BridgeProfileSelectedDeviceConfig("FALCON 9", true));

    BringupRuntime.synchronizeBridgeRuntimeConfig(groups, selected, config, List.of());

    BridgeGroupManager.Group motors = groups.getGroup("motors");
    assertNotNull(motors);
    assertTrue(groups.hasDevice("motors", "FALCON 9"));
    assertTrue(groups.hasDevice("motors", "SPARKMAX/NEO 25"));
    assertEquals("FALCON 9", selected.device);
    assertTrue(selected.enabled);
    assertNotNull(groups.getGroup("active-group"));
  }

  @Test
  void synchronizeBridgeRuntimeConfigFallsBackToDefaultGroupWhenNoGroupsDefined() {
    BridgeGroupManager groups = new BridgeGroupManager();
    BridgeGroupManager.SelectedState selected = new BridgeGroupManager.SelectedState();
    List<BringupUtil.DeviceEntry> fallbackDevices =
        List.of(
            new BringupUtil.DeviceEntry(9, 4, 2, "CAN", "CTRE", "falcon", "FALCON 9", "FALCON", null, null, null),
            new BringupUtil.DeviceEntry(25, 5, 2, "CAN", "REV", "neo", "SPARKMAX/NEO 25", "NEO", null, null, null));

    BringupRuntime.synchronizeBridgeRuntimeConfig(
        groups,
        selected,
        BringupUtil.BridgeProfileRuntimeConfig.empty(),
        fallbackDevices);

    assertTrue(groups.hasDevice("defaultGroup", "FALCON 9"));
    assertTrue(groups.hasDevice("defaultGroup", "SPARKMAX/NEO 25"));
    assertNotNull(groups.getGroup("active-group"));
  }

  @Test
  void lifecycleSingletonEntryTreatsControllerAndInfrastructureAsPreservedSupport() {
    BringupUtil.DeviceEntry controller =
        new BringupUtil.DeviceEntry(
            0, 9, 1, "USB", "Microsoft", "xboxController", "controller0", null, null, null, null);
    BringupUtil.DeviceEntry pdp =
        new BringupUtil.DeviceEntry(
            20, 4, 8, "CAN", "CTRE", "PDP", "pdp", null, null, null, null);
    BringupUtil.DeviceEntry limitSwitch =
        new BringupUtil.DeviceEntry(
            0, 1, 0, "DIO", "NI", "limitSwitch", "lmtSw0", null, null, null, null);

    assertTrue(BringupRuntime.isLifecycleSingletonEntry(controller));
    assertTrue(BringupRuntime.isLifecycleSingletonEntry(pdp));
    assertFalse(BringupRuntime.isLifecycleSingletonEntry(limitSwitch));
  }

  @Test
  void selectActivationMembersStrictRejectsUnavailableMembers() {
    BringupRuntime.ActivationMemberSelection selection =
        BringupRuntime.selectActivationMembers(
            ActivationMembershipMode.STRICT,
            List.of("FALCON 9", "SPARKMAX/NEO 25"),
            label -> "FALCON 9".equals(label));

    assertFalse(selection.allowActivation());
    assertEquals(List.of(), selection.attemptedDeviceLabels());
    assertEquals(List.of("SPARKMAX/NEO 25"), selection.skippedDeviceLabels());
    assertEquals("REQUESTED_DEVICES_NOT_RUNNABLE", selection.errorCode());
  }

  @Test
  void selectActivationMembersPartialSkipsUnavailableMembers() {
    BringupRuntime.ActivationMemberSelection selection =
        BringupRuntime.selectActivationMembers(
            ActivationMembershipMode.PARTIAL,
            List.of("FALCON 9", "SPARKMAX/NEO 25"),
            label -> "FALCON 9".equals(label));

    assertTrue(selection.allowActivation());
    assertEquals(List.of("FALCON 9"), selection.attemptedDeviceLabels());
    assertEquals(List.of("SPARKMAX/NEO 25"), selection.skippedDeviceLabels());
  }

  @Test
  void selectActivationMembersForceAttemptsEverything() {
    BringupRuntime.ActivationMemberSelection selection =
        BringupRuntime.selectActivationMembers(
            ActivationMembershipMode.FORCE,
            List.of("FALCON 9", "SPARKMAX/NEO 25"),
            label -> false);

    assertTrue(selection.allowActivation());
    assertEquals(
        List.of("FALCON 9", "SPARKMAX/NEO 25"),
        selection.attemptedDeviceLabels());
    assertEquals(List.of(), selection.skippedDeviceLabels());
  }

  @Test
  void lifecycleViewEligibleForActivationTreatsDefinedOutOfScopeDeviceAsEligible() throws Exception {
    DeviceLifecycleRegistry.DeviceLifecycleView lifecycle =
        deviceLifecycleView(
            "FALCON 9",
            "defined",
            0.0,
            false,
            "Device is not in scope.");

    assertTrue(BringupRuntime.isLifecycleViewEligibleForActivation(lifecycle));
  }

  @Test
  void lifecycleViewEligibleForActivationRejectsExplicitNoPresenceDevice() throws Exception {
    DeviceLifecycleRegistry.DeviceLifecycleView lifecycle =
        deviceLifecycleView(
            "SPARKMAX/NEO 25",
            "in-scope-stale",
            0.0,
            false,
            "Presence score below threshold; device is not present.");

    assertFalse(BringupRuntime.isLifecycleViewEligibleForActivation(lifecycle));
  }

  private static DeviceLifecycleRegistry.DeviceLifecycleView deviceLifecycleView(
      String label,
      String lifecycleState,
      double presenceScore,
      boolean testable,
      String notTestableReason) throws Exception {
    Constructor<DeviceLifecycleRegistry.DeviceLifecycleView> constructor =
        DeviceLifecycleRegistry.DeviceLifecycleView.class.getDeclaredConstructor(
            String.class,
            String.class,
            double.class,
            boolean.class,
            boolean.class,
            boolean.class,
            boolean.class,
            String.class,
            long.class,
            String.class);
    constructor.setAccessible(true);
    return constructor.newInstance(
        label,
        lifecycleState,
        presenceScore,
        testable,
        false,
        false,
        false,
        "refresh",
        0L,
        notTestableReason);
  }
}
