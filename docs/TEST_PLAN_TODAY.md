# Test Plan (Today)

## Purpose
Validate the new storage layers (JsonStore + Schema Store) and their CLI/UI integrations with explicit commands.

## Preconditions
- Repo root: `C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1`
- Python available on PATH.
- Use `--no-can --no-nt` for local CLI testing.

---

## A) CLI Tests (Explicit Commands)

### A1) Start the CLI (local only)
```
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

Expected:
- CLI prompt appears.
- No crash.

### A2) Validate local config (Schema Store path)
Commands:
```
configure terminal
validate config
end
```

Expected:
- `OK: Config is valid.` or explicit error list with locations.

### A3) Validate bindings (Schema Store path)
Commands:
```
configure terminal
bindings validate
end
```

Expected:
- `OK: Config is valid.` or a bindings-specific error list.

### A4) Validate CAN mappings (Schema Store path)
Commands:
```
configure terminal
can-mappings validate
end
```

Expected:
- `OK: Config is valid.` or a mappings-specific error list.

### A5) Show dirty state
Commands:
```
show config dirty
```

Expected:
- `Local dirty state:` block prints all dirty flags.

---

## B) UI Tests

### B1) Bridge UI loads tests from store
Command:
```
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python tools\can_nt\can_nt_bridge.py --ui --no-can --no-nt
```

Expected:
- Test list populates.
- If root `bringup_tests.json` exists, it is preferred over deploy copy.

### B2) Live topology view loads profiles via store
Command:
```
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python -m tools.can_topology.live_topology_view
```

Expected:
- Topology renders from `data\bringup_system.json` if present.
- Falls back to deploy copy if not.

---

## C) Topology Editor Tests

### C1) Open default profile path (store-backed)
Command:
```
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python -m tools.can_topology.can_top_editor
```

Actions:
- File ? Open Profile
- Select `data\bringup_system.json`

Expected:
- Loads without error.
- Device registry and profiles populate.

---

## D) Regression Compile Checks
Command:
```
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python -m py_compile tools\config\json_store.py tools\config\schema_store.py tools\config\config_store.py tools\can_nt\bridge_cli.py tools\can_nt\bringup_ui.py tools\can_topology\live_topology_view.py tools\can_topology\can_top_editor.py
```

Expected:
- No syntax errors.
