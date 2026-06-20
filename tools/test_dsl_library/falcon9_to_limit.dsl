test "falcon9_to_limit"

device "FALCON 9"
device "lmtSw0"

main:
	set "FALCON 9".output_percent_cmd = 0.20


	abort "FALCON 9".current_actual > 40

	success lmtSw0.pressed



