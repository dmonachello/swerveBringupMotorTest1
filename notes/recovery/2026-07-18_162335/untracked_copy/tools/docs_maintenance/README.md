# Docs Maintenance Pipeline

Purpose: provide a repo-local, extendable documentation maintenance pipeline for this project tree.

## Current Scope

- inventory Markdown files in the repository
- classify editable vs generated pages
- identify entry-point pages
- emit a machine-readable health report
- detect broken links, orphans, duplicate title families, and terminology drift
- propose related topics, wiki links, glossary seeds, and canonical rename candidates
- generate repo-local documentation artifacts:
  - `docs/INDEX.md`
  - `docs/GLOSSARY.md`
  - `docs/mocs/*.md`
  - `docs/DOCS_HEALTH_REPORT.md`
  - `docs/DOCS_GRAPH_SUGGESTIONS.md`

## Pipeline Passes

- inventory
- health report
- link graph
- terminology and duplicate-title reporting
- MOC and top-level index planning
- related-topics and wiki-link suggestion generation
- glossary generation
- generated artifact writing

## Usage

```powershell
python -m tools.docs_maintenance.main --repo-root . --pretty
```

Generate the Markdown artifacts in `docs/` while also printing the JSON report:

```powershell
python -m tools.docs_maintenance.main --repo-root . --pretty --write-artifacts
```

On-demand saved report:

```powershell
powershell -ExecutionPolicy Bypass -File tools/docs_maintenance/run_docs_maintenance.ps1
```

Register weekly scheduled run:

```powershell
powershell -ExecutionPolicy Bypass -File tools/docs_maintenance/register_scheduled_task.ps1
```

## Notes

- The current implementation is intentionally conservative.
- It generates vault entrypoints and hub pages without rewriting existing engineering prose.
- It keeps the pipeline structure modular so later passes can still be added without redesign.
- The scheduled-task helper registers a weekly run every Sunday at `9:00 AM` local time.
