# Codex Skills in VS Code

## Purpose

Show how to create, install, and use custom Codex skills from VS Code, with `journal-entry` as a concrete example.

## What a Skill Is

A Codex skill is a folder under `.codex/skills` containing:

- `SKILL.md` (required): trigger description + operating instructions.
- Optional `scripts/`: deterministic helper scripts.
- Optional `agents/openai.yaml`: metadata for skill UI.

## Prerequisites

- VS Code with Codex CLI workflow available.
- A workspace folder where you can create files.
- Python installed if your skill uses Python scripts.

## Recommended Workflow

### 1) Decide the Skill Contract

Purpose: define exactly what the skill should do and what inputs it needs.

For a journal skill, contract might be:

- Create one Markdown file per run.
- Collect multi-line text from user input.
- Save in a default journal directory unless overridden.

### 2) Create the Skill Folder

Purpose: place the skill where Codex discovers it.

Windows example:

```powershell
New-Item -ItemType Directory -Force C:\Users\<you>\.codex\skills\journal-entry\scripts
New-Item -ItemType Directory -Force C:\Users\<you>\.codex\skills\journal-entry\agents
```

### 3) Write `SKILL.md`

Purpose: tell Codex when to trigger the skill and how to run it.

Minimal `SKILL.md` content:

```yaml
---
name: "journal-entry"
description: "Create daily journal Markdown files and collect entry text from the user. Use when the user asks to create or append a journal note."
---
```

```md
Journal Entry

Run:

python C:\Users\<you>\.codex\skills\journal-entry\scripts\create_journal_entry.py
```

Guidelines:

- Put trigger context in frontmatter `description`.
- Keep body procedural and concise.
- Include real command examples.

### 4) Add an Implementation Script

Purpose: make behavior reliable and repeatable.

`journal-entry` script responsibilities:

- Resolve output directory from `--journal-dir`, `JOURNAL_DIR`, or default `%USERPROFILE%\journal`.
- Prompt for multi-line input.
- Stop on sentinel input such as `:wq`.
- Write file as `YYYY-MM-DD.md`, with suffixes for collisions.

Example script path:

- `C:\Users\<you>\.codex\skills\journal-entry\scripts\create_journal_entry.py`

### 5) Add Optional UI Metadata

Purpose: improve skill discoverability in supported UIs.

Example file:

```yaml
version: 1
interface:
  display_name: Journal Entry
  short_description: Create a dated Markdown journal note
  default_prompt: Create a journal Markdown file and collect my entry text.
```

Path:

- `C:\Users\<you>\.codex\skills\journal-entry\agents\openai.yaml`

### 6) Test End-to-End

Purpose: verify the skill works before regular use.

Manual run test:

```powershell
python C:\Users\<you>\.codex\skills\journal-entry\scripts\create_journal_entry.py --title "Skill Test"
```

Then enter sample lines and finish with:

```text
:wq
```

Confirm a Markdown file was created in the expected directory.

## How to Use Skills in Daily Work

### Trigger by Name in Chat

Purpose: force Codex to load and apply a specific skill.

Examples:

```text
[$journal-entry]
Text: Short end-of-day reflection.
```

```text
[$screenshot] take a screenshot of my desktop
```

### Provide Inputs in a Simple Template

Purpose: keep requests consistent and easy to parse.

Suggested template:

```text
[$journal-entry]
Title: Bringup Notes
Dir: C:\path\to\journal
Text:
- item 1
- item 2
```

If `Dir` is omitted, the skill can fall back to `JOURNAL_DIR`.

### Set a Persistent Default Directory

Purpose: avoid repeating the journal path each time.

Windows (user-scoped):

```powershell
setx JOURNAL_DIR "C:\Users\<you>\path\to\journal"
```

Open a new terminal/session if the updated environment variable is not visible immediately.

## `journal-entry` Example Summary

Working example components:

- Skill doc: `C:\Users\dmona\.codex\skills\journal-entry\SKILL.md`
- Script: `C:\Users\dmona\.codex\skills\journal-entry\scripts\create_journal_entry.py`
- Metadata: `C:\Users\dmona\.codex\skills\journal-entry\agents\openai.yaml`

Usage example:

```text
[$journal-entry]
Title: New Journal Skill
Text: This is a test skill
```

Expected result:

- Markdown file created in configured journal directory.

## Troubleshooting

- Skill not triggering: verify frontmatter `name` and `description` exist in `SKILL.md`.
- Wrong output folder: verify `JOURNAL_DIR` and any `--journal-dir` override.
- Script errors: run the script directly in terminal to isolate Python/runtime issues.
- Missing skill in list: confirm folder is directly under `.codex/skills`.

## Tradeoffs

- Script-based skills are more reliable but require maintaining code.
- Pure `SKILL.md` instructions are fast to create but can be less deterministic.
- Strongly scoped trigger descriptions reduce false activation but may require more explicit prompts.

## Future Extensions

- Add non-interactive mode (single `--text` argument).
- Add template sections (Wins, Issues, Next Steps).
- Add append mode for same-day entries.
- Add optional auto-open in default editor.
