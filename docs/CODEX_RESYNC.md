# Codex Resync Command

**Instruction for Codex:** Follow this file whenever the user says `resync`.

When you see the user message:

```
resync
```

Do all of the following in order:

1. `git pull`
2. `git log -1 --stat`
3. Summarize the latest commit in plain English, highlighting:
   - The main theme of the change
   - Key affected areas (CLI, UI, robot code, docs, tools, etc.)
   - Any new tools or migration steps

If the user adds extra scope (e.g. "resync and re-scan CLI docs"), do the above and then scan the requested area.
