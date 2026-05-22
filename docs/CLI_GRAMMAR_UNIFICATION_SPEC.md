SPEC_STATUS: PARTIALLY_IMPLEMENTED

**CLI Grammar Unification Spec**

**Purpose**  
Define a single grammar-driven data structure used for parsing, command completion, help/usage, and diagnostics.

**Goals**
- One authoritative grammar source for parsing and completion.
- Remove manual command lists from the completer.
- Provide consistent errors, hints, and help text.
- Preserve current CLI behavior and compatibility aliases.

**Non-Goals**
- No behavior changes to existing commands unless explicitly noted.
- No removal of legacy commands (e.g., `write tests`) without deprecation.
- No requirement to add new runtime dependencies unless approved.

**Terms**
- Grammar Source: The canonical file that defines CLI syntax.
- Grammar Graph: An in-memory structure derived from the grammar.
- Parse AST: Command AST produced from the grammar.
- Completion: Next-token suggestions based on the grammar graph and current input.

**Grammar Source**
Purpose: Define one authoritative syntax definition.
- Source file: `tools/can_nt/bridge_cli_ebnf.txt`.
- The EBNF is the single source of truth.
- Generated artifacts are derived from EBNF only.
- EBNF updates require regeneration of parser/metadata.

**Grammar Graph**
Purpose: Provide a shared, traversable structure for parser and completer.
- Graph nodes represent non-terminals and terminals.
- Graph edges represent valid transitions.
- Tokens are classified as:
  - Literal keywords (e.g., `show`, `profile`).
  - Typed placeholders (e.g., `<path>`, `<profile>`).
  - Flags (e.g., `--json`, `--pretty`).
- Graph retains:
  - Rule names.
  - Token classes.
  - Source locations (for diagnostics).
  - Optional semantic tags (e.g., â€œrequires config modeâ€).

**Core Data Structure**
Purpose: Provide a single model used by parsing, completion, and help.
- Name: `CliGrammarModel`.
- Fields:
  - `rules`: dict of rule name -> rule node.
  - `terminals`: list of terminal tokens (keywords/flags).
  - `placeholders`: list of placeholder tokens.
  - `aliases`: map of alias -> canonical token.
  - `modes`: map of mode -> allowed root rules.
  - `help`: map of command -> help text (optional).
- Serialization:
  - Persist a JSON version for tooling and tests.
  - Runtime loads from JSON or EBNF depending on environment.

**Parser**
Purpose: Produce a command AST from the grammar model.
- Replace manual parser tables with grammar-driven parsing.
- Parsing steps:
  1. Tokenize input.
  2. Apply prefix expansion (unique abbreviations).
  3. Parse tokens against grammar graph for the current mode.
  4. Emit a typed `CommandAst`.
- Error handling:
  - Return expected tokens at the failure point.
  - Provide a specific hint (e.g., â€œexpected `config` after `import`â€).

**Command Completion**
Purpose: Use the grammar graph to produce valid next tokens.
- Completion input:
  - Mode, current tokens, prefix (partial token).
- Completion output:
  - Exact next-token suggestions valid at the current parse frontier.
  - If a placeholder is expected, return `<path>`/`<profile>` etc.
- Completion does not need command-specific hardcoding.
- Completion respects aliases and abbreviations.

**Help and Usage**
Purpose: Generate `help` and `show commands` from grammar.
- `show commands` uses the grammar model for the current mode.
- `help <topic>` can fall back to grammar-based usage if no manual help exists.
- Manual help remains allowed for high-detail sections.

**Backward Compatibility**
Purpose: Preserve existing command behavior.
- Keep legacy aliases (e.g., `write tests`) with deprecation warnings.
- Keep existing token names unless explicitly replaced.
- Preserve unique-prefix abbreviations.

**Validation and Diagnostics**
Purpose: Improve error clarity and script linting.
- On parse failure:
  - Show the expected tokens.
  - Show the closest valid commands.
- Add an offline CLI script linter:
  - `lint script <path>` to parse and report all errors with line numbers.

**Examples**
Purpose: Show target behaviors clearly.
- Completion:
  - Input: `import` -> suggestions: `config`.
  - Input: `import config` -> suggestions: `<path>`.
  - Input: `show can-mappings` -> suggestions: `manufacturers`, `device-types`, flags.
- Errors:
  - Input: `save tests` -> error: â€œexpected `<path>`.â€
  - Input: `validate` -> error: â€œexpected `all|config|profiles|tests|bindings|can-mappings`.â€

**Implementation Plan**
Purpose: Deliver in incremental, testable steps.
1. Build grammar model:
   - Parse EBNF into `CliGrammarModel`.
   - Emit JSON artifact for tests.
2. Grammar-driven completion:
   - Replace manual completion lists with grammar graph traversal.
3. Grammar-driven parser:
   - Replace current parser tables with grammar parsing.
4. Help integration:
   - Generate `show commands` from grammar.
5. Script linter:
   - Add `lint script <path>`.

**Testing**
Purpose: Ensure behavior is unchanged while refactoring.
- Unit tests:
  - Grammar model matches EBNF rules.
  - Completion suggestions for common commands.
  - Parse AST matches previous behavior for key commands.
- CLI smoke tests:
  - `show`, `profile`, `group`, `tests`, `bindings`, `can-mappings`.
  - Legacy `write tests` warning still works.
- Batch script lint tests for known scripts in `myData/`.

**Tradeoffs**
Purpose: Surface design costs explicitly.
- Pros:
  - Single source of truth.
  - Fewer mismatches between parser and completer.
  - Better error messages.
- Cons:
  - Larger refactor.
  - EBNF parser/graph adds complexity.
  - Potential performance impact if grammar graph is too large.

**Future Extensions**
Purpose: Identify next logical steps.
- Grammar-aware â€œdid you meanâ€ suggestions.
- Auto-generated CLI reference docs.
- IDE/GUI integration using the grammar JSON.

