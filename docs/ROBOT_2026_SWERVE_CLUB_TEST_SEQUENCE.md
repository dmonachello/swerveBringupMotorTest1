# robot_2026_swerve Club Test Sequence

## Purpose

Bring up the `robot_2026_swerve` profile on a real robot using the Bridge CLI, staged motor instantiation, and joystick-driven vendor groups.

## Scope

This sequence assumes:

- only the swerve drive hardware is connected
- the active profile is `robot_2026_swerve`
- the Kraken drive motors are controlled from the Xbox left stick
- the REV angle motors are controlled from the Xbox right stick
- testing is incremental, one drive motor and one angle motor at a time

## Important Model

- `krakens` is the drive motor group
- `neos` is the angle motor group
- `leftDrive` is the left joystick input binding
- `rightDrive` is the right joystick input binding
- `add next` instantiates the next motor in profile order
- group member `enable` / `disable` determines which instantiated motors respond

## Important Safety Notes

- Group bindings can command any enabled group member.
- Group bindings can also force creation of a configured device if that group member is enabled.
- Because of that, disable all group members first, then enable only the motor pair currently under test.
- The two DSL tests remain available, but they are bulk tests. Do not use them for staged one-motor-at-a-time bringup.
- `controller0.B` aborts the two DSL joystick tests, but this staged group-binding flow does not depend on those tests.

## Profile Motor Order

`add next` will instantiate motors in this order:

1. `frontLeft Drive Motor`
2. `frontLeft Angle Motor`
3. `frontRight Drive Motor`
4. `frontRight Angle Motor`
5. `backLeft Drive Motor`
6. `backLeft Angle Motor`
7. `backRight Drive Motor`
8. `backRight Angle Motor`

## Start The CLI

```text
python tools\can_nt\bridge_cli.py --rio 172.22.11.2
```

## Connect And Inspect

```text
connect
show status
show profile robot_2026_swerve
show group krakens
show group neos
```

## One-Time Group Binding Setup

Enter config mode:

```text
configure terminal
```

Configure `krakens`:

```text
group krakens
no bind
bind leftDrive analog
member "frontLeft Drive Motor" disable
member "frontRight Drive Motor" disable
member "backLeft Drive Motor" disable
member "backRight Drive Motor" disable
enable
```

Configure `neos`:

```text
group neos
no bind
bind rightDrive analog
member "frontLeft Angle Motor" disable
member "frontRight Angle Motor" disable
member "backLeft Angle Motor" disable
member "backRight Angle Motor" disable
enable
```

Exit config mode:

```text
end
```

Verify:

```text
show group krakens
show group neos
```

## Test Front Left

Instantiate the next two motors:

```text
add next
add next
```

Enable only the front-left pair:

```text
configure terminal
group krakens
member "frontLeft Drive Motor" enable
group neos
member "frontLeft Angle Motor" enable
end
```

Expected behavior:

- left joystick Y controls `frontLeft Drive Motor`
- right joystick Y controls `frontLeft Angle Motor`

Useful checks:

```text
show status
show runtime-state
show group krakens
show group neos
```

## Test Front Right

Instantiate the next two motors:

```text
add next
add next
```

Disable the old pair and enable the new pair:

```text
configure terminal
group krakens
member "frontLeft Drive Motor" disable
member "frontRight Drive Motor" enable
group neos
member "frontLeft Angle Motor" disable
member "frontRight Angle Motor" enable
end
```

Expected behavior:

- left joystick Y controls `frontRight Drive Motor`
- right joystick Y controls `frontRight Angle Motor`

## Test Back Left

Instantiate the next two motors:

```text
add next
add next
```

Disable the old pair and enable the new pair:

```text
configure terminal
group krakens
member "frontRight Drive Motor" disable
member "backLeft Drive Motor" enable
group neos
member "frontRight Angle Motor" disable
member "backLeft Angle Motor" enable
end
```

Expected behavior:

- left joystick Y controls `backLeft Drive Motor`
- right joystick Y controls `backLeft Angle Motor`

## Test Back Right

Instantiate the next two motors:

```text
add next
add next
```

Disable the old pair and enable the new pair:

```text
configure terminal
group krakens
member "backLeft Drive Motor" disable
member "backRight Drive Motor" enable
group neos
member "backLeft Angle Motor" disable
member "backRight Angle Motor" enable
end
```

Expected behavior:

- left joystick Y controls `backRight Drive Motor`
- right joystick Y controls `backRight Angle Motor`

## Enable All Drive Motors

If the staged pass is clean and you want all drive motors active together:

```text
configure terminal
group krakens
member "frontLeft Drive Motor" enable
member "frontRight Drive Motor" enable
member "backLeft Drive Motor" enable
member "backRight Drive Motor" enable
end
```

## Enable All Angle Motors

If the staged pass is clean and you want all angle motors active together:

```text
configure terminal
group neos
member "frontLeft Angle Motor" enable
member "frontRight Angle Motor" enable
member "backLeft Angle Motor" enable
member "backRight Angle Motor" enable
end
```

## Emergency / Recovery Commands

If outputs do not behave as expected:

```text
show status
show runtime-state
clear stop-latch
```

To disable all staged joystick control quickly:

```text
configure terminal
group krakens
disable
group neos
disable
end
```

To re-enable them later:

```text
configure terminal
group krakens
enable
group neos
enable
end
```

## Shutdown

```text
disconnect
quit
```

## Short Version

```text
python tools\can_nt\bridge_cli.py --rio 172.22.11.2
connect
configure terminal
group krakens
no bind
bind leftDrive analog
member "frontLeft Drive Motor" disable
member "frontRight Drive Motor" disable
member "backLeft Drive Motor" disable
member "backRight Drive Motor" disable
enable
group neos
no bind
bind rightDrive analog
member "frontLeft Angle Motor" disable
member "frontRight Angle Motor" disable
member "backLeft Angle Motor" disable
member "backRight Angle Motor" disable
enable
end
add next
add next
configure terminal
group krakens
member "frontLeft Drive Motor" enable
group neos
member "frontLeft Angle Motor" enable
end
```
