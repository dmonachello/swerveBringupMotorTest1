Purpose: Collect Git commands discussed in this session for quick reference, with brief explanations.

## Status And Diffs
Purpose: Inspect the working tree and understand what has changed.

- `git status --short`: Show a compact list of modified and untracked files.
- `git status -sb`: Show branch tracking status plus a short change summary.
- `git diff`: Show all unstaged changes (line-level).
- `git diff --stat`: Show a summary of changed files and line counts.
- `git diff -- tools/can_nt/can_cli.py`: Show changes only for a single file.

## Staging And Commits
Purpose: Stage changes and create commits you can push or share.

- `git add <path>`: Stage a file or folder so it will be included in the next commit.
- `git commit -m "message"`: Record a snapshot of staged changes with a message.

## Remotes And Sync
Purpose: Sync your local repo with the remote.

- `git fetch`: Update references to remote branches without changing your working tree.
- `git push`: Upload local commits to the tracked remote branch.
- `git push origin <tag>`: Push a specific tag to the remote.

## Tags
Purpose: Create, list, inspect, and delete release markers.

- `git tag`: List all tags.
- `git tag <tag-name>`: Create a lightweight tag pointing to the current commit.
- `git tag -a <tag-name> -m "message"`: Create an annotated tag (recommended for releases).
- `git show <tag-name>`: Show the commit and metadata a tag points to.
- `git tag -d <tag-name>`: Delete a local tag.
- `git push origin :refs/tags/<tag-name>`: Delete a tag from the remote.

## Tag Listings (Chronological)
Purpose: List tags by creation or tagging date.

- `git for-each-ref --sort=creatordate --format="%(creatordate:short) %(refname:short)" refs/tags`: Show tags sorted by creation date.
- `git for-each-ref --sort=taggerdate --format="%(refname:short) %(taggerdate:short) %(objectname:short) %(subject)" refs/tags`: Show tags with date, commit hash, and subject.

## Tag Diffs And Logs
Purpose: Compare releases and review changes between tags.

- `git diff <tag-a> <tag-b>`: Show full diffs between two tags.
- `git diff --stat <tag-a> <tag-b>`: Show a summary of file changes between two tags.
- `git log --oneline <tag-a>..<tag-b>`: List commits that are in `<tag-b>` but not in `<tag-a>`.

## Branching From Tags
Purpose: Move to a tag or start a new branch from a release tag.

- `git checkout <tag-name>`: Check out the repo at a tag (detached HEAD).
- `git checkout -b <branch-name> <tag-name>`: Create a new branch starting at the tag.

## Upstream Checks
Purpose: Confirm tracking branch and divergence with remote.

- `git rev-parse --abbrev-ref --symbolic-full-name '@{u}'`: Show the upstream branch your current branch tracks.
- `git log --oneline --left-right HEAD...origin/main`: Show commits ahead/behind relative to `origin/main`.
