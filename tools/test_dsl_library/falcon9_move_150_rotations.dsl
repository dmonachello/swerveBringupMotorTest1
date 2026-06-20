test "falcon9_move_150_rotations"

device "FALCON 9"

main:
    set "FALCON 9".output_percent_cmd = 0.25

    abort "FALCON 9".current_actual > 40

    require "FALCON 9".position_delta > 10

    until "FALCON 9".position_delta > 150.0
    until timer.elapsed >= 60.0
