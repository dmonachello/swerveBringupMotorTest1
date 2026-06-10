package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.manufacturers.DeviceAddResult;
import frc.robot.manufacturers.DeviceRegistration;
import frc.robot.manufacturers.DeviceRole;
import frc.robot.manufacturers.DeviceTypeBucket;
import frc.robot.manufacturers.ManufacturerGroup;
import frc.robot.manufacturers.microsoft.MicrosoftDeviceGroup;
import frc.robot.manufacturers.microsoft.XboxControllerDevice;
import frc.robot.registry.RegistrationHeader;
import frc.robot.tests.BringupTestContext;
import frc.robot.tests.BringupTestResult;
import frc.robot.tests.dsl.DslBringupTest;
import frc.robot.tests.dsl.DslModels;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

class DslBringupTestTest {
  private static final String TEST_NAME = "spin";
  private static final String MOTOR_LABEL = "motor-a";
  private static final String VENDOR = "REV";
  private static final String DEVICE_TYPE = "NEO";
  private static final String SOURCE = "test";
  private static final String OWNER = "unit";
  private static final String EMPTY = "";
  private static final String CONTROLLER_LABEL = "controller0";
  private static final String CONTROLLER_TYPE = "xboxController";
  private static final String DSL_MOTOR_TYPE = "motor";
  private static final String SIGNAL_A = "A";
  private static final String SIGNAL_X = "X";
  private static final String SIGNAL_D_UP = "D_UP";
  private static final String SIGNAL_FAULTS = "faults";
  private static final String SIGNAL_LEFT_Y = "leftY";
  private static final String FIELD_DEVICE_REGISTRY = "DEVICE_REGISTRY";
  private static final String CLASS_DEVICE_DEFINITION = "frc.robot.BringupUtil$DeviceDefinition";
  private static final String FIELD_LABEL = "label";
  private static final String FIELD_TYPE = "type";
  private static final int CAN_ID = 25;
  private static final double DUTY = 0.15;
  private static final double START_SEC = 10.0;
  private static final double UPDATE_SEC = 10.02;
  private static final double FINISH_SEC = 11.51;
  private Map<String, Object> originalDeviceRegistry;

  @AfterEach
  void restoreDeviceRegistry() throws Exception {
    XboxControllerDevice.setControllerInputs(Map.of());
    if (originalDeviceRegistry == null) {
      return;
    }
    Map<String, Object> registry = deviceRegistry();
    registry.clear();
    registry.putAll(originalDeviceRegistry);
    originalDeviceRegistry = null;
  }

  @Test
  void dslTestReappliesDutyUntilFinished() {
    RecordingDevice device = new RecordingDevice();
    DslBringupTest test = new DslBringupTest(buildTest());
    BringupTestContext context = context(device);

    assertTrue(test.start(context, START_SEC));
    test.update(context, UPDATE_SEC);
    test.update(context, FINISH_SEC);

    assertEquals(BringupTestResult.PASS, test.getResult());
    assertEquals(2, device.dutyWrites);
    assertEquals(2, device.stopWrites);
    assertEquals(DUTY, device.lastDuty);
  }

  @Test
  void dslTestReadsXboxControllerButtonSignal() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    BringupTestContext context = controllerContext();
    XboxControllerDevice.setControllerInputs(Map.of(CONTROLLER_LABEL, Map.of(SIGNAL_A, 1.0)));
    DslBringupTest test = new DslBringupTest(buildControllerButtonTest());

    assertTrue(test.start(context, START_SEC));
    test.update(context, UPDATE_SEC);

    assertEquals(BringupTestResult.PASS, test.getResult());
  }

  @Test
  void dslTestReadsXboxControllerExtendedButtonSignals() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    BringupTestContext context = controllerContext();
    XboxControllerDevice.setControllerInputs(
        Map.of(CONTROLLER_LABEL, Map.of(SIGNAL_X, 1.0, SIGNAL_D_UP, 1.0)));
    DslBringupTest xButtonTest = new DslBringupTest(buildControllerButtonTest(SIGNAL_X));
    DslBringupTest dpadUpTest = new DslBringupTest(buildControllerButtonTest(SIGNAL_D_UP));

    assertTrue(xButtonTest.start(context, START_SEC));
    xButtonTest.update(context, UPDATE_SEC);
    assertEquals(BringupTestResult.PASS, xButtonTest.getResult());

    assertTrue(dpadUpTest.start(context, START_SEC));
    dpadUpTest.update(context, UPDATE_SEC);
    assertEquals(BringupTestResult.PASS, dpadUpTest.getResult());
  }

  @Test
  void dslTestReadsXboxControllerAxisSignal() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    BringupTestContext context = controllerContext();
    XboxControllerDevice.setControllerInputs(Map.of(CONTROLLER_LABEL, Map.of(SIGNAL_LEFT_Y, 0.7)));
    DslBringupTest test = new DslBringupTest(buildControllerAxisTest());

    assertTrue(test.start(context, START_SEC));
    test.update(context, UPDATE_SEC);

    assertEquals(BringupTestResult.PASS, test.getResult());
  }

  @Test
  void dslTestEnabledStateCanToggle() {
    DslBringupTest test = new DslBringupTest(buildTest(), false);

    assertFalse(test.isEnabled());

    test.setEnabled(true);
    assertTrue(test.isEnabled());

    test.setEnabled(false);
    assertFalse(test.isEnabled());
  }

  @Test
  void dslTestUsesXboxControllerAxisForSignalSet() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    RecordingDevice motor = new RecordingDevice();
    BringupTestContext context = combinedContext(motor, new XboxControllerDevice(0, CONTROLLER_LABEL));
    XboxControllerDevice.setControllerInputs(Map.of(CONTROLLER_LABEL, Map.of(SIGNAL_LEFT_Y, 0.8)));
    DslBringupTest test = new DslBringupTest(buildSignalSetMainTest(0.25, 0.0, false));

    assertTrue(test.start(context, START_SEC));
    test.update(context, UPDATE_SEC);
    test.update(context, 11.1);

    assertEquals(BringupTestResult.PASS, test.getResult());
    assertEquals(2, motor.dutyWrites);
    assertEquals(0.2, motor.lastDuty, 0.0001);
  }

  @Test
  void dslSignalSetWithoutStoredDefaultLiteralStillUsesLiveAxisValue() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    RecordingDevice motor = new RecordingDevice();
    BringupTestContext context = combinedContext(motor, new XboxControllerDevice(0, CONTROLLER_LABEL));
    XboxControllerDevice.setControllerInputs(Map.of(CONTROLLER_LABEL, Map.of(SIGNAL_LEFT_Y, 0.8)));
    DslModels.DslNormalizedTest normalized = buildSignalSetMainTest(0.25, 0.0, false);
    normalized.main.sets.get(0).defaultLiteral = null;
    DslBringupTest test = new DslBringupTest(normalized);

    assertTrue(test.start(context, START_SEC));
    test.update(context, UPDATE_SEC);
    test.update(context, 11.1);

    assertEquals(BringupTestResult.PASS, test.getResult());
    assertEquals(2, motor.dutyWrites);
    assertEquals(0.2, motor.lastDuty, 0.0001);
  }

  @Test
  void dslSignalSetRequiredDevicesIncludeControllerInputs() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    seedConfiguredDeviceType(MOTOR_LABEL, DSL_MOTOR_TYPE);
    DslBringupTest test = new DslBringupTest(buildSignalSetMainTest(0.25, 0.0, false));

    assertEquals(List.of(MOTOR_LABEL, CONTROLLER_LABEL), test.getRequiredDeviceKeys());
  }

  @Test
  void dslSignalSetFailsStartupWhenInitSourceUnavailable() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    RecordingDevice motor = new RecordingDevice();
    BringupTestContext context = combinedContext(motor, new XboxControllerDevice(0, CONTROLLER_LABEL));
    DslBringupTest test = new DslBringupTest(buildSignalSetMainTest(0.25, 0.0, true));

    assertFalse(test.start(context, START_SEC));
    assertEquals(BringupTestResult.FAIL, test.getResult());
    assertEquals("Signal set source unavailable at startup: controller0.leftY", test.getStatus());
  }

  @Test
  void dslSignalSetFailsNormalStopWhenFallbackStillActive() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    RecordingDevice motor = new RecordingDevice();
    BringupTestContext context = combinedContext(motor, new XboxControllerDevice(0, CONTROLLER_LABEL));
    DslBringupTest test = new DslBringupTest(buildSignalSetMainTest(0.25, 0.0, false));

    assertTrue(test.start(context, START_SEC));
    test.update(context, 11.1);

    assertEquals(BringupTestResult.FAIL, test.getResult());
    assertEquals("until until_1: timer.elapsed >= 1.0 value=1.100 (fallback active)", test.getStatus());
    assertEquals(1, motor.dutyWrites);
    assertEquals(0.0, motor.lastDuty, 0.0001);
    assertTrue(test.buildRunDetails().toString().contains("signalSetFallbacks"));
  }

  @Test
  void dslSignalSetPassesAfterFallbackRecoversBeforeNormalStop() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    RecordingDevice motor = new RecordingDevice();
    BringupTestContext context = combinedContext(motor, new XboxControllerDevice(0, CONTROLLER_LABEL));
    DslBringupTest test = new DslBringupTest(buildSignalSetMainTest(0.25, 0.0, false));

    assertTrue(test.start(context, START_SEC));
    test.update(context, UPDATE_SEC);
    XboxControllerDevice.setControllerInputs(Map.of(CONTROLLER_LABEL, Map.of(SIGNAL_LEFT_Y, 0.6)));
    test.update(context, 10.5);
    test.update(context, 11.1);

    assertEquals(BringupTestResult.PASS, test.getResult());
    assertEquals(3, motor.dutyWrites);
    assertEquals(0.15, motor.lastDuty, 0.0001);
  }

  @Test
  void dslSignalSetAppliesDeadbandBeforeScaling() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    RecordingDevice motor = new RecordingDevice();
    BringupTestContext context = combinedContext(motor, new XboxControllerDevice(0, CONTROLLER_LABEL));
    XboxControllerDevice.setControllerInputs(Map.of(CONTROLLER_LABEL, Map.of(SIGNAL_LEFT_Y, 0.05)));
    DslBringupTest test = new DslBringupTest(buildSignalSetMainTest(0.25, 0.0, false, 0.08));

    assertTrue(test.start(context, START_SEC));
    test.update(context, UPDATE_SEC);
    test.update(context, 11.1);

    assertEquals(BringupTestResult.PASS, test.getResult());
    assertEquals(2, motor.dutyWrites);
    assertEquals(0.0, motor.lastDuty, 0.0001);
  }

  @Test
  void dslSignalSetLeavesValuesOutsideDeadbandUnchangedBeforeScaling() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    RecordingDevice motor = new RecordingDevice();
    BringupTestContext context = combinedContext(motor, new XboxControllerDevice(0, CONTROLLER_LABEL));
    XboxControllerDevice.setControllerInputs(Map.of(CONTROLLER_LABEL, Map.of(SIGNAL_LEFT_Y, 0.1)));
    DslBringupTest test = new DslBringupTest(buildSignalSetMainTest(0.25, 0.0, false, 0.08));

    assertTrue(test.start(context, START_SEC));
    test.update(context, UPDATE_SEC);
    test.update(context, 11.1);

    assertEquals(BringupTestResult.PASS, test.getResult());
    assertEquals(2, motor.dutyWrites);
    assertEquals(0.025, motor.lastDuty, 0.0001);
  }

  @Test
  void dslSignalSetFailsWhenResolvedValueIsOutOfRange() {
    seedConfiguredDeviceType(CONTROLLER_LABEL, CONTROLLER_TYPE);
    RecordingDevice motor = new RecordingDevice();
    BringupTestContext context = combinedContext(motor, new XboxControllerDevice(0, CONTROLLER_LABEL));
    XboxControllerDevice.setControllerInputs(Map.of(CONTROLLER_LABEL, Map.of(SIGNAL_LEFT_Y, 0.8)));
    DslBringupTest test = new DslBringupTest(buildSignalSetMainTest(2.0, 0.0, false));

    assertTrue(test.start(context, START_SEC));
    test.update(context, UPDATE_SEC);

    assertEquals(BringupTestResult.FAIL, test.getResult());
    assertEquals("Signal set produced out-of-range value: target=motor-a.output value=1.6", test.getStatus());
  }

  @Test
  void dslClearFailsWhenTargetDoesNotSupportRuntimeClear() {
    RecordingDevice motor = new NonClearableRecordingDevice();
    DslBringupTest test = new DslBringupTest(buildInitClearTest());
    BringupTestContext context = context(motor);

    assertFalse(test.start(context, START_SEC));
    assertEquals(BringupTestResult.FAIL, test.getResult());
    assertEquals("Unsupported clear DSL target at runtime: motor-a.faults", test.getStatus());
  }

  @Test
  void dslStableRequireLatchesOnlyAfterContinuousDuration() {
    SignalRecordingDevice motor = new SignalRecordingDevice();
    motor.setSignal("velocity", 150.0);
    DslBringupTest test = new DslBringupTest(buildStableRequireTest());
    BringupTestContext context = context(motor);

    assertTrue(test.start(context, START_SEC));
    test.update(context, START_SEC + 0.05);
    assertEquals(BringupTestResult.RUNNING, test.getResult());

    test.update(context, START_SEC + 0.12);
    test.update(context, START_SEC + 0.30);

    assertEquals(BringupTestResult.PASS, test.getResult());
    assertTrue(test.buildRunDetails().toString().contains("stableSatisfied=true"));
    assertTrue(test.buildRunDetails().toString().contains("latchedSatisfied=true"));
  }

  @Test
  void dslStableAbortIgnoresBriefSpikeButFailsSustainedSpike() {
    SignalRecordingDevice motor = new SignalRecordingDevice();
    DslBringupTest test = new DslBringupTest(buildStableAbortTest());
    BringupTestContext context = context(motor);

    assertTrue(test.start(context, START_SEC));
    motor.setSignal("current", 45.0);
    test.update(context, START_SEC + 0.05);
    motor.setSignal("current", 0.0);
    test.update(context, START_SEC + 0.08);
    assertEquals(BringupTestResult.RUNNING, test.getResult());

    motor.setSignal("current", 45.0);
    test.update(context, START_SEC + 0.20);
    test.update(context, START_SEC + 0.36);

    assertEquals(BringupTestResult.FAIL, test.getResult());
    assertEquals("abort abort_1: abort motor-a.current > 40 stable 0.1 value=45.000", test.getStatus());
  }

  @Test
  void dslRangeConditionsSupportBetweenAndOutside() {
    SignalRecordingDevice motor = new SignalRecordingDevice();
    motor.setSignal("current", 15.0);
    DslBringupTest test = new DslBringupTest(buildRangeConditionTest());
    BringupTestContext context = context(motor);

    assertTrue(test.start(context, START_SEC));
    test.update(context, START_SEC + 0.12);
    motor.setSignal("current", 25.0);
    test.update(context, START_SEC + 0.20);

    assertEquals(BringupTestResult.PASS, test.getResult());
  }

  private static DslModels.DslNormalizedTest buildTest() {
    DslModels.DslNormalizedTest test = new DslModels.DslNormalizedTest();
    test.name = TEST_NAME;
    DslModels.DslDeviceRef device = new DslModels.DslDeviceRef();
    device.name = MOTOR_LABEL;
    test.devices.add(device);

    DslModels.DslSetStatement set = new DslModels.DslSetStatement();
    set.id = "set_1";
    set.text = "set motor-a.output = 0.15";
    set.target = reference(MOTOR_LABEL, "output");
    set.literal = numberLiteral(DUTY);
    test.main.sets.add(set);

    DslModels.DslCondition until = new DslModels.DslCondition();
    until.id = "until_1";
    until.kind = "until";
    until.text = "timer.elapsed >= 1.5";
    until.reference = reference("timer", "elapsed");
    until.operator = ">=";
    until.literal = numberLiteral(1.5);
    test.main.untils.add(until);
    return test;
  }

  private static DslModels.DslNormalizedTest buildControllerButtonTest() {
    return buildControllerButtonTest(SIGNAL_A);
  }

  private static DslModels.DslNormalizedTest buildControllerButtonTest(String signalName) {
    DslModels.DslNormalizedTest test = new DslModels.DslNormalizedTest();
    test.name = "controller_button";
    DslModels.DslDeviceRef device = new DslModels.DslDeviceRef();
    device.name = CONTROLLER_LABEL;
    test.devices.add(device);

    DslModels.DslCondition success = new DslModels.DslCondition();
    success.id = "success_1";
    success.kind = "success";
    success.text = "success controller0." + signalName;
    success.reference = reference(CONTROLLER_LABEL, signalName);
    test.main.successes.add(success);
    return test;
  }

  private static DslModels.DslNormalizedTest buildControllerAxisTest() {
    DslModels.DslNormalizedTest test = new DslModels.DslNormalizedTest();
    test.name = "controller_axis";
    DslModels.DslDeviceRef device = new DslModels.DslDeviceRef();
    device.name = CONTROLLER_LABEL;
    test.devices.add(device);

    DslModels.DslCondition success = new DslModels.DslCondition();
    success.id = "success_1";
    success.kind = "success";
    success.text = "success controller0.leftY > 0.5";
    success.reference = reference(CONTROLLER_LABEL, SIGNAL_LEFT_Y);
    success.operator = ">";
    success.literal = numberLiteral(0.5);
    test.main.successes.add(success);
    return test;
  }

  private static DslModels.DslNormalizedTest buildSignalSetMainTest(
      double scale,
      double defaultValue,
      boolean setInInit) {
    return buildSignalSetMainTest(scale, defaultValue, setInInit, null);
  }

  private static DslModels.DslNormalizedTest buildSignalSetMainTest(
      double scale,
      double defaultValue,
      boolean setInInit,
      Double deadband) {
    DslModels.DslNormalizedTest test = new DslModels.DslNormalizedTest();
    test.name = "controller_drive";
    DslModels.DslDeviceRef motor = new DslModels.DslDeviceRef();
    motor.name = MOTOR_LABEL;
    test.devices.add(motor);
    DslModels.DslDeviceRef controller = new DslModels.DslDeviceRef();
    controller.name = CONTROLLER_LABEL;
    test.devices.add(controller);

    DslModels.DslSetStatement set = new DslModels.DslSetStatement();
    set.id = "set_1";
    set.text =
        "set motor-a.output = controller0.leftY scaled "
            + scale
            + " default "
            + defaultValue;
    set.target = reference(MOTOR_LABEL, "output");
    set.source = reference(CONTROLLER_LABEL, SIGNAL_LEFT_Y);
    set.deadband = deadband;
    set.scale = scale;
    set.defaultLiteral = numberLiteral(defaultValue);
    if (setInInit) {
      test.init.sets.add(set);
    } else {
      test.main.sets.add(set);
    }

    DslModels.DslCondition until = new DslModels.DslCondition();
    until.id = "until_1";
    until.kind = "until";
    until.text = "timer.elapsed >= 1.0";
    until.reference = reference("timer", "elapsed");
    until.operator = ">=";
    until.literal = numberLiteral(1.0);
    test.main.untils.add(until);
    return test;
  }

  private static DslModels.DslNormalizedTest buildInitClearTest() {
    DslModels.DslNormalizedTest test = new DslModels.DslNormalizedTest();
    test.name = "clear_faults";
    DslModels.DslDeviceRef motor = new DslModels.DslDeviceRef();
    motor.name = MOTOR_LABEL;
    test.devices.add(motor);

    DslModels.DslClearStatement clear = new DslModels.DslClearStatement();
    clear.id = "clear_1";
    clear.text = "clear motor-a.faults";
    clear.target = reference(MOTOR_LABEL, SIGNAL_FAULTS);
    test.init.clears.add(clear);
    return test;
  }

  private static DslModels.DslNormalizedTest buildStableRequireTest() {
    DslModels.DslNormalizedTest test = new DslModels.DslNormalizedTest();
    test.name = "stable_require";
    DslModels.DslDeviceRef motor = new DslModels.DslDeviceRef();
    motor.name = MOTOR_LABEL;
    test.devices.add(motor);

    DslModels.DslCondition require = new DslModels.DslCondition();
    require.id = "require_1";
    require.kind = "require";
    require.text = "require motor-a.velocity > 100 stable 0.1";
    require.reference = reference(MOTOR_LABEL, "velocity");
    require.mode = "comparison";
    require.operator = ">";
    require.literal = numberLiteral(100.0);
    require.stableSeconds = 0.1;
    test.main.requires.add(require);

    DslModels.DslCondition until = new DslModels.DslCondition();
    until.id = "until_1";
    until.kind = "until";
    until.text = "timer.elapsed >= 0.25";
    until.reference = reference("timer", "elapsed");
    until.mode = "comparison";
    until.operator = ">=";
    until.literal = numberLiteral(0.25);
    test.main.untils.add(until);
    return test;
  }

  private static DslModels.DslNormalizedTest buildStableAbortTest() {
    DslModels.DslNormalizedTest test = new DslModels.DslNormalizedTest();
    test.name = "stable_abort";
    DslModels.DslDeviceRef motor = new DslModels.DslDeviceRef();
    motor.name = MOTOR_LABEL;
    test.devices.add(motor);

    DslModels.DslCondition abort = new DslModels.DslCondition();
    abort.id = "abort_1";
    abort.kind = "abort";
    abort.text = "abort motor-a.current > 40 stable 0.1";
    abort.reference = reference(MOTOR_LABEL, "current");
    abort.mode = "comparison";
    abort.operator = ">";
    abort.literal = numberLiteral(40.0);
    abort.stableSeconds = 0.1;
    test.main.aborts.add(abort);

    DslModels.DslCondition until = new DslModels.DslCondition();
    until.id = "until_1";
    until.kind = "until";
    until.text = "timer.elapsed >= 1.0";
    until.reference = reference("timer", "elapsed");
    until.mode = "comparison";
    until.operator = ">=";
    until.literal = numberLiteral(1.0);
    test.main.untils.add(until);
    return test;
  }

  private static DslModels.DslNormalizedTest buildRangeConditionTest() {
    DslModels.DslNormalizedTest test = new DslModels.DslNormalizedTest();
    test.name = "range_conditions";
    DslModels.DslDeviceRef motor = new DslModels.DslDeviceRef();
    motor.name = MOTOR_LABEL;
    test.devices.add(motor);

    DslModels.DslCondition require = new DslModels.DslCondition();
    require.id = "require_1";
    require.kind = "require";
    require.text = "require motor-a.current between 10 20 stable 0.1";
    require.reference = reference(MOTOR_LABEL, "current");
    require.mode = "between";
    require.lowLiteral = numberLiteral(10.0);
    require.highLiteral = numberLiteral(20.0);
    require.stableSeconds = 0.1;
    test.main.requires.add(require);

    DslModels.DslCondition success = new DslModels.DslCondition();
    success.id = "success_1";
    success.kind = "success";
    success.text = "success motor-a.current outside 0 20";
    success.reference = reference(MOTOR_LABEL, "current");
    success.mode = "outside";
    success.lowLiteral = numberLiteral(0.0);
    success.highLiteral = numberLiteral(20.0);
    test.main.successes.add(success);
    return test;
  }

  private void seedConfiguredDeviceType(String label, String type) {
    try {
      Map<String, Object> registry = deviceRegistry();
      if (originalDeviceRegistry == null) {
        originalDeviceRegistry = new LinkedHashMap<>(registry);
      }
      Class<?> definitionClass = Class.forName(CLASS_DEVICE_DEFINITION);
      Constructor<?> constructor = definitionClass.getDeclaredConstructor();
      constructor.setAccessible(true);
      Object definition = constructor.newInstance();
      setField(definition, FIELD_LABEL, label);
      setField(definition, FIELD_TYPE, type);
      registry.put(normalizeKey(label), definition);
    } catch (ReflectiveOperationException ex) {
      throw new AssertionError(ex);
    }
  }

  @SuppressWarnings("unchecked")
  private static Map<String, Object> deviceRegistry() throws ReflectiveOperationException {
    Field field = BringupUtil.class.getDeclaredField(FIELD_DEVICE_REGISTRY);
    field.setAccessible(true);
    return (Map<String, Object>) field.get(null);
  }

  private static void setField(Object target, String name, Object value) throws ReflectiveOperationException {
    Field field = target.getClass().getDeclaredField(name);
    field.setAccessible(true);
    field.set(target, value);
  }

  private static String normalizeKey(String value) {
    return value == null ? EMPTY : value.trim().toUpperCase().replaceAll("[^A-Z0-9]+", EMPTY);
  }

  private static DslModels.DslReference reference(String device, String signal) {
    DslModels.DslReference reference = new DslModels.DslReference();
    reference.device = device;
    reference.signal = signal;
    reference.text = device + "." + signal;
    return reference;
  }

  private static DslModels.DslLiteral numberLiteral(double value) {
    DslModels.DslLiteral literal = new DslModels.DslLiteral();
    literal.value = value;
    literal.valueType = "number";
    return literal;
  }

  private static BringupTestContext context(DeviceUnit device) {
    RegistrationHeader header =
        new RegistrationHeader(VENDOR, VENDOR, DEVICE_TYPE, SOURCE, OWNER, EMPTY, EMPTY);
    DeviceRegistration registration =
        new DeviceRegistration(header, VENDOR, DEVICE_TYPE, DEVICE_TYPE, DeviceRole.MOTOR, false, null);
    DeviceTypeBucket bucket = new DeviceTypeBucket(registration, List.of(device), false);
    return new BringupTestContext(List.of(new SingleGroup(header, bucket)));
  }

  private static BringupTestContext controllerContext() {
    DeviceUnit device = new XboxControllerDevice(0, CONTROLLER_LABEL);
    DeviceRegistration registration =
        new DeviceRegistration(
            XboxControllerDevice.HEADER,
            MicrosoftDeviceGroup.VENDOR,
            CONTROLLER_TYPE,
            CONTROLLER_TYPE,
            DeviceRole.MISC,
            false,
            null);
    DeviceTypeBucket bucket = new DeviceTypeBucket(registration, List.of(device), false);
    return new BringupTestContext(List.of(new SingleGroup(MicrosoftDeviceGroup.HEADER, bucket)));
  }

  private static BringupTestContext combinedContext(DeviceUnit motor, DeviceUnit controller) {
    RegistrationHeader motorHeader =
        new RegistrationHeader(VENDOR, VENDOR, DEVICE_TYPE, SOURCE, OWNER, EMPTY, EMPTY);
    DeviceRegistration motorRegistration =
        new DeviceRegistration(motorHeader, VENDOR, DEVICE_TYPE, DEVICE_TYPE, DeviceRole.MOTOR, false, null);
    DeviceTypeBucket motorBucket = new DeviceTypeBucket(motorRegistration, List.of(motor), false);
    DeviceRegistration controllerRegistration =
        new DeviceRegistration(
            XboxControllerDevice.HEADER,
            MicrosoftDeviceGroup.VENDOR,
            CONTROLLER_TYPE,
            CONTROLLER_TYPE,
            DeviceRole.MISC,
            false,
            null);
    DeviceTypeBucket controllerBucket = new DeviceTypeBucket(controllerRegistration, List.of(controller), false);
    return new BringupTestContext(
        List.of(
            new SingleGroup(motorHeader, motorBucket),
            new SingleGroup(MicrosoftDeviceGroup.HEADER, controllerBucket)));
  }

  private static class RecordingDevice implements DeviceUnit {
    private int dutyWrites;
    private int stopWrites;
    private double lastDuty;
    private boolean created;

    @Override
    public int getCanId() {
      return CAN_ID;
    }

    @Override
    public RegistrationHeader getHeader() {
      return new RegistrationHeader(VENDOR, VENDOR, DEVICE_TYPE, SOURCE, OWNER, EMPTY, EMPTY);
    }

    @Override
    public String getDeviceType() {
      return DEVICE_TYPE;
    }

    @Override
    public String getLabel() {
      return MOTOR_LABEL;
    }

    @Override
    public boolean isCreated() {
      return created;
    }

    @Override
    public void ensureCreated() {
      created = true;
    }

    @Override
    public void close() {}

    @Override
    public void clearFaults() {}

    @Override
    public DeviceSnapshot snapshot() {
      return new DeviceSnapshot();
    }

    @Override
    public void setDuty(double duty) {
      dutyWrites++;
      lastDuty = duty;
    }

    @Override
    public void stop() {
      stopWrites++;
    }
  }

  private static final class NonClearableRecordingDevice extends RecordingDevice {
    @Override
    public boolean clearDslSignal(String signalName) {
      return false;
    }
  }

  private static final class SignalRecordingDevice extends RecordingDevice {
    private final Map<String, Object> signals = new LinkedHashMap<>();

    private void setSignal(String signalName, Object value) {
      signals.put(signalName, value);
    }

    @Override
    public Object readDslSignal(String signalName) {
      return signals.get(signalName);
    }
  }

  private static final class SingleGroup implements ManufacturerGroup {
    private final RegistrationHeader header;
    private final DeviceTypeBucket bucket;

    private SingleGroup(RegistrationHeader header, DeviceTypeBucket bucket) {
      this.header = header;
      this.bucket = bucket;
    }

    @Override
    public RegistrationHeader getHeader() {
      return header;
    }

    @Override
    public List<DeviceTypeBucket> getDeviceBuckets() {
      return List.of(bucket);
    }

    @Override
    public DeviceAddResult addNextMotor() {
      return null;
    }

    @Override
    public void resetLowCurrentTimers() {}

    @Override
    public List<DeviceUnit> getTestDevices() {
      return List.of();
    }

    @Override
    public void addAll() {}

    @Override
    public void setDuty(double duty) {}

    @Override
    public void stopAll() {}

    @Override
    public void clearFaults() {}

    @Override
    public void closeAll() {}

    @Override
    public List<DeviceSnapshot> captureSnapshots(double nowSec) {
      return List.of();
    }
  }
}
