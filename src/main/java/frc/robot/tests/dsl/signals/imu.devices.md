# Device Type: imu

## Function

- Inertial measurement devices used for orientation evidence without commanding motion directly.

## Details

- Use this for configured devices whose logical DSL type resolves to `imu`, such as `Pigeon`.
- `yaw`, `pitch`, and `roll` are live absolute readings from the runtime snapshot.
- `yaw_delta`, `pitch_delta`, and `roll_delta` compare the current reading to the value captured at test start.
- Aggregate signals such as `yaw_delta_max_abs` prove that orientation changed sometime during the run.
- `angular_velocity_x`, `angular_velocity_y`, and `angular_velocity_z` are device-frame angular rates in degrees per second.
- `accel_x`, `accel_y`, and `accel_z` are accelerometer readings in G.
- `supply_voltage` reports the IMU supply rail in volts.
- `faults` is true when active or sticky IMU faults are reported and may be cleared with `clear "device".faults`.

## Examples

device "pigeon 2"

main:
    until timer.elapsed >= 2.0
    require "pigeon 2".yaw_delta_max_abs > 5.0

test "pigeon_static_sanity"
device "pigeon 2"

main:
    until timer.elapsed >= 0.5
    require "pigeon 2".angular_velocity_z < 2.0
    require "pigeon 2".accel_z > 0.7
    require "pigeon 2".supply_voltage > 10.0
    require "pigeon 2".faults == false
