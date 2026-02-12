---
description: Initialize AGENTS.md memory structure for project with interactive wizard
---

# /auto-memory:init

Initialize auto-managed AGENTS.md memory files for this project.

## Prerequisites

- Project should have `.ai/` directory (created by LNAI)
- Git repository recommended for change detection

## Workflow

### Step 1: Check Existing AGENTS.md

If `.ai/AGENTS.md` already exists, ask the user:

**Question**: "AGENTS.md already exists. How should I handle it?"

**Options**:
- **Migrate**: Convert existing content to auto-managed format (add markers around existing sections)
- **Backup**: Create AGENTS.md.backup and generate fresh
- **Merge**: Keep existing content as MANUAL section, add auto-managed sections
- **Cancel**: Abort initialization

### Step 2: Scan Directory Structure

Detect frameworks and build systems:

| File | Framework |
|------|-----------|
| `package.json` | Node.js/JavaScript |
| `pyproject.toml`, `setup.py` | Python |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `Makefile` | Make-based builds |
| `Dockerfile` | Container builds |

Extract build/test/lint commands from config files.

### Step 3: Identify Subtree Candidates (Monorepos)

Look for boundaries that warrant separate AGENTS.md files:
- `packages/*` (monorepo packages)
- `apps/*` (monorepo applications)
- `src/` with distinct modules
- Any directory with its own package.json/pyproject.toml

### Step 4: Detect Code Patterns

Analyze source files for conventions:
- **Naming**: PascalCase, camelCase, snake_case usage
- **Imports**: ES6 modules, CommonJS, ordering patterns
- **Architecture**: Feature-based, layered, MVC patterns
- **Style**: Indentation (2 vs 4 spaces), quotes, semicolons

### Step 5: Present Findings

Summarize detected information and confirm:
- Detected framework(s) and commands
- Suggested subtree locations (if monorepo)
- Detected patterns and conventions

Ask: "Should I generate AGENTS.md with these findings?"

### Step 6: Generate AGENTS.md

Create `.ai/AGENTS.md` with auto-managed sections:

```markdown
# Project Name

<!-- AUTO-MANAGED: project-description -->
## Overview

[Detected from README or package.json]

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: build-commands -->
## Build & Development Commands

[Extracted from config files]

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

[Directory structure analysis]

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Code Conventions

[Detected patterns]

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: patterns -->
## Detected Patterns

[AI-detected recurring patterns]

<!-- END AUTO-MANAGED -->

<!-- MANUAL -->
## Project-Specific Notes

Add custom notes here. This section is never auto-modified.

<!-- END MANUAL -->
```

### Step 7: Create Subtree Files (if applicable)

For each identified subtree, create `packages/name/AGENTS.md`:

```markdown
# Package Name

<!-- AUTO-MANAGED: module-description -->
## Purpose

[Module description]

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Module Architecture

[Module structure]

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Module Conventions

[Module-specific patterns]

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: dependencies -->
## Key Dependencies

[Module dependencies]

<!-- END AUTO-MANAGED -->
```

## Output

Report:
- Files created/modified
- Sections populated
- Suggested next steps (e.g., "Run /auto-memory:status to verify")
