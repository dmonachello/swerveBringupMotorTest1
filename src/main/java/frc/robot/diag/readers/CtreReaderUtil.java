package frc.robot.diag.readers;

import com.ctre.phoenix6.BaseStatusSignal;
import com.ctre.phoenix6.StatusSignal;
import com.ctre.phoenix6.hardware.TalonFX;
import java.util.List;

// CTRE-specific helpers for extracting fault flags from status signals.
public final class CtreReaderUtil {
  private CtreReaderUtil() {}

  public static void collectFaultFlags(TalonFX talon, List<String> out) {
    var bootDuringEnable = talon.getFault_BootDuringEnable();
    var bridgeBrownout = talon.getFault_BridgeBrownout();
    var deviceTemp = talon.getFault_DeviceTemp();
    var forwardHardLimit = talon.getFault_ForwardHardLimit();
    var forwardSoftLimit = talon.getFault_ForwardSoftLimit();
    var fusedSensorOutOfSync = talon.getFault_FusedSensorOutOfSync();
    var hardware = talon.getFault_Hardware();
    var missingDifferentialFx = talon.getFault_MissingDifferentialFX();
    var missingHardLimitRemote = talon.getFault_MissingHardLimitRemote();
    var missingSoftLimitRemote = talon.getFault_MissingSoftLimitRemote();
    var overSupplyV = talon.getFault_OverSupplyV();
    var procTemp = talon.getFault_ProcTemp();
    var remoteSensorDataInvalid = talon.getFault_RemoteSensorDataInvalid();
    var remoteSensorPosOverflow = talon.getFault_RemoteSensorPosOverflow();
    var remoteSensorReset = talon.getFault_RemoteSensorReset();
    var reverseHardLimit = talon.getFault_ReverseHardLimit();
    var reverseSoftLimit = talon.getFault_ReverseSoftLimit();
    var staticBrakeDisabled = talon.getFault_StaticBrakeDisabled();
    var statorCurrLimit = talon.getFault_StatorCurrLimit();
    var supplyCurrLimit = talon.getFault_SupplyCurrLimit();
    var undervoltage = talon.getFault_Undervoltage();
    var unlicensedFeatureInUse = talon.getFault_UnlicensedFeatureInUse();
    var unstableSupplyV = talon.getFault_UnstableSupplyV();
    var usingFusedCancoderUnlicensed = talon.getFault_UsingFusedCANcoderWhileUnlicensed();

    BaseStatusSignal.refreshAll(
        bootDuringEnable,
        bridgeBrownout,
        deviceTemp,
        forwardHardLimit,
        forwardSoftLimit,
        fusedSensorOutOfSync,
        hardware,
        missingDifferentialFx,
        missingHardLimitRemote,
        missingSoftLimitRemote,
        overSupplyV,
        procTemp,
        remoteSensorDataInvalid,
        remoteSensorPosOverflow,
        remoteSensorReset,
        reverseHardLimit,
        reverseSoftLimit,
        staticBrakeDisabled,
        statorCurrLimit,
        supplyCurrLimit,
        undervoltage,
        unlicensedFeatureInUse,
        unstableSupplyV,
        usingFusedCancoderUnlicensed);

    appendIf(out, "BootDuringEnable", isTrue(bootDuringEnable));
    appendIf(out, "BridgeBrownout", isTrue(bridgeBrownout));
    appendIf(out, "DeviceTemp", isTrue(deviceTemp));
    appendIf(out, "ForwardHardLimit", isTrue(forwardHardLimit));
    appendIf(out, "ForwardSoftLimit", isTrue(forwardSoftLimit));
    appendIf(out, "FusedSensorOutOfSync", isTrue(fusedSensorOutOfSync));
    appendIf(out, "Hardware", isTrue(hardware));
    appendIf(out, "MissingDifferentialFX", isTrue(missingDifferentialFx));
    appendIf(out, "MissingHardLimitRemote", isTrue(missingHardLimitRemote));
    appendIf(out, "MissingSoftLimitRemote", isTrue(missingSoftLimitRemote));
    appendIf(out, "OverSupplyV", isTrue(overSupplyV));
    appendIf(out, "ProcTemp", isTrue(procTemp));
    appendIf(out, "RemoteSensorDataInvalid", isTrue(remoteSensorDataInvalid));
    appendIf(out, "RemoteSensorPosOverflow", isTrue(remoteSensorPosOverflow));
    appendIf(out, "RemoteSensorReset", isTrue(remoteSensorReset));
    appendIf(out, "ReverseHardLimit", isTrue(reverseHardLimit));
    appendIf(out, "ReverseSoftLimit", isTrue(reverseSoftLimit));
    appendIf(out, "StaticBrakeDisabled", isTrue(staticBrakeDisabled));
    appendIf(out, "StatorCurrLimit", isTrue(statorCurrLimit));
    appendIf(out, "SupplyCurrLimit", isTrue(supplyCurrLimit));
    appendIf(out, "Undervoltage", isTrue(undervoltage));
    appendIf(out, "UnlicensedFeatureInUse", isTrue(unlicensedFeatureInUse));
    appendIf(out, "UnstableSupplyV", isTrue(unstableSupplyV));
    appendIf(out, "UsingFusedCANcoderWhileUnlicensed", isTrue(usingFusedCancoderUnlicensed));
  }

  public static void collectStickyFaultFlags(TalonFX talon, List<String> out) {
    var bootDuringEnable = talon.getStickyFault_BootDuringEnable();
    var bridgeBrownout = talon.getStickyFault_BridgeBrownout();
    var deviceTemp = talon.getStickyFault_DeviceTemp();
    var forwardHardLimit = talon.getStickyFault_ForwardHardLimit();
    var forwardSoftLimit = talon.getStickyFault_ForwardSoftLimit();
    var fusedSensorOutOfSync = talon.getStickyFault_FusedSensorOutOfSync();
    var hardware = talon.getStickyFault_Hardware();
    var missingDifferentialFx = talon.getStickyFault_MissingDifferentialFX();
    var missingHardLimitRemote = talon.getStickyFault_MissingHardLimitRemote();
    var missingSoftLimitRemote = talon.getStickyFault_MissingSoftLimitRemote();
    var overSupplyV = talon.getStickyFault_OverSupplyV();
    var procTemp = talon.getStickyFault_ProcTemp();
    var remoteSensorDataInvalid = talon.getStickyFault_RemoteSensorDataInvalid();
    var remoteSensorPosOverflow = talon.getStickyFault_RemoteSensorPosOverflow();
    var remoteSensorReset = talon.getStickyFault_RemoteSensorReset();
    var reverseHardLimit = talon.getStickyFault_ReverseHardLimit();
    var reverseSoftLimit = talon.getStickyFault_ReverseSoftLimit();
    var staticBrakeDisabled = talon.getStickyFault_StaticBrakeDisabled();
    var statorCurrLimit = talon.getStickyFault_StatorCurrLimit();
    var supplyCurrLimit = talon.getStickyFault_SupplyCurrLimit();
    var undervoltage = talon.getStickyFault_Undervoltage();
    var unlicensedFeatureInUse = talon.getStickyFault_UnlicensedFeatureInUse();
    var unstableSupplyV = talon.getStickyFault_UnstableSupplyV();
    var usingFusedCancoderUnlicensed = talon.getStickyFault_UsingFusedCANcoderWhileUnlicensed();

    BaseStatusSignal.refreshAll(
        bootDuringEnable,
        bridgeBrownout,
        deviceTemp,
        forwardHardLimit,
        forwardSoftLimit,
        fusedSensorOutOfSync,
        hardware,
        missingDifferentialFx,
        missingHardLimitRemote,
        missingSoftLimitRemote,
        overSupplyV,
        procTemp,
        remoteSensorDataInvalid,
        remoteSensorPosOverflow,
        remoteSensorReset,
        reverseHardLimit,
        reverseSoftLimit,
        staticBrakeDisabled,
        statorCurrLimit,
        supplyCurrLimit,
        undervoltage,
        unlicensedFeatureInUse,
        unstableSupplyV,
        usingFusedCancoderUnlicensed);

    appendIf(out, "BootDuringEnable", isTrue(bootDuringEnable));
    appendIf(out, "BridgeBrownout", isTrue(bridgeBrownout));
    appendIf(out, "DeviceTemp", isTrue(deviceTemp));
    appendIf(out, "ForwardHardLimit", isTrue(forwardHardLimit));
    appendIf(out, "ForwardSoftLimit", isTrue(forwardSoftLimit));
    appendIf(out, "FusedSensorOutOfSync", isTrue(fusedSensorOutOfSync));
    appendIf(out, "Hardware", isTrue(hardware));
    appendIf(out, "MissingDifferentialFX", isTrue(missingDifferentialFx));
    appendIf(out, "MissingHardLimitRemote", isTrue(missingHardLimitRemote));
    appendIf(out, "MissingSoftLimitRemote", isTrue(missingSoftLimitRemote));
    appendIf(out, "OverSupplyV", isTrue(overSupplyV));
    appendIf(out, "ProcTemp", isTrue(procTemp));
    appendIf(out, "RemoteSensorDataInvalid", isTrue(remoteSensorDataInvalid));
    appendIf(out, "RemoteSensorPosOverflow", isTrue(remoteSensorPosOverflow));
    appendIf(out, "RemoteSensorReset", isTrue(remoteSensorReset));
    appendIf(out, "ReverseHardLimit", isTrue(reverseHardLimit));
    appendIf(out, "ReverseSoftLimit", isTrue(reverseSoftLimit));
    appendIf(out, "StaticBrakeDisabled", isTrue(staticBrakeDisabled));
    appendIf(out, "StatorCurrLimit", isTrue(statorCurrLimit));
    appendIf(out, "SupplyCurrLimit", isTrue(supplyCurrLimit));
    appendIf(out, "Undervoltage", isTrue(undervoltage));
    appendIf(out, "UnlicensedFeatureInUse", isTrue(unlicensedFeatureInUse));
    appendIf(out, "UnstableSupplyV", isTrue(unstableSupplyV));
    appendIf(out, "UsingFusedCANcoderWhileUnlicensed", isTrue(usingFusedCancoderUnlicensed));
  }

  private static boolean isTrue(StatusSignal<Boolean> signal) {
    return Boolean.TRUE.equals(signal.getValue());
  }

  private static void appendIf(List<String> out, String name, boolean active) {
    if (!active) {
      return;
    }
    out.add(name);
  }
}
