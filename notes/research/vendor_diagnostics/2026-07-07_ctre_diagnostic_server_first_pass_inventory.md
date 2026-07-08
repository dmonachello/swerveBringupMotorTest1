# CTRE Diagnostic Server First-Pass Inventory

## Purpose

Purpose: record the first observed CTRE Diagnostic Server request/response inventory from Phoenix Tuner traffic capture.

This note is a discovery artifact, not a complete API specification.

## Source Artifacts

- Capture file: `C:\Users\dmona\ctre1.pcapng`
- Observed host: `172.22.11.2`
- Observed service: HTTP on TCP port `1250`
- Tool workflow: Phoenix Tuner device list view plus Talon FX blink action

## Verified Transport Contract

- Transport: `HTTP`
- Method: `GET`
- Host pattern: `http://<rio>:1250/`
- Request shape: root path plus query parameters

Observed request pattern:

```text
/?action=<action>[&model=<model>][&id=<id>][&canbus=<canbus>][&cmd=<cmd>]
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

## Observed Actions

## 1. `getdevices`

- Safety class: `read_only`
- Scope: global inventory
- Request:

```text
GET /?action=getdevices HTTP/1.1
```

Observed behavior:

- repeated polling by Phoenix Tuner
- returns CTRE device inventory plus capability hints

Response top-level fields:

- `BusUtilPerc`
- `DeviceArray`
- `GeneralReturn`

## 2. `getversion`

- Safety class: `read_only`
- Scope: server/system metadata
- Request:

```text
GET /?action=getversion HTTP/1.1
```

Response top-level fields:

- `Compliancy`
- `GeneralReturn`
- `ReleaseInfo`
- `SearchDirectory`
- `System`
- `Version`

## 3. `runcaniv`

- Safety class: `read_like_but_stateful`
- Scope: support/tooling helper
- Requests:

```text
GET /?action=runcaniv&cmd=--version HTTP/1.1
GET /?action=runcaniv&cmd=-l HTTP/1.1
```

Observed behavior:

- returns command output as text inside JSON
- appears related to CANivore helper tooling, not direct motor diagnostics

Response top-level fields:

- `Command`
- `GeneralReturn`
- `Output`

## 4. `blink`

- Safety class: `visible_side_effect`
- Scope: device-targeted
- Request:

```text
GET /?action=blink&model=Talon%20FX&id=9&canbus=rio HTTP/1.1
```

Observed behavior:

- proves targeting contract for device actions
- not read-only

Required observed parameters:

- `action`
- `model`
- `id`
- `canbus`

## Observed `getdevices` Field Inventory

Purpose: record the per-device fields already visible from one read-only endpoint.

Observed device object fields:

- `BootloaderRev`
- `CANbus`
- `CANivoreDevName`
- `Compliancy`
- `CurrentVers`
- `HardwareRev`
- `ID`
- `IsPROApplication`
- `IsPROLicensed`
- `LicenseCapacity`
- `LicenseResponseCode`
- `LicenseSigs`
- `Licenses`
- `LicensesValid`
- `ManDate`
- `Model`
- `Name`
- `SerialNo`
- `SoftStatus`
- `SupportsConfigs`
- `SupportsControl_v2`
- `SupportsDecoratedSelfTest`
- `SupportsLicensing`
- `Vendor`

## Observed Device Instances

## Talon FX, CAN ID 9

- `Model`: `Talon FX`
- `CANbus`: `rio`
- `CurrentVers`: `26.1.0.0 (Phoenix 6)`
- `SoftStatus`: `Running Application.`
- `SupportsConfigs`: `true`
- `SupportsControl_v2`: `true`
- `SupportsDecoratedSelfTest`: `true`
- `SupportsLicensing`: `true`

Interpretation:

- this device likely has richer readable capability than the PDP
- `SupportsDecoratedSelfTest=true` is the strongest clue that additional read-only diagnostic actions probably exist

## PDP, CAN ID 20

- `Model`: `PDP`
- `CANbus`: `rio`
- `CurrentVers`: `1.40 (Phoenix 5)`
- `SoftStatus`: `Running Application.`
- `SupportsConfigs`: `false`
- `SupportsControl_v2`: `false`
- `SupportsDecoratedSelfTest`: `false`
- `SupportsLicensing`: `false`

Interpretation:

- this device exposes a more limited capability surface than the Talon FX

## What This Capture Does Not Yet Prove

- the full list of supported `action=` values
- whether Talon FX self-test is exposed through this same service
- whether faults, live signals, or sticky faults are available
- whether there are additional per-device read-only endpoints for PDP
- whether POST or non-root paths are ever used

## Current Inventory Judgment

This is a valid first-pass action inventory, but not a full CTRE capability enumeration.

What is proven now:

- the service exists and is scriptable
- the service uses root-path GET requests with query parameters
- `getdevices` is the inventory bootstrap endpoint
- `getversion` is a stable server metadata endpoint
- device-targeted actions use `model`, `id`, and `canbus`

What still needs capture:

- Talon FX self-test view
- Talon FX detailed diagnostics/faults view
- PDP detail view
- any config/status tab that appears read-only

## Recommended Next Enumeration Steps

1. Capture one session that opens Talon FX self-test only.
2. Capture one session that opens Talon FX detailed diagnostics/faults only.
3. Capture one session that opens PDP details only.
4. Diff the observed `action=` values and response schemas.
5. Extend the machine-readable inventory artifact with the newly discovered actions and fields.
