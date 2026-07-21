---
name: thread-backup
description: >-
  Back up the current working thread to local repo files as fully as possible
  when the user asks to checkpoint, archive, preserve, or recover a Codex /
  ChatGPT thread. Use for local thread handoff bundles that capture visible
  thread content, repo state, git state, diffs, and a restoration summary.
---

# Thread Backup

Create a local recovery bundle for the current working thread.

## Hard Limit

This skill cannot extract hidden server-side chat history or restore a broken
thread from OpenAI systems.

It can only preserve:

- the current visible conversation content available in this thread
- a concise restoration summary written now
- any transcript text the user pastes or exports
- repo, git, diff, and workspace state at backup time

## Output Location

Write bundles under:

```text
notes/thread_backups/
```

Use a timestamped subdirectory:

```text
YYYY-MM-DD_HHMMSS[-label]/
```

## What To Capture

Always capture:

- current branch and HEAD
- `git status`
- staged diff summary
- unstaged diff summary
- tracked diff patch against HEAD
- untracked file list
- recent git log
- concise restoration summary in markdown
- environment summary:
  - cwd
  - date/time
  - branch
  - HEAD sha

When available, also capture:

- user-pasted transcript text
- exported chat transcript file content
- relevant recovery notes already present in the repo

## Required Behavior

1. Be explicit about the hard limit above.
2. Create a short restoration summary in markdown before or alongside the
   snapshot. That summary should say:
   - what the thread was working on
   - current known state
   - unresolved questions
   - safest next steps
3. Run the bundled snapshot script to capture repo state.
4. If the user provides transcript text or a local transcript file, save that
   into the same bundle.
5. At the end, report the exact bundle path.

## Default Workflow

1. Choose a short label if the user provided one.
2. Write `restoration_summary.md` in the bundle directory.
3. Run `scripts/backup_bundle.py`.
4. If transcript text is available, save:
   - `thread_transcript.md`
   - or `thread_transcript.txt`
5. If the repo already has recovery notes for the same event, leave them in
   place and reference them from the summary instead of duplicating large prose.

## Script

Use:

```text
.codex/skills/thread-backup/scripts/backup_bundle.py
```

Example:

```powershell
@'
# Restoration Summary

- Topic: centralized control refactor recovery
- Current state: recovery branch created and verified
- Next step: continue remaining shared-state refactor
'@ | python .codex/skills/thread-backup/scripts/backup_bundle.py --repo-root . --label centralized-control --summary-stdin
```

To attach a pasted/exported transcript file:

```powershell
python .codex/skills/thread-backup/scripts/backup_bundle.py --repo-root . --label centralized-control --summary-file notes/tmp/summary.md --transcript-file notes/tmp/chat-export.md
```

## Notes

- Prefer additive backups. Never delete earlier bundles.
- Keep the summary concise and factual.
- Do not claim the bundle can fully restore hidden chat state.
