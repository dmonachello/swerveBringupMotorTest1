# Corrected Step-by-step Procedure (CLI Bringup)

0) Start CLI (fresh session)

```cmd
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

1) Select or Create Profile

```text
configure terminal
profile home_tests_033026
```

2) Remove Conflicting Tests State (recommended)

Purpose: ensure you are not editing leftover in-memory tests from a previous session or file.

```text
tests load bringup_tests.json
tests clear
```

Notes:
- If `bringup_tests.json` does not exist yet, skip `tests load` and run `tests clear` only.
- `tests load bringup_tests.json` ensures the CLI is working from a known file.
- `tests clear` wipes all test sets in memory so you can start clean.

3) Add Device to the Active Profile (required before tests can reference it)

```text
device "Feeder Motor"
set interface CAN
set manufacturer 5
set deviceType 2
set id 26
set model "REV NEO"
set type motor
exit
save profiles data/bringup_system.json
```

4) Refresh the Active Profile (so tests can see new devices)

```text
profile home_tests_033026
```

5) Create a New Test Set

```text
test set clean_033026
```

6) Create the FeederSpin Test (includes device!)

```text
test create FeederSpin
type button
device add "Feeder Motor"
inputSource controller0.A
duty 0.2
termination time 2.0
exit
```

7) Verify

```text
show tests
show test FeederSpin
```

8) Save Tests to a Custom File

```text
write tests my_tests.json
```

## Notes

- `device add` must reference a label that exists in the active profile (step 2).
- Controller names are explicit now: use `controller0.A`, not `primary.A`.
- `show tests` lists all sets plus the active set.
- `write tests` validates all sets in memory unless you ran `tests clear`.
- `write tests` must be run from `bridge(config)#` or `bridge(config-profile-...)#` (not from `bridge(config-test-...)#`). Use `exit` or `end` to leave test edit mode first.

## Clean Verification Procedure (CLI Config + Tests)

1) Start CLI

```cmd
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

2) Enter config mode

```text
configure terminal
```

3) Verify the profile exists

```text
show profiles
```

4) Select the profile under test

```text
profile home_tests_033026
```

5) Verify the device list

```text
show devices
```

Expected:
- `Feeder Motor` is present.

6) Load the tests file to verify

```text
tests load my_tests.json
```

7) Verify test sets and active set

```text
show tests
```

Expected:
- `default` contains `FeederSpin`.

8) Inspect the test

```text
show test FeederSpin
```

Expected:
- `devices: Feeder Motor`
- `inputSource: controller0.A`
- `duty: 0.2`
- `time: {'timeoutSec': 2.0, 'onTimeout': 'pass'}`
