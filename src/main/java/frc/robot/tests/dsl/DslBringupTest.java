package frc.robot.tests.dsl;

import frc.robot.BringupPrinter;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.diag.snapshots.DeviceSnapshot;
import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
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
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * NAME
 *   DslBringupTest - Execution engine wrapper for one normalized DSL test.
 */
public final class DslBringupTest implements BringupTest {
  private static final String BUILTIN_TIMER_NAME = "timer";

  private final DslNormalizedTest test;
  private final Map<String, DeviceUnit> devices = new LinkedHashMap<>();
  private final Map<String, Double> startPositions = new HashMap<>();
  private final Map<String, Boolean> requireSatisfied = new LinkedHashMap<>();
  private final Map<String, Double> requireSatisfiedAt = new LinkedHashMap<>();
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
  public List<String> getMotorKeys() {
    List<String> names = new ArrayList<>();
    if (test == null || test.devices == null) {
      return names;
    }
    for (DslModels.DslDeviceRef device : test.devices) {
      if (device != null && device.name != null) {
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
    startPositions.clear();
    requireSatisfied.clear();
    requireSatisfiedAt.clear();
    lastSampleValues.clear();
    finalized = false;
    for (DslModels.DslDeviceRef ref : test.devices) {
      if (ref == null || ref.name == null || ref.name.isBlank()) {
        continue;
      }
      DeviceUnit device = context.findDeviceByLabel(ref.name);
      if (device == null) {
        status = "Device not found: " + ref.name;
        result = BringupTestResult.FAIL;
        return false;
      }
      device.ensureCreated();
      devices.put(ref.name, device);
      Object position = readSignalValue(ref.name, DslSignalRegistry.SIGNAL_POSITION, nowSec);
      if (position instanceof Number numberValue) {
        startPositions.put(ref.name, numberValue.doubleValue());
      }
    }
    applySafeValues(nowSec, false);
    applyClears(test.init.clears);
    applySets(test.init.sets, nowSec);
    startSec = nowSec;
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
    applySets(test.main.sets, nowSec);
    Map<String, Object> samples = sampleAll(nowSec);
    for (DslCondition require : test.main.requires) {
      if (!Boolean.TRUE.equals(requireSatisfied.get(require.id)) && evaluateCondition(require, samples, nowSec)) {
        requireSatisfied.put(require.id, true);
        requireSatisfiedAt.put(require.id, nowSec - startSec);
      }
    }
    for (DslCondition condition : test.main.aborts) {
      if (evaluateCondition(condition, samples, nowSec)) {
        status = "abort " + condition.id + ": " + condition.text;
        result = BringupTestResult.FAIL;
        stop(context);
        return;
      }
    }
    for (DslCondition condition : test.main.successes) {
      if (evaluateCondition(condition, samples, nowSec)) {
        status = "success " + condition.id + ": " + condition.text;
        result = BringupTestResult.PASS;
        stop(context);
        return;
      }
    }
    for (DslCondition condition : test.main.untils) {
      if (evaluateCondition(condition, samples, nowSec)) {
        boolean allSatisfied = true;
        for (Boolean value : requireSatisfied.values()) {
          if (!Boolean.TRUE.equals(value)) {
            allSatisfied = false;
            break;
          }
        }
        status = "until " + condition.id + ": " + condition.text;
        result = allSatisfied ? BringupTestResult.PASS : BringupTestResult.FAIL;
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
    applyClears(test.close.clears);
    applySets(test.close.sets, startSec);
    applySafeValues(startSec, true);
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

  private void applySets(List<DslSetStatement> sets, double nowSec) {
    for (DslSetStatement statement : sets) {
      if (statement == null || statement.target == null || statement.literal == null) {
        continue;
      }
      String deviceType = resolveDeviceType(statement.target.device);
      if (DslSignalRegistry.DEVICE_TYPE_MOTOR.equals(deviceType)
          && DslSignalRegistry.SIGNAL_OUTPUT.equals(statement.target.signal)) {
        DeviceUnit device = devices.get(statement.target.device);
        if (device != null && statement.literal.value instanceof Number numberValue) {
          device.setDuty(numberValue.doubleValue());
        }
      }
    }
  }

  private void applyClears(List<DslClearStatement> clears) {
    for (DslClearStatement statement : clears) {
      if (statement == null || statement.target == null) {
        continue;
      }
      if (DslSignalRegistry.SIGNAL_FAULTS.equals(statement.target.signal)) {
        DeviceUnit device = devices.get(statement.target.device);
        if (device != null) {
          device.clearFaults();
        }
      }
    }
  }

  private void applySafeValues(double nowSec, boolean finalExit) {
    for (Map.Entry<String, DeviceUnit> entry : devices.entrySet()) {
      String deviceName = entry.getKey();
      String deviceType = resolveDeviceType(deviceName);
      Map<String, DslSignalRegistry.SignalMeta> signals = DslSignalRegistry.registry().get(deviceType);
      if (signals == null) {
        continue;
      }
      for (Map.Entry<String, DslSignalRegistry.SignalMeta> signalEntry : signals.entrySet()) {
        if (!signalEntry.getValue().writable()) {
          continue;
        }
        if (finalExit && isUnsafeExit(deviceName, signalEntry.getKey())) {
          continue;
        }
        if (DslSignalRegistry.SIGNAL_OUTPUT.equals(signalEntry.getKey())) {
          entry.getValue().stop();
        }
      }
    }
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

  private Map<String, Object> sampleAll(double nowSec) {
    Map<String, Object> samples = new LinkedHashMap<>();
    for (DslCondition condition : allConditions()) {
      String key = condition.reference.text;
      if (!samples.containsKey(key)) {
        samples.put(key, readSignalValue(condition.reference.device, condition.reference.signal, nowSec));
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

  private boolean evaluateCondition(DslCondition condition, Map<String, Object> samples, double nowSec) {
    Object left = samples.get(condition.reference.text);
    if (condition.operator == null || condition.operator.isBlank()) {
      return Boolean.TRUE.equals(left);
    }
    Object right = condition.literal != null ? condition.literal.value : null;
    if (left instanceof Number leftNumber && right instanceof Number rightNumber) {
      double a = leftNumber.doubleValue();
      double b = rightNumber.doubleValue();
      return switch (condition.operator) {
        case ">" -> a > b;
        case ">=" -> a >= b;
        case "<" -> a < b;
        case "<=" -> a <= b;
        case "==" -> Double.compare(a, b) == 0;
        case "!=" -> Double.compare(a, b) != 0;
        default -> false;
      };
    }
    if (left instanceof Boolean leftBool && right instanceof Boolean rightBool) {
      return switch (condition.operator) {
        case "==" -> leftBool == rightBool;
        case "!=" -> leftBool != rightBool;
        default -> false;
      };
    }
    if (left != null && right != null) {
      return switch (condition.operator) {
        case "==" -> left.toString().equals(right.toString());
        case "!=" -> !left.toString().equals(right.toString());
        default -> false;
      };
    }
    return false;
  }

  private Object readSignalValue(String deviceName, String signalName, double nowSec) {
    if (BUILTIN_TIMER_NAME.equalsIgnoreCase(deviceName) && DslSignalRegistry.SIGNAL_ELAPSED.equals(signalName)) {
      return nowSec - startSec;
    }
    DeviceUnit device = devices.get(deviceName);
    if (device == null) {
      return null;
    }
    String deviceType = resolveDeviceType(deviceName);
    if (DslSignalRegistry.DEVICE_TYPE_MOTOR.equals(deviceType)) {
      if (DslSignalRegistry.SIGNAL_POSITION.equals(signalName)) {
        Double position = device.getPositionRotations();
        if (position == null) {
          return null;
        }
        Double start = startPositions.get(deviceName);
        return start != null ? position - start : position;
      }
      DeviceSnapshot snapshot = device.snapshot();
      RevMotorAttachment rev = snapshot.getAttachment(RevMotorAttachment.class);
      CtreMotorAttachment ctre = snapshot.getAttachment(CtreMotorAttachment.class);
      if (DslSignalRegistry.SIGNAL_CURRENT.equals(signalName)) {
        if (rev != null) {
          return rev.motorCurrentA;
        }
        if (ctre != null) {
          return ctre.motorCurrentA;
        }
      }
      if (DslSignalRegistry.SIGNAL_TEMPERATURE.equals(signalName)) {
        if (rev != null) {
          return rev.tempC;
        }
        if (ctre != null) {
          return ctre.tempC;
        }
      }
      if (DslSignalRegistry.SIGNAL_VELOCITY.equals(signalName)) {
        if (rev != null) {
          return rev.velRpm;
        }
        if (ctre != null) {
          return ctre.velRpm;
        }
      }
    }
    if (DslSignalRegistry.DEVICE_TYPE_LIMIT_SWITCH.equals(deviceType)
        && DslSignalRegistry.SIGNAL_PRESSED.equals(signalName)) {
      DeviceSnapshot snapshot = device.snapshot();
      LimitsAttachment limits = snapshot.getAttachment(LimitsAttachment.class);
      if (limits == null || limits.switches == null || limits.switches.isEmpty()) {
        return null;
      }
      LimitsAttachment.LimitSwitchState state = limits.switches.get(0);
      return state != null && Boolean.TRUE.equals(state.closed);
    }
    if (DslSignalRegistry.DEVICE_TYPE_ENCODER_EXTERNAL.equals(deviceType)
        && DslSignalRegistry.SIGNAL_POSITION.equals(signalName)) {
      Double position = device.getPositionRotations();
      if (position == null) {
        return null;
      }
      Double start = startPositions.get(deviceName);
      return start != null ? position - start : position;
    }
    return null;
  }

  private String resolveDeviceType(String deviceName) {
    if (BUILTIN_TIMER_NAME.equalsIgnoreCase(deviceName)) {
      return DslSignalRegistry.DEVICE_TYPE_TEST_TIMER;
    }
    String configured = BringupUtil.getConfiguredDeviceTypeByLabel(deviceName);
    if (configured != null && !configured.isBlank()) {
      return configured;
    }
    return devices.containsKey(deviceName) ? DslSignalRegistry.DEVICE_TYPE_MOTOR : null;
  }
}
