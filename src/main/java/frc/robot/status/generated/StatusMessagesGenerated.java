package frc.robot.status.generated;

import java.util.HashMap;
import java.util.Map;

/** AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration. */
public final class StatusMessagesGenerated {
  public static final String GENERATED_FROM_HASH = "b6ad8dd4a8eadd0e1c360a5c352c5dc481ff11ff358c40fc49d9c6e9e49660e0";
  private static final Map<Integer, String> TABLE = new HashMap<>();

  static {
    TABLE.put(65547, "Invalid flag: {flag}.");
    TABLE.put(65555, "Invalid command syntax.");
    TABLE.put(65563, "Missing required argument: {arg}.");
    TABLE.put(65571, "Unknown command.");
    TABLE.put(131083, "Invalid value: {value}.");
    TABLE.put(131091, "Value out of range: {value}.");
    TABLE.put(131099, "Required value missing: {field}.");
    TABLE.put(196616, "Success.");
    TABLE.put(196626, "Operation cancelled.");
    TABLE.put(196635, "Command failed.");
    TABLE.put(196643, "Internal error.");
    TABLE.put(196651, "Operation not supported.");
    TABLE.put(262155, "Invalid device field: {field}.");
    TABLE.put(262163, "Device not defined: {device}.");
    TABLE.put(262171, "Device not found: {device}.");
    TABLE.put(327690, "Group has no members: {group}.");
    TABLE.put(327699, "Invalid binding.");
    TABLE.put(327707, "Group member not found: {device}.");
    TABLE.put(327715, "Group not found: {group}.");
    TABLE.put(393227, "Invalid input binding.");
    TABLE.put(393235, "Input binding not found: {binding}.");
    TABLE.put(458762, "Robot not connected.");
    TABLE.put(458771, "Failed to send command.");
    TABLE.put(458779, "Failed to connect.");
    TABLE.put(458787, "Handshake failed.");
    TABLE.put(458795, "Robot unavailable.");
    TABLE.put(458803, "Command timed out.");
    TABLE.put(524296, "Config valid.");
    TABLE.put(524305, "Config imported.");
    TABLE.put(524313, "Config merged.");
    TABLE.put(524321, "Config saved.");
    TABLE.put(524331, "Duplicate label: {label}.");
    TABLE.put(524339, "Config invalid: {detail}.");
    TABLE.put(524347, "Missing device: {device}.");
    TABLE.put(524355, "Config not loaded.");
    TABLE.put(524363, "Active profile required.");
  }

  public static String getMessageTemplate(int code) {
    return TABLE.get(code);
  }

  private StatusMessagesGenerated() {}
}
