---
description: Sync AGENTS.md with recent file changes detected by git
---

# /auto-memory:sync

Detect files changed recently and update AGENTS.md incrementally.

## When to Use

- After manual file edits outside the AI session
- After pulling changes from remote
- When AGENTS.md seems out of sync with codebase
- Periodically to catch any drift

## Workflow

### Step 1: Verify Git Repository

```bash
git rev-parse --is-inside-work-tree
```

If not a git repo:
- Report error: "Not a git repository. Use /auto-memory:init for manual setup."

### Step 2: Detect Changed Files

```bash
# Modified tracked files (uncommitted)
git diff --name-only HEAD

# Staged files
git diff --cached --name-only

# New untracked files (excluding ignored)
git ls-files --others --exclude-standard

# Recent commits (last 5)
git diff --name-only HEAD~5..HEAD
```

### Step 3: Filter Files

Exclude from processing:
- Files in `.ai/` directory
- `AGENTS.md` files themselves
- Files in `node_modules/`, `vendor/`, `.git/`
- Binary files and images
- Lock files (package-lock.json, yarn.lock, etc.)

### Step 4: Categorize Changes

Map changed files to AGENTS.md sections:

| Changed File | Target Section |
|--------------|----------------|
| `package.json`, `Makefile`, `pyproject.toml` | `build-commands` |
| New directories created | `architecture` |
| Source files with new patterns | `conventions`, `patterns` |
| `README.md` | `project-description` |
| Files in `packages/*` | Subtree AGENTS.md |

### Step 5: Analyze Impact

For each category, determine:
- What new content should be added?
- What existing content should be updated?
- What content should be removed? (verify with grep first)

### Step 6: Update AGENTS.md

Apply changes following the algorithm in SKILL.md:
1. Read current AGENTS.md sections
2. Merge new information with existing
3. Remove stale content (after verification)
4. Write updated sections within markers

### Step 7: Report Summary

```
Sync complete.

Changed files analyzed: 12
Sections updated:
  - build-commands: Added "make lint-fix" command
  - architecture: Added packages/new-module/ directory
  - conventions: Updated import ordering pattern

No changes needed:
  - project-description
  - patterns
```

## Notes

- Only updates AUTO-MANAGED sections
- Never touches MANUAL sections
- Verifies content removal with grep before deleting
- For full rebuild, use /auto-memory:init with "Backup" option
