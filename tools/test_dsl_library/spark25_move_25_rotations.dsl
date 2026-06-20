test "spark25_move_25_rotations"

device "SPARKMAX/NEO 25"

main:
	set "SPARKMAX/NEO 25".output_percent_cmd = 0.25

	until "SPARKMAX/NEO 25".position_delta > 25.0
	require "SPARKMAX/NEO 25".velocity_actual > 50
	require "SPARKMAX/NEO 25".current_actual > 0.5
	abort "SPARKMAX/NEO 25".current_actual > 30


