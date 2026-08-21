package frc.robot.diag.probe;

import com.ctre.phoenix6.BaseStatusSignal;
import com.ctre.phoenix6.StatusCode;
import com.ctre.phoenix6.hardware.CANcoder;
import com.ctre.phoenix6.hardware.Pigeon2;
import com.ctre.phoenix6.hardware.TalonFX;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.revrobotics.REVLibError;
import com.revrobotics.spark.SparkBase;
import com.revrobotics.spark.SparkFlex;
import com.revrobotics.spark.SparkMax;
import edu.wpi.first.units.Units;
import frc.robot.BringupCore;
import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;
import frc.robot.devices.ctre.CtreCANCoderDevice;
import frc.robot.devices.ctre.CtrePigeonDevice;
import frc.robot.devices.ctre.CtrePdpDevice;
import frc.robot.devices.ctre.CtreTalonFxDevice;
import frc.robot.devices.ni.RoboRioDevice;
import frc.robot.devices.rev.RevFlexVortexDevice;
import frc.robot.devices.rev.RevPdhDevice;
import frc.robot.devices.rev.RevSparkMaxNeo550Device;
import frc.robot.devices.rev.RevSparkMaxNeoDevice;
import frc.robot.diag.snapshots.RobotControllerBusAttachment;
import frc.robot.diag.snapshots.RobotControllerPowerAttachment;
import frc.robot.diag.snapshots.RobotControllerRailsAttachment;
import frc.robot.manufacturers.ctre.diag.CtreReaderUtil;
import frc.robot.manufacturers.ctre.diag.PdpStatusAttachment;
import frc.robot.manufacturers.ctre.util.PdpStatusReader;
import frc.robot.manufacturers.rev.diag.PdhStatusAttachment;
import frc.robot.manufacturers.rev.diag.RevReaderUtil;
import frc.robot.manufacturers.rev.util.PdhStatusReader;
import frc.robot.status.generated.StatusCatalogGenerated;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * NAME
 *   ActiveDevicePresenceProbe - One-shot heavy full-state probe for runtime-owned devices.
 *
 * DESCRIPTION
 *   Probes the currently active runtime-owned CAN devices using already-open
 *   vendor handles. The probe never commands motion and returns a structured
 *   score/bucket result plus compact operator text.
 */
public final class ActiveDevicePresenceProbe {
  private static final String MODE_ONE_SHOT = "oneShot";
  private static final String STATUS_OK = "ok";
  private static final String STATUS_WARNING = "warning";
  private static final String STATUS_ERROR = "error";
  private static final String BUCKET_PRESENT = "present";
  private static final String BUCKET_DEGRADED = "degraded";
  private static final String BUCKET_ABSENT = "absent";
  private static final String BUCKET_UNKNOWN = "unknown";
  private static final String DEVICE_INTERFACE_CAN = "CAN";
  private static final String VENDOR_CTRE = "CTRE";
  private static final String VENDOR_REV = "REV";
  private static final String MODEL_TALON_FX = "TALON_FX";
  private static final String MODEL_SPARK_MAX = "SPARK_MAX";
  private static final String MODEL_SPARK_FLEX = "SPARK_FLEX";
  private static final String MODEL_CANCODER = "CANCODER";
  private static final String MODEL_PIGEON = "PIGEON";
  private static final String MODEL_PDP = "PDP";
  private static final String MODEL_PDH = "PDH";
  private static final String MODEL_ROBORIO = "ROBORIO";
  private static final String MODEL_UNSUPPORTED = "UNSUPPORTED";
  private static final String TEXT_SESSION_SUCCESS = "Probe completed successfully.";
  private static final String TEXT_SESSION_WARN = "Probe completed with warnings.";
  private static final String TEXT_SESSION_EMPTY = "No active CAN devices were available for probing.";
  private static final String TEXT_SESSION_UNSUPPORTED = "No supported active CAN probe targets were found.";
  private static final String TEXT_INVALID_TARGET = "Invalid probe target.";
  private static final String TEXT_UNSUPPORTED_MODEL_PREFIX = "Unsupported device model: ";
  private static final String TEXT_RUNTIME_DEVICE_MISSING = "Runtime device handle unavailable.";
  private static final String TEXT_SNAPSHOT_NOT_ALLOWED =
      "Device not in the active lifecycle snapshot scope.";
  private static final String TEXT_STATUS_NOT_OK = "One or more Phoenix status reads were not OK.";
  private static final String TEXT_STATUS_FORCE_ABSENT = "Phoenix status was stale or transmit failed.";
  private static final String TEXT_PD_WEAK = "Power-distribution API evidence was too weak for a confident absence call.";
  private static final String TEXT_PD_ABSENT = "Power-distribution API evidence indicates the device is absent or disconnected.";
  private static final String TEXT_EXCEPTION_PREFIX = "Probe exception: ";
  private static final String TEXT_FIELD_SEPARATOR = " | ";
  private static final String TEXT_EVIDENCE_PREFIX = "  ";
  private static final String TEXT_PASS_PREFIX = "+ ";
  private static final String TEXT_FAIL_PREFIX = "- ";
  private static final String TEXT_NEWLINE = "\n";
  private static final String TEXT_EQUALS = " = ";
  private static final String TEXT_EMPTY = "";
  private static final String OBSERVED_OK = "OK";
  private static final String OBSERVED_NOT_OK = "NOT_OK";
  private static final String CODE_OBJECT_CONSTRUCTED = "OBJECT_CONSTRUCTED";
  private static final String CODE_OBJECT_HANDLE_REUSED = "OBJECT_HANDLE_REUSED";
  private static final String CODE_CLEAR_STICKY_OK = "CLEAR_STICKY_OK";
  private static final String CODE_CLEAR_STICKY_FAILED = "CLEAR_STICKY_FAILED";
  private static final String CODE_STATUS_REFRESH_OK = "STATUS_REFRESH_OK";
  private static final String CODE_BUS_VOLTAGE_VALID = "BUS_VOLTAGE_VALID";
  private static final String CODE_TEMPERATURE_READ_VALID = "TEMPERATURE_READ_VALID";
  private static final String CODE_CURRENT_READ_VALID = "CURRENT_READ_VALID";
  private static final String CODE_POSITION_READ_VALID = "POSITION_READ_VALID";
  private static final String CODE_NO_ACTIVE_FAULTS = "NO_ACTIVE_FAULTS";
  private static final String CODE_NO_STICKY_FAULTS = "NO_STICKY_FAULTS";
  private static final String CODE_LAST_ERROR_OK = "LAST_ERROR_OK";
  private static final String CODE_APPLIED_OUTPUT_VALID = "APPLIED_OUTPUT_VALID";
  private static final String CODE_NO_ACTIVE_WARNINGS = "NO_ACTIVE_WARNINGS";
  private static final String CODE_SWITCHABLE_READ_VALID = "SWITCHABLE_READ_VALID";
  private static final String CODE_POWER_FRESHNESS_GATE = "POWER_FRESHNESS_GATE";
  private static final String CODE_EXCEPTION_THROWN = "EXCEPTION_THROWN";
  private static final int MAX_SCORE = 100;
  private static final int PRESENT_THRESHOLD = 70;
  private static final int DEGRADED_THRESHOLD = 35;
  private static final int WEIGHT_CONSTRUCT = 5;
  private static final int TALON_STATUS_OK = 30;
  private static final int TALON_BUS_VOLTAGE = 15;
  private static final int TALON_TEMPERATURE = 10;
  private static final int TALON_CURRENT = 10;
  private static final int TALON_POSITION = 10;
  private static final int TALON_NO_ACTIVE_FAULTS = 10;
  private static final int TALON_NO_STICKY_FAULTS = 10;
  private static final int CANCODER_STATUS_OK = 35;
  private static final int CANCODER_POSITION = 20;
  private static final int CANCODER_VELOCITY = 15;
  private static final int CANCODER_NO_ACTIVE_FAULTS = 15;
  private static final int CANCODER_NO_STICKY_FAULTS = 15;
  private static final int PIGEON_STATUS_OK = 30;
  private static final int PIGEON_SUPPLY_VOLTAGE = 20;
  private static final int PIGEON_YAW = 10;
  private static final int PIGEON_PITCH = 10;
  private static final int PIGEON_ROLL = 10;
  private static final int PIGEON_NO_ACTIVE_FAULTS = 10;
  private static final int PIGEON_NO_STICKY_FAULTS = 10;
  private static final int REV_LAST_ERROR_OK = 25;
  private static final int REV_BUS_VOLTAGE = 20;
  private static final int REV_CURRENT = 10;
  private static final int REV_TEMPERATURE = 10;
  private static final int REV_APPLIED_OUTPUT = 10;
  private static final int REV_NO_ACTIVE_FAULTS = 10;
  private static final int REV_NO_ACTIVE_WARNINGS = 10;
  private static final int PD_BUS_VOLTAGE = 25;
  private static final int PD_TOTAL_CURRENT = 20;
  private static final int PD_TEMPERATURE = 20;
  private static final int PD_SWITCHABLE = 15;
  private static final int PD_NO_ACTIVE_FAULTS = 15;
  private static final int CONTROLLER_INPUT_VOLTAGE = 20;
  private static final int CONTROLLER_NOT_BROWNED_OUT = 15;
  private static final int CONTROLLER_BUS_STATUS = 20;
  private static final int CONTROLLER_RAIL_3V3 = 10;
  private static final int CONTROLLER_RAIL_5V = 10;
  private static final int CONTROLLER_RAIL_6V = 10;
  private static final int CONTROLLER_NO_RAIL_FAULTS = 10;
  private static final double MIN_VALID_BUS_VOLTAGE = 1.0;
  private static final double MAX_VALID_BUS_VOLTAGE = 30.0;
  private static final double MAX_VALID_CURRENT_A = 500.0;
  private static final double MAX_VALID_TEMP_C = 250.0;
  private static final double MAX_VALID_DUTY = 1.05;
  private static final double MAX_CONTROLLER_UTILIZATION_PCT = 100.0;
  private static final double MIN_VALID_3V3_VOLTAGE = 2.5;
  private static final double MAX_VALID_3V3_VOLTAGE = 4.0;
  private static final double MIN_VALID_5V_VOLTAGE = 4.0;
  private static final double MAX_VALID_5V_VOLTAGE = 6.0;
  private static final double MIN_VALID_6V_VOLTAGE = 5.0;
  private static final double MAX_VALID_6V_VOLTAGE = 7.5;
  private static final double MIN_MEANINGFUL_CURRENT_A = 0.05;
  private static final double MIN_MEANINGFUL_POWER_TEMP_C = 1.0;
  private static final int MIN_VALID_POWER_CHANNEL_COUNT = 1;
  private static final int EXPECTED_RESET_BITS = 0;
  private static final long EXPECTED_ZERO_FAULT_BITS = 0L;
  private static final String TEXT_SESSION_HEADER = "=== Full Device State Probe ===";
  private static final String TEXT_DURATION_MS = "durationMs";
  private static final String TEXT_TOTAL_DURATION_MS = "totalDurationMs";
  private static final String TEXT_SLOWEST_DEVICE_LABEL = "slowestDeviceLabel";
  private static final String TEXT_SLOWEST_DEVICE_DURATION_MS = "slowestDeviceDurationMs";
  private static final String TEXT_STAGE_TIMINGS = "stageTimings";
  private static final String TEXT_STAGE_HANDLE = "handle";
  private static final String TEXT_STAGE_GET_HANDLE = "getHandle";
  private static final String TEXT_STAGE_PREFLIGHT = "preflight";
  private static final String TEXT_STAGE_CLEAR_STICKY = "clearSticky";
  private static final String TEXT_STAGE_VENDOR_READ = "vendorRead";
  private static final String TEXT_STAGE_EVALUATE = "evaluate";
  private static final String TEXT_STAGE_SNAPSHOT = "snapshot";
  private static final String TEXT_MS_SUFFIX = " ms";
  private static final String LABEL_KEY_EMPTY = "";

  /**
   * NAME
   *   runOnce - Probe supported active runtime-owned CAN devices once.
   *
   * PARAMETERS
   *   core - active runtime core that owns the current device handles.
   *   preclearSticky - when true, clear sticky faults where safely supported.
   *
   * RETURNS
   *   Session result containing per-device evidence plus text/JSON output.
   */
  public ProbeSessionResult runOnce(BringupCore core, boolean preclearSticky) {
    long sessionStartNs = System.nanoTime();
    if (core == null) {
      ProbeSessionResult result = ProbeSessionResult.failed(TEXT_SESSION_EMPTY);
      result.totalDurationMs = nanosToMs(System.nanoTime() - sessionStartNs);
      return result;
    }
    List<ProbeDeviceResult> results = new ArrayList<>();
    int unsupportedCount = 0;
    int canCount = 0;
    for (BringupUtil.DeviceEntry entry : probeCandidateEntries(core)) {
      if (!isCanEntry(entry)) {
        continue;
      }
      canCount++;
      DeviceUnit device = core.findDeviceByLabel(entry.label);
      ProbeTarget target = resolveTarget(entry, device);
      if (!core.isLifecycleSnapshotAllowed(entry.label)
          && !isSupplementalProbeTarget(target.model)) {
        results.add(snapshotNotAllowed(target));
        continue;
      }
      if (MODEL_UNSUPPORTED.equals(target.model)) {
        unsupportedCount++;
        continue;
      }
      results.add(probeTarget(target, device, preclearSticky));
    }
    if (results.isEmpty()) {
      if (canCount == 0) {
        ProbeSessionResult result = ProbeSessionResult.failed(TEXT_SESSION_EMPTY);
        result.totalDurationMs = nanosToMs(System.nanoTime() - sessionStartNs);
        return result;
      }
      ProbeSessionResult result = ProbeSessionResult.failed(TEXT_SESSION_UNSUPPORTED);
      result.totalDurationMs = nanosToMs(System.nanoTime() - sessionStartNs);
      return result;
    }
    ProbeSessionResult session = ProbeSessionResult.fromDevices(results, unsupportedCount);
    session.totalDurationMs = nanosToMs(System.nanoTime() - sessionStartNs);
    session.finishProfilingSummary();
    return session;
  }

  static List<BringupUtil.DeviceEntry> mergeProbeEntries(
      List<BringupUtil.DeviceEntry> activeEntries,
      List<BringupUtil.DeviceEntry> profileEntries,
      Map<String, String> supplementalModelsByLabel) {
    LinkedHashMap<String, BringupUtil.DeviceEntry> byLabel = new LinkedHashMap<>();
    addProbeEntries(byLabel, activeEntries);
    if (profileEntries != null && supplementalModelsByLabel != null) {
      for (BringupUtil.DeviceEntry entry : profileEntries) {
        if (entry == null || !isCanEntryStatic(entry)) {
          continue;
        }
        String normalizedLabel = normalizeLabel(entry.label);
        if (normalizedLabel.isBlank() || byLabel.containsKey(normalizedLabel)) {
          continue;
        }
        String model = supplementalModelsByLabel.get(normalizedLabel);
        if (isSupplementalProbeTarget(model)) {
          byLabel.put(normalizedLabel, entry);
        }
      }
    }
    return new ArrayList<>(byLabel.values());
  }

  static boolean isSupplementalProbeTarget(String model) {
    String normalized = model != null ? model.trim().toUpperCase(Locale.ROOT) : LABEL_KEY_EMPTY;
    return MODEL_PDP.equals(normalized) || MODEL_PDH.equals(normalized);
  }

  private static boolean isCanEntryStatic(BringupUtil.DeviceEntry entry) {
    if (entry == null) {
      return false;
    }
    String iface = entry.deviceInterface;
    return iface != null && DEVICE_INTERFACE_CAN.equalsIgnoreCase(iface.trim());
  }

  private static String normalizeLabel(String label) {
    return label != null ? label.trim().toLowerCase(Locale.ROOT) : LABEL_KEY_EMPTY;
  }

  private static void addProbeEntries(
      Map<String, BringupUtil.DeviceEntry> byLabel,
      List<BringupUtil.DeviceEntry> entries) {
    if (byLabel == null || entries == null) {
      return;
    }
    for (BringupUtil.DeviceEntry entry : entries) {
      if (entry == null || !isCanEntryStatic(entry)) {
        continue;
      }
      String normalizedLabel = normalizeLabel(entry.label);
      if (!normalizedLabel.isBlank()) {
        byLabel.putIfAbsent(normalizedLabel, entry);
      }
    }
  }

  private List<BringupUtil.DeviceEntry> probeCandidateEntries(BringupCore core) {
    List<BringupUtil.DeviceEntry> activeEntries = BringupUtil.getActiveDevicesSorted();
    if (core == null) {
      return activeEntries;
    }
    String selectedProfile = BringupUtil.getSelectedCanProfile();
    List<BringupUtil.DeviceEntry> profileEntries =
        selectedProfile == null || selectedProfile.isBlank()
            ? Collections.emptyList()
            : BringupUtil.getProfileDevicesSorted(selectedProfile);
    Map<String, String> supplementalModelsByLabel = new LinkedHashMap<>();
    for (BringupUtil.DeviceEntry entry : profileEntries) {
      if (entry == null || entry.label == null || entry.label.isBlank()) {
        continue;
      }
      DeviceUnit device = core.findDeviceByLabel(entry.label);
      ProbeTarget target = resolveTarget(entry, device);
      if (isSupplementalProbeTarget(target.model)) {
        supplementalModelsByLabel.put(normalizeLabel(entry.label), target.model);
      }
    }
    return mergeProbeEntries(activeEntries, profileEntries, supplementalModelsByLabel);
  }

  private boolean isCanEntry(BringupUtil.DeviceEntry entry) {
    return isCanEntryStatic(entry);
  }

  private ProbeTarget resolveTarget(BringupUtil.DeviceEntry entry, DeviceUnit device) {
    String label = entry != null && entry.label != null ? entry.label : TEXT_EMPTY;
    int canId = entry != null ? entry.id : -1;
    String vendor = entry != null && entry.vendor != null ? entry.vendor : TEXT_EMPTY;
    String model = inferProbeModel(device);
    if (MODEL_TALON_FX.equals(model)
        || MODEL_CANCODER.equals(model)
        || MODEL_PIGEON.equals(model)
        || MODEL_PDP.equals(model)) {
      vendor = VENDOR_CTRE;
    } else if (MODEL_SPARK_MAX.equals(model)
        || MODEL_SPARK_FLEX.equals(model)
        || MODEL_PDH.equals(model)) {
      vendor = VENDOR_REV;
    }
    return new ProbeTarget(label, canId, normalizeVendor(vendor), model);
  }

  static String inferProbeModel(DeviceUnit device) {
    if (device instanceof CtreTalonFxDevice) {
      return MODEL_TALON_FX;
    }
    if (device instanceof RevSparkMaxNeoDevice || device instanceof RevSparkMaxNeo550Device) {
      return MODEL_SPARK_MAX;
    }
    if (device instanceof RevFlexVortexDevice) {
      return MODEL_SPARK_FLEX;
    }
    if (device instanceof CtreCANCoderDevice) {
      return MODEL_CANCODER;
    }
    if (device instanceof CtrePigeonDevice) {
      return MODEL_PIGEON;
    }
    if (device instanceof CtrePdpDevice) {
      return MODEL_PDP;
    }
    if (device instanceof RevPdhDevice) {
      return MODEL_PDH;
    }
    if (device instanceof RoboRioDevice) {
      return MODEL_ROBORIO;
    }
    return MODEL_UNSUPPORTED;
  }

  private String normalizeVendor(String vendor) {
    if (vendor == null || vendor.isBlank()) {
      return TEXT_EMPTY;
    }
    return vendor.trim().toUpperCase(Locale.ROOT);
  }

  private ProbeDeviceResult probeTarget(
      ProbeTarget target,
      DeviceUnit device,
      boolean preclearSticky) {
    if (target == null || target.label == null || target.label.isBlank() || target.canId < 0) {
      return invalidTarget(target, TEXT_INVALID_TARGET);
    }
    if (MODEL_UNSUPPORTED.equals(target.model)) {
      return unsupportedTarget(target, TEXT_UNSUPPORTED_MODEL_PREFIX + target.label);
    }
    if (device == null || !device.isCreated()) {
      return missingRuntimeDevice(target);
    }
    return switch (target.model) {
      case MODEL_TALON_FX -> probeTalonFx(target, (CtreTalonFxDevice) device, preclearSticky);
      case MODEL_SPARK_MAX -> probeSparkMax(target, device, preclearSticky);
      case MODEL_SPARK_FLEX -> probeSparkFlex(target, (RevFlexVortexDevice) device, preclearSticky);
      case MODEL_CANCODER -> probeCancoder(target, (CtreCANCoderDevice) device, preclearSticky);
      case MODEL_PIGEON -> probePigeon(target, (CtrePigeonDevice) device, preclearSticky);
      case MODEL_PDP -> probePdp(target, (CtrePdpDevice) device, preclearSticky);
      case MODEL_PDH -> probePdh(target, (RevPdhDevice) device, preclearSticky);
      case MODEL_ROBORIO -> probeRoboRio(target, (RoboRioDevice) device);
      default -> unsupportedTarget(target, TEXT_UNSUPPORTED_MODEL_PREFIX + target.model);
    };
  }

  private ProbeDeviceResult probeTalonFx(
      ProbeTarget target,
      CtreTalonFxDevice device,
      boolean preclearSticky) {
    long deviceStartNs = System.nanoTime();
    ProbeAccumulator acc = new ProbeAccumulator(target);
    long stageStartNs = System.nanoTime();
    TalonFX talon = device.getActiveHandleForProbe();
    acc.recordStageDuration(TEXT_STAGE_GET_HANDLE, nanosToMs(System.nanoTime() - stageStartNs));
    if (talon == null) {
      ProbeDeviceResult result = missingRuntimeDevice(target);
      result.totalDurationMs = nanosToMs(System.nanoTime() - deviceStartNs);
      return result;
    }
    stageStartNs = System.nanoTime();
    acc.pass(CODE_OBJECT_HANDLE_REUSED, "Using runtime-owned TalonFX handle.", WEIGHT_CONSTRUCT,
        Integer.toString(target.canId));
    acc.recordStageDuration(TEXT_STAGE_PREFLIGHT, nanosToMs(System.nanoTime() - stageStartNs));
    acc.recordStageDuration(TEXT_STAGE_HANDLE, nanosToMs(System.nanoTime() - deviceStartNs));
    try {
      if (preclearSticky) {
        stageStartNs = System.nanoTime();
        StatusCode clearStatus = talon.clearStickyFaults();
        if (clearStatus == StatusCode.OK) {
          acc.pass(CODE_CLEAR_STICKY_OK, "Cleared Phoenix sticky faults.", 0, OBSERVED_OK);
        } else {
          acc.warn(CODE_CLEAR_STICKY_FAILED, "Phoenix sticky-fault clear did not return OK.", 0,
              String.valueOf(clearStatus), StatusCatalogGenerated.SS__DEVICE__COMMUNICATION_WEAK);
        }
        acc.recordStageDuration(TEXT_STAGE_CLEAR_STICKY, nanosToMs(System.nanoTime() - stageStartNs));
      }
      stageStartNs = System.nanoTime();
      var supplyVoltage = talon.getSupplyVoltage();
      var dutyCycle = talon.getDutyCycle();
      var faultField = talon.getFaultField();
      var stickyFaultField = talon.getStickyFaultField();
      var deviceTemp = talon.getDeviceTemp();
      var supplyCurrent = talon.getSupplyCurrent();
      var position = talon.getPosition();
      BaseStatusSignal.refreshAll(
          supplyVoltage,
          dutyCycle,
          faultField,
          stickyFaultField,
          deviceTemp,
          supplyCurrent,
          position);
      acc.recordStageDuration(TEXT_STAGE_VENDOR_READ, nanosToMs(System.nanoTime() - stageStartNs));
      stageStartNs = System.nanoTime();
      boolean allOk = true;
      allOk &= isOkStatus(supplyVoltage.getStatus());
      allOk &= isOkStatus(dutyCycle.getStatus());
      allOk &= isOkStatus(faultField.getStatus());
      allOk &= isOkStatus(stickyFaultField.getStatus());
      allOk &= isOkStatus(deviceTemp.getStatus());
      allOk &= isOkStatus(supplyCurrent.getStatus());
      allOk &= isOkStatus(position.getStatus());
      if (allOk) {
        acc.pass(CODE_STATUS_REFRESH_OK, "All Phoenix status reads returned OK.", TALON_STATUS_OK, OBSERVED_OK);
      } else {
        acc.fail(CODE_STATUS_REFRESH_OK, TEXT_STATUS_NOT_OK, TALON_STATUS_OK, OBSERVED_NOT_OK);
      }
      double busV = supplyVoltage.getValue().in(Units.Volts);
      addTelemetryCheck(
          acc,
          allOk && isReasonableBusVoltage(busV),
          CODE_BUS_VOLTAGE_VALID,
          "Bus voltage looks valid.",
          allOk ? "Bus voltage not in expected range." : "Bus voltage ignored because Phoenix status was not fresh.",
          TALON_BUS_VOLTAGE,
          formatDouble(busV));
      double tempC = deviceTemp.getValue().in(Units.Celsius);
      addTelemetryCheck(
          acc,
          allOk && isFiniteInRange(tempC, 0.0, MAX_VALID_TEMP_C),
          CODE_TEMPERATURE_READ_VALID,
          "Temperature read succeeded.",
          allOk ? "Temperature read failed." : "Temperature ignored because Phoenix status was not fresh.",
          TALON_TEMPERATURE,
          formatDouble(tempC));
      double currentA = supplyCurrent.getValue().in(Units.Amps);
      addTelemetryCheck(
          acc,
          allOk && isFiniteInRange(currentA, 0.0, MAX_VALID_CURRENT_A),
          CODE_CURRENT_READ_VALID,
          "Current read succeeded.",
          allOk ? "Current read failed." : "Current ignored because Phoenix status was not fresh.",
          TALON_CURRENT,
          formatDouble(currentA));
      long faultsRaw = faultField.getValue();
      long stickyFaultsRaw = stickyFaultField.getValue();
      List<String> activeFaultNames = new ArrayList<>();
      List<String> stickyFaultNames = new ArrayList<>();
      if (CtreReaderUtil.shouldReadDetailedFaultFlags(
          faultField.getStatus(),
          stickyFaultField.getStatus())) {
        CtreReaderUtil.collectFaultFlags(talon, activeFaultNames);
        CtreReaderUtil.collectStickyFaultFlags(talon, stickyFaultNames);
      } else {
        CtreReaderUtil.appendDetailedFlagReadSkipped(activeFaultNames);
        CtreReaderUtil.appendDetailedFlagReadSkipped(stickyFaultNames);
      }
      if (allOk && faultsRaw == 0L) {
        acc.pass(CODE_NO_ACTIVE_FAULTS, "No active Phoenix fault bits.", TALON_NO_ACTIVE_FAULTS, "0");
      } else {
        acc.fail(CODE_NO_ACTIVE_FAULTS,
            allOk ? "Active Phoenix fault bits were reported." : "Active-fault check ignored because Phoenix status was not fresh.",
            TALON_NO_ACTIVE_FAULTS,
            "faults=" + faultsRaw);
        if (allOk) {
          acc.warnEntries("Active CTRE fault", activeFaultNames, StatusCatalogGenerated.SS__DEVICE__FAULTS_ACTIVE);
        }
      }
      if (allOk && stickyFaultsRaw == 0L) {
        acc.pass(CODE_NO_STICKY_FAULTS, "No Phoenix sticky fault bits.", TALON_NO_STICKY_FAULTS, "0");
      } else {
        acc.fail(CODE_NO_STICKY_FAULTS,
            allOk ? "Phoenix sticky fault bits were reported." : "Sticky-fault check ignored because Phoenix status was not fresh.",
            TALON_NO_STICKY_FAULTS,
            "sticky=" + stickyFaultsRaw);
        if (allOk) {
          acc.warnEntries("Sticky CTRE fault", stickyFaultNames, StatusCatalogGenerated.SS__DEVICE__FAULTS_ACTIVE);
        }
      }
      double positionRot = position.getValue().in(Units.Rotations);
      addTelemetryCheck(
          acc,
          allOk && Double.isFinite(positionRot),
          CODE_POSITION_READ_VALID,
          "Position read succeeded.",
          allOk ? "Position read failed." : "Position ignored because Phoenix status was not fresh.",
          TALON_POSITION,
          formatDouble(positionRot));
      if (!allOk) {
        acc.forceBucket(BUCKET_ABSENT, StatusCatalogGenerated.SS__DEVICE__ABSENT, TEXT_STATUS_FORCE_ABSENT);
      }
      acc.recordStageDuration(TEXT_STAGE_EVALUATE, nanosToMs(System.nanoTime() - stageStartNs));
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    } catch (Exception ex) {
      acc.error(CODE_EXCEPTION_THROWN, TEXT_EXCEPTION_PREFIX + ex.getClass().getSimpleName(),
          MAX_SCORE, safeExceptionMessage(ex), StatusCatalogGenerated.SS__DEVICE__PROBE_EXCEPTION);
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    }
  }

  private ProbeDeviceResult probeSparkMax(
      ProbeTarget target,
      DeviceUnit device,
      boolean preclearSticky) {
    SparkMax spark = null;
    if (device instanceof RevSparkMaxNeoDevice neo) {
      spark = neo.getActiveHandleForProbe();
    } else if (device instanceof RevSparkMaxNeo550Device neo550) {
      spark = neo550.getActiveHandleForProbe();
    }
    return probeRevSparkBase(target, spark, preclearSticky);
  }

  private ProbeDeviceResult probeSparkFlex(
      ProbeTarget target,
      RevFlexVortexDevice device,
      boolean preclearSticky) {
    return probeRevSparkBase(target, device.getActiveHandleForProbe(), preclearSticky);
  }

  private ProbeDeviceResult probeCancoder(
      ProbeTarget target,
      CtreCANCoderDevice device,
      boolean preclearSticky) {
    long deviceStartNs = System.nanoTime();
    ProbeAccumulator acc = new ProbeAccumulator(target);
    long stageStartNs = System.nanoTime();
    CANcoder cancoder = device.getActiveHandleForProbe();
    acc.recordStageDuration(TEXT_STAGE_GET_HANDLE, nanosToMs(System.nanoTime() - stageStartNs));
    if (cancoder == null) {
      ProbeDeviceResult result = missingRuntimeDevice(target);
      result.totalDurationMs = nanosToMs(System.nanoTime() - deviceStartNs);
      return result;
    }
    acc.pass(
        CODE_OBJECT_HANDLE_REUSED,
        "Using runtime-owned CANcoder handle.",
        WEIGHT_CONSTRUCT,
        Integer.toString(target.canId));
    acc.recordStageDuration(TEXT_STAGE_HANDLE, nanosToMs(System.nanoTime() - deviceStartNs));
    try {
      if (preclearSticky) {
        stageStartNs = System.nanoTime();
        StatusCode clearStatus = cancoder.clearStickyFaults();
        if (clearStatus == StatusCode.OK) {
          acc.pass(CODE_CLEAR_STICKY_OK, "Cleared Phoenix sticky faults.", 0, OBSERVED_OK);
        } else {
          acc.warn(
              CODE_CLEAR_STICKY_FAILED,
              "Phoenix sticky-fault clear did not return OK.",
              0,
              String.valueOf(clearStatus),
              StatusCatalogGenerated.SS__DEVICE__COMMUNICATION_WEAK);
        }
        acc.recordStageDuration(TEXT_STAGE_CLEAR_STICKY, nanosToMs(System.nanoTime() - stageStartNs));
      }
      stageStartNs = System.nanoTime();
      var absolutePosition = cancoder.getAbsolutePosition();
      var velocity = cancoder.getVelocity();
      var faultField = cancoder.getFaultField();
      var stickyFaultField = cancoder.getStickyFaultField();
      BaseStatusSignal.refreshAll(absolutePosition, velocity, faultField, stickyFaultField);
      acc.recordStageDuration(TEXT_STAGE_VENDOR_READ, nanosToMs(System.nanoTime() - stageStartNs));
      stageStartNs = System.nanoTime();
      boolean allOk = true;
      allOk &= isOkStatus(absolutePosition.getStatus());
      allOk &= isOkStatus(velocity.getStatus());
      allOk &= isOkStatus(faultField.getStatus());
      allOk &= isOkStatus(stickyFaultField.getStatus());
      if (allOk) {
        acc.pass(
            CODE_STATUS_REFRESH_OK,
            "All Phoenix status reads returned OK.",
            CANCODER_STATUS_OK,
            OBSERVED_OK);
      } else {
        acc.fail(CODE_STATUS_REFRESH_OK, TEXT_STATUS_NOT_OK, CANCODER_STATUS_OK, OBSERVED_NOT_OK);
      }
      double absoluteRot = absolutePosition.getValue().in(Units.Rotations);
      addTelemetryCheck(
          acc,
          allOk && Double.isFinite(absoluteRot),
          CODE_POSITION_READ_VALID,
          "Absolute position read succeeded.",
          allOk
              ? "Absolute position read failed."
              : "Absolute position ignored because Phoenix status was not fresh.",
          CANCODER_POSITION,
          formatDouble(absoluteRot));
      double velocityRps = velocity.getValue().in(Units.RotationsPerSecond);
      addTelemetryCheck(
          acc,
          allOk && Double.isFinite(velocityRps),
          CODE_CURRENT_READ_VALID,
          "Velocity read succeeded.",
          allOk ? "Velocity read failed." : "Velocity ignored because Phoenix status was not fresh.",
          CANCODER_VELOCITY,
          formatDouble(velocityRps));
      long faultsRaw = faultField.getValue();
      if (allOk && faultsRaw == EXPECTED_ZERO_FAULT_BITS) {
        acc.pass(CODE_NO_ACTIVE_FAULTS, "No active Phoenix fault bits.", CANCODER_NO_ACTIVE_FAULTS, "0");
      } else {
        acc.fail(
            CODE_NO_ACTIVE_FAULTS,
            allOk
                ? "Active Phoenix fault bits were reported."
                : "Active-fault check ignored because Phoenix status was not fresh.",
            CANCODER_NO_ACTIVE_FAULTS,
            "faults=" + faultsRaw);
      }
      long stickyFaultsRaw = stickyFaultField.getValue();
      if (allOk && stickyFaultsRaw == EXPECTED_ZERO_FAULT_BITS) {
        acc.pass(CODE_NO_STICKY_FAULTS, "No Phoenix sticky fault bits.", CANCODER_NO_STICKY_FAULTS, "0");
      } else {
        acc.fail(
            CODE_NO_STICKY_FAULTS,
            allOk
                ? "Phoenix sticky fault bits were reported."
                : "Sticky-fault check ignored because Phoenix status was not fresh.",
            CANCODER_NO_STICKY_FAULTS,
            "sticky=" + stickyFaultsRaw);
      }
      if (!allOk) {
        acc.forceBucket(BUCKET_ABSENT, StatusCatalogGenerated.SS__DEVICE__ABSENT, TEXT_STATUS_FORCE_ABSENT);
      }
      acc.recordStageDuration(TEXT_STAGE_EVALUATE, nanosToMs(System.nanoTime() - stageStartNs));
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    } catch (Exception ex) {
      acc.error(
          CODE_EXCEPTION_THROWN,
          TEXT_EXCEPTION_PREFIX + ex.getClass().getSimpleName(),
          MAX_SCORE,
          safeExceptionMessage(ex),
          StatusCatalogGenerated.SS__DEVICE__PROBE_EXCEPTION);
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    }
  }

  private ProbeDeviceResult probePigeon(
      ProbeTarget target,
      CtrePigeonDevice device,
      boolean preclearSticky) {
    long deviceStartNs = System.nanoTime();
    ProbeAccumulator acc = new ProbeAccumulator(target);
    long stageStartNs = System.nanoTime();
    Pigeon2 pigeon = device.getActiveHandleForProbe();
    acc.recordStageDuration(TEXT_STAGE_GET_HANDLE, nanosToMs(System.nanoTime() - stageStartNs));
    if (pigeon == null) {
      ProbeDeviceResult result = missingRuntimeDevice(target);
      result.totalDurationMs = nanosToMs(System.nanoTime() - deviceStartNs);
      return result;
    }
    acc.pass(
        CODE_OBJECT_HANDLE_REUSED,
        "Using runtime-owned Pigeon2 handle.",
        WEIGHT_CONSTRUCT,
        Integer.toString(target.canId));
    acc.recordStageDuration(TEXT_STAGE_HANDLE, nanosToMs(System.nanoTime() - deviceStartNs));
    try {
      if (preclearSticky) {
        stageStartNs = System.nanoTime();
        StatusCode clearStatus = pigeon.clearStickyFaults();
        if (clearStatus == StatusCode.OK) {
          acc.pass(CODE_CLEAR_STICKY_OK, "Cleared Phoenix sticky faults.", 0, OBSERVED_OK);
        } else {
          acc.warn(
              CODE_CLEAR_STICKY_FAILED,
              "Phoenix sticky-fault clear did not return OK.",
              0,
              String.valueOf(clearStatus),
              StatusCatalogGenerated.SS__DEVICE__COMMUNICATION_WEAK);
        }
        acc.recordStageDuration(TEXT_STAGE_CLEAR_STICKY, nanosToMs(System.nanoTime() - stageStartNs));
      }
      stageStartNs = System.nanoTime();
      var yaw = pigeon.getYaw();
      var pitch = pigeon.getPitch();
      var roll = pigeon.getRoll();
      var supplyVoltage = pigeon.getSupplyVoltage();
      var faultField = pigeon.getFaultField();
      var stickyFaultField = pigeon.getStickyFaultField();
      BaseStatusSignal.refreshAll(yaw, pitch, roll, supplyVoltage, faultField, stickyFaultField);
      acc.recordStageDuration(TEXT_STAGE_VENDOR_READ, nanosToMs(System.nanoTime() - stageStartNs));
      stageStartNs = System.nanoTime();
      boolean allOk = true;
      allOk &= isOkStatus(yaw.getStatus());
      allOk &= isOkStatus(pitch.getStatus());
      allOk &= isOkStatus(roll.getStatus());
      allOk &= isOkStatus(supplyVoltage.getStatus());
      allOk &= isOkStatus(faultField.getStatus());
      allOk &= isOkStatus(stickyFaultField.getStatus());
      if (allOk) {
        acc.pass(
            CODE_STATUS_REFRESH_OK,
            "All Phoenix status reads returned OK.",
            PIGEON_STATUS_OK,
            OBSERVED_OK);
      } else {
        acc.fail(CODE_STATUS_REFRESH_OK, TEXT_STATUS_NOT_OK, PIGEON_STATUS_OK, OBSERVED_NOT_OK);
      }
      double busV = supplyVoltage.getValue().in(Units.Volts);
      addTelemetryCheck(
          acc,
          allOk && isReasonableBusVoltage(busV),
          CODE_BUS_VOLTAGE_VALID,
          "Supply voltage looks valid.",
          allOk
              ? "Supply voltage not in expected range."
              : "Supply voltage ignored because Phoenix status was not fresh.",
          PIGEON_SUPPLY_VOLTAGE,
          formatDouble(busV));
      addTelemetryCheck(
          acc,
          allOk && Double.isFinite(yaw.getValue().in(Units.Degrees)),
          CODE_POSITION_READ_VALID,
          "Yaw read succeeded.",
          allOk ? "Yaw read failed." : "Yaw ignored because Phoenix status was not fresh.",
          PIGEON_YAW,
          formatDouble(yaw.getValue().in(Units.Degrees)));
      addTelemetryCheck(
          acc,
          allOk && Double.isFinite(pitch.getValue().in(Units.Degrees)),
          CODE_TEMPERATURE_READ_VALID,
          "Pitch read succeeded.",
          allOk ? "Pitch read failed." : "Pitch ignored because Phoenix status was not fresh.",
          PIGEON_PITCH,
          formatDouble(pitch.getValue().in(Units.Degrees)));
      addTelemetryCheck(
          acc,
          allOk && Double.isFinite(roll.getValue().in(Units.Degrees)),
          CODE_CURRENT_READ_VALID,
          "Roll read succeeded.",
          allOk ? "Roll read failed." : "Roll ignored because Phoenix status was not fresh.",
          PIGEON_ROLL,
          formatDouble(roll.getValue().in(Units.Degrees)));
      long faultsRaw = faultField.getValue();
      if (allOk && faultsRaw == EXPECTED_ZERO_FAULT_BITS) {
        acc.pass(CODE_NO_ACTIVE_FAULTS, "No active Phoenix fault bits.", PIGEON_NO_ACTIVE_FAULTS, "0");
      } else {
        acc.fail(
            CODE_NO_ACTIVE_FAULTS,
            allOk
                ? "Active Phoenix fault bits were reported."
                : "Active-fault check ignored because Phoenix status was not fresh.",
            PIGEON_NO_ACTIVE_FAULTS,
            "faults=" + faultsRaw);
      }
      long stickyFaultsRaw = stickyFaultField.getValue();
      if (allOk && stickyFaultsRaw == EXPECTED_ZERO_FAULT_BITS) {
        acc.pass(CODE_NO_STICKY_FAULTS, "No Phoenix sticky fault bits.", PIGEON_NO_STICKY_FAULTS, "0");
      } else {
        acc.fail(
            CODE_NO_STICKY_FAULTS,
            allOk
                ? "Phoenix sticky fault bits were reported."
                : "Sticky-fault check ignored because Phoenix status was not fresh.",
            PIGEON_NO_STICKY_FAULTS,
            "sticky=" + stickyFaultsRaw);
      }
      if (!allOk) {
        acc.forceBucket(BUCKET_ABSENT, StatusCatalogGenerated.SS__DEVICE__ABSENT, TEXT_STATUS_FORCE_ABSENT);
      }
      acc.recordStageDuration(TEXT_STAGE_EVALUATE, nanosToMs(System.nanoTime() - stageStartNs));
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    } catch (Exception ex) {
      acc.error(
          CODE_EXCEPTION_THROWN,
          TEXT_EXCEPTION_PREFIX + ex.getClass().getSimpleName(),
          MAX_SCORE,
          safeExceptionMessage(ex),
          StatusCatalogGenerated.SS__DEVICE__PROBE_EXCEPTION);
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    }
  }

  private ProbeDeviceResult probeRevSparkBase(
      ProbeTarget target,
      SparkBase device,
      boolean preclearSticky) {
    long deviceStartNs = System.nanoTime();
    ProbeAccumulator acc = new ProbeAccumulator(target);
    if (device == null) {
      ProbeDeviceResult result = missingRuntimeDevice(target);
      result.totalDurationMs = nanosToMs(System.nanoTime() - deviceStartNs);
      return result;
    }
    acc.pass(CODE_OBJECT_HANDLE_REUSED, "Using runtime-owned REV handle.", WEIGHT_CONSTRUCT,
        Integer.toString(target.canId));
    try {
      acc.recordStageDuration(TEXT_STAGE_HANDLE, nanosToMs(System.nanoTime() - deviceStartNs));
      if (preclearSticky) {
        long stageStartNs = System.nanoTime();
        device.clearFaults();
        REVLibError clearError = device.getLastError();
        if (clearError == REVLibError.kOk) {
          acc.pass(CODE_CLEAR_STICKY_OK, "Cleared REV sticky faults.", 0, OBSERVED_OK);
        } else {
          acc.warn(CODE_CLEAR_STICKY_FAILED, "REV clearFaults did not return kOk.", 0,
              String.valueOf(clearError), StatusCatalogGenerated.SS__DEVICE__COMMUNICATION_WEAK);
        }
        acc.recordStageDuration(TEXT_STAGE_CLEAR_STICKY, nanosToMs(System.nanoTime() - stageStartNs));
      }
      long stageStartNs = System.nanoTime();
      double busV = device.getBusVoltage();
      double appliedOutput = device.getAppliedOutput();
      double currentA = device.getOutputCurrent();
      double tempC = device.getMotorTemperature();
      var faults = device.getFaults();
      var stickyFaults = device.getStickyFaults();
      var warnings = device.getWarnings();
      var stickyWarnings = device.getStickyWarnings();
      REVLibError lastError = device.getLastError();
      acc.recordStageDuration(TEXT_STAGE_VENDOR_READ, nanosToMs(System.nanoTime() - stageStartNs));
      stageStartNs = System.nanoTime();
      boolean commHealthy = lastError == REVLibError.kOk;
      if (commHealthy) {
        acc.pass(CODE_LAST_ERROR_OK, "REV last error returned kOk.", REV_LAST_ERROR_OK, String.valueOf(lastError));
      } else {
        acc.fail(CODE_LAST_ERROR_OK, "REV last error was not kOk.", REV_LAST_ERROR_OK, String.valueOf(lastError));
      }
      addTelemetryCheck(
          acc,
          commHealthy && isReasonableBusVoltage(busV),
          CODE_BUS_VOLTAGE_VALID,
          "Bus voltage looks valid.",
          commHealthy ? "Bus voltage not in expected range." : "Bus voltage ignored because communication was not healthy.",
          REV_BUS_VOLTAGE,
          formatDouble(busV));
      addTelemetryCheck(
          acc,
          commHealthy && isFiniteInRange(currentA, 0.0, MAX_VALID_CURRENT_A),
          CODE_CURRENT_READ_VALID,
          "Current read succeeded.",
          commHealthy ? "Current read failed." : "Current ignored because communication was not healthy.",
          REV_CURRENT,
          formatDouble(currentA));
      addTelemetryCheck(
          acc,
          commHealthy && isFiniteInRange(tempC, 0.0, MAX_VALID_TEMP_C),
          CODE_TEMPERATURE_READ_VALID,
          "Temperature read succeeded.",
          commHealthy ? "Temperature read failed." : "Temperature ignored because communication was not healthy.",
          REV_TEMPERATURE,
          formatDouble(tempC));
      addTelemetryCheck(
          acc,
          commHealthy && isFiniteInRange(Math.abs(appliedOutput), 0.0, MAX_VALID_DUTY),
          CODE_APPLIED_OUTPUT_VALID,
          "Applied output read succeeded.",
          commHealthy ? "Applied output read failed." : "Applied output ignored because communication was not healthy.",
          REV_APPLIED_OUTPUT,
          formatDouble(appliedOutput));
      if (commHealthy && faults.rawBits == EXPECTED_RESET_BITS) {
        acc.pass(CODE_NO_ACTIVE_FAULTS, "No active REV faults.", REV_NO_ACTIVE_FAULTS, "0");
      } else {
        acc.fail(CODE_NO_ACTIVE_FAULTS,
            commHealthy ? "Active REV faults were reported." : "REV faults ignored because communication was not healthy.",
            REV_NO_ACTIVE_FAULTS,
            Integer.toString(faults.rawBits));
        if (commHealthy) {
          List<String> names = new ArrayList<>();
          RevReaderUtil.collectFaultFlags(faults, names);
          acc.warnEntries("Active REV fault", names, StatusCatalogGenerated.SS__DEVICE__FAULTS_ACTIVE);
          List<String> stickyNames = new ArrayList<>();
          RevReaderUtil.collectFaultFlags(stickyFaults, stickyNames);
          acc.warnEntries("Sticky REV fault", stickyNames, StatusCatalogGenerated.SS__DEVICE__FAULTS_ACTIVE);
        }
      }
      if (commHealthy && warnings.rawBits == EXPECTED_RESET_BITS) {
        acc.pass(CODE_NO_ACTIVE_WARNINGS, "No active REV warnings.", REV_NO_ACTIVE_WARNINGS, "0");
      } else {
        acc.fail(CODE_NO_ACTIVE_WARNINGS,
            commHealthy ? "Active REV warnings were reported." : "REV warnings ignored because communication was not healthy.",
            REV_NO_ACTIVE_WARNINGS,
            Integer.toString(warnings.rawBits));
        if (commHealthy) {
          List<String> names = new ArrayList<>();
          RevReaderUtil.collectWarningFlags(warnings, names);
          acc.warnEntries("Active REV warning", names, StatusCatalogGenerated.SS__DEVICE__WARNINGS_ACTIVE);
          List<String> stickyNames = new ArrayList<>();
          RevReaderUtil.collectWarningFlags(stickyWarnings, stickyNames);
          acc.warnEntries("Sticky REV warning", stickyNames, StatusCatalogGenerated.SS__DEVICE__WARNINGS_ACTIVE);
        }
      }
      if (lastError == REVLibError.kCANDisconnected) {
        acc.error(CODE_LAST_ERROR_OK, "REV reported CAN disconnected.", MAX_SCORE,
            String.valueOf(lastError), StatusCatalogGenerated.SS__DEVICE__CAN_DISCONNECTED);
        acc.forceBucket(BUCKET_ABSENT, StatusCatalogGenerated.SS__DEVICE__ABSENT, "REV communication reported CAN disconnected.");
      } else if (!commHealthy) {
        acc.warn(CODE_LAST_ERROR_OK, "REV communication evidence was weak.", 0,
            String.valueOf(lastError), StatusCatalogGenerated.SS__DEVICE__COMMUNICATION_WEAK);
      }
      acc.recordStageDuration(TEXT_STAGE_EVALUATE, nanosToMs(System.nanoTime() - stageStartNs));
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    } catch (Exception ex) {
      acc.error(CODE_EXCEPTION_THROWN, TEXT_EXCEPTION_PREFIX + ex.getClass().getSimpleName(),
          MAX_SCORE, safeExceptionMessage(ex), StatusCatalogGenerated.SS__DEVICE__PROBE_EXCEPTION);
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    }
  }

  private ProbeDeviceResult probePdp(
      ProbeTarget target,
      CtrePdpDevice device,
      boolean preclearSticky) {
    long deviceStartNs = System.nanoTime();
    ProbeAccumulator acc = new ProbeAccumulator(target);
    PdpStatusReader reader = device.getActiveReaderForProbe();
    if (reader == null) {
      ProbeDeviceResult result = missingRuntimeDevice(target);
      result.totalDurationMs = nanosToMs(System.nanoTime() - deviceStartNs);
      return result;
    }
    acc.pass(CODE_OBJECT_HANDLE_REUSED, "Using runtime-owned PDP reader.", WEIGHT_CONSTRUCT,
        Integer.toString(target.canId));
    try {
      acc.recordStageDuration(TEXT_STAGE_HANDLE, nanosToMs(System.nanoTime() - deviceStartNs));
      if (preclearSticky) {
        long stageStartNs = System.nanoTime();
        reader.clearStickyFaults();
        acc.pass(CODE_CLEAR_STICKY_OK, "Cleared PDP sticky faults.", 0, OBSERVED_OK);
        acc.recordStageDuration(TEXT_STAGE_CLEAR_STICKY, nanosToMs(System.nanoTime() - stageStartNs));
      }
      long stageStartNs = System.nanoTime();
      PdpStatusAttachment status = reader.snapshot();
      acc.recordStageDuration(TEXT_STAGE_SNAPSHOT, nanosToMs(System.nanoTime() - stageStartNs));
      stageStartNs = System.nanoTime();
      scorePowerStatus(acc, status.voltage, status.totalCurrent, status.temperature,
          status.switchableEnabled, status.brownout || status.canWarning || status.hardwareFault,
          status.stickyBrownout || status.stickyCanWarning || status.stickyCanBusOff || status.stickyHasReset);
      boolean strongPresenceEvidence = hasStrongPowerPresenceEvidence(
          status.voltage, status.temperature, status.totalCurrent, status.channelCurrentA);
      if (shouldForceAbsentForPowerProbe(strongPresenceEvidence, acc.score())) {
        acc.warn(
            CODE_POWER_FRESHNESS_GATE,
            "PDP freshness gate failed; default-like telemetry is not strong presence evidence.",
            0,
            formatPowerEvidenceObserved(status.voltage, status.temperature, status.totalCurrent, status.channelCurrentA),
            StatusCatalogGenerated.SS__DEVICE__COMMUNICATION_WEAK);
        acc.forceBucket(BUCKET_ABSENT, StatusCatalogGenerated.SS__DEVICE__ABSENT, TEXT_PD_ABSENT);
      }
      acc.recordStageDuration(TEXT_STAGE_EVALUATE, nanosToMs(System.nanoTime() - stageStartNs));
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    } catch (Exception ex) {
      acc.warn(CODE_EXCEPTION_THROWN, TEXT_EXCEPTION_PREFIX + ex.getClass().getSimpleName(), 0,
          safeExceptionMessage(ex), StatusCatalogGenerated.SS__DEVICE__COMMUNICATION_WEAK);
      acc.forceBucket(BUCKET_ABSENT, StatusCatalogGenerated.SS__DEVICE__ABSENT, TEXT_PD_ABSENT);
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    }
  }

  private ProbeDeviceResult probePdh(
      ProbeTarget target,
      RevPdhDevice device,
      boolean preclearSticky) {
    long deviceStartNs = System.nanoTime();
    ProbeAccumulator acc = new ProbeAccumulator(target);
    PdhStatusReader reader = device.getActiveReaderForProbe();
    if (reader == null) {
      ProbeDeviceResult result = missingRuntimeDevice(target);
      result.totalDurationMs = nanosToMs(System.nanoTime() - deviceStartNs);
      return result;
    }
    acc.pass(CODE_OBJECT_HANDLE_REUSED, "Using runtime-owned PDH reader.", WEIGHT_CONSTRUCT,
        Integer.toString(target.canId));
    try {
      acc.recordStageDuration(TEXT_STAGE_HANDLE, nanosToMs(System.nanoTime() - deviceStartNs));
      if (preclearSticky) {
        long stageStartNs = System.nanoTime();
        reader.clearStickyFaults();
        acc.pass(CODE_CLEAR_STICKY_OK, "Cleared PDH sticky faults.", 0, OBSERVED_OK);
        acc.recordStageDuration(TEXT_STAGE_CLEAR_STICKY, nanosToMs(System.nanoTime() - stageStartNs));
      }
      long stageStartNs = System.nanoTime();
      PdhStatusAttachment status = reader.snapshot();
      acc.recordStageDuration(TEXT_STAGE_SNAPSHOT, nanosToMs(System.nanoTime() - stageStartNs));
      stageStartNs = System.nanoTime();
      scorePowerStatus(acc, status.voltage, status.totalCurrent, status.temperature,
          status.switchableEnabled, status.brownout || status.canWarning || status.hardwareFault,
          status.stickyBrownout || status.stickyCanWarning || status.stickyCanBusOff || status.stickyHasReset);
      boolean strongPresenceEvidence = hasStrongPowerPresenceEvidence(
          status.voltage, status.temperature, status.totalCurrent, status.channelCurrentA);
      if (shouldForceAbsentForPowerProbe(strongPresenceEvidence, acc.score())) {
        acc.warn(
            CODE_POWER_FRESHNESS_GATE,
            "PDH freshness gate failed; default-like telemetry is not strong presence evidence.",
            0,
            formatPowerEvidenceObserved(status.voltage, status.temperature, status.totalCurrent, status.channelCurrentA),
            StatusCatalogGenerated.SS__DEVICE__COMMUNICATION_WEAK);
        acc.forceBucket(BUCKET_ABSENT, StatusCatalogGenerated.SS__DEVICE__ABSENT, TEXT_PD_ABSENT);
      }
      acc.recordStageDuration(TEXT_STAGE_EVALUATE, nanosToMs(System.nanoTime() - stageStartNs));
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    } catch (Exception ex) {
      acc.warn(CODE_EXCEPTION_THROWN, TEXT_EXCEPTION_PREFIX + ex.getClass().getSimpleName(), 0,
          safeExceptionMessage(ex), StatusCatalogGenerated.SS__DEVICE__COMMUNICATION_WEAK);
      acc.forceBucket(BUCKET_ABSENT, StatusCatalogGenerated.SS__DEVICE__ABSENT, TEXT_PD_ABSENT);
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    }
  }

  private ProbeDeviceResult probeRoboRio(
      ProbeTarget target,
      RoboRioDevice device) {
    long deviceStartNs = System.nanoTime();
    ProbeAccumulator acc = new ProbeAccumulator(target);
    if (device == null) {
      ProbeDeviceResult result = missingRuntimeDevice(target);
      result.totalDurationMs = nanosToMs(System.nanoTime() - deviceStartNs);
      return result;
    }
    acc.pass(CODE_OBJECT_HANDLE_REUSED, "Using runtime-owned roboRIO snapshot.", WEIGHT_CONSTRUCT,
        Integer.toString(target.canId));
    try {
      acc.recordStageDuration(TEXT_STAGE_HANDLE, nanosToMs(System.nanoTime() - deviceStartNs));
      long stageStartNs = System.nanoTime();
      var snapshot = device.snapshot();
      acc.recordStageDuration(TEXT_STAGE_SNAPSHOT, nanosToMs(System.nanoTime() - stageStartNs));
      stageStartNs = System.nanoTime();
      RobotControllerPowerAttachment power = snapshot.getAttachment(RobotControllerPowerAttachment.class);
      RobotControllerRailsAttachment rails = snapshot.getAttachment(RobotControllerRailsAttachment.class);
      RobotControllerBusAttachment bus = snapshot.getAttachment(RobotControllerBusAttachment.class);
      if (power == null || rails == null || bus == null) {
        acc.error(
            CODE_EXCEPTION_THROWN,
            "Controller snapshot attachments missing.",
            MAX_SCORE,
            describeMissingControllerAttachments(power, rails, bus),
            StatusCatalogGenerated.SS__DEVICE__PROBE_EXCEPTION);
        acc.forceBucket(BUCKET_ABSENT, StatusCatalogGenerated.SS__DEVICE__ABSENT, TEXT_RUNTIME_DEVICE_MISSING);
        acc.recordStageDuration(TEXT_STAGE_EVALUATE, nanosToMs(System.nanoTime() - stageStartNs));
        acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
        return acc.finish();
      }
      addTelemetryCheck(
          acc,
          isReasonableBusVoltage(power.inputVoltage),
          CODE_BUS_VOLTAGE_VALID,
          "Controller input voltage looks valid.",
          "Controller input voltage not in expected range.",
          CONTROLLER_INPUT_VOLTAGE,
          formatDouble(power.inputVoltage));
      addTelemetryCheck(
          acc,
          !power.brownout,
          CODE_NO_ACTIVE_FAULTS,
          "Controller is not browned out.",
          "Controller reports brownout.",
          CONTROLLER_NOT_BROWNED_OUT,
          Boolean.toString(power.brownout));
      addTelemetryCheck(
          acc,
          hasReadableRobotControllerBusAttachment(bus),
          CODE_STATUS_REFRESH_OK,
          "Controller CAN status looks readable.",
          "Controller CAN status is not readable.",
          CONTROLLER_BUS_STATUS,
          formatRobotControllerBusObserved(bus));
      addTelemetryCheck(
          acc,
          isHealthyRobotControllerRail(rails.rail3v3Enabled, rails.rail3v3Voltage, MIN_VALID_3V3_VOLTAGE, MAX_VALID_3V3_VOLTAGE),
          CODE_SWITCHABLE_READ_VALID,
          "3.3V rail looks healthy.",
          "3.3V rail is disabled or out of range.",
          CONTROLLER_RAIL_3V3,
          formatRobotControllerRailObserved(rails.rail3v3Enabled, rails.rail3v3Voltage, rails.rail3v3FaultCount));
      addTelemetryCheck(
          acc,
          isHealthyRobotControllerRail(rails.rail5vEnabled, rails.rail5vVoltage, MIN_VALID_5V_VOLTAGE, MAX_VALID_5V_VOLTAGE),
          CODE_CURRENT_READ_VALID,
          "5V rail looks healthy.",
          "5V rail is disabled or out of range.",
          CONTROLLER_RAIL_5V,
          formatRobotControllerRailObserved(rails.rail5vEnabled, rails.rail5vVoltage, rails.rail5vFaultCount));
      addTelemetryCheck(
          acc,
          isHealthyRobotControllerRail(rails.rail6vEnabled, rails.rail6vVoltage, MIN_VALID_6V_VOLTAGE, MAX_VALID_6V_VOLTAGE),
          CODE_TEMPERATURE_READ_VALID,
          "6V rail looks healthy.",
          "6V rail is disabled or out of range.",
          CONTROLLER_RAIL_6V,
          formatRobotControllerRailObserved(rails.rail6vEnabled, rails.rail6vVoltage, rails.rail6vFaultCount));
      addTelemetryCheck(
          acc,
          hasNoRobotControllerRailFaults(rails),
          CODE_NO_STICKY_FAULTS,
          "Controller rail fault counts are clear.",
          "Controller rail fault counts are non-zero.",
          CONTROLLER_NO_RAIL_FAULTS,
          formatRobotControllerRailFaultsObserved(rails));
      acc.recordStageDuration(TEXT_STAGE_EVALUATE, nanosToMs(System.nanoTime() - stageStartNs));
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    } catch (Exception ex) {
      acc.error(
          CODE_EXCEPTION_THROWN,
          TEXT_EXCEPTION_PREFIX + ex.getClass().getSimpleName(),
          MAX_SCORE,
          safeExceptionMessage(ex),
          StatusCatalogGenerated.SS__DEVICE__PROBE_EXCEPTION);
      acc.setTotalDurationMs(nanosToMs(System.nanoTime() - deviceStartNs));
      return acc.finish();
    }
  }

  private void scorePowerStatus(
      ProbeAccumulator acc,
      double voltage,
      double totalCurrent,
      double temperature,
      boolean switchableEnabled,
      boolean activeFaults,
      boolean stickyFaults) {
    addTelemetryCheck(
        acc,
        isReasonableBusVoltage(voltage),
        CODE_BUS_VOLTAGE_VALID,
        "Bus voltage looks valid.",
        "Bus voltage not in expected range.",
        PD_BUS_VOLTAGE,
        formatDouble(voltage));
    addTelemetryCheck(
        acc,
        isFiniteInRange(totalCurrent, 0.0, MAX_VALID_CURRENT_A),
        CODE_CURRENT_READ_VALID,
        "Total current read succeeded.",
        "Total current read failed.",
        PD_TOTAL_CURRENT,
        formatDouble(totalCurrent));
    addTelemetryCheck(
        acc,
        isFiniteInRange(temperature, 0.0, MAX_VALID_TEMP_C),
        CODE_TEMPERATURE_READ_VALID,
        "Temperature read succeeded.",
        "Temperature read failed.",
        PD_TEMPERATURE,
        formatDouble(temperature));
    acc.pass(CODE_SWITCHABLE_READ_VALID, "Switchable-channel read succeeded.", PD_SWITCHABLE,
        Boolean.toString(switchableEnabled));
    if (!activeFaults) {
      acc.pass(CODE_NO_ACTIVE_FAULTS, "No active power-distribution faults.", PD_NO_ACTIVE_FAULTS, "false");
    } else {
      acc.fail(CODE_NO_ACTIVE_FAULTS, "Active power-distribution faults were reported.", PD_NO_ACTIVE_FAULTS, "true");
      acc.warn(CODE_NO_ACTIVE_FAULTS, "Active power-distribution faults were reported.", 0,
          "true", StatusCatalogGenerated.SS__DEVICE__FAULTS_ACTIVE);
    }
    if (stickyFaults) {
      acc.warn(CODE_NO_STICKY_FAULTS, "Sticky power-distribution faults were reported.", 0,
          "true", StatusCatalogGenerated.SS__DEVICE__FAULTS_ACTIVE);
    }
  }

  static boolean hasStrongPowerPresenceEvidence(
      double voltage,
      double temperature,
      double totalCurrent,
      double[] channelCurrents) {
    if (!isReasonableBusVoltage(voltage)) {
      return false;
    }
    if (!isFiniteInRange(temperature, 0.0, MAX_VALID_TEMP_C)) {
      return false;
    }
    if (!isFiniteInRange(totalCurrent, 0.0, MAX_VALID_CURRENT_A)) {
      return false;
    }
    if (channelCurrents == null || channelCurrents.length < MIN_VALID_POWER_CHANNEL_COUNT) {
      return false;
    }
    for (double current : channelCurrents) {
      if (!isFiniteInRange(current, 0.0, MAX_VALID_CURRENT_A)) {
        return false;
      }
    }
    return true;
  }

  static boolean shouldForceAbsentForPowerProbe(boolean strongPresenceEvidence, int score) {
    return !strongPresenceEvidence;
  }

  static boolean hasReadableRobotControllerBusAttachment(RobotControllerBusAttachment bus) {
    if (bus == null) {
      return false;
    }
    return isFiniteInRange(bus.canUtilizationPct, 0.0, MAX_CONTROLLER_UTILIZATION_PCT)
        && bus.canRxErrorCount >= 0
        && bus.canTxErrorCount >= 0
        && bus.canBusOffCount >= 0
        && bus.canTxFullCount >= 0;
  }

  static boolean isHealthyRobotControllerRail(
      boolean enabled,
      double voltage,
      double minVoltage,
      double maxVoltage) {
    return enabled && isFiniteInRange(voltage, minVoltage, maxVoltage);
  }

  static boolean hasNoRobotControllerRailFaults(RobotControllerRailsAttachment rails) {
    if (rails == null) {
      return false;
    }
    return rails.rail3v3FaultCount == 0
        && rails.rail5vFaultCount == 0
        && rails.rail6vFaultCount == 0;
  }

  private String describeMissingControllerAttachments(
      RobotControllerPowerAttachment power,
      RobotControllerRailsAttachment rails,
      RobotControllerBusAttachment bus) {
    return "power="
        + Boolean.toString(power != null)
        + ", rails="
        + Boolean.toString(rails != null)
        + ", bus="
        + Boolean.toString(bus != null);
  }

  private String formatRobotControllerBusObserved(RobotControllerBusAttachment bus) {
    if (bus == null) {
      return "missing";
    }
    return "utilPct="
        + formatDouble(bus.canUtilizationPct)
        + ", rxErr="
        + bus.canRxErrorCount
        + ", txErr="
        + bus.canTxErrorCount
        + ", busOff="
        + bus.canBusOffCount
        + ", txFull="
        + bus.canTxFullCount;
  }

  private String formatRobotControllerRailObserved(
      boolean enabled,
      double voltage,
      int faultCount) {
    return "enabled="
        + Boolean.toString(enabled)
        + ", voltage="
        + formatDouble(voltage)
        + ", faults="
        + faultCount;
  }

  private String formatRobotControllerRailFaultsObserved(RobotControllerRailsAttachment rails) {
    if (rails == null) {
      return "missing";
    }
    return "3v3="
        + rails.rail3v3FaultCount
        + ", 5v="
        + rails.rail5vFaultCount
        + ", 6v="
        + rails.rail6vFaultCount;
  }

  private String formatPowerEvidenceObserved(
      double voltage,
      double temperature,
      double totalCurrent,
      double[] channelCurrents) {
    return "busV="
        + formatDouble(voltage)
        + ", tempC="
        + formatDouble(temperature)
        + ", totalCurrentA="
        + formatDouble(totalCurrent)
        + ", anyChannelCurrent="
        + Boolean.toString(hasAnyMeaningfulChannelCurrent(channelCurrents));
  }

  private boolean hasAnyMeaningfulChannelCurrent(double[] channelCurrents) {
    if (channelCurrents == null) {
      return false;
    }
    for (double current : channelCurrents) {
      if (isFiniteInRange(current, MIN_MEANINGFUL_CURRENT_A, MAX_VALID_CURRENT_A)) {
        return true;
      }
    }
    return false;
  }

  private void addTelemetryCheck(
      ProbeAccumulator acc,
      boolean passed,
      String code,
      String passDescription,
      String failDescription,
      int weight,
      String observedValue) {
    if (passed) {
      acc.pass(code, passDescription, weight, observedValue);
    } else {
      acc.fail(code, failDescription, weight, observedValue);
    }
  }

  private boolean isOkStatus(StatusCode code) {
    return code == StatusCode.OK;
  }

  private static boolean isReasonableBusVoltage(double value) {
    return isFiniteInRange(value, MIN_VALID_BUS_VOLTAGE, MAX_VALID_BUS_VOLTAGE);
  }

  private static boolean isFiniteInRange(double value, double min, double max) {
    return Double.isFinite(value) && value >= min && value <= max;
  }

  private static String formatDouble(double value) {
    if (!Double.isFinite(value)) {
      return "NaN";
    }
    return String.format(Locale.US, "%.3f", value);
  }

  private String safeExceptionMessage(Exception ex) {
    if (ex == null || ex.getMessage() == null || ex.getMessage().isBlank()) {
      return ex != null ? ex.getClass().getSimpleName() : TEXT_EMPTY;
    }
    return ex.getClass().getSimpleName() + ": " + ex.getMessage();
  }

  private double nanosToMs(long elapsedNs) {
    return elapsedNs / 1_000_000.0;
  }

  private ProbeDeviceResult invalidTarget(ProbeTarget target, String detail) {
    ProbeDeviceResult result = baseResult(target);
    result.code = StatusCatalogGenerated.SS__DEVICE__PROBE_INVALID_TARGET;
    result.status = statusForCode(result.code);
    result.bucket = BUCKET_UNKNOWN;
    result.message = detail;
    result.errors.add(detail);
    return result;
  }

  private ProbeDeviceResult unsupportedTarget(ProbeTarget target, String detail) {
    ProbeDeviceResult result = baseResult(target);
    result.code = StatusCatalogGenerated.SS__DEVICE__PROBE_UNSUPPORTED_MODEL;
    result.status = statusForCode(result.code);
    result.bucket = BUCKET_UNKNOWN;
    result.message = detail;
    result.errors.add(detail);
    return result;
  }

  private ProbeDeviceResult missingRuntimeDevice(ProbeTarget target) {
    ProbeDeviceResult result = baseResult(target);
    result.code = StatusCatalogGenerated.SS__DEVICE__ABSENT;
    result.status = statusForCode(result.code);
    result.bucket = BUCKET_ABSENT;
    result.message = TEXT_RUNTIME_DEVICE_MISSING;
    result.errors.add(TEXT_RUNTIME_DEVICE_MISSING);
    return result;
  }

  private ProbeDeviceResult snapshotNotAllowed(ProbeTarget target) {
    ProbeDeviceResult result = baseResult(target);
    result.code = StatusCatalogGenerated.SS__DEVICE__ABSENT;
    result.status = statusForCode(result.code);
    result.bucket = BUCKET_UNKNOWN;
    result.message = TEXT_SNAPSHOT_NOT_ALLOWED;
    result.errors.add(TEXT_SNAPSHOT_NOT_ALLOWED);
    return result;
  }

  private ProbeDeviceResult baseResult(ProbeTarget target) {
    ProbeDeviceResult result = new ProbeDeviceResult();
    if (target != null) {
      result.label = target.label;
      result.vendor = target.vendor;
      result.model = target.model;
      result.canId = target.canId;
    }
    result.maxScore = MAX_SCORE;
    return result;
  }

  private String statusForCode(int code) {
    int severity = code & 0x7;
    if (severity == 0) {
      return STATUS_OK;
    }
    if (severity <= 2) {
      return STATUS_WARNING;
    }
    return STATUS_ERROR;
  }

  private static final class ProbeTarget {
    private final String label;
    private final int canId;
    private final String vendor;
    private final String model;

    private ProbeTarget(String label, int canId, String vendor, String model) {
      this.label = label != null ? label : TEXT_EMPTY;
      this.canId = canId;
      this.vendor = vendor != null ? vendor : TEXT_EMPTY;
      this.model = model != null ? model : MODEL_UNSUPPORTED;
    }
  }

  private final class ProbeAccumulator {
    private final ProbeDeviceResult result;
    private String forcedBucket;
    private int forcedCode;
    private String forcedMessage;

    private ProbeAccumulator(ProbeTarget target) {
      this.result = baseResult(target);
    }

    private void recordStageDuration(String stage, double durationMs) {
      if (stage == null || stage.isBlank() || !Double.isFinite(durationMs)) {
        return;
      }
      result.stageDurationsMs.put(stage, durationMs);
    }

    private void setTotalDurationMs(double durationMs) {
      if (!Double.isFinite(durationMs)) {
        return;
      }
      result.totalDurationMs = durationMs;
    }

    private void pass(String code, String description, int weight, String observedValue) {
      result.score += weight;
      result.evidence.add(new ProbeEvidence(code, description, weight, true, observedValue));
    }

    private void fail(String code, String description, int weight, String observedValue) {
      result.evidence.add(new ProbeEvidence(code, description, weight, false, observedValue));
    }

    private void warn(String code, String description, int weight, String observedValue, int statusCode) {
      result.evidence.add(new ProbeEvidence(code, description, weight, false, observedValue));
      result.warnings.add(description);
      if (result.code == 0) {
        result.code = statusCode;
      }
    }

    private void error(String code, String description, int weight, String observedValue, int statusCode) {
      result.evidence.add(new ProbeEvidence(code, description, weight, false, observedValue));
      result.errors.add(description);
      result.code = statusCode;
      result.status = statusForCode(statusCode);
    }

    private void warnEntries(String prefix, List<String> names, int statusCode) {
      if (names == null) {
        return;
      }
      for (String name : names) {
        if (name == null || name.isBlank()) {
          continue;
        }
        warn(prefix, prefix + ": " + name, 0, name, statusCode);
      }
    }

    private void forceBucket(String bucket, int code, String message) {
      this.forcedBucket = bucket;
      this.forcedCode = code;
      this.forcedMessage = message;
    }

    private int score() {
      return result.score;
    }

    private ProbeDeviceResult finish() {
      if (forcedBucket != null && !forcedBucket.isBlank()) {
        result.bucket = forcedBucket;
        result.code = forcedCode;
        result.message = forcedMessage;
        result.status = statusForCode(result.code);
        return result;
      }
      if (result.score >= PRESENT_THRESHOLD) {
        result.bucket = BUCKET_PRESENT;
        result.code = StatusCatalogGenerated.SS__DEVICE__PRESENT;
        result.message = "Device present: " + result.label + ".";
      } else if (result.score >= DEGRADED_THRESHOLD) {
        result.bucket = BUCKET_DEGRADED;
        result.code = StatusCatalogGenerated.SS__DEVICE__DEGRADED;
        result.message = "Device degraded: " + result.label + ".";
      } else {
        result.bucket = BUCKET_ABSENT;
        result.code = StatusCatalogGenerated.SS__DEVICE__ABSENT;
        result.message = "Device absent: " + result.label + ".";
      }
      result.status = statusForCode(result.code);
      return result;
    }
  }

  /**
   * NAME
   *   ProbeSessionResult - Structured one-shot probe output.
   */
  public static final class ProbeSessionResult {
    public int code;
    public String status = STATUS_OK;
    public String message = TEXT_EMPTY;
    public String mode = MODE_ONE_SHOT;
    public int targetCount;
    public int presentCount;
    public int degradedCount;
    public int absentCount;
    public int unknownCount;
    public int unsupportedCount;
    public double totalDurationMs;
    public String slowestDeviceLabel = TEXT_EMPTY;
    public double slowestDeviceDurationMs;
    public final List<ProbeDeviceResult> devices = new ArrayList<>();

    private static ProbeSessionResult failed(String message) {
      ProbeSessionResult result = new ProbeSessionResult();
      result.code = StatusCatalogGenerated.SS__EXECUTOR__FAILED;
      result.status = STATUS_ERROR;
      result.message = message;
      return result;
    }

    private static ProbeSessionResult fromDevices(List<ProbeDeviceResult> results, int unsupportedCount) {
      ProbeSessionResult session = new ProbeSessionResult();
      session.devices.addAll(results);
      session.targetCount = results.size();
      session.unsupportedCount = unsupportedCount;
      boolean anyError = false;
      boolean anyWarning = false;
      for (ProbeDeviceResult result : results) {
        if (result == null) {
          continue;
        }
        switch (result.bucket) {
          case BUCKET_PRESENT -> session.presentCount++;
          case BUCKET_DEGRADED -> session.degradedCount++;
          case BUCKET_ABSENT -> session.absentCount++;
          default -> session.unknownCount++;
        }
        if (STATUS_ERROR.equals(result.status)) {
          anyError = true;
        } else if (STATUS_WARNING.equals(result.status)) {
          anyWarning = true;
        }
      }
      if (!anyError && !anyWarning && session.unknownCount == 0 && session.absentCount == 0 && session.degradedCount == 0) {
        session.code = StatusCatalogGenerated.SS__EXECUTOR__SUCCESS;
        session.status = STATUS_OK;
        session.message = TEXT_SESSION_SUCCESS;
      } else {
        session.code = StatusCatalogGenerated.SS__EXECUTOR__COMPLETED_WITH_WARNINGS;
        session.status = STATUS_WARNING;
        session.message = TEXT_SESSION_WARN;
      }
      return session;
    }

    private void finishProfilingSummary() {
      double slowestMs = -1.0;
      String slowestLabel = TEXT_EMPTY;
      for (ProbeDeviceResult result : devices) {
        if (result == null || !Double.isFinite(result.totalDurationMs)) {
          continue;
        }
        if (result.totalDurationMs > slowestMs) {
          slowestMs = result.totalDurationMs;
          slowestLabel = result.label != null ? result.label : TEXT_EMPTY;
        }
      }
      if (slowestMs >= 0.0) {
        slowestDeviceDurationMs = slowestMs;
        slowestDeviceLabel = slowestLabel;
      }
    }

    public String toJsonString() {
      return toJsonObject().toString();
    }

    public JsonObject toJsonObject() {
      JsonObject root = new JsonObject();
      root.addProperty("code", code);
      root.addProperty("status", status);
      root.addProperty("message", message);
      root.addProperty("mode", mode);
      root.addProperty("targetCount", targetCount);
      root.addProperty(TEXT_TOTAL_DURATION_MS, totalDurationMs);
      root.addProperty(TEXT_SLOWEST_DEVICE_LABEL, slowestDeviceLabel);
      root.addProperty(TEXT_SLOWEST_DEVICE_DURATION_MS, slowestDeviceDurationMs);
      JsonObject summary = new JsonObject();
      summary.addProperty(BUCKET_PRESENT, presentCount);
      summary.addProperty(BUCKET_DEGRADED, degradedCount);
      summary.addProperty(BUCKET_ABSENT, absentCount);
      summary.addProperty(BUCKET_UNKNOWN, unknownCount);
      summary.addProperty("unsupported", unsupportedCount);
      root.add("summary", summary);
      JsonArray deviceArray = new JsonArray();
      for (ProbeDeviceResult device : devices) {
        deviceArray.add(device.toJsonObject());
      }
      root.add("devices", deviceArray);
      return root;
    }

    public String toText() {
      StringBuilder sb = new StringBuilder();
      sb.append(TEXT_SESSION_HEADER).append(TEXT_NEWLINE);
      sb.append("Session").append(TEXT_FIELD_SEPARATOR)
          .append(message).append(TEXT_FIELD_SEPARATOR)
          .append("targets ").append(targetCount).append(TEXT_FIELD_SEPARATOR)
          .append("present ").append(presentCount).append(TEXT_FIELD_SEPARATOR)
          .append("degraded ").append(degradedCount).append(TEXT_FIELD_SEPARATOR)
          .append("absent ").append(absentCount).append(TEXT_FIELD_SEPARATOR)
          .append("unknown ").append(unknownCount)
          .append(TEXT_FIELD_SEPARATOR).append(TEXT_TOTAL_DURATION_MS).append(TEXT_EQUALS)
          .append(formatDouble(totalDurationMs));
      if (unsupportedCount > 0) {
        sb.append(TEXT_FIELD_SEPARATOR).append("unsupported ").append(unsupportedCount);
      }
      if (slowestDeviceLabel != null && !slowestDeviceLabel.isBlank()) {
        sb.append(TEXT_FIELD_SEPARATOR)
            .append(TEXT_SLOWEST_DEVICE_LABEL)
            .append(TEXT_EQUALS)
            .append(slowestDeviceLabel)
            .append('(')
            .append(formatDouble(slowestDeviceDurationMs))
            .append(TEXT_MS_SUFFIX)
            .append(')');
      }
      sb.append(TEXT_NEWLINE);
      for (ProbeDeviceResult device : devices) {
        sb.append(device.toText());
      }
      return sb.toString().trim();
    }
  }

  /**
   * NAME
   *   ProbeDeviceResult - Per-device probe result row.
   */
  public static final class ProbeDeviceResult {
    public int code;
    public String status = STATUS_OK;
    public String message = TEXT_EMPTY;
    public String vendor = TEXT_EMPTY;
    public int canId;
    public String model = TEXT_EMPTY;
    public String label = TEXT_EMPTY;
    public String bucket = BUCKET_UNKNOWN;
    public int score;
    public int maxScore;
    public double totalDurationMs;
    public final Map<String, Double> stageDurationsMs = new LinkedHashMap<>();
    public final List<ProbeEvidence> evidence = new ArrayList<>();
    public final LinkedHashSet<String> warnings = new LinkedHashSet<>();
    public final LinkedHashSet<String> errors = new LinkedHashSet<>();

    public JsonObject toJsonObject() {
      JsonObject root = new JsonObject();
      root.addProperty("code", code);
      root.addProperty("status", status);
      root.addProperty("message", message);
      root.addProperty("label", label);
      root.addProperty("vendor", vendor);
      root.addProperty("model", model);
      root.addProperty("canId", canId);
      root.addProperty("bucket", bucket);
      root.addProperty("score", score);
      root.addProperty("maxScore", maxScore);
      root.addProperty(TEXT_DURATION_MS, totalDurationMs);
      JsonObject stageObject = new JsonObject();
      for (Map.Entry<String, Double> entry : stageDurationsMs.entrySet()) {
        if (entry.getKey() == null || entry.getKey().isBlank() || entry.getValue() == null) {
          continue;
        }
        stageObject.addProperty(entry.getKey(), entry.getValue());
      }
      root.add(TEXT_STAGE_TIMINGS, stageObject);
      JsonArray evidenceArray = new JsonArray();
      for (ProbeEvidence row : evidence) {
        evidenceArray.add(row.toJsonObject());
      }
      root.add("evidence", evidenceArray);
      root.add("warnings", toStringArray(warnings));
      root.add("errors", toStringArray(errors));
      return root;
    }

    private JsonArray toStringArray(Iterable<String> values) {
      JsonArray out = new JsonArray();
      if (values == null) {
        return out;
      }
      for (String value : values) {
        out.add(value);
      }
      return out;
    }

    public String toText() {
      StringBuilder sb = new StringBuilder();
      sb.append(label).append(TEXT_FIELD_SEPARATOR)
          .append(vendor).append(TEXT_FIELD_SEPARATOR)
          .append(model).append(TEXT_FIELD_SEPARATOR)
          .append("CAN ").append(canId).append(TEXT_FIELD_SEPARATOR)
          .append(bucket).append(TEXT_FIELD_SEPARATOR)
          .append("score ").append(score).append('/').append(maxScore)
          .append(TEXT_FIELD_SEPARATOR).append(TEXT_DURATION_MS).append(TEXT_EQUALS)
          .append(formatDouble(totalDurationMs))
          .append(TEXT_NEWLINE);
      if (!stageDurationsMs.isEmpty()) {
        sb.append(TEXT_EVIDENCE_PREFIX).append("timings");
        boolean first = true;
        for (Map.Entry<String, Double> entry : stageDurationsMs.entrySet()) {
          if (entry.getKey() == null || entry.getKey().isBlank() || entry.getValue() == null) {
            continue;
          }
          sb.append(first ? TEXT_FIELD_SEPARATOR : ", ");
          sb.append(entry.getKey()).append(TEXT_EQUALS).append(formatDouble(entry.getValue()));
          first = false;
        }
        sb.append(TEXT_NEWLINE);
      }
      for (ProbeEvidence row : evidence) {
        sb.append(TEXT_EVIDENCE_PREFIX)
            .append(row.passed ? TEXT_PASS_PREFIX : TEXT_FAIL_PREFIX)
            .append(row.code);
        if (row.observedValue != null && !row.observedValue.isBlank()) {
          sb.append(TEXT_EQUALS).append(row.observedValue);
        }
        sb.append(TEXT_NEWLINE);
      }
      for (String warning : warnings) {
        sb.append(TEXT_EVIDENCE_PREFIX).append(TEXT_FAIL_PREFIX).append(warning).append(TEXT_NEWLINE);
      }
      for (String error : errors) {
        sb.append(TEXT_EVIDENCE_PREFIX).append(TEXT_FAIL_PREFIX).append(error).append(TEXT_NEWLINE);
      }
      return sb.toString();
    }
  }

  /**
   * NAME
   *   ProbeEvidence - One evidence row for the active presence probe.
   */
  public static final class ProbeEvidence {
    public final String code;
    public final String description;
    public final int weight;
    public final boolean passed;
    public final String observedValue;

    private ProbeEvidence(
        String code,
        String description,
        int weight,
        boolean passed,
        String observedValue) {
      this.code = code != null ? code : TEXT_EMPTY;
      this.description = description != null ? description : TEXT_EMPTY;
      this.weight = weight;
      this.passed = passed;
      this.observedValue = observedValue != null ? observedValue : TEXT_EMPTY;
    }

    public JsonObject toJsonObject() {
      JsonObject root = new JsonObject();
      root.addProperty("code", code);
      root.addProperty("description", description);
      root.addProperty("weight", weight);
      root.addProperty("passed", passed);
      root.addProperty("observedValue", observedValue);
      return root;
    }
  }
}
