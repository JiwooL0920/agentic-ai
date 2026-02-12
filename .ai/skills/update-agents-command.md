# /update-agents Command

## Trigger
When user types `/update-agents` or asks to "update agents.md" or "sync project memory"

## Instructions

Analyze recent changes and update `.ai/AGENTS.md` if needed:

### Step 1: Gather Context
```bash
# Recent commits (last 5)
git log --oneline -5

# Files changed in last commit
git diff --name-only HEAD~1

# Uncommitted changes
git status --short
```

### Step 2: Analyze Impact

For each changed area, determine if it affects:
- Build/dev commands
- Project structure
- Coding conventions
- Dependencies
- Architecture

### Step 3: Update AGENTS.md

If updates needed:
1. Read current `.ai/AGENTS.md`
2. Edit only the affected sections
3. Keep changes minimal and accurate
4. Preserve formatting

### Step 4: Report

Output a brief summary:
```
Updated .ai/AGENTS.md:
- Added: make deploy command
- Updated: Project Structure (new packages/ml/ directory)
```

Or if no updates needed:
```
No AGENTS.md updates needed — changes don't affect project documentation.
```
