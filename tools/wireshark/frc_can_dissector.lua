-- FRC CAN extended-ID post-dissector for Wireshark
-- Adds manufacturer, device type, API class/index, and device ID fields.
-- Place in %APPDATA%\Wireshark\plugins and restart Wireshark.

-- Toggle: set to false to disable vendor-specific payload decoding.
local ENABLE_VENDOR_DECODE = true

local frccan = Proto("frccan", "FRC CAN (Ext ID)")

local f_ext = ProtoField.bool("frccan.extended", "Extended ID", base.NONE)
local f_arb = ProtoField.uint32("frccan.arb_id", "Arbitration ID", base.HEX)
local f_mfg = ProtoField.uint8("frccan.manufacturer", "Manufacturer", base.DEC)
local f_mfg_name = ProtoField.string("frccan.manufacturer_name", "Manufacturer Name")
local f_dtype = ProtoField.uint8("frccan.device_type", "Device Type", base.DEC)
local f_dtype_name = ProtoField.string("frccan.device_type_name", "Device Type Name")
local f_apic = ProtoField.uint8("frccan.api_class", "API Class", base.DEC)
local f_apic_name = ProtoField.string("frccan.api_class_name", "API Class Name (FRC Example)")
local f_apix = ProtoField.uint8("frccan.api_index", "API Index", base.DEC)
local f_apix_name = ProtoField.string("frccan.api_index_name", "API Index Name (FRC Example)")
local f_did = ProtoField.uint8("frccan.device_id", "Device ID", base.DEC)
local f_rtr = ProtoField.bool("frccan.rtr", "Remote Transmission Request", base.NONE)
local f_broadcast = ProtoField.bool("frccan.is_broadcast", "Broadcast Message", base.NONE)
local f_heartbeat = ProtoField.bool("frccan.is_heartbeat", "RoboRIO Heartbeat", base.NONE)

-- REV SPARK MAX/FLEX (unverified payload decode)
local f_rev_applied_out   = ProtoField.float("frccan.rev.applied_output", "REV Applied Output (Unverified)")
local f_rev_faults        = ProtoField.uint16("frccan.rev.faults", "REV Faults (Unverified)", base.HEX)
local f_rev_sticky_faults = ProtoField.uint16("frccan.rev.sticky_faults", "REV Sticky Faults (Unverified)", base.HEX)
local f_rev_is_follower   = ProtoField.bool("frccan.rev.is_follower", "REV Is Follower (Unverified)", 16, nil, 0x8000)
local f_rev_velocity      = ProtoField.float("frccan.rev.velocity", "REV Velocity RPM (Unverified)")
local f_rev_temp          = ProtoField.uint8("frccan.rev.temp", "REV Temperature C (Unverified)", base.DEC)
local f_rev_voltage_raw   = ProtoField.uint16("frccan.rev.voltage_raw", "REV Voltage Raw (Unverified)", base.DEC)
local f_rev_current_raw   = ProtoField.uint16("frccan.rev.current_raw", "REV Current Raw (Unverified)", base.DEC)
local f_rev_position      = ProtoField.float("frccan.rev.position", "REV Position Rotations (Unverified)")
local f_rev_analog_volt   = ProtoField.uint16("frccan.rev.analog_voltage", "REV Analog Voltage Raw (Unverified)", base.DEC)
local f_rev_analog_vel    = ProtoField.uint32("frccan.rev.analog_velocity", "REV Analog Velocity Raw (Unverified)", base.DEC)
local f_rev_analog_pos    = ProtoField.float("frccan.rev.analog_position", "REV Analog Position (Unverified)")
local f_rev_alt_vel       = ProtoField.float("frccan.rev.alt_velocity", "REV Alt Encoder Velocity (Unverified)")
local f_rev_alt_pos       = ProtoField.float("frccan.rev.alt_position", "REV Alt Encoder Position (Unverified)")
local f_rev_duty_pos      = ProtoField.float("frccan.rev.duty_position", "REV Duty Abs Position (Unverified)")
local f_rev_duty_angle    = ProtoField.uint16("frccan.rev.duty_angle", "REV Duty Angle Raw (Unverified)", base.DEC)
local f_rev_duty_vel      = ProtoField.float("frccan.rev.duty_velocity", "REV Duty Velocity (Unverified)")
local f_rev_duty_freq     = ProtoField.uint16("frccan.rev.duty_freq", "REV Duty Frequency Hz (Unverified)", base.DEC)

-- CTRE Phoenix (unverified payload decode)
local f_ctre_func_code = ProtoField.uint8("frccan.ctre.func_code", "CTRE Function Code (Unverified)", base.HEX, {
    [0x45] = "Read Parameter(s)",
    [0x46] = "Write Parameter(s)",
    [0x47] = "System Commands",
    [0x50] = "Digital Control"
})
local f_ctre_dig_pot   = ProtoField.uint8("frccan.ctre.digital_pot", "CTRE Digital Pot/Throttle (Unverified)", base.DEC)
local f_ctre_dig_btn   = ProtoField.uint8("frccan.ctre.digital_buttons", "CTRE Digital Buttons (Unverified)", base.HEX)
local f_ctre_dig_mode  = ProtoField.uint8("frccan.ctre.digital_mode", "CTRE Digital Mode (Unverified)", base.HEX)
local f_ctre_out_curr  = ProtoField.uint8("frccan.ctre.output_current", "CTRE Output Current A (Unverified)", base.DEC)
local f_ctre_pwm_out   = ProtoField.uint8("frccan.ctre.pwm_output", "CTRE PWM Output 0-255 (Unverified)", base.DEC)
local f_ctre_act_lim   = ProtoField.uint8("frccan.ctre.active_limit", "CTRE Active Current Limit (Unverified)", base.DEC)
local f_ctre_temp      = ProtoField.uint8("frccan.ctre.temp", "CTRE Temperature C (Unverified)", base.DEC)
local f_ctre_supply_v  = ProtoField.float("frccan.ctre.supply_v", "CTRE Supply Voltage V (Unverified)")
local f_ctre_soc       = ProtoField.uint8("frccan.ctre.soc", "CTRE State Of Charge % (Unverified)", base.DEC)
local f_ctre_sys_state = ProtoField.uint8("frccan.ctre.sys_state", "CTRE System State (Unverified)", base.HEX)
local f_ctre_mot_state = ProtoField.uint8("frccan.ctre.mot_state", "CTRE Motor State (Unverified)", base.HEX)
local f_ctre_com_alarm = ProtoField.uint8("frccan.ctre.comm_alarms", "CTRE Comm Alarms (Unverified)", base.HEX)
local f_ctre_chg_mode  = ProtoField.uint8("frccan.ctre.charge_mode", "CTRE Charge Mode (Unverified)", base.HEX)
local f_ctre_fault     = ProtoField.uint8("frccan.ctre.fault_code", "CTRE Fault Code (Unverified)", base.HEX)
local f_ctre_thr_anlg  = ProtoField.uint16("frccan.ctre.throttle_analog", "CTRE Throttle Analog mV (Unverified)", base.DEC)
local f_ctre_thr_cmd   = ProtoField.uint8("frccan.ctre.throttle_cmd", "CTRE Throttle Command (Unverified)", base.DEC)
local f_ctre_anlg_in   = ProtoField.uint16("frccan.ctre.analog_in_v", "CTRE Analog In mV (Unverified)", base.DEC)
local f_ctre_act_rpm   = ProtoField.uint16("frccan.ctre.actual_rpm", "CTRE Actual RPM (Unverified)", base.DEC)
local f_ctre_tgt_rpm   = ProtoField.uint16("frccan.ctre.target_rpm", "CTRE Target RPM (Unverified)", base.DEC)
local f_ctre_misc_stat = ProtoField.uint8("frccan.ctre.misc_status", "CTRE Misc Status (Unverified)", base.HEX)
local f_ctre_aux_stat  = ProtoField.uint8("frccan.ctre.aux_status", "CTRE Aux Status (Unverified)", base.HEX)

frccan.fields = {
    f_ext,
    f_arb,
    f_mfg,
    f_mfg_name,
    f_dtype,
    f_dtype_name,
    f_apic,
    f_apic_name,
    f_apix,
    f_apix_name,
    f_did,
    f_rtr,
    f_broadcast,
    f_heartbeat,
    f_rev_applied_out,
    f_rev_faults,
    f_rev_sticky_faults,
    f_rev_is_follower,
    f_rev_velocity,
    f_rev_temp,
    f_rev_voltage_raw,
    f_rev_current_raw,
    f_rev_position,
    f_rev_analog_volt,
    f_rev_analog_vel,
    f_rev_analog_pos,
    f_rev_alt_vel,
    f_rev_alt_pos,
    f_rev_duty_pos,
    f_rev_duty_angle,
    f_rev_duty_vel,
    f_rev_duty_freq,
    f_ctre_func_code,
    f_ctre_dig_pot,
    f_ctre_dig_btn,
    f_ctre_dig_mode,
    f_ctre_out_curr,
    f_ctre_pwm_out,
    f_ctre_act_lim,
    f_ctre_temp,
    f_ctre_supply_v,
    f_ctre_soc,
    f_ctre_sys_state,
    f_ctre_mot_state,
    f_ctre_com_alarm,
    f_ctre_chg_mode,
    f_ctre_fault,
    f_ctre_thr_anlg,
    f_ctre_thr_cmd,
    f_ctre_anlg_in,
    f_ctre_act_rpm,
    f_ctre_tgt_rpm,
    f_ctre_misc_stat,
    f_ctre_aux_stat,
}

local MFG_NAMES = {
    [0] = "Broadcast",
    [1] = "NI",
    [2] = "Luminary Micro",
    [3] = "DEKA",
    [4] = "CTR Electronics",
    [5] = "REV Robotics",
    [6] = "Grapple",
    [7] = "MindSensors",
    [8] = "Team Use",
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

local DEVICE_TYPE_NAMES = {
    [0] = "Broadcast Messages",
    [1] = "Robot Controller",
    [2] = "Motor Controller",
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
    [31] = "Firmware Update",
}

-- FRC CAN documentation provides example API class/index meanings for motor controllers.
local API_CLASS_NAMES = {
    [0] = "Voltage Control Mode",
    [1] = "Speed Control Mode",
    [2] = "Voltage Compensation Mode",
    [3] = "Position Control Mode",
    [4] = "Current Control Mode",
    [5] = "Status",
    [6] = "Periodic Status",
    [7] = "Configuration",
    [8] = "Ack",
}

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

local HEARTBEAT_CAN_ID = 0x01011840

local function field_new(name)
    local ok, f = pcall(Field.new, name)
    if ok then
        return f
    end
    return nil
end

local can_id_f = field_new("can.id") or field_new("can.arbitration_id")
local can_rtr_f = field_new("can.flags.rtr") or field_new("can.rtr")

function frccan.dissector(tvb, pinfo, tree)
    local can_id = can_id_f()
    if not can_id then
        return
    end
    if not can_id_f then
        return
    end

    local arb = tonumber(can_id.value)
    if not arb then
        return
    end

    if arb <= 0x7FF then
        return
    end

    local device_type = bit.rshift(bit.band(arb, 0x1F000000), 24)
    local manufacturer = bit.rshift(bit.band(arb, 0x00FF0000), 16)
    local api_class = bit.rshift(bit.band(arb, 0x0000FC00), 10)
    local api_index = bit.rshift(bit.band(arb, 0x000003C0), 6)
    local device_id = bit.band(arb, 0x0000003F)
    local is_broadcast = (device_type == 0 and manufacturer == 0 and api_class == 0)
    local is_heartbeat = (arb == HEARTBEAT_CAN_ID)

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
    if device_type == 2 and api_class == 1 then
        subtree:add(f_apix_name, API_INDEX_SPEED[api_index] or "Unknown")
    end
    if is_broadcast then
        subtree:add(f_apix_name, BROADCAST_API_INDEX[api_index] or "Unknown")
    end
    subtree:add(f_did, device_id)
    subtree:add(f_broadcast, is_broadcast)
    subtree:add(f_heartbeat, is_heartbeat)
    if can_rtr_f then
        local rtr_val = can_rtr_f()
        if rtr_val then
            subtree:add(f_rtr, rtr_val.value)
        end
    end

    if ENABLE_VENDOR_DECODE then
        -- REV SPARK MAX/FLEX payload decode (Unverified)
        if manufacturer == 5 and device_type == 2 and api_class == 6 then
            local rev_tree = subtree:add("REV Status (Unverified)")
            if api_index == 0 and tvb:len() >= 6 then
                local applied_out_raw = tvb(0,2):le_int()
                rev_tree:add(f_rev_applied_out, tvb(0,2), applied_out_raw / 32767.0)
                rev_tree:add_le(f_rev_faults, tvb(2,2))
                rev_tree:add_le(f_rev_is_follower, tvb(2,2))
                rev_tree:add_le(f_rev_sticky_faults, tvb(4,2))
            elseif api_index == 1 and tvb:len() >= 8 then
                rev_tree:add_le(f_rev_velocity, tvb(0,4))
                rev_tree:add(f_rev_temp, tvb(4,1))
                local v_c_raw = tvb(5,3):le_uint()
                local volt_raw = bit.band(v_c_raw, 0xFFF)
                local curr_raw = bit.band(bit.rshift(v_c_raw, 12), 0xFFF)
                rev_tree:add(f_rev_voltage_raw, tvb(5,3), volt_raw)
                rev_tree:add(f_rev_current_raw, tvb(5,3), curr_raw)
            elseif api_index == 2 and tvb:len() >= 4 then
                rev_tree:add_le(f_rev_position, tvb(0,4))
            elseif api_index == 3 and tvb:len() >= 8 then
                local v_v_raw = tvb(0,4):le_uint()
                local a_volt_raw = bit.band(v_v_raw, 0x3FF)
                local a_vel_raw = bit.band(bit.rshift(v_v_raw, 10), 0x3FFFFF)
                rev_tree:add(f_rev_analog_volt, tvb(0,4), a_volt_raw)
                rev_tree:add(f_rev_analog_vel, tvb(0,4), a_vel_raw)
                rev_tree:add_le(f_rev_analog_pos, tvb(4,4))
            elseif api_index == 4 and tvb:len() >= 8 then
                rev_tree:add_le(f_rev_alt_vel, tvb(0,4))
                rev_tree:add_le(f_rev_alt_pos, tvb(4,4))
            elseif api_index == 5 and tvb:len() >= 6 then
                rev_tree:add_le(f_rev_duty_pos, tvb(0,4))
                rev_tree:add_le(f_rev_duty_angle, tvb(4,2))
            elseif api_index == 6 and tvb:len() >= 6 then
                rev_tree:add_le(f_rev_duty_vel, tvb(0,4))
                rev_tree:add_le(f_rev_duty_freq, tvb(4,2))
            end
        end

        -- CTRE Phoenix payload decode (Unverified, J1939-style PF/PS)
        local pf = bit.band(bit.rshift(arb, 16), 0xFF)
        local ps = bit.band(bit.rshift(arb, 8), 0xFF)
        local is_control = (pf == 0xEF)
        local is_status = (pf == 0xFF and ps <= 0x07)
        if is_control or is_status then
            local ctre_tree = subtree:add("CTRE Status (Unverified)")
            if is_control and tvb:len() > 0 then
                local func_val = tvb(0,1):uint()
                ctre_tree:add(f_ctre_func_code, tvb(0,1))
                if func_val == 0x50 and tvb:len() >= 4 then
                    ctre_tree:add(f_ctre_dig_pot, tvb(1,1))
                    ctre_tree:add(f_ctre_dig_btn, tvb(2,1))
                    ctre_tree:add(f_ctre_dig_mode, tvb(3,1))
                end
            elseif is_status then
                local payload_tree = ctre_tree:add("CTRE Status Payload (Unverified)")
                if ps == 0x00 and tvb:len() >= 5 then
                    payload_tree:add(f_ctre_out_curr, tvb(1,1))
                    payload_tree:add(f_ctre_pwm_out, tvb(2,1))
                    payload_tree:add(f_ctre_act_lim, tvb(4,1))
                elseif ps == 0x01 and tvb:len() >= 4 then
                    payload_tree:add(f_ctre_temp, tvb(0,1))
                    local v_raw = tvb(1,1):uint()
                    payload_tree:add(f_ctre_supply_v, tvb(1,1), v_raw / 4.0)
                    payload_tree:add(f_ctre_soc, tvb(3,1))
                elseif ps == 0x03 and tvb:len() >= 8 then
                    payload_tree:add(f_ctre_sys_state, tvb(0,1))
                    payload_tree:add(f_ctre_mot_state, tvb(1,1))
                    payload_tree:add(f_ctre_com_alarm, tvb(2,1))
                    payload_tree:add(f_ctre_chg_mode, tvb(3,1))
                    payload_tree:add(f_ctre_fault, tvb(4,1))
                elseif ps == 0x04 and tvb:len() >= 6 then
                    payload_tree:add_le(f_ctre_thr_anlg, tvb(0,2))
                    payload_tree:add(f_ctre_thr_cmd, tvb(2,1))
                    payload_tree:add_le(f_ctre_anlg_in, tvb(4,2))
                elseif ps == 0x05 and tvb:len() >= 4 then
                    payload_tree:add_le(f_ctre_act_rpm, tvb(0,2))
                    payload_tree:add_le(f_ctre_tgt_rpm, tvb(2,2))
                elseif ps == 0x06 and tvb:len() >= 6 then
                    payload_tree:add(f_ctre_misc_stat, tvb(4,1))
                    payload_tree:add(f_ctre_aux_stat, tvb(5,1))
                elseif ps == 0x02 or ps == 0x07 then
                    payload_tree:add(tvb(0, tvb:len()), "CTRE Custom Status (Unverified)")
                end
            end
        end
    end

    -- Optional: add a brief hint in the Info column
    local mfg_name = MFG_NAMES[manufacturer] or "Unknown"
    local type_name = DEVICE_TYPE_NAMES[device_type] or "Unknown"
    pinfo.cols.info:append(string.format("  FRC %s/%s id=%d", mfg_name, type_name, device_id))
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
