test "spark25_leftY"

device "SPARKMAX/NEO 25"
device "controller0"

main:
	set "SPARKMAX/NEO 25".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0

	until timer.elapsed >= 10.0

