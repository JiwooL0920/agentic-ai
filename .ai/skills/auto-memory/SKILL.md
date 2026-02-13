---
name: auto-memory
description: Automatically keep AGENTS.md in sync with codebase changes. Use after completing significant work (new features, refactors, architecture changes) to update project documentation. Triggers on /auto-memory commands or when AI detects documentation drift.
---

# Auto-Memory Skill

Automatically maintain AGENTS.md documentation as the codebase evolves. Adapted for OpenCode/Cursor environments without hook support.

## Guidelines

**MANDATORY**: All rules below must be followed exactly. Violations produce incorrect AGENTS.md content.

@guidelines.md

## Self-Trigger Protocol

Since OpenCode/Cursor lack hooks, the AI must self-trigger updates at appropriate times.

### When to Trigger

**MUST trigger after:**
- Adding new features or modules
- Refactoring architecture (new dirs, renamed components)
- Adding/changing build commands (package.json, Makefile, pyproject.toml)
- Modifying significant patterns or conventions
- Adding new dependencies that affect workflows

**DO NOT trigger for:**
- Bug fixes that don't change architecture
- Test additions that don't reveal new patterns
- Documentation-only changes
- Minor refactors within existing patterns

### Trigger Checklist (End of Task)

Ask yourself:
1. Did I create new directories or rename existing ones?
2. Did I add/modify build, test, or lint commands?
3. Did I introduce new coding patterns used 3+ times?
4. Did I add dependencies that change developer workflow?

If YES to any: Run the update algorithm below.

## Algorithm

1. **Identify changed files**: Recall files modified during the session or use git:
   ```bash
   git diff --name-only HEAD~1      # Recent commits
   git diff --name-only             # Uncommitted changes
   ```

2. **Categorize changes**: Map files to AGENTS.md sections:

   | File Type | Section |
   |-----------|---------|
   | README, root configs | `project-description` |
   | package.json, Makefile, pyproject.toml | `build-commands` |
   | New directories, structural changes | `architecture` |
   | Source files with patterns | `conventions`, `patterns` |
   | Significant commits | `git-insights` |

3. **Analyze impact**: Determine what needs updating:
   - New build commands added?
   - Architecture changed (new dirs, renamed components)?
   - New coding patterns detected (3+ occurrences)?
   - Dependencies added/removed?

4. **Verify before removing**: Before removing documented content:
   - Use grep to search codebase for the item
   - Exclude: node_modules, vendor, .git, __pycache__
   - If item exists elsewhere: keep it
   - If item not found anywhere: mark for removal

5. **Update AGENTS.md**: Modify relevant sections:
   - Preserve AUTO-MANAGED markers
   - Never touch MANUAL sections
   - Apply content rules (specific, concise, structured)

6. **Validate**: Ensure updates follow guidelines:
   - No generic instructions added
   - Specific and actionable content
   - Proper markdown formatting

## Marker Syntax

AGENTS.md uses HTML comment markers for selective updates:

```markdown
<!-- AUTO-MANAGED: section-name -->
## Section Heading

Content that will be automatically updated

<!-- END AUTO-MANAGED -->

<!-- MANUAL -->
## Custom Notes

Content that will never be touched

<!-- END MANUAL -->
```

**CRITICAL**: Use the EXACT format above. Do NOT use variations:
- `<!-- BEGIN AUTO-MANAGED: name -->` - WRONG (no BEGIN prefix)
- `<!-- END AUTO-MANAGED: name -->` - WRONG (no name in closing tag)
- `<!-- AUTO-MANAGED section-name -->` - WRONG (missing colon)

## Section Names

### Root AGENTS.md Sections

| Section | Purpose | Update Triggers |
|---------|---------|-----------------|
| `project-description` | Project overview | README changes, major refactors |
| `build-commands` | Build, test, lint commands | package.json, Makefile, pyproject.toml |
| `architecture` | Directory structure, components | New dirs, renamed files, structural changes |
| `conventions` | Naming, imports, code standards | Pattern changes in source files |
| `patterns` | AI-detected coding patterns | Repeated patterns across files |
| `git-insights` | Decisions from git history | Significant commits |
| `best-practices` | Project-specific best practices | Manual updates only |

### Subtree AGENTS.md Sections (for monorepos)

| Section | Purpose | Update Triggers |
|---------|---------|-----------------|
| `module-description` | Module purpose | Module README, major changes |
| `architecture` | Module structure | File changes within module |
| `conventions` | Module-specific conventions | Pattern changes in module |
| `dependencies` | Key module dependencies | Import changes, package updates |

## Content Rules

- **Be specific**: "Use 2-space indentation" not "Format code properly"
- **Include commands**: Build, test, lint, dev commands
- **Document patterns**: Code style, naming conventions, architectural decisions
- **Keep concise**: Target < 500 lines; use imports for detailed specs
- **Use structure**: Bullet points under descriptive markdown headings
- **Stay current**: Remove outdated information when updating
- **Avoid generic**: No "follow best practices" or "write clean code"
- **Exclude moving targets**: Never include:
  - Version numbers (e.g., "v1.2.3")
  - Test counts or coverage percentages
  - Progress metrics or dates
  - Any metrics that become stale after each commit

## Token Efficiency

- Keep sections concise - bullet points, not paragraphs
- Use imports (`@path/to/file`) for detailed specs
- Size limits: Root 150-200 lines, Subtrees 50-75 lines

## Output

Return a brief summary:
- "Updated [section names] in AGENTS.md based on changes to [file names]"
- "Removed [pattern] from [section] - no longer used in codebase"
- "No updates needed - changes do not affect documented sections"

## Commands

- `/auto-memory:init` - Initialize AGENTS.md with auto-managed markers
- `/auto-memory:sync` - Sync AGENTS.md with recent git changes
- `/auto-memory:status` - Show sync status and pending changes

---

## Branch Context Auto-Generation

In addition to manual AGENTS.md updates, this project has **automatic branch context generation** via a pre-commit hook.

### How It Works

On every `git commit`, the `.husky/pre-commit` hook:

1. Detects the current branch name
2. Gathers staged files, diff stats, and commit history
3. Calls `opencode` to generate an AI summary
4. Creates/updates `.ai/AGENTS/AGENTS-<branch>.md`
5. Auto-stages the context file so it's included in the commit

### Generated Files Location

```
.ai/AGENTS/
├── AGENTS-main.md           # Main branch context
├── AGENTS-feature-auth.md   # Feature branch context
├── AGENTS-fix-memory-leak.md
└── ...
```

### Skip Conditions

The hook skips generation when:
- `SKIP_BRANCH_CONTEXT=1` environment variable is set
- `CI=1` (running in CI/CD)
- No staged files
- Detached HEAD state
- `opencode` CLI not available (falls back to minimal template)

### Manual Override

```bash
# Skip for a single commit
SKIP_BRANCH_CONTEXT=1 git commit -m "quick fix"

# Generate context manually
opencode -p "Generate branch context for $(git branch --show-current)"
```

### Prompt Template

The prompt for context generation is at `.ai/prompts/branch-context.md`. Modify it to change what information is captured.

### Integration with AGENTS.md

The root `.ai/AGENTS.md` should reference branch context files:

```markdown
## Branch-Specific Context

For detailed context on active development branches, see files in `.ai/AGENTS/`:
- Each file follows naming: `AGENTS-<branch-name>.md`
- Auto-generated on each commit via pre-commit hook
- Contains: branch purpose, progress, recent changes, files modified, next steps
```
