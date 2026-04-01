# Corrected Step-by-step Procedure (CLI Bringup)

0) Start CLI (fresh session)

```cmd
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

Notes:
- If `bringup_system.json` is invalid, the CLI will still start in recovery mode and print warnings. Fix the profile data, then `save profiles ...`.
TBD Screenshot: Recovery-mode CLI startup showing the warning banner and the active prompt.

0a) Inspect the current workspace (optional but recommended)

```text
show workspace
```

Expected:
- Paths for profiles/tests/bindings/mappings.
- Active profile and active test set.
- Dirty flags (should be false on a fresh session).

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
- If you want to merge tests from another file instead of replacing, use `tests merge <path>`.

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
Screenshot: `show tests` output listing multiple test sets and the active set.
```text

bridge(config-profile-home_tests_033026)# show tests
Test sets:
  clean_033026 (1 tests)
  default (0 tests)
Active test set: clean_033026
- FeederSpin (button) devices=1 enabled=False
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.

bridge(config-profile-home_tests_033026)# show test FeederSpin
Test: FeederSpin
  type: button
  enabled: False
  devices: Feeder Motor
  inputSource: controller0.A
  duty: 0.2
  termination: hold=False time=2.0 rotation=None
  time: {'timeoutSec': 2.0, 'onTimeout': 'fail'}
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_tests_033026)#
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
- Commands are case-insensitive (`inputSource`, `inputsource`, `InputSource` all work).
- To delete a device:
  - `no device "<label>"` from config/profile mode, or
  - `device "<label>"` then `delete` from device mode.
- If both profiles and tests are dirty, you can use `save all` to persist everything with the current file paths.

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
TBD Screenshot: `show profiles` output listing available profiles.

4) Select the profile under test

```text
profile home_tests_033026
```

5) Verify the device list

```text
show devices
```
TBD Screenshot: `show devices` output with `Feeder Motor` present.

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
