test "motors_to_limit"

device "FALCON 9"
device "lmtSw0"
device "SPARKMAX/NEO 25"

main:
	set "FALCON 9".output_percent_cmd = 0.15

	set "SPARKMAX/NEO 25".output_percent_cmd = 0.15

	abort "SPARKMAX/NEO 25".current_actual > 40
	abort "FALCON 9".current_actual > 40

	success lmtSw0.pressed
	until timer.elapsed >= 3.0



