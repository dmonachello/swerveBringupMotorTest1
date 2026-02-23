-- FRC CAN extended-ID post-dissector for Wireshark
-- Adds manufacturer, device type, API class/index, and device ID fields.
-- Place in %APPDATA%\Wireshark\plugins and restart Wireshark.

local frccan = Proto("frccan", "FRC CAN (Ext ID)")

local f_ext = ProtoField.bool("frccan.extended", "Extended ID", base.NONE)
local f_mfg = ProtoField.uint8("frccan.manufacturer", "Manufacturer", base.DEC)
local f_mfg_name = ProtoField.string("frccan.manufacturer_name", "Manufacturer Name")
local f_dtype = ProtoField.uint8("frccan.device_type", "Device Type", base.DEC)
local f_dtype_name = ProtoField.string("frccan.device_type_name", "Device Type Name")
local f_apic = ProtoField.uint8("frccan.api_class", "API Class", base.DEC)
local f_apic_name = ProtoField.string("frccan.api_class_name", "API Class Name (FRC Example)")
local f_apix = ProtoField.uint8("frccan.api_index", "API Index", base.DEC)
local f_apix_name = ProtoField.string("frccan.api_index_name", "API Index Name (FRC Example)")
local f_did = ProtoField.uint8("frccan.device_id", "Device ID", base.DEC)

frccan.fields = {
    f_ext,
    f_mfg,
    f_mfg_name,
    f_dtype,
    f_dtype_name,
    f_apic,
    f_apic_name,
    f_apix,
    f_apix_name,
    f_did,
}

local MFG_NAMES = {
    [0] = "Broadcast",
    [1] = "NI",
    [2] = "LuminaryMicro",
    [3] = "DEKA",
    [4] = "CTRE",
    [5] = "REV",
    [6] = "Grapple",
    [7] = "MindSensors",
    [8] = "TeamUse",
    [9] = "KauaiLabs",
    [10] = "Copperforge",
    [11] = "PlayingWithFusion",
    [12] = "Studica",
    [13] = "TheThriftyBot",
    [14] = "ReduxRobotics",
    [15] = "AndyMark",
    [16] = "VividHosting",
    [17] = "VertosRobotics",
    [18] = "SWYFTRobotics",
    [19] = "LumynLabs",
    [20] = "BrushlandLabs",
}

local DEVICE_TYPE_NAMES = {
    [0] = "BroadcastMessages",
    [1] = "RobotController",
    [2] = "MotorController",
    [3] = "RelayController",
    [4] = "GyroSensor",
    [5] = "Accelerometer",
    [6] = "DistanceSensor",
    [7] = "Encoder",
    [8] = "PowerDistributionModule",
    [9] = "PneumaticsController",
    [10] = "Miscellaneous",
    [11] = "IOBreakout",
    [12] = "ServoController",
    [13] = "ColorSensor",
    [31] = "FirmwareUpdate",
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

local function field_new(name)
    local ok, f = pcall(Field.new, name)
    if ok then
        return f
    end
    return nil
end

local can_id_f = field_new("can.id") or field_new("can.arbitration_id")

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

    local subtree = tree:add(frccan, "FRC CAN (Ext ID)")
    subtree:add(f_ext, true)
    subtree:add(f_mfg, manufacturer)
    subtree:add(f_mfg_name, MFG_NAMES[manufacturer] or "Unknown")
    subtree:add(f_dtype, device_type)
    subtree:add(f_dtype_name, DEVICE_TYPE_NAMES[device_type] or "Unknown")
    subtree:add(f_apic, api_class)
    if device_type == 2 then
        subtree:add(f_apic_name, API_CLASS_NAMES[api_class] or "Unknown")
    end
    subtree:add(f_apix, api_index)
    if device_type == 2 and api_class == 1 then
        subtree:add(f_apix_name, API_INDEX_SPEED[api_index] or "Unknown")
    end
    subtree:add(f_did, device_id)

    -- Optional: add a brief hint in the Info column
    pinfo.cols.info:append(string.format("  FRC mfg=%d type=%d id=%d", manufacturer, device_type, device_id))
end

register_postdissector(frccan)
