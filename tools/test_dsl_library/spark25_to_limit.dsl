test "spark25_to_limit"

device "SPARKMAX/NEO 25"
device "lmtSw0"

main:
	set "SPARKMAX/NEO 25".output_percent_cmd = 0.20


	abort "SPARKMAX/NEO 25".current_actual > 40

	success lmtSw0.pressed



