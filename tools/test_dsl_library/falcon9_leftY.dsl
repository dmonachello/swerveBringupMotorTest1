test "falcon9_leftY"

device "FALCON 9"
device "controller0"

main:
	set "FALCON 9".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0

	until timer.elapsed >= 10.0

