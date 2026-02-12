---
description: Show AGENTS.md memory sync status
---

# /auto-memory:status

Display the current status of AGENTS.md memory synchronization.

## What It Shows

### 1. AGENTS.md Locations

Find all AGENTS.md files in the project:

```bash
find . -name "AGENTS.md" -not -path "*/node_modules/*" -not -path "*/.git/*"
```

Report:
- Root: `.ai/AGENTS.md` - [exists/missing]
- Subtrees found: `packages/core/AGENTS.md`, etc.

### 2. Section Status

For each AGENTS.md file, report sections:

```
.ai/AGENTS.md:
  AUTO-MANAGED sections:
    - project-description: 15 lines
    - build-commands: 25 lines
    - architecture: 40 lines
    - conventions: 20 lines
    - patterns: 10 lines
  MANUAL sections:
    - 1 section (never auto-modified)
  Total: 120 lines
```

### 3. Pending Changes

Check for files changed since last AGENTS.md modification:

```bash
# Get AGENTS.md last modified time
stat -f %m .ai/AGENTS.md

# Find files modified after AGENTS.md
find . -newer .ai/AGENTS.md -type f \
  -not -path "*/node_modules/*" \
  -not -path "*/.git/*" \
  -not -name "*.md"
```

Report:
```
Pending changes: 5 files modified since last sync
  - src/api/routes/new-endpoint.py
  - packages/core/src/agents/new-agent.ts
  - package.json
  - Makefile
  - src/services/auth.py
```

### 4. Drift Detection

Compare documented content against codebase:

- **Build commands**: Verify documented commands exist in config files
- **Architecture**: Check if documented directories still exist
- **Patterns**: Spot-check if documented patterns still appear in code

Report any drift:
```
Potential drift detected:
  - build-commands: "npm run legacy-test" not found in package.json
  - architecture: "src/deprecated/" directory no longer exists
```

### 5. Recommendations

Based on status, suggest actions:

```
Recommendations:
  - Run /auto-memory:sync to process 5 pending changes
  - Consider removing stale "legacy-test" command from build-commands
  - Architecture section needs update for removed directory
```

## Output Format

```
=== AGENTS.md Status ===

Files:
  Root: .ai/AGENTS.md (exists, 120 lines)
  Subtrees: 2 found
    - packages/core/AGENTS.md (75 lines)
    - packages/ui/AGENTS.md (60 lines)

Pending Changes: 5 files
  [list of files]

Drift Detected: 2 issues
  [list of issues]

Recommendations:
  [suggested actions]

Last sync: 2 hours ago
```

## Quick Actions

After viewing status, common follow-ups:
- `/auto-memory:sync` - Process pending changes
- `/auto-memory:init` - Rebuild from scratch (if major drift)
- Manual edit - Fix specific issues in MANUAL section
