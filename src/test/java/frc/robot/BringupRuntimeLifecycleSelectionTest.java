package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.CanBusHealth;
import frc.robot.diag.lifecycle.activation.ActivationMembershipMode;
import frc.robot.diag.lifecycle.runtime.DeviceRuntimeState;
import frc.robot.devices.DeviceLifecycleOwnership;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.tests.BringupTest;
import frc.robot.telemetry.SampledTelemetrySampler;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
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
  void synchronizeBridgeRuntimeConfigPreservesExistingManualActiveGroupMembers() {
    BridgeGroupManager groups = new BridgeGroupManager();
    groups.createGroup("active-group");
    groups.addDevice("active-group", "FALCON 9", false);
    groups.addDevice("active-group", "SPARKMAX/NEO 25", false);
    groups.setMemberEnabled("active-group", "SPARKMAX/NEO 25", false);
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

    assertTrue(groups.hasDevice("active-group", "FALCON 9"));
    assertTrue(groups.hasDevice("active-group", "SPARKMAX/NEO 25"));
    assertFalse(
        groups.getGroup("active-group").members.get("sparkmax/neo 25").enabled);
  }

  @Test
  void restoreActiveGroupRestoresManualMembersAfterFullClearAndRecreate() {
    BridgeGroupManager groups = new BridgeGroupManager();
    groups.createGroup("active-group");
    groups.addDevice("active-group", "FALCON 9", false);
    groups.addDevice("active-group", "SPARKMAX/NEO 25", false);
    groups.setMemberEnabled("active-group", "SPARKMAX/NEO 25", false);

    BringupRuntime.PreservedActiveGroup preserved =
        BringupRuntime.preserveActiveGroup(groups.getGroup("active-group"));

    groups.clear();
    groups.createGroup("active-group");
    BringupRuntime.restoreActiveGroup(groups, preserved);

    assertTrue(groups.hasDevice("active-group", "FALCON 9"));
    assertTrue(groups.hasDevice("active-group", "SPARKMAX/NEO 25"));
    assertFalse(
        groups.getGroup("active-group").members.get("sparkmax/neo 25").enabled);
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
  void lifecycleDeviceInstantiationUsesAppSingletonAllocationForSingletonBackedDevices() {
    TestSingletonDevice device = new TestSingletonDevice(9025, "CTRE", "PDP", "pdp");
    BringupUtil.DeviceEntry entry =
        new BringupUtil.DeviceEntry(
            9025, 4, 8, "CAN", "CTRE", "PDP", "pdp", null, null, null, null);

    assertFalse(BringupRuntime.isLifecycleDeviceInstantiated(entry, device));
    assertFalse(BringupRuntime.isLifecycleDeviceInstantiated(entry, null));

    BringupUtil.markAppSingletonAllocated(device);

    assertTrue(BringupRuntime.isLifecycleDeviceInstantiated(entry, device));
    assertTrue(BringupRuntime.isLifecycleDeviceInstantiated(entry, null));
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

  @Test
  void restoreSelectedTestSelectionPreservesNamedTestAcrossCoreReplacement() throws Exception {
    BringupCore core = new BringupCore(new SampledTelemetrySampler(), new DeviceLifecycleRegistry());
    List<BringupTest> tests =
        List.of(
            fakeTest("test_minimal_25_9_spark25_leftY"),
            fakeTest("falcon9_move_150_rotations"),
            fakeTest("newTests_123"));

    Field bringupTestsField = BringupCore.class.getDeclaredField("bringupTests");
    bringupTestsField.setAccessible(true);
    @SuppressWarnings("unchecked")
    List<BringupTest> bringupTests = (List<BringupTest>) bringupTestsField.get(core);
    bringupTests.clear();
    bringupTests.addAll(tests);

    Field selectableTestsField = BringupCore.class.getDeclaredField("selectableTests");
    selectableTestsField.setAccessible(true);
    @SuppressWarnings("unchecked")
    List<BringupTest> selectableTests = (List<BringupTest>) selectableTestsField.get(core);
    selectableTests.clear();

    Method refreshSelectableTests =
        BringupCore.class.getDeclaredMethod("refreshSelectableTests", String.class);
    refreshSelectableTests.setAccessible(true);
    refreshSelectableTests.invoke(core, "newTests_123");

    BringupRuntime.restoreSelectedTestSelection(core, "newTests_123");

    assertEquals("newTests_123", core.getSelectedBringupTestName());
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

  private static BringupTest fakeTest(String name) {
    return new BringupTest() {
      @Override
      public String getName() {
        return name;
      }

      @Override
      public boolean isEnabled() {
        return true;
      }

      @Override
      public boolean isRunning() {
        return false;
      }

      @Override
      public boolean isFinished() {
        return false;
      }

      @Override
      public frc.robot.tests.BringupTestResult getResult() {
        return frc.robot.tests.BringupTestResult.PASS;
      }

      @Override
      public String getStatus() {
        return "";
      }

      @Override
      public boolean start(frc.robot.tests.BringupTestContext context, double nowSec) {
        return false;
      }

      @Override
      public void update(frc.robot.tests.BringupTestContext context, double nowSec) {}

      @Override
      public void stop(frc.robot.tests.BringupTestContext context) {}

      @Override
      public List<String> getRequiredDeviceKeys() {
        return List.of();
      }
    };
  }

  private static final class TestSingletonDevice implements DeviceUnit {
    private final int canId;
    private final String vendor;
    private final String type;
    private final String label;

    private TestSingletonDevice(int canId, String vendor, String type, String label) {
      this.canId = canId;
      this.vendor = vendor;
      this.type = type;
      this.label = label;
    }

    @Override
    public int getCanId() {
      return canId;
    }

    @Override
    public String getDeviceType() {
      return type;
    }

    @Override
    public String getLabel() {
      return label;
    }

    @Override
    public boolean isCreated() {
      return false;
    }

    @Override
    public void ensureCreated() {}

    @Override
    public void close() {}

    @Override
    public void clearFaults() {}

    @Override
    public DeviceSnapshot snapshot() {
      return new DeviceSnapshot();
    }

    @Override
    public DeviceLifecycleOwnership getLifecycleOwnership() {
      return DeviceLifecycleOwnership.APP_OWNED_SINGLETON_SERVICE;
    }

    @Override
    public frc.robot.registry.RegistrationHeader getHeader() {
      return new frc.robot.registry.RegistrationHeader(label, vendor, type, "test", "test", "", "");
    }
  }
}
