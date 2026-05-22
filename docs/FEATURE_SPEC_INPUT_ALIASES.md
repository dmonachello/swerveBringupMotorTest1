SPEC_STATUS: IMPLEMENTED

**Input Aliases Spec**
Purpose: Define how controller input aliases are stored, resolved, and validated across the robot runtime and CLI.

**Scope**
Purpose: Establish what this feature does and does not do.
- Do: Provide a data-driven alias system for controller input identifiers across CLI, UI, and robot runtime.
- Do: Allow profile-specific aliases to override global aliases.
- Do: Resolve aliases consistently for bindings, usage queries, and suppression logic.
- Do not: Change any binding semantics, commands, or NetworkTables keys.
- Do not: Transmit any CAN frames from the PC tool.

**Motivation**
Purpose: Make controller naming consistent and customizable without hardcoded labels.
- Remove special-case handling of `driver` and `operator` in code.
- Allow teams to define their own naming conventions (e.g., `pilot`, `gunner`, `c0`, `blue`).
- Ensure identical behavior regardless of alias form entered in the CLI.

**Data Model**
Purpose: Specify where aliases live and how they are merged.
- Global aliases live in `bringup_bindings.json` under `inputAliases`.
- Profile aliases live in `bringup_system.json` inside each profile under `inputAliases`.
- Profile aliases override global aliases on key collisions.
- Aliases map from `alias -> canonical`.
- Canonical keys are always in normalized dot form (lowercase, dot-separated).
- Profile aliases are applied only when that profile is active.
- Base controller identifiers are `controller0` through `controller5`.

**Normalization Rules**
Purpose: Define how input identifiers are normalized for lookup.
- Trim leading/trailing whitespace.
- Convert to lowercase.
- No other normalization is performed (no underscore or space rewriting).

**Canonical Input Keys**
Purpose: Define the supported canonical inputs.
- Buttons: `driver.a`, `driver.b`, `driver.x`, `driver.y`, `driver.lb`, `driver.rb`, `driver.back`, `driver.start`, `driver.ls`, `driver.rs`, `operator.*` equivalents.
- D-pad: `driver.dpad.up`, `driver.dpad.right`, `driver.dpad.down`, `driver.dpad.left`, `operator.*` equivalents.
- Axes: `driver.left.x`, `driver.left.y`, `driver.right.x`, `driver.right.y`, `driver.left.trigger`, `driver.right.trigger`, `operator.*` equivalents.
- UI: `ui.slider1`, `ui.slider2`, `ui.button1`, `ui.button2`.

**Combo Inputs**
Purpose: Define how combo bindings relate to aliases.
- Combo inputs are not part of the alias system in this version.
- Combo bindings remain in raw form (example: `controller0` + `combo` + `LB+RB`).
- Alias maps must not target combo inputs.

**Alias Resolution**
Purpose: Describe the algorithm used to map alias to canonical.
- Normalize input by trimming and lowercasing.
- If an input is a canonical value, it is accepted as-is.
- If an input is an alias key, resolve it one step to its canonical target.
- Alias chaining is not supported.
- If resolution fails, the original normalized key is treated as unknown.

**Migration & Implicit Aliases**
Purpose: Define how existing bindings behave.
- Existing bindings remain valid without `inputAliases`.
- There are no implicit aliases in code.
- The default `bringup_bindings.json` provides common alias mappings (for example `controller0.a -> driver.a`).

**Validation Rules**
Purpose: Define when an input is considered valid.
- A binding input is valid if it resolves to a supported canonical key.
- Unknown inputs are rejected with a clear error message.
- UI and CLI validation use the same resolver and canonical set as the robot runtime.

**Validation Timing**
Purpose: Define when alias validation happens.
- Group bindings are validated when they are added through the CLI or UI.
- `show binding-usage <input>` validates and resolves the query input at command time.
- Global bindings loaded from `bringup_bindings.json` are not rejected based on alias resolution.

**Suppression Rules**
Purpose: Define how local bindings override global bindings.
- Local inputs are collected from group bindings.
- Local inputs are resolved to canonical keys using the merged alias map.
- Global bindings are suppressed when their alias-resolved input matches a local canonical key.
- Suppression is evaluated per loop with no extra controller reads.

**CLI Behavior**
Purpose: Define user-visible behavior in the CLI.
- Inputs can be specified using any known alias.
- `show binding-usage <input>` resolves aliases and reports all matching bindings.
- `show input-aliases` prints the merged alias map for the active profile.
- `group bind` accepts alias inputs and stores them as entered.
- Output displays the stored input identifiers, not the resolved canonical values.

**Robot Runtime Behavior**
Purpose: Define behavior in the robot code.
- Alias maps are merged at startup and when the active profile changes.
- The merged map is used for:
  - Binding suppression.
  - Group binding input resolution.
  - UI command validation.
- No changes to timing or loop scheduling are introduced.

**Failure Modes**
Purpose: Define expected behavior on invalid data.
- Missing alias maps: resolution becomes identity (no aliasing).
- Alias targets that are not canonical are invalid.
- Unknown inputs: rejected by validation and ignored in binding evaluation.

**Profile Switching**
Purpose: Define alias behavior on profile changes.
- When the active profile changes, the merged alias map is recomputed.
- Profile-specific aliases apply only while their profile is active.
- Bindings that depend on a profile-only alias may become invalid outside that profile.

**Compatibility**
Purpose: Preserve existing behavior and data contracts.
- Existing binding files remain valid without `inputAliases`.
- Existing CLI commands continue to accept canonical inputs.
- The alias system is additive and backward compatible.

**Examples**
Purpose: Show typical alias definitions and usage.
- Global aliases (`bringup_bindings.json`):
  - `controller0.a -> driver.a`
  - `controller1.a -> operator.a`
  - `c0.left.y -> driver.left.y`
  - `c1.right.trigger -> operator.right.trigger`
- Profile override (`bringup_system.json`, profile `home`):
  - `pilot.a -> driver.a`
  - `gunner.a -> operator.a`
- CLI usage:
  - `show binding-usage driver.a`
  - `show binding-usage controller0.a`
  - `group bind <group> pilot.a hold 0.25`

**Error Message Examples**
Purpose: Describe expected error outputs.
- Unknown input in binding:
  - Error: `Unknown input: pilot.a`
  - Hint: `Use a canonical input or define an alias in inputAliases.`

**Test Strategy**
Purpose: Enumerate minimum tests for this feature.
- Alias resolves to canonical (single-level).
- Profile alias overrides global alias.
- Unknown alias is rejected at group bind time.
- Local override suppresses matching global binding via alias resolution.
- Profile switch invalidates a profile-only alias.

**Tradeoffs**
Purpose: Document key tradeoffs.
- More flexibility at the cost of additional validation and merge logic.
- Aliases can hide typos if an alias maps to the wrong canonical input.
- Keeping stored inputs as-entered improves UX but can make files less uniform.

**Future Extensions**
Purpose: Identify safe follow-on improvements.
- Add schema validation to warn about alias cycles or duplicate canonical targets.
- Allow alias profiles for controller families beyond Xbox if needed.

