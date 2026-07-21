package frc.robot.tests.dsl;

import frc.robot.BringupPrinter;
import frc.robot.BringupUtil;
import frc.robot.DeviceLifecycleRegistry;
import frc.robot.devices.DeviceUnit;
import frc.robot.tests.BringupTest;
import frc.robot.tests.BringupTestContext;
import frc.robot.tests.BringupTestResult;
import frc.robot.tests.dsl.DslModels.DslClearStatement;
import frc.robot.tests.dsl.DslModels.DslCondition;
import frc.robot.tests.dsl.DslModels.DslNormalizedTest;
import frc.robot.tests.dsl.DslModels.DslSetStatement;
import frc.robot.tests.dsl.DslModels.DslUnsafeExit;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * NAME
 *   DslBringupTest - Execution engine wrapper for one normalized DSL test.
 */
public final class DslBringupTest implements BringupTest {
  private static final String BUILTIN_TIMER_NAME = "timer";
  private static final String PHASE_INIT = "init";
  private static final String PHASE_MAIN = "main";
  private static final String PHASE_CLOSE = "close";
  private static final String CONDITION_MODE_BARE = "bare";
  private static final String CONDITION_MODE_COMPARISON = "comparison";
  private static final String CONDITION_MODE_BETWEEN = "between";
  private static final String CONDITION_MODE_OUTSIDE = "outside";
  private static final String OPERATOR_GT = ">";
  private static final String OPERATOR_GTE = ">=";
  private static final String OPERATOR_LT = "<";
  private static final String OPERATOR_LTE = "<=";
  private static final String OPERATOR_EQ = "==";
  private static final String OPERATOR_NEQ = "!=";
  private static final String DETAIL_KEY_CONDITIONS = "conditions";
  private static final String DETAIL_KEY_RAW = "raw";
  private static final String DETAIL_KEY_EFFECTIVE = "effective";
  private static final String DETAIL_KEY_STABLE_ELAPSED_SEC = "stableElapsedSec";
  private static final String DETAIL_KEY_STABLE_TARGET_SEC = "stableTargetSec";
  private static final String DETAIL_KEY_STABLE_SATISFIED = "stableSatisfied";
  private static final double WARNING_COOLDOWN_SEC = 1.0;
  private static final double SAFE_STOP_OUTPUT = 0.0;
  private static final double DEFAULT_SIGNAL_SET_FALLBACK = 0.0;
  private final DslNormalizedTest test;
  private final Map<String, DeviceUnit> devices = new LinkedHashMap<>();
  private final Map<String, String> declaredDeviceTypes = new LinkedHashMap<>();
  private final Map<String, Double> startPositions = new HashMap<>();
  private final Map<String, Boolean> requireSatisfied = new LinkedHashMap<>();
  private final Map<String, Double> requireSatisfiedAt = new LinkedHashMap<>();
  private final Map<String, Double> warningLastSec = new HashMap<>();
  private final Map<String, Boolean> fallbackActiveBySetId = new LinkedHashMap<>();
  private final Map<String, Double> lastResolvedSetValues = new LinkedHashMap<>();
  private final Map<String, Double> aggregateSignalMaxValues = new LinkedHashMap<>();
  private final Map<String, Boolean> conditionLastRawValues = new LinkedHashMap<>();
  private final Map<String, Boolean> conditionRawValues = new LinkedHashMap<>();
  private final Map<String, Boolean> conditionEffectiveValues = new LinkedHashMap<>();
  private final Map<String, Double> conditionStableStartSec = new LinkedHashMap<>();
  private final Map<String, Double> conditionStableElapsedSec = new LinkedHashMap<>();
  private final Map<String, Boolean> conditionStableSatisfied = new LinkedHashMap<>();
  private final Set<String> fallbackActiveThisTick = new HashSet<>();
  private BringupTestResult result = BringupTestResult.NOT_RUN;
  private String status = "";
  private double startSec = 0.0;
  private boolean finalized = false;
  private final Map<String, Object> lastSampleValues = new LinkedHashMap<>();

  public DslBringupTest(DslNormalizedTest test) {
    this.test = test;
  }

  @Override
  public String getName() {
    return test != null && test.name != null && !test.name.isBlank() ? test.name : "DSL Test";
  }

  @Override
  public boolean isEnabled() {
    return true;
  }

  @Override
  public boolean isRunning() {
    return result == BringupTestResult.RUNNING;
  }

  @Override
  public boolean isFinished() {
    return result == BringupTestResult.PASS || result == BringupTestResult.FAIL || result == BringupTestResult.INTERRUPTED;
  }

  @Override
  public BringupTestResult getResult() {
    return result;
  }

  @Override
  public String getStatus() {
    return status;
  }

  @Override
  public List<String> getRequiredDeviceKeys() {
    List<String> names = new ArrayList<>();
    if (test == null || test.devices == null) {
      return names;
    }
    for (DslModels.DslDeviceRef device : test.devices) {
      if (device != null && device.name != null && isRequiredHardwareDeviceName(device.name)) {
        names.add(device.name);
      }
    }
    return names;
  }

  @Override
  public boolean start(BringupTestContext context, double nowSec) {
    if (test == null || test.devices == null || test.devices.isEmpty()) {
      status = "No devices declared";
      result = BringupTestResult.FAIL;
      return false;
    }
    devices.clear();
    declaredDeviceTypes.clear();
    startPositions.clear();
    requireSatisfied.clear();
    requireSatisfiedAt.clear();
    lastSampleValues.clear();
    warningLastSec.clear();
    fallbackActiveBySetId.clear();
    lastResolvedSetValues.clear();
    aggregateSignalMaxValues.clear();
    conditionLastRawValues.clear();
    conditionRawValues.clear();
    conditionEffectiveValues.clear();
    conditionStableStartSec.clear();
    conditionStableElapsedSec.clear();
    conditionStableSatisfied.clear();
    fallbackActiveThisTick.clear();
    finalized = false;
    startSec = nowSec;
    for (DslModels.DslDeviceRef ref : test.devices) {
      if (ref == null || ref.name == null || ref.name.isBlank()) {
        continue;
      }
      String deviceType = resolveDeviceType(ref.name);
      if (deviceType != null && !deviceType.isBlank()) {
        declaredDeviceTypes.put(ref.name, deviceType);
      }
      DeviceUnit device = context.findDeviceByLabel(ref.name);
      if (device == null) {
        status = "Device not found: " + ref.name;
        result = BringupTestResult.FAIL;
        return false;
      }
      if (!context.isDeviceTestable(ref.name) && !context.isDeviceInstantiable(ref.name)) {
        status = lifecycleBlockedStatus(context, ref.name, "lifecycle-eligible");
        result = BringupTestResult.FAIL;
        return false;
      }
      if (!device.isCreated() && !context.isDeviceInstantiable(ref.name)) {
        status = lifecycleBlockedStatus(context, ref.name, "instantiable");
        result = BringupTestResult.FAIL;
        return false;
      }
      device.ensureCreated();
      devices.put(ref.name, device);
      Object position = readSignalValue(context, ref.name, DslSignalRegistry.SIGNAL_POSITION, nowSec);
      if (position instanceof Number numberValue) {
        startPositions.put(ref.name, numberValue.doubleValue());
      }
    }
    applySafeValues(context, nowSec, false);
    if (!applyClears(context, test.init.clears)) {
      return false;
    }
    if (!applySets(context, test.init.sets, nowSec, PHASE_INIT)) {
      return false;
    }
    for (DslCondition require : test.main.requires) {
      requireSatisfied.put(require.id, false);
    }
    result = BringupTestResult.RUNNING;
    status = "Running";
    long runId = context != null ? context.getRunId() : 0L;
    String prefix = runId > 0 ? ("Test started #" + runId + ": ") : "Test started: ";
    BringupPrinter.enqueue(prefix + getName());
    return true;
  }

  @Override
  public void update(BringupTestContext context, double nowSec) {
    if (result != BringupTestResult.RUNNING) {
      return;
    }
    fallbackActiveThisTick.clear();
    if (!applySets(context, test.main.sets, nowSec, PHASE_MAIN)) {
      stop(context);
      return;
    }
    Map<String, Object> samples = sampleAll(context, nowSec);
    Map<String, Boolean> conditionValues = evaluateAllConditions(samples, nowSec);
    for (DslCondition require : test.main.requires) {
      if (shouldRevokeLatchedRequire(require, samples)) {
        requireSatisfied.put(require.id, false);
        requireSatisfiedAt.remove(require.id);
        continue;
      }
      if (!Boolean.TRUE.equals(requireSatisfied.get(require.id))
          && Boolean.TRUE.equals(conditionValues.get(require.id))) {
        requireSatisfied.put(require.id, true);
        requireSatisfiedAt.put(require.id, nowSec - startSec);
      }
    }
    for (DslCondition condition : test.main.aborts) {
      if (Boolean.TRUE.equals(conditionValues.get(condition.id))) {
        status = "abort " + condition.id + ": " + condition.text;
        result = BringupTestResult.FAIL;
        stop(context);
        return;
      }
    }
    for (DslCondition condition : test.main.successes) {
      if (Boolean.TRUE.equals(conditionValues.get(condition.id))) {
        status = "success " + condition.id + ": " + condition.text;
        result = BringupTestResult.PASS;
        stop(context);
        return;
      }
    }
    for (DslCondition condition : test.main.untils) {
      if (Boolean.TRUE.equals(conditionValues.get(condition.id))) {
        boolean allSatisfied = true;
        for (Boolean value : requireSatisfied.values()) {
          if (!Boolean.TRUE.equals(value)) {
            allSatisfied = false;
            break;
          }
        }
        status = "until " + condition.id + ": " + condition.text;
        if (!fallbackActiveThisTick.isEmpty()) {
          status = status + " (fallback active)";
          result = BringupTestResult.FAIL;
        } else {
          result = allSatisfied ? BringupTestResult.PASS : BringupTestResult.FAIL;
        }
        stop(context);
        return;
      }
    }
  }

  @Override
  public void stop(BringupTestContext context) {
    if (finalized) {
      return;
    }
    if (result == BringupTestResult.RUNNING) {
      result = BringupTestResult.INTERRUPTED;
      status = status == null || status.isBlank() ? "Interrupted" : status;
    }
    applyClears(context, test.close.clears);
    applySets(context, test.close.sets, startSec, PHASE_CLOSE);
    applySafeValues(context, startSec, true);
    finalized = true;
  }

  public boolean skipGlobalStopOnFinish() {
    return true;
  }

  public Map<String, Object> buildRunDetails() {
    Map<String, Object> details = new LinkedHashMap<>();
    details.put("test", getName());
    details.put("status", status != null ? status : "");
    details.put("result", result != null ? result.name() : "");
    details.put("requires", buildRequireDetails());
    details.put("lastSamples", new LinkedHashMap<>(lastSampleValues));
    details.put("aggregateSignals", new LinkedHashMap<>(aggregateSignalMaxValues));
    details.put("lastResolvedSets", new LinkedHashMap<>(lastResolvedSetValues));
    details.put("signalSetFallbacks", buildSignalSetFallbackDetails());
    details.put(DETAIL_KEY_CONDITIONS, buildConditionDetails());
    details.put("unsafeExit", buildUnsafeExitDetails());
    return details;
  }

  private List<Map<String, Object>> buildRequireDetails() {
    if (test == null || test.main == null || test.main.requires == null) {
      return Collections.emptyList();
    }
    List<Map<String, Object>> rows = new ArrayList<>();
    for (DslCondition condition : test.main.requires) {
      if (condition == null) {
        continue;
      }
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("id", condition.id);
      row.put("text", condition.text);
      boolean satisfied = Boolean.TRUE.equals(requireSatisfied.get(condition.id));
      row.put("satisfied", satisfied);
      row.put("satisfiedAtSec", requireSatisfiedAt.get(condition.id));
      row.put("sampleValue", lastSampleValues.get(condition.reference.text));
      if (condition.stableSeconds != null) {
        row.put(DETAIL_KEY_RAW, conditionRawValues.get(condition.id));
        row.put(DETAIL_KEY_STABLE_ELAPSED_SEC, conditionStableElapsedSec.get(condition.id));
        row.put(DETAIL_KEY_STABLE_TARGET_SEC, condition.stableSeconds);
        row.put(DETAIL_KEY_STABLE_SATISFIED, conditionStableSatisfied.get(condition.id));
      }
      rows.add(row);
    }
    return rows;
  }

  private List<Map<String, Object>> buildConditionDetails() {
    List<Map<String, Object>> rows = new ArrayList<>();
    for (DslCondition condition : allConditions()) {
      if (condition == null || condition.stableSeconds == null) {
        continue;
      }
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("id", condition.id);
      row.put("text", condition.text);
      row.put(DETAIL_KEY_RAW, conditionRawValues.get(condition.id));
      row.put(DETAIL_KEY_EFFECTIVE, conditionEffectiveValues.get(condition.id));
      row.put(DETAIL_KEY_STABLE_ELAPSED_SEC, conditionStableElapsedSec.get(condition.id));
      row.put(DETAIL_KEY_STABLE_TARGET_SEC, condition.stableSeconds);
      row.put(DETAIL_KEY_STABLE_SATISFIED, conditionStableSatisfied.get(condition.id));
      if ("require".equals(condition.kind)) {
        row.put("latchedSatisfied", requireSatisfied.get(condition.id));
      }
      rows.add(row);
    }
    return rows;
  }

  private List<Map<String, Object>> buildUnsafeExitDetails() {
    if (test == null || test.unsafeExit == null) {
      return Collections.emptyList();
    }
    List<Map<String, Object>> rows = new ArrayList<>();
    for (DslUnsafeExit unsafeExit : test.unsafeExit) {
      if (unsafeExit == null || unsafeExit.target == null) {
        continue;
      }
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("id", unsafeExit.id);
      row.put("text", unsafeExit.text);
      row.put("device", unsafeExit.target.device);
      row.put("signal", unsafeExit.target.signal);
      rows.add(row);
    }
    return rows;
  }

  private List<Map<String, Object>> buildSignalSetFallbackDetails() {
    List<Map<String, Object>> rows = new ArrayList<>();
    for (Map.Entry<String, Boolean> entry : fallbackActiveBySetId.entrySet()) {
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("id", entry.getKey());
      row.put("active", Boolean.TRUE.equals(entry.getValue()));
      rows.add(row);
    }
    return rows;
  }

  private boolean applySets(BringupTestContext context, List<DslSetStatement> sets, double nowSec, String phaseName) {
    for (DslSetStatement statement : sets) {
      if (statement == null || statement.target == null) {
        continue;
      }
      ResolvedSetValue resolved = resolveSetValue(context, statement, nowSec, phaseName);
      if (!resolved.continueExecution) {
        return false;
      }
      if (!resolved.shouldWrite) {
        continue;
      }
      if (!writeTargetSignal(context, statement, resolved.value)) {
        return false;
      }
    }
    return true;
  }

  private boolean applyClears(BringupTestContext context, List<DslClearStatement> clears) {
    for (DslClearStatement statement : clears) {
      if (statement == null || statement.target == null) {
        continue;
      }
      DeviceUnit device = devices.get(statement.target.device);
      if (device == null) {
        status = "Device not found: " + statement.target.device;
        result = BringupTestResult.FAIL;
        return false;
      }
      if (!context.isDeviceTestable(statement.target.device)) {
        status = lifecycleBlockedStatus(context, statement.target.device, "testable for clear");
        result = BringupTestResult.FAIL;
        return false;
      }
      if (!device.clearDslSignal(statement.target.signal)) {
        status = "Unsupported clear DSL target at runtime: " + statement.target.text;
        result = BringupTestResult.FAIL;
        return false;
      }
    }
    return true;
  }

  private void applySafeValues(BringupTestContext context, double nowSec, boolean finalExit) {
    for (Map.Entry<String, DeviceUnit> entry : devices.entrySet()) {
      String deviceName = entry.getKey();
      if (!context.isDeviceTestable(deviceName)) {
        continue;
      }
      String deviceType = resolveDeviceType(deviceName);
      Map<String, frc.robot.tests.dsl.signals.DslSignalMeta> signals =
          DslSignalRegistry.registry().get(deviceType);
      if (signals == null) {
        continue;
      }
      for (Map.Entry<String, frc.robot.tests.dsl.signals.DslSignalMeta> signalEntry : signals.entrySet()) {
        if (!signalEntry.getValue().writable()) {
          continue;
        }
        if (finalExit && isUnsafeExit(deviceName, signalEntry.getKey())) {
          continue;
        }
        Double safeValue = signalEntry.getValue().safeValue();
        if (safeValue != null) {
          if (shouldApplySafeStop(signalEntry.getKey(), safeValue.doubleValue())) {
            entry.getValue().stop();
          } else {
            entry.getValue().writeDslSignal(signalEntry.getKey(), safeValue.doubleValue());
          }
        }
      }
    }
  }

  private boolean shouldApplySafeStop(String signalName, double safeValue) {
    return DslSignalRegistry.SIGNAL_OUTPUT.equals(signalName)
        && Double.compare(safeValue, SAFE_STOP_OUTPUT) == 0;
  }

  private boolean isUnsafeExit(String deviceName, String signalName) {
    for (DslUnsafeExit item : test.unsafeExit) {
      if (item != null && item.target != null
          && deviceName.equalsIgnoreCase(item.target.device)
          && signalName.equalsIgnoreCase(item.target.signal)) {
        return true;
      }
    }
    return false;
  }

  private ResolvedSetValue resolveSetValue(
      BringupTestContext context,
      DslSetStatement statement,
      double nowSec,
      String phaseName) {
    if (statement.literal != null) {
      if (!(statement.literal.value instanceof Number numberValue)) {
        status = "Set literal is not numeric: " + statement.text;
        result = BringupTestResult.FAIL;
        return ResolvedSetValue.fail();
      }
      double value = numberValue.doubleValue();
      if (!isTargetValueInRange(context, statement.target.device, statement.target.signal, value)) {
        return handleOutOfRange(statement, value, phaseName, nowSec);
      }
      lastResolvedSetValues.put(statement.id, value);
      return ResolvedSetValue.write(value);
    }
    if (statement.source == null || statement.scale == null) {
      status = "Signal set incomplete: " + statement.text;
      result = BringupTestResult.FAIL;
      return ResolvedSetValue.fail();
    }
    Object sourceValue = readSignalValue(context, statement.source.device, statement.source.signal, nowSec);
    if (!(sourceValue instanceof Number numberValue)) {
      return handleUnavailableSource(context, statement, phaseName, nowSec);
    }
    double source = applyDeadband(numberValue.doubleValue(), statement.deadband);
    double resolved = source * statement.scale.doubleValue();
    if (!isTargetValueInRange(context, statement.target.device, statement.target.signal, resolved)) {
      return handleOutOfRange(statement, resolved, phaseName, nowSec);
    }
    lastResolvedSetValues.put(statement.id, resolved);
    clearFallbackWarning(statement, nowSec);
    return ResolvedSetValue.write(resolved);
  }

  private ResolvedSetValue handleUnavailableSource(
      BringupTestContext context,
      DslSetStatement statement,
      String phaseName,
      double nowSec) {
    if (PHASE_INIT.equals(phaseName)) {
      status = "Signal set source unavailable at startup: " + statement.source.text;
      result = BringupTestResult.FAIL;
      return ResolvedSetValue.fail();
    }
    if (PHASE_CLOSE.equals(phaseName)) {
      return ResolvedSetValue.skip();
    }
    Double fallbackValue = resolveSignalSetDefaultValue(statement);
    if (fallbackValue == null) {
      status = "Signal set default is not numeric: " + statement.text;
      result = BringupTestResult.FAIL;
      return ResolvedSetValue.fail();
    }
    double fallback = fallbackValue.doubleValue();
    if (!isTargetValueInRange(context, statement.target.device, statement.target.signal, fallback)) {
      status = "Signal set default out of range: " + statement.text;
      result = BringupTestResult.FAIL;
      return ResolvedSetValue.fail();
    }
    lastResolvedSetValues.put(statement.id, fallback);
    markFallbackWarning(statement, fallback, nowSec);
    return ResolvedSetValue.write(fallback);
  }

  private Double resolveSignalSetDefaultValue(DslSetStatement statement) {
    if (statement.defaultLiteral == null) {
      return DEFAULT_SIGNAL_SET_FALLBACK;
    }
    if (!(statement.defaultLiteral.value instanceof Number defaultNumber)) {
      return null;
    }
    return defaultNumber.doubleValue();
  }

  private ResolvedSetValue handleOutOfRange(
      DslSetStatement statement,
      double value,
      String phaseName,
      double nowSec) {
    String message =
        "Signal set produced out-of-range value: target="
            + statement.target.text
            + " value="
            + value;
    if (PHASE_CLOSE.equals(phaseName)) {
      logWarningThrottled(statement.id + ":range", message, nowSec);
      return ResolvedSetValue.skip();
    }
    status = message;
    result = BringupTestResult.FAIL;
    return ResolvedSetValue.fail();
  }

  private boolean writeTargetSignal(
      BringupTestContext context,
      DslSetStatement statement,
      double value) {
    DeviceUnit device = devices.get(statement.target.device);
    if (device == null) {
      status = "Device not found: " + statement.target.device;
      result = BringupTestResult.FAIL;
      return false;
    }
    if (!context.isDeviceTestable(statement.target.device)) {
      status = lifecycleBlockedStatus(context, statement.target.device, "testable for write");
      result = BringupTestResult.FAIL;
      return false;
    }
    if (device.writeDslSignal(statement.target.signal, value)) {
      return true;
    }
    status = "Unsupported writable DSL target at runtime: " + statement.target.text;
    result = BringupTestResult.FAIL;
    return false;
  }

  private boolean isTargetValueInRange(
      BringupTestContext context,
      String deviceName,
      String signalName,
      double value) {
    DeviceUnit device = devices.get(deviceName);
    if (device == null || !context.isDeviceTestable(deviceName)) {
      return false;
    }
    return device.isDslWritableValueInRange(signalName, value);
  }

  private double applyDeadband(double value, Double deadband) {
    if (deadband == null) {
      return value;
    }
    return Math.abs(value) < deadband.doubleValue() ? 0.0 : value;
  }

  private void markFallbackWarning(DslSetStatement statement, double fallback, double nowSec) {
    fallbackActiveThisTick.add(statement.id);
    fallbackActiveBySetId.put(statement.id, true);
    logWarningThrottled(
        statement.id + ":fallback",
        "Signal set fallback active: target="
            + statement.target.text
            + " source="
            + statement.source.text
            + " default="
            + fallback,
        nowSec);
  }

  private void clearFallbackWarning(DslSetStatement statement, double nowSec) {
    if (!Boolean.TRUE.equals(fallbackActiveBySetId.get(statement.id))) {
      return;
    }
    fallbackActiveBySetId.put(statement.id, false);
    BringupPrinter.enqueue(
        "Signal set source recovered: target="
            + statement.target.text
            + " source="
            + statement.source.text);
  }

  private void logWarningThrottled(String key, String message, double nowSec) {
    Double last = warningLastSec.get(key);
    if (last != null && (nowSec - last.doubleValue()) < WARNING_COOLDOWN_SEC) {
      return;
    }
    warningLastSec.put(key, nowSec);
    BringupPrinter.enqueue(message);
  }

  private Map<String, Object> sampleAll(BringupTestContext context, double nowSec) {
    Map<String, Object> samples = new LinkedHashMap<>();
    for (DslCondition condition : allConditions()) {
      String key = condition.reference.text;
      if (!samples.containsKey(key)) {
        samples.put(key, readSignalValue(context, condition.reference.device, condition.reference.signal, nowSec));
      }
    }
    lastSampleValues.clear();
    lastSampleValues.putAll(samples);
    return samples;
  }

  private List<DslCondition> allConditions() {
    List<DslCondition> all = new ArrayList<>();
    all.addAll(test.main.aborts);
    all.addAll(test.main.successes);
    all.addAll(test.main.untils);
    all.addAll(test.main.requires);
    return all;
  }

  private Map<String, Boolean> evaluateAllConditions(Map<String, Object> samples, double nowSec) {
    Map<String, Boolean> results = new LinkedHashMap<>();
    for (DslCondition condition : allConditions()) {
      if (condition == null) {
        continue;
      }
      boolean effectiveValue = evaluateCondition(condition, samples, nowSec);
      results.put(condition.id, effectiveValue);
    }
    return results;
  }

  private boolean evaluateCondition(DslCondition condition, Map<String, Object> samples, double nowSec) {
    boolean rawValue = evaluateRawCondition(condition, samples);
    conditionRawValues.put(condition.id, rawValue);
    boolean effectiveValue = updateStableFilter(condition, rawValue, nowSec);
    conditionEffectiveValues.put(condition.id, effectiveValue);
    conditionLastRawValues.put(condition.id, rawValue);
    return effectiveValue;
  }

  private boolean evaluateRawCondition(DslCondition condition, Map<String, Object> samples) {
    Object left = samples.get(condition.reference.text);
    String mode = resolveConditionMode(condition);
    if (CONDITION_MODE_BARE.equals(mode)) {
      return Boolean.TRUE.equals(left);
    }
    if (CONDITION_MODE_BETWEEN.equals(mode) || CONDITION_MODE_OUTSIDE.equals(mode)) {
      return evaluateRangeCondition(condition, left, CONDITION_MODE_OUTSIDE.equals(mode));
    }
    Object right = condition.literal != null ? condition.literal.value : null;
    if (left instanceof Number leftNumber && right instanceof Number rightNumber) {
      double a = leftNumber.doubleValue();
      double b = rightNumber.doubleValue();
      return switch (condition.operator) {
        case OPERATOR_GT -> a > b;
        case OPERATOR_GTE -> a >= b;
        case OPERATOR_LT -> a < b;
        case OPERATOR_LTE -> a <= b;
        case OPERATOR_EQ -> Double.compare(a, b) == 0;
        case OPERATOR_NEQ -> Double.compare(a, b) != 0;
        default -> false;
      };
    }
    if (left instanceof Boolean leftBool && right instanceof Boolean rightBool) {
      return switch (condition.operator) {
        case OPERATOR_EQ -> leftBool == rightBool;
        case OPERATOR_NEQ -> leftBool != rightBool;
        default -> false;
      };
    }
    if (left != null && right != null) {
      return switch (condition.operator) {
        case OPERATOR_EQ -> left.toString().equals(right.toString());
        case OPERATOR_NEQ -> !left.toString().equals(right.toString());
        default -> false;
      };
    }
    return false;
  }

  private String resolveConditionMode(DslCondition condition) {
    if (condition.mode != null && !condition.mode.isBlank()) {
      return condition.mode;
    }
    if (condition.operator != null && !condition.operator.isBlank()) {
      return CONDITION_MODE_COMPARISON;
    }
    if (condition.lowLiteral != null || condition.highLiteral != null) {
      return CONDITION_MODE_BETWEEN;
    }
    return CONDITION_MODE_BARE;
  }

  private boolean evaluateRangeCondition(DslCondition condition, Object left, boolean outsideMode) {
    Object lowValue = condition.lowLiteral != null ? condition.lowLiteral.value : null;
    Object highValue = condition.highLiteral != null ? condition.highLiteral.value : null;
    if (!(left instanceof Number leftNumber)
        || !(lowValue instanceof Number lowNumber)
        || !(highValue instanceof Number highNumber)) {
      return false;
    }
    double sample = leftNumber.doubleValue();
    double low = lowNumber.doubleValue();
    double high = highNumber.doubleValue();
    boolean inside = sample >= low && sample <= high;
    return outsideMode ? !inside : inside;
  }

  private boolean updateStableFilter(DslCondition condition, boolean rawValue, double nowSec) {
    if (condition.stableSeconds == null) {
      return rawValue;
    }
    if (!rawValue) {
      conditionStableStartSec.remove(condition.id);
      conditionStableElapsedSec.put(condition.id, 0.0);
      conditionStableSatisfied.put(condition.id, false);
      return false;
    }
    boolean previousRaw = Boolean.TRUE.equals(conditionLastRawValues.get(condition.id));
    Double previousStart = conditionStableStartSec.get(condition.id);
    double stableStart = previousRaw && previousStart != null ? previousStart.doubleValue() : nowSec;
    double stableElapsed = nowSec - stableStart;
    boolean stableSatisfied = stableElapsed >= condition.stableSeconds.doubleValue();
    conditionStableStartSec.put(condition.id, stableStart);
    conditionStableElapsedSec.put(condition.id, stableElapsed);
    conditionStableSatisfied.put(condition.id, stableSatisfied);
    return stableSatisfied;
  }

  private Object readSignalValue(BringupTestContext context, String deviceName, String signalName, double nowSec) {
    if (BUILTIN_TIMER_NAME.equalsIgnoreCase(deviceName) && DslSignalRegistry.SIGNAL_ELAPSED.equals(signalName)) {
      return nowSec - startSec;
    }
    DeviceUnit device = devices.get(deviceName);
    if (device == null || !context.isDeviceSnapshotAllowed(deviceName)) {
      return null;
    }
    if (DslSignalRegistry.SIGNAL_CURRENT_ACTUAL_MAX.equals(signalName)) {
      return updateAggregateSignalMax(
          deviceName,
          signalName,
          readSignalValue(context, deviceName, DslSignalRegistry.SIGNAL_CURRENT_ACTUAL, nowSec),
          false);
    }
    if (DslSignalRegistry.SIGNAL_VELOCITY_ACTUAL_MAX_ABS.equals(signalName)) {
      return updateAggregateSignalMax(
          deviceName,
          signalName,
          readSignalValue(context, deviceName, DslSignalRegistry.SIGNAL_VELOCITY_ACTUAL, nowSec),
          true);
    }
    if (DslSignalRegistry.SIGNAL_POSITION_DELTA_MAX_ABS.equals(signalName)) {
      return updateAggregateSignalMax(
          deviceName,
          signalName,
          readSignalValue(context, deviceName, DslSignalRegistry.SIGNAL_POSITION_DELTA, nowSec),
          true);
    }
    return readDeviceSignalValue(deviceName, signalName);
  }

  private Object readDeviceSignalValue(String deviceName, String signalName) {
    DeviceUnit device = devices.get(deviceName);
    if (device == null) {
      return null;
    }
    String deviceType = resolveDeviceType(deviceName);
    Object deviceSignal = device.readDslSignal(signalName);
    if (deviceSignal instanceof Number numberValue
        && isDeltaPositionSignal(signalName)
        && (DslSignalRegistry.DEVICE_TYPE_MOTOR.equals(deviceType)
            || DslSignalRegistry.DEVICE_TYPE_ENCODER_EXTERNAL.equals(deviceType))) {
      Double start = startPositions.get(deviceName);
      double position = numberValue.doubleValue();
      return start != null ? position - start.doubleValue() : position;
    }
    return deviceSignal;
  }

  private boolean shouldRevokeLatchedRequire(DslCondition condition, Map<String, Object> samples) {
    if (condition == null || condition.reference == null) {
      return false;
    }
    if (!Boolean.TRUE.equals(requireSatisfied.get(condition.id))) {
      return false;
    }
    String deviceType = resolveDeviceType(condition.reference.device);
    if (!DslSignalRegistry.DEVICE_TYPE_PDP.equals(deviceType)
        && !DslSignalRegistry.DEVICE_TYPE_PDH.equals(deviceType)) {
      return false;
    }
    return samples.get(condition.reference.text) == null;
  }

  private Object updateAggregateSignalMax(
      String deviceName,
      String signalName,
      Object sampleValue,
      boolean absoluteValue) {
    String key = deviceName + "|" + signalName;
    Double previous = aggregateSignalMaxValues.get(key);
    if (!(sampleValue instanceof Number numberValue)) {
      return previous;
    }
    double candidate = numberValue.doubleValue();
    if (absoluteValue) {
      candidate = Math.abs(candidate);
    }
    if (previous == null || candidate > previous.doubleValue()) {
      aggregateSignalMaxValues.put(key, candidate);
      return candidate;
    }
    return previous;
  }

  private boolean isDeltaPositionSignal(String signalName) {
    return DslSignalRegistry.SIGNAL_POSITION.equals(signalName)
        || DslSignalRegistry.SIGNAL_POSITION_DELTA.equals(signalName);
  }

  private boolean isRequiredHardwareDeviceName(String deviceName) {
    String deviceType = resolveDeviceType(deviceName);
    return !DslSignalRegistry.DEVICE_TYPE_TEST_TIMER.equals(deviceType);
  }

  private String resolveDeviceType(String deviceName) {
    if (BUILTIN_TIMER_NAME.equalsIgnoreCase(deviceName)) {
      return DslSignalRegistry.DEVICE_TYPE_TEST_TIMER;
    }
    String declared = declaredDeviceTypes.get(deviceName);
    if (declared != null && !declared.isBlank()) {
      return declared;
    }
    String configured = BringupUtil.getConfiguredDeviceTypeByLabel(deviceName);
    if (configured != null && !configured.isBlank()) {
      return configured;
    }
    return devices.containsKey(deviceName) ? DslSignalRegistry.DEVICE_TYPE_MOTOR : null;
  }

  private String lifecycleBlockedStatus(
      BringupTestContext context,
      String deviceName,
      String operationName) {
    DeviceLifecycleRegistry.DeviceLifecycleView lifecycle = context.deviceLifecycleView(deviceName);
    String reason = lifecycle != null ? lifecycle.notTestableReason : "lifecycle blocked";
    return "Device not " + operationName + ": " + deviceName + " (" + reason + ")";
  }

  private static final class ResolvedSetValue {
    private final boolean continueExecution;
    private final boolean shouldWrite;
    private final double value;

    private ResolvedSetValue(boolean continueExecution, boolean shouldWrite, double value) {
      this.continueExecution = continueExecution;
      this.shouldWrite = shouldWrite;
      this.value = value;
    }

    private static ResolvedSetValue write(double value) {
      return new ResolvedSetValue(true, true, value);
    }

    private static ResolvedSetValue skip() {
      return new ResolvedSetValue(true, false, 0.0);
    }

    private static ResolvedSetValue fail() {
      return new ResolvedSetValue(false, false, 0.0);
    }
  }
}
