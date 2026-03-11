package frc.robot;

import frc.robot.diag.snapshots.LimitsAttachment;
import frc.robot.diag.snapshots.MotorSpecAttachment;
import frc.robot.manufacturers.ctre.diag.CtreMotorAttachment;
import frc.robot.manufacturers.rev.diag.RevMotorAttachment;
import java.util.List;

/**
 * NAME
 *   BringupHealthFormat - Formatting helpers for health output.
 *
 * DESCRIPTION
 *   Provides concise formatting utilities for fault summaries, limits, and
 *   numeric formatting used in bringup reports.
 */
public final class BringupHealthFormat {
  private BringupHealthFormat() {}

  /**
   * NAME
   *   formatRevFaultSummary - Format REV fault/warning summary text.
   *
   * PARAMETERS
   *   rev - REV motor attachment.
   *
   * RETURNS
   *   Summary string or empty string when unavailable.
   */
  public static String formatRevFaultSummary(RevMotorAttachment rev) {
    if (rev == null) {
      return "";
    }
    StringBuilder sb = new StringBuilder(128);
    sb.append(" faults=0x").append(Integer.toHexString(rev.faultsRaw));
    sb.append(formatFlagList(rev.faultFlags));
    sb.append(" sticky=0x").append(Integer.toHexString(rev.stickyFaultsRaw));
    sb.append(formatFlagList(rev.stickyFaultFlags));
    sb.append(" warnings=0x").append(Integer.toHexString(rev.warningsRaw));
    sb.append(formatFlagList(rev.warningFlags));
    sb.append(" stickyWarn=0x").append(Integer.toHexString(rev.stickyWarningsRaw));
    sb.append(formatFlagList(rev.stickyWarningFlags));
    return sb.toString();
  }

  /**
   * NAME
   *   formatCtreFaultSummary - Format CTRE fault summary text.
   *
   * PARAMETERS
   *   ctre - CTRE motor attachment.
   *
   * RETURNS
   *   Summary string or empty string when unavailable.
   */
  public static String formatCtreFaultSummary(CtreMotorAttachment ctre) {
    if (ctre == null) {
      return "";
    }
    StringBuilder sb = new StringBuilder(128);
    sb.append(" fault=0x").append(Integer.toHexString(ctre.faultsRaw));
    sb.append(formatFlagList(ctre.faultFlags));
    sb.append(" sticky=0x").append(Integer.toHexString(ctre.stickyFaultsRaw));
    sb.append(formatFlagList(ctre.stickyFaultFlags));
    return sb.toString();
  }

  /**
   * NAME
   *   formatMotorSpecNote - Format motor spec/current comparison note.
   *
   * PARAMETERS
   *   spec - Motor spec attachment.
   *   motorCurrent - Current in amps.
   *
   * RETURNS
   *   Summary string or empty string when unavailable.
   */
  public static String formatMotorSpecNote(MotorSpecAttachment spec, Double motorCurrent) {
    if (spec == null || spec.freeCurrentA == null || spec.stallCurrentA == null) {
      return "";
    }
    double free = spec.freeCurrentA;
    double stall = spec.stallCurrentA;
    double current = motorCurrent != null ? motorCurrent : 0.0;
    String ratio = free > 0.0 ? String.format("%.2fx", current / free) : "?";
    return " specFree=" + String.format("%.1f", free) + "A" +
        " specStall=" + String.format("%.0f", stall) + "A" +
        " freeRatio=" + ratio;
  }

  /**
   * NAME
   *   formatLimitSummary - Format limit switch summary text.
   *
   * PARAMETERS
   *   limits - Limits attachment.
   *
   * RETURNS
   *   Summary string or empty string when no limits are configured.
   */
  public static String formatLimitSummary(LimitsAttachment limits) {
    if (limits == null || (limits.fwdDio < 0 && limits.revDio < 0)) {
      return "";
    }
    StringBuilder sb = new StringBuilder(48);
    sb.append(" limits=");
    if (limits.fwdDio >= 0) {
      sb.append("fwd:DIO").append(limits.fwdDio)
          .append("=").append(formatLimitState(limits.fwdClosed));
    }
    if (limits.revDio >= 0) {
      if (limits.fwdDio >= 0) {
        sb.append(",");
      }
      sb.append("rev:DIO").append(limits.revDio)
          .append("=").append(formatLimitState(limits.revClosed));
    }
    if (limits.invert) {
      sb.append(" inv");
    }
    return sb.toString();
  }

  /**
   * NAME
   *   formatLimitState - Format a single limit state.
   */
  private static String formatLimitState(Boolean closed) {
    if (closed == null) {
      return "?";
    }
    return closed ? "CLOSED" : "OPEN";
  }

  /**
   * NAME
   *   formatFlagList - Format a list of fault/warning flags.
   */
  private static String formatFlagList(List<String> flags) {
    if (flags == null || flags.isEmpty()) {
      return "";
    }
    return " [" + String.join(",", flags) + "]";
  }

  /**
   * NAME
   *   safeDouble - Replace null with 0.0 for formatting.
   */
  public static double safeDouble(Double value) {
    return value == null ? 0.0 : value;
  }

  /**
   * NAME
   *   safeText - Replace null with empty string for formatting.
   */
  public static String safeText(String value) {
    return value == null ? "" : value;
  }
}
