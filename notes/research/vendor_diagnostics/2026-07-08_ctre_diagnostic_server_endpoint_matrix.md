# CTRE Diagnostic Server Endpoint Matrix

## Purpose

Purpose: record the richer CTRE diagnostic-server endpoint behavior observed from direct HTTP testing against the roboRIO CTRE service.

This note is a discovery artifact, not a complete API specification.

## Source Artifacts

- Observed host: `172.22.11.2`
- Observed service: HTTP on TCP port `1250`
- Query style: `GET /?action=...`
- Target CAN bus: `rio`
- Observed devices:
  - `Talon FX` CAN ID `9`
  - `PDP` CAN ID `20`
  - `Pigeon 2 vers. S` CAN ID `19`

## Scope

This note covers `CTRE` diagnostic-server HTTP behavior only.

It does not cover:

- REV Hardware Client traffic
- REV USB bridge behavior
- mixed-vendor CAN passive captures except where they corroborate CTRE device presence

## Verified Transport Contract

- Transport: `HTTP`
- Method: `GET`
- Host pattern: `http://<rio>:1250/`
- Request shape:

```text
/?action=<action>[&model=<model>][&id=<id>][&canbus=<canbus>][&signal=<signal>][&cmd=<cmd>]
```

Observed common response pattern:

- JSON body
- top-level `GeneralReturn` object
- `GeneralReturn.Action`
- `GeneralReturn.CANbus`
- `GeneralReturn.Error`
- `GeneralReturn.ErrorMessage`
- `GeneralReturn.ID`
- `GeneralReturn.Model`

## Device Inventory

Observed from `getdevices`:

- `Talon FX` CAN ID `9`
  - Phoenix `6`
  - `SupportsConfigs=true`
  - `SupportsControl_v2=true`
  - `SupportsDecoratedSelfTest=true`
- `PDP` CAN ID `20`
  - Phoenix `5`
  - `SupportsConfigs=false`
  - `SupportsDecoratedSelfTest=false`
- `Pigeon 2 vers. S` CAN ID `19`
  - Phoenix `6`
  - `SupportsConfigs=true`
  - `SupportsDecoratedSelfTest=true`

## Endpoint Matrix

## Global Endpoints

### `getdevices`

- Safety class: `read_only`
- Scope: global inventory
- Observed status: `works`

Confirmed value:

- returns the CTRE device list and capability hints

Notable fields:

- `BusUtilPerc`
- `DeviceArray`
- `GeneralReturn`

### `getversion`

- Safety class: `read_only`
- Scope: service metadata
- Observed status: `works`

Confirmed value:

- returns service/system version info such as:
  - `ReleaseInfo`
  - `System`
  - `Version`

### `getcanbusstats`

- Safety class: `read_only`
- Scope: bus statistics
- Observed status: `works`

Observed working forms:

```text
/?action=getcanbusstats&canbus=rio
/?action=getcanbusstats&model=Talon%20FX&id=9&canbus=rio
```

Confirmed value:

- returns bus-level health counters
- response appears valid even when a device-specific query form is used

Notable fields:

- `BusOffCnt`
- `BusUtilPerc`
- `REC`
- `TEC`
- `TxFullCnt`

## Talon FX, CAN ID 9

### `blink`

- Safety class: `visible_side_effect`
- Observed status: `works`

Confirmed value:

- proves device-targeted action routing via `model`, `id`, and `canbus`

### `deviceinformation`

- Safety class: `read_only`
- Observed status: `works`

Confirmed value:

- returns UI/device-detail style metadata
- observed content included LED and FRC lock fields

### `decoratedselftest`

- Safety class: `read_only`
- Observed status: `works`

Confirmed value:

- strongest observed structured telemetry surface for Talon FX
- returns named or ID-keyed signals with `Units` and `Value`
- includes:
  - firmware/build metadata
  - supply voltage
  - temperatures
  - current signals
  - control mode
  - fault/sticky-fault booleans
  - licensing state

Interpretation:

- this endpoint is already rich enough to support meaningful read-only diagnostics for Phoenix 6 Talon FX devices

### `getsignals`

- Safety class: `read_only`
- Observed status: `works`

Confirmed value:

- returns signal catalog metadata
- provides:
  - signal `Id`
  - signal `Name`
  - signal `Summary`
  - signal `Units`

Interpretation:

- this appears to be the schema/introspection companion for signal-based reads

### `getconfigv2`

- Safety class: `read_only`
- Observed status: `works`

Confirmed value:

- returns structured configuration groups and config entries
- includes:
  - group names and summaries
  - config names
  - signal IDs
  - types
  - limits
  - enum choices
  - current values

Interpretation:

- `getconfigv2` is the strongest observed structured configuration inventory endpoint
- this is much richer than the earlier unsupported `getconfig` call

### `getconfig`

- Safety class: `read_only`
- Observed status: `fails`
- Error: `-135`
- Error message: `This feature is not supported for this device model.`

Interpretation:

- for Talon FX on this service version, `getconfigv2` is the usable path, not `getconfig`

### `selftest`

- Safety class: `read_only_or_gated`
- Observed status: `fails`
- Error: `-144`
- Error message: `This feature requires Tuner X.`

Interpretation:

- raw self-test access for Talon FX is feature-gated
- however `decoratedselftest` is still available and useful

### `getsignalvalue`

- Safety class: `read_only`
- Observed status: `fails`
- Error: `-1002`

Observed failing forms:

```text
/?action=getsignalvalue&model=Talon%20FX&id=9&canbus=rio&signal=SupplyVoltage
/?action=getsignalvalue&model=Talon%20FX&id=9&canbus=rio&signal=1781
```

Interpretation:

- either this endpoint expects an additional argument shape, or it is not usable in this service/context as attempted
- `getsignals` plus `decoratedselftest` are currently the better read surfaces

## PDP, CAN ID 20

### `selftest`

- Safety class: `read_only`
- Observed status: `works`

Confirmed value:

- returns a large plain-text diagnostic block rather than a structured signal object
- includes:
  - channel currents
  - battery voltage
  - temperature
  - fault status
  - sticky faults
  - build info

Interpretation:

- older Phoenix 5 PDP support is present, but the format is text-heavy and less structured than Phoenix 6 decorated self-test

SID_COMMENT: a future parser could still extract useful fields from this text block if PDP support is needed for automated inventory/health reporting.

### `deviceinformation`

- Safety class: `unknown`
- Observed status: `not yet confirmed`

### `getsignals`

- Safety class: `unknown`
- Observed status: `not yet confirmed`

## Pigeon 2 vers. S, CAN ID 19

### `decoratedselftest`

- Safety class: `read_only`
- Observed status: `works`

Confirmed value:

- returns structured Phoenix 6 telemetry/fault state
- observed content included:
  - yaw/pitch/roll
  - quaternion values
  - gravity vector
  - accelerometer
  - angular velocity
  - magnetic field
  - supply voltage
  - fault/sticky-fault fields
  - build and firmware info

Interpretation:

- this endpoint is the strongest read-only surface observed so far for Pigeon diagnostics

### `getsignals`

- Safety class: `read_only`
- Observed status: `works`

Confirmed value:

- returns the schema/catalog for Pigeon signals
- corroborates the meanings of many IDs seen in `decoratedselftest`

## Observed Patterns

### Phoenix 6 Devices

Observed on:

- `Talon FX`
- `Pigeon 2 vers. S`

Pattern:

- `getdevices` advertises richer capability
- `decoratedselftest` works and returns structured telemetry
- `getsignals` works and returns signal metadata
- config/state surfaces are significantly more machine-friendly

### Phoenix 5 / Older Device Surface

Observed on:

- `PDP`

Pattern:

- device is still discoverable
- useful diagnostics exist
- response style is older and less structured

## Immediate Design Implications

For CTRE-specific diagnostics, the most useful current read-only surfaces appear to be:

1. `getdevices`
2. `getcanbusstats`
3. `decoratedselftest` for Phoenix 6 devices
4. `getsignals` for Phoenix 6 devices
5. `getconfigv2` where supported
6. `selftest` for older devices like PDP

This means a first-pass CTRE diagnostics client could likely be split into:

- inventory/bootstrap:
  - `getdevices`
  - `getversion`
  - `getcanbusstats`
- Phoenix 6 detail:
  - `decoratedselftest`
  - `getsignals`
  - `getconfigv2`
- older-device fallback:
  - `selftest`

## What This Note Does Not Yet Prove

- the complete list of accepted `action=` values
- exact rules for `getsignalvalue`
- whether `deviceinformation` is broadly available on all CTRE device families
- whether some actions mutate device state beyond obvious cases like `blink`
- whether repeated structured endpoint access induces measurable CTRE CAN-bus traffic changes

## Recommended Next Steps

1. Capture one clean endpoint inventory pass per CTRE device family present on the bus.
2. Confirm whether `deviceinformation` and `getsignals` work for `PDP`.
3. Test `getconfigv2` on `Pigeon 2 vers. S`.
4. Determine whether `getsignalvalue` has an undocumented parameter contract.
5. Preserve representative raw responses as fixtures for future parser work.
