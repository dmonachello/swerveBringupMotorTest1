test "falcon9_xbox_controller_smoke"
device "FALCON 9"
device "controller0"

init:
    # Clear Falcon sticky faults before starting the smoke test.
    clear "FALCON 9".faults

main:
    # Command Falcon output from the live left Y controller value.
    # If controller input is temporarily unavailable, fall back to zero output.
    set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0

    # Fail immediately if the motor looks unsafe.
    abort "FALCON 9".current > 35
    abort "FALCON 9".temperature > 80

    # Pressing B fails the test immediately.
    abort controller0.B

    # Stop normally after three seconds.
    until timer.elapsed >= 3.0

    # A must be pressed at least once before the timer ends.
    require controller0.A

    # The Falcon must draw some current and report motion before normal stop.
    require "FALCON 9".current > 1.0
    require "FALCON 9".velocity > 100

close:
    # Clear sticky faults again after the verdict is already determined.
    clear "FALCON 9".faults
