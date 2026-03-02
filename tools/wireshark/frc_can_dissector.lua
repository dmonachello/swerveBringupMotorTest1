-- FRC CAN extended-ID post-dissector for Wireshark.
-- Adds manufacturer, device type, API class/index, and device ID fields.
-- Includes optional vendor payload decoding (REV + CTRE) marked UNVERIFIED.
-- Place in %APPDATA%\Wireshark\plugins and restart Wireshark.
-- Toggle: set to false to disable vendor-specific payload decoding.
--
-- Notes:
-- - This is a post-dissector: it never transmits CAN frames and never alters data.
-- - All payload field meanings here are hypotheses unless confirmed by controlled tests.
-- - The FRC extended CAN ID is 29 bits. This dissector masks and parses that layout.
-- - Keep additions additive; never remove existing keys/fields once documented.
-- - This file is intentionally verbose as a learning tool.
--
-- How to extend this file:
-- 1) Add new constants for the IDs you care about (manufacturer, device type, API class).
-- 2) Add new ProtoFields for payload bytes you want to display.
-- 3) Add decode logic inside the ENABLE_VENDOR_DECODE block and gate it tightly.
-- 4) Update CAN_BACKGROUND.md with any new assumptions or hypotheses.

local ENABLE_VENDOR_DECODE = true

local frccan = Proto("frccan", "FRC CAN (Ext ID)")

-- Core header fields (FRC extended ID).
-- These are derived from the 29-bit arbitration ID.
local f_ext = ProtoField.bool("frccan.extended", "Extended ID", base.NONE) -- Indicates 29-bit ID.
local f_arb = ProtoField.uint32("frccan.arb_id", "Arbitration ID", base.HEX) -- Full 29-bit ID in hex.
local f_mfg = ProtoField.uint8("frccan.manufacturer", "Manufacturer", base.DEC) -- Manufacturer field (8-bit).
local f_mfg_name = ProtoField.string("frccan.manufacturer_name", "Manufacturer Name") -- Friendly lookup name.
local f_dtype = ProtoField.uint8("frccan.device_type", "Device Type", base.DEC) -- Device type field (5-bit).
local f_dtype_name = ProtoField.string("frccan.device_type_name", "Device Type Name") -- Friendly lookup name.
local f_apic = ProtoField.uint8("frccan.api_class", "API Class", base.DEC) -- API class field (6-bit).
local f_apic_name = ProtoField.string("frccan.api_class_name", "API Class Name (FRC Example)") -- Friendly lookup name.
local f_apix = ProtoField.uint8("frccan.api_index", "API Index", base.DEC) -- API index field (4-bit).
local f_apix_name = ProtoField.string("frccan.api_index_name", "API Index Name (FRC Example)") -- Friendly lookup name.
local f_did = ProtoField.uint8("frccan.device_id", "Device ID", base.DEC) -- Device ID field (6-bit).
local f_rtr = ProtoField.bool("frccan.rtr", "Remote Transmission Request", base.NONE) -- RTR flag if present.
local f_broadcast = ProtoField.bool("frccan.is_broadcast", "Broadcast Message", base.NONE) -- Broadcast/system message marker.
local f_heartbeat = ProtoField.bool("frccan.is_heartbeat", "RoboRIO Heartbeat", base.NONE) -- Heartbeat frame marker.

-- J1939-style PF/PS fields used by CTRE Phoenix protocol (Unverified).
-- We show these for visibility even when the FRC fields are also decoded.
local f_pf = ProtoField.uint8("frccan.j1939_pf", "J1939 Protocol Format (PF)", base.HEX) -- J1939 PF (8-bit).
local f_ps = ProtoField.uint8("frccan.j1939_ps", "J1939 Protocol Specific (PS)", base.HEX) -- J1939 PS (8-bit).

-- Common numeric constants for readability.
-- Masks are applied to the 29-bit arbitration ID.
local STANDARD_CAN_MAX_ID = 0x7FF -- Any ID <= 0x7FF is a standard 11-bit CAN ID.
local MASK_DEVICE_TYPE = 0x1F000000 -- Bits 28:24 (device type).
local MASK_MFG = 0x00FF0000 -- Bits 23:16 (manufacturer).
local MASK_API_CLASS = 0x0000FC00 -- Bits 15:10 (API class).
local MASK_API_INDEX = 0x000003C0 -- Bits 9:6 (API index).
local MASK_DEVICE_ID = 0x0000003F -- Bits 5:0 (device ID).

-- FRC manufacturer IDs (from published CAN IDs; keep in sync with docs).
local MFG_BROADCAST = 0 -- Special value for broadcast/system frames.
local MFG_CTRE = 4 -- CTRE (Talon FX, CANcoder, CANdle, etc.).
local MFG_REV = 5 -- REV (Spark MAX, Spark Flex, etc.).

-- FRC device types.
local DEVTYPE_BROADCAST = 0 -- Broadcast/system message.
local DEVTYPE_MOTOR_CONTROLLER = 2 -- Generic motor controller type.

-- API class values used in this dissector.
local API_CLASS_BROADCAST = 0 -- Broadcast/system API class.
local API_CLASS_SPEED = 1 -- Example: speed control class.
local API_CLASS_PERIODIC_STATUS = 6 -- Periodic status frames.

-- J1939 PF/PS values used by CTRE (Unverified).
local J1939_PF_CONTROL = 0xEF -- CTRE control PDU1 (destination specific).
local J1939_PF_STATUS = 0xFF -- CTRE status PDU2 (broadcast status pages).
local J1939_STATUS_PS_MAX = 0x07 -- Status pages 0x00..0x07.

-- REV periodic status frame index values (Unverified).
-- These correspond to "Periodic Status 0..6" used by Spark MAX / Flex devices.
local REV_STATUS_0 = 0 -- Applied output + faults.
local REV_STATUS_1 = 1 -- Velocity + temp + raw voltage/current.
local REV_STATUS_2 = 2 -- Position.
local REV_STATUS_3 = 3 -- Analog sensor packed fields.
local REV_STATUS_4 = 4 -- Alternate encoder.
local REV_STATUS_5 = 5 -- Duty-cycle absolute position.
local REV_STATUS_6 = 6 -- Duty-cycle velocity/frequency.

-- CTRE J1939 status page values (Unverified).
-- These are PF=0xFF and PS=0x00..0x07.
local CTRE_STATUS_0 = 0x00 -- FF00 Motor drive status.
local CTRE_STATUS_1 = 0x01 -- FF01 Monitor status.
local CTRE_STATUS_2 = 0x02 -- FF02 Custom/unknown status.
local CTRE_STATUS_3 = 0x03 -- FF03 System status.
local CTRE_STATUS_4 = 0x04 -- FF04 Throttle status.
local CTRE_STATUS_5 = 0x05 -- FF05 Speed status.
local CTRE_STATUS_6 = 0x06 -- FF06 Digital control status.
local CTRE_STATUS_7 = 0x07 -- FF07 Custom/unknown status.

-- REV SPARK MAX/FLEX (unverified payload decode)
-- These fields are added only when we identify a REV periodic status frame.
local f_rev_applied_out = ProtoField.float("frccan.rev.applied_output", "REV Applied Output (Unverified)") -- Applied duty/output.
local f_rev_faults = ProtoField.uint16("frccan.rev.faults", "REV Faults (Unverified)", base.HEX) -- Fault bitmask.
local f_rev_sticky_faults = ProtoField.uint16("frccan.rev.sticky_faults", "REV Sticky Faults (Unverified)", base.HEX) -- Sticky fault bitmask.
local f_rev_is_follower = ProtoField.bool("frccan.rev.is_follower", "REV Is Follower (Unverified)", 16, nil, 0x8000) -- Bit inside faults word.
local f_rev_velocity = ProtoField.float("frccan.rev.velocity", "REV Velocity RPM (Unverified)") -- Velocity from encoder.
local f_rev_temp = ProtoField.uint8("frccan.rev.temp", "REV Temperature C (Unverified)", base.DEC) -- Device temperature.
local f_rev_voltage_raw = ProtoField.uint16("frccan.rev.voltage_raw", "REV Voltage Raw (Unverified)", base.DEC) -- 12-bit packed voltage.
local f_rev_current_raw = ProtoField.uint16("frccan.rev.current_raw", "REV Current Raw (Unverified)", base.DEC) -- 12-bit packed current.
local f_rev_position = ProtoField.float("frccan.rev.position", "REV Position Rotations (Unverified)") -- Position in rotations.
local f_rev_analog_volt = ProtoField.uint16("frccan.rev.analog_voltage", "REV Analog Voltage Raw (Unverified)", base.DEC) -- 10-bit analog voltage.
local f_rev_analog_vel = ProtoField.uint32("frccan.rev.analog_velocity", "REV Analog Velocity Raw (Unverified)", base.DEC) -- 22-bit analog velocity.
local f_rev_analog_pos = ProtoField.float("frccan.rev.analog_position", "REV Analog Position (Unverified)") -- Analog position/velocity.
local f_rev_alt_vel = ProtoField.float("frccan.rev.alt_velocity", "REV Alt Encoder Velocity (Unverified)") -- Alt encoder velocity.
local f_rev_alt_pos = ProtoField.float("frccan.rev.alt_position", "REV Alt Encoder Position (Unverified)") -- Alt encoder position.
local f_rev_duty_pos = ProtoField.float("frccan.rev.duty_position", "REV Duty Abs Position (Unverified)") -- Duty cycle abs position.
local f_rev_duty_angle = ProtoField.uint16("frccan.rev.duty_angle", "REV Duty Angle Raw (Unverified)", base.DEC) -- Raw angle.
local f_rev_duty_vel = ProtoField.float("frccan.rev.duty_velocity", "REV Duty Velocity (Unverified)") -- Duty cycle velocity.
local f_rev_duty_freq = ProtoField.uint16("frccan.rev.duty_freq", "REV Duty Frequency Hz (Unverified)", base.DEC) -- Duty cycle frequency.

-- CTRE Phoenix (unverified payload decode)
-- These fields are added only when we identify CTRE PF/PS frames.
local f_ctre_func_code = ProtoField.uint8("frccan.ctre.func_code", "CTRE Function Code (Unverified)", base.HEX, {
    -- CTRE function codes observed in docs and community references.
    [0x45] = "Read Parameter(s)",
    [0x46] = "Write Parameter(s)",
    [0x47] = "System Commands",
    [0x50] = "Digital Control"
})
local f_ctre_dig_pot = ProtoField.uint8("frccan.ctre.digital_pot", "CTRE Digital Pot/Throttle (Unverified)", base.DEC) -- Throttle/digital pot.
local f_ctre_dig_btn = ProtoField.uint8("frccan.ctre.digital_buttons", "CTRE Digital Buttons (Unverified)", base.HEX) -- Digital buttons bitfield.
local f_ctre_dig_mode = ProtoField.uint8("frccan.ctre.digital_mode", "CTRE Digital Mode (Unverified)", base.HEX) -- Digital mode.
local f_ctre_out_curr = ProtoField.uint8("frccan.ctre.output_current", "CTRE Output Current A (Unverified)", base.DEC) -- Current in amps.
local f_ctre_pwm_out = ProtoField.uint8("frccan.ctre.pwm_output", "CTRE PWM Output 0-255 (Unverified)", base.DEC) -- Output duty scaled 0..255.
local f_ctre_act_lim = ProtoField.uint8("frccan.ctre.active_limit", "CTRE Active Current Limit (Unverified)", base.DEC) -- Current limit flag/value.
local f_ctre_temp = ProtoField.uint8("frccan.ctre.temp", "CTRE Temperature C (Unverified)", base.DEC) -- Temperature in C.
local f_ctre_supply_v = ProtoField.float("frccan.ctre.supply_v", "CTRE Supply Voltage V (Unverified)") -- Supply voltage (scaled).
local f_ctre_soc = ProtoField.uint8("frccan.ctre.soc", "CTRE State Of Charge % (Unverified)", base.DEC) -- Battery SOC.
local f_ctre_sys_state = ProtoField.uint8("frccan.ctre.sys_state", "CTRE System State (Unverified)", base.HEX) -- System state flags.
local f_ctre_mot_state = ProtoField.uint8("frccan.ctre.mot_state", "CTRE Motor State (Unverified)", base.HEX) -- Motor state flags.
local f_ctre_com_alarm = ProtoField.uint8("frccan.ctre.comm_alarms", "CTRE Comm Alarms (Unverified)", base.HEX) -- Comm alarm flags.
local f_ctre_chg_mode = ProtoField.uint8("frccan.ctre.charge_mode", "CTRE Charge Mode (Unverified)", base.HEX) -- Charge mode.
local f_ctre_fault = ProtoField.uint8("frccan.ctre.fault_code", "CTRE Fault Code (Unverified)", base.HEX) -- Fault code.
local f_ctre_thr_anlg = ProtoField.uint16("frccan.ctre.throttle_analog", "CTRE Throttle Analog mV (Unverified)", base.DEC) -- Analog throttle mV.
local f_ctre_thr_cmd = ProtoField.uint8("frccan.ctre.throttle_cmd", "CTRE Throttle Command (Unverified)", base.DEC) -- Throttle command.
local f_ctre_anlg_in = ProtoField.uint16("frccan.ctre.analog_in_v", "CTRE Analog In mV (Unverified)", base.DEC) -- Analog input mV.
local f_ctre_act_rpm = ProtoField.uint16("frccan.ctre.actual_rpm", "CTRE Actual RPM (Unverified)", base.DEC) -- Actual RPM.
local f_ctre_tgt_rpm = ProtoField.uint16("frccan.ctre.target_rpm", "CTRE Target RPM (Unverified)", base.DEC) -- Target RPM.
local f_ctre_misc_stat = ProtoField.uint8("frccan.ctre.misc_status", "CTRE Misc Status (Unverified)", base.HEX) -- Misc status.
local f_ctre_aux_stat = ProtoField.uint8("frccan.ctre.aux_status", "CTRE Aux Status (Unverified)", base.HEX) -- Aux status.

-- Register all fields with Wireshark for display.
frccan.fields = {
    f_ext, f_arb, f_mfg, f_mfg_name, f_dtype, f_dtype_name, f_apic, f_apic_name, f_apix, f_apix_name, f_did,
    f_rtr, f_broadcast, f_heartbeat, f_pf, f_ps,
    f_rev_applied_out, f_rev_faults, f_rev_sticky_faults, f_rev_is_follower, f_rev_velocity, f_rev_temp,
    f_rev_voltage_raw, f_rev_current_raw, f_rev_position, f_rev_analog_volt, f_rev_analog_vel, f_rev_analog_pos,
    f_rev_alt_vel, f_rev_alt_pos, f_rev_duty_pos, f_rev_duty_angle, f_rev_duty_vel, f_rev_duty_freq,
    f_ctre_func_code, f_ctre_dig_pot, f_ctre_dig_btn, f_ctre_dig_mode, f_ctre_out_curr, f_ctre_pwm_out,
    f_ctre_act_lim, f_ctre_temp, f_ctre_supply_v, f_ctre_soc, f_ctre_sys_state, f_ctre_mot_state,
    f_ctre_com_alarm, f_ctre_chg_mode, f_ctre_fault, f_ctre_thr_anlg, f_ctre_thr_cmd, f_ctre_anlg_in,
    f_ctre_act_rpm, f_ctre_tgt_rpm, f_ctre_misc_stat, f_ctre_aux_stat
}

-- Manufacturer lookup table (FRC spec values).
-- Keep this list up to date as new vendors are discovered.
local MFG_NAMES = {
    [0] = "Broadcast",            -- 0 is special: broadcast/system messages.
    [1] = "NI",                   -- National Instruments (roboRIO).
    [2] = "Luminary Micro",
    [3] = "DEKA",
    [4] = "CTR Electronics",      -- CTRE motor controllers, sensors, etc.
    [5] = "REV Robotics",         -- REV motor controllers, sensors, etc.
    [6] = "Grapple",
    [7] = "MindSensors",
    [8] = "Team Use",             -- For team-specific devices.
    [9] = "Kauai Labs",
    [10] = "Copperforge",
    [11] = "Playing With Fusion",
    [12] = "Studica",
    [13] = "The Thrifty Bot",
    [14] = "Redux Robotics",
    [15] = "AndyMark",
    [16] = "Vivid Hosting",
    [17] = "Vertos Robotics",
    [18] = "SWYFT Robotics",
    [19] = "Lumyn Labs",
    [20] = "Brushland Labs",
}

-- Device type lookup table (FRC spec values).
local DEVICE_TYPE_NAMES = {
    [0] = "Broadcast Messages",     -- Not a device; system broadcast.
    [1] = "Robot Controller",       -- roboRIO or equivalent.
    [2] = "Motor Controller",       -- Talon, Spark, etc.
    [3] = "Relay Controller",
    [4] = "Gyro Sensor",
    [5] = "Accelerometer",
    [6] = "Distance Sensor",
    [7] = "Encoder",
    [8] = "Power Distribution Module",
    [9] = "Pneumatics Controller",
    [10] = "Miscellaneous",
    [11] = "IO Breakout",
    [12] = "Servo Controller",
    [13] = "Color Sensor",
    [31] = "Firmware Update",       -- Special update channel.
}

-- API class lookup table for FRC CAN (example meanings).
-- Some classes are vendor-specific or device-specific; these are generic labels.
local API_CLASS_NAMES = {
    [0] = "Voltage Control Mode",   -- Example mode names.
    [1] = "Speed Control Mode",
    [2] = "Voltage Compensation Mode",
    [3] = "Position Control Mode",
    [4] = "Current Control Mode",
    [5] = "Status",
    [6] = "Periodic Status",
    [7] = "Configuration",
    [8] = "Ack",
}

-- Example API index meanings for motor-controller speed control mode.
-- These names are from FRC documentation examples and may not apply universally.
local API_INDEX_SPEED = {
    [0] = "Enable Control",
    [1] = "Disable Control",
    [2] = "Set Setpoint",
    [3] = "P Constant",
    [4] = "I Constant",
    [5] = "D Constant",
    [6] = "Set Reference",
    [7] = "Trusted Enable",
    [8] = "Trusted Set No Ack",
    [10] = "Trusted Set Setpoint No Ack",
    [11] = "Set Setpoint No Ack",
}

-- Broadcast API index meanings (system-level commands).
local BROADCAST_API_INDEX = {
    [0] = "Disable",
    [1] = "System Halt",
    [2] = "System Reset",
    [3] = "Device Assign",
    [4] = "Device Query",
    [5] = "Heartbeat",
    [6] = "Sync",
    [7] = "Update",
    [8] = "Firmware Version",
    [9] = "Enumerate",
    [10] = "System Resume",
}

-- Common heartbeat ID observed on the roboRIO (FRC CAN).
local HEARTBEAT_CAN_ID = 0x01011840

-- Wireshark can expose CAN ID fields under different names depending on version.
local function field_new(name)
    local ok, f = pcall(Field.new, name)
    if ok then return f end
    return nil
end

-- CAN ID and RTR flag may appear under different Wireshark field names.
local can_id_f = field_new("can.id") or field_new("can.arbitration_id")
local can_rtr_f = field_new("can.flags.rtr") or field_new("can.rtr")

function frccan.dissector(tvb, pinfo, tree)
    -- Resolve the CAN ID for this packet.
    local can_id = can_id_f()
    if not can_id then return end
    if not can_id_f then return end

    -- Convert the arbitration ID to a number and ignore standard (11-bit) IDs.
    local arb = tonumber(can_id.value)
    if not arb then return end
    if arb <= STANDARD_CAN_MAX_ID then return end

    -- Extract FRC addressing fields from the 29-bit ID.
    -- FRC extended ID layout (common convention):
    -- [28:24]=Device Type, [23:16]=Manufacturer, [15:10]=API Class,
    -- [9:6]=API Index, [5:0]=Device ID.
    local device_type = bit.rshift(bit.band(arb, MASK_DEVICE_TYPE), 24)
    local manufacturer = bit.rshift(bit.band(arb, MASK_MFG), 16)
    local api_class = bit.rshift(bit.band(arb, MASK_API_CLASS), 10)
    local api_index = bit.rshift(bit.band(arb, MASK_API_INDEX), 6)
    local device_id = bit.band(arb, MASK_DEVICE_ID)

    local is_broadcast = (device_type == DEVTYPE_BROADCAST and manufacturer == MFG_BROADCAST and api_class == API_CLASS_BROADCAST)
    local is_heartbeat = (arb == HEARTBEAT_CAN_ID)
    local pf = bit.band(bit.rshift(arb, 16), 0xFF)
    local ps = bit.band(bit.rshift(arb, 8), 0xFF)

    -- Build the main tree for this frame.
    local subtree = tree:add(frccan, "FRC CAN (Ext ID)")
    subtree:add(f_ext, true)
    subtree:add(f_arb, arb)
    subtree:add(f_mfg, manufacturer)
    subtree:add(f_mfg_name, MFG_NAMES[manufacturer] or "Unknown")
    subtree:add(f_dtype, device_type)
    subtree:add(f_dtype_name, DEVICE_TYPE_NAMES[device_type] or "Unknown")
    subtree:add(f_apic, api_class)
    subtree:add(f_apic_name, API_CLASS_NAMES[api_class] or "Unknown")
    subtree:add(f_apix, api_index)

    -- Add API index names only when we recognize the class/context.
    if device_type == DEVTYPE_MOTOR_CONTROLLER and api_class == API_CLASS_SPEED then
        subtree:add(f_apix_name, API_INDEX_SPEED[api_index] or "Unknown")
    end
    if is_broadcast then
        subtree:add(f_apix_name, BROADCAST_API_INDEX[api_index] or "Unknown")
    end

    subtree:add(f_did, device_id)
    subtree:add(f_broadcast, is_broadcast)
    subtree:add(f_heartbeat, is_heartbeat)

    -- J1939 PF/PS are useful for CTRE frames.
    if pf ~= 0x00 or ps ~= 0x00 then
        subtree:add(f_pf, pf)
        subtree:add(f_ps, ps)
    end

    -- Report Remote Transmission Request flag when available.
    if can_rtr_f then
        local rtr_val = can_rtr_f()
        if rtr_val then
            subtree:add(f_rtr, rtr_val.value)
        end
    end

    if ENABLE_VENDOR_DECODE then
        -- REV periodic status frames (unverified).
        if manufacturer == MFG_REV and device_type == DEVTYPE_MOTOR_CONTROLLER and api_class == API_CLASS_PERIODIC_STATUS then
            local rev_tree = subtree:add("REV Status (Unverified)")
            -- Status 0: applied output + faults.
            if api_index == REV_STATUS_0 and tvb:len() >= 6 then
                local applied_out_raw = tvb(0,2):le_int()
                rev_tree:add(f_rev_applied_out, tvb(0,2), applied_out_raw / 32767.0)
                rev_tree:add_le(f_rev_faults, tvb(2,2))
                rev_tree:add_le(f_rev_is_follower, tvb(2,2))
                rev_tree:add_le(f_rev_sticky_faults, tvb(4,2))
            -- Status 1: velocity + temp + raw voltage/current (packed).
            elseif api_index == REV_STATUS_1 and tvb:len() >= 8 then
                rev_tree:add_le(f_rev_velocity, tvb(0,4))
                rev_tree:add(f_rev_temp, tvb(4,1))
                local v_c_raw = tvb(5,3):le_uint()
                local volt_raw = bit.band(v_c_raw, 0xFFF)
                local curr_raw = bit.band(bit.rshift(v_c_raw, 12), 0xFFF)
                rev_tree:add(f_rev_voltage_raw, tvb(5,3), volt_raw)
                rev_tree:add(f_rev_current_raw, tvb(5,3), curr_raw)
            -- Status 2: position.
            elseif api_index == REV_STATUS_2 and tvb:len() >= 4 then
                rev_tree:add_le(f_rev_position, tvb(0,4))
            -- Status 3: analog sensor packed fields.
            elseif api_index == REV_STATUS_3 and tvb:len() >= 8 then
                local v_v_raw = tvb(0,4):le_uint()
                local a_volt_raw = bit.band(v_v_raw, 0x3FF)
                local a_vel_raw = bit.band(bit.rshift(v_v_raw, 10), 0x3FFFFF)
                rev_tree:add(f_rev_analog_volt, tvb(0,4), a_volt_raw)
                rev_tree:add(f_rev_analog_vel, tvb(0,4), a_vel_raw)
                rev_tree:add_le(f_rev_analog_pos, tvb(4,4))
            -- Status 4: alternate encoder.
            elseif api_index == REV_STATUS_4 and tvb:len() >= 8 then
                rev_tree:add_le(f_rev_alt_vel, tvb(0,4))
                rev_tree:add_le(f_rev_alt_pos, tvb(4,4))
            -- Status 5: duty-cycle absolute position.
            elseif api_index == REV_STATUS_5 and tvb:len() >= 6 then
                rev_tree:add_le(f_rev_duty_pos, tvb(0,4))
                rev_tree:add_le(f_rev_duty_angle, tvb(4,2))
            -- Status 6: duty-cycle velocity/frequency.
            elseif api_index == REV_STATUS_6 and tvb:len() >= 6 then
                rev_tree:add_le(f_rev_duty_vel, tvb(0,4))
                rev_tree:add_le(f_rev_duty_freq, tvb(4,2))
            end
        end

        local is_control = (pf == J1939_PF_CONTROL)
        local is_status = (pf == J1939_PF_STATUS and ps <= J1939_STATUS_PS_MAX)

        if is_control or is_status then
            -- CTRE J1939-style control/status frames (unverified).
            local ctre_tree = subtree:add("CTRE Status (Unverified)")
            if is_control and tvb:len() > 0 then
                -- Control frames: function code in byte 0.
                local func_val = tvb(0,1):uint()
                ctre_tree:add(f_ctre_func_code, tvb(0,1))
                -- Digital control payload (when function code indicates it).
                if func_val == 0x50 and tvb:len() >= 4 then
                    ctre_tree:add(f_ctre_dig_pot, tvb(1,1))
                    ctre_tree:add(f_ctre_dig_btn, tvb(2,1))
                    ctre_tree:add(f_ctre_dig_mode, tvb(3,1))
                end
            elseif is_status then
                local payload_tree = ctre_tree:add("CTRE Status Payload (Unverified)")
                -- Status FF00: motor drive status.
                if ps == CTRE_STATUS_0 and tvb:len() >= 5 then
                    payload_tree:add(f_ctre_out_curr, tvb(1,1))
                    payload_tree:add(f_ctre_pwm_out, tvb(2,1))
                    payload_tree:add(f_ctre_act_lim, tvb(4,1))
                -- Status FF01: monitor status.
                elseif ps == CTRE_STATUS_1 and tvb:len() >= 4 then
                    payload_tree:add(f_ctre_temp, tvb(0,1))
                    local v_raw = tvb(1,1):uint()
                    payload_tree:add(f_ctre_supply_v, tvb(1,1), v_raw / 4.0)
                    payload_tree:add(f_ctre_soc, tvb(3,1))
                -- Status FF03: system status.
                elseif ps == CTRE_STATUS_3 and tvb:len() >= 8 then
                    payload_tree:add(f_ctre_sys_state, tvb(0,1))
                    payload_tree:add(f_ctre_mot_state, tvb(1,1))
                    payload_tree:add(f_ctre_com_alarm, tvb(2,1))
                    payload_tree:add(f_ctre_chg_mode, tvb(3,1))
                    payload_tree:add(f_ctre_fault, tvb(4,1))
                -- Status FF04: throttle status.
                elseif ps == CTRE_STATUS_4 and tvb:len() >= 6 then
                    payload_tree:add_le(f_ctre_thr_anlg, tvb(0,2))
                    payload_tree:add(f_ctre_thr_cmd, tvb(2,1))
                    payload_tree:add_le(f_ctre_anlg_in, tvb(4,2))
                -- Status FF05: speed status.
                elseif ps == CTRE_STATUS_5 and tvb:len() >= 4 then
                    payload_tree:add_le(f_ctre_act_rpm, tvb(0,2))
                    payload_tree:add_le(f_ctre_tgt_rpm, tvb(2,2))
                -- Status FF06: digital control status.
                elseif ps == CTRE_STATUS_6 and tvb:len() >= 6 then
                    payload_tree:add(f_ctre_misc_stat, tvb(4,1))
                    payload_tree:add(f_ctre_aux_stat, tvb(5,1))
                -- Status FF02/FF07: custom or unknown payloads.
                elseif ps == CTRE_STATUS_2 or ps == CTRE_STATUS_7 then
                    payload_tree:add(tvb(0, tvb:len()), "CTRE Custom Status (Unverified)")
                end
            end
        elseif manufacturer == MFG_CTRE then
            -- CTRE frames that match the FRC manufacturer but not J1939 PF/PS patterns.
            local ctre_tree = subtree:add("CTRE FRC Message (Unverified)")
            ctre_tree:add(tvb(0, tvb:len()), "Undocumented/Proprietary CTRE FRC Payload")
        end
    end

    -- Short Info column hint (kept concise for readability).
    local mfg_name = MFG_NAMES[manufacturer] or "Unknown"
    local type_name = DEVICE_TYPE_NAMES[device_type] or "Unknown"

    pinfo.cols.info:append(string.format(" FRC %s/%s id=%d", mfg_name, type_name, device_id))

    if is_broadcast then
        pinfo.cols.info:append(" [BCAST]")
    end
    if is_heartbeat then
        pinfo.cols.info:append(" [HEARTBEAT]")
    end
    if can_rtr_f then
        local rtr_val = can_rtr_f()
        if rtr_val and rtr_val.value then
            pinfo.cols.info:append(" [RTR]")
        end
    end
end

register_postdissector(frccan)
