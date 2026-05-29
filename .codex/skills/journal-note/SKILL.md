---
name: journal-note
description: >-
  Create or update short repo journal notes under notes/journal when the user
  asks to add a journal note, reflection, or working note. Use for dated,
  date-prefixed markdown note files in this repo's established journal style.
---

# Journal Note

Write repo journal notes under:

```text
notes/journal/
```

## Rules

- Do not create journal notes at repo root.
- Use a date-prefixed filename:

```text
YYYY-MM-DD-short-slug.md
```

- Use the current local date unless the user explicitly asks for a different
  date.
- Keep the note short and direct.
- Match the existing style in `notes/journal/`:
  - simple markdown
  - short bullet points
  - one note per file/topic
- Normalize the slug to lowercase words joined by hyphens.
- If the user gives a quoted title, derive the slug from that title.
- If a note with the same intended filename already exists, append to that file
  instead of creating a duplicate unless the user clearly wants a separate note.

## Workflow

1. Inspect `notes/journal/` naming/style only if needed.
2. Choose the filename from the date and topic.
3. Write the note as concise bullets.
4. Prefer preserving the user's wording, tightening only for clarity.

## Examples

User:

```text
new journal note - "testing plan"
```

Create:

```text
notes/journal/2026-05-29-testing-plan.md
```

User:

```text
add a journal note about codex lowering activation energy
```

Create a short dated bullet note under `notes/journal/`.
