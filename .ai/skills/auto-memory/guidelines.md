# Auto-Memory Guidelines

Guidelines for maintaining AGENTS.md documentation in OpenCode/Cursor environments.

## Memory Scope

This skill manages **project-level** AGENTS.md files:
- **Project Root**: `./.ai/AGENTS.md` - team-shared, version controlled
- **Subtree**: `./packages/*/AGENTS.md`, `./apps/*/AGENTS.md` - module-specific docs

## Content Rules

- **Be specific**: "Use 2-space indentation" not "Format code properly"
- **Include commands**: Build, test, lint, dev commands with exact syntax
- **Document patterns**: Code style, naming conventions, architectural decisions
- **Keep concise**: Target < 500 lines; use imports for detailed specs
- **Use structure**: Bullet points under descriptive markdown headings
- **Stay current**: Remove outdated information when updating
- **Avoid generic**: No "follow best practices" or "write clean code"
- **Exclude moving targets**: Never include ephemeral data:
  - Version numbers (e.g., "v1.2.3", "0.6.0")
  - Test counts or coverage percentages (e.g., "74 tests", "85% coverage")
  - Progress metrics (e.g., "3/5 complete", "TODO: 12 items")
  - Dates or timestamps (e.g., "last updated 2024-01-15")
  - Line counts or file sizes
  - Any metrics that become stale after each commit

## Marker Format

AGENTS.md files use HTML comment markers for selective updates:

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
- `<!-- AUTO-MANAGED section-name -->` - WRONG (missing colon after AUTO-MANAGED)

## Key Distinctions

### Conventions vs Patterns

- **conventions**: Explicit rules humans decided (naming, imports, formatting)
- **patterns**: Implicit patterns AI detected from recurring code structures

### When to Update vs Remove

**Update when:**
- New patterns appear 3+ times in codebase
- Build commands change in config files
- Directory structure changes

**Remove when:**
- Pattern no longer exists anywhere (verify with grep)
- Command no longer in any config file
- Directory/file was deleted

**Always verify before removing:**
```bash
# Search for pattern before removing from docs
grep -r "pattern" src/ --exclude-dir={node_modules,vendor,.git}
```

## Stale Command Detection

Compare documented commands against commands that actually executed successfully:

| Documented | Actually Worked | Action |
|------------|-----------------|--------|
| `python pytest` | `python -m pytest` | Update |
| `npm test` | `npm run test` | Update |
| `pytest tests/` | `uv run pytest` | Update |

Source: Successful terminal executions from session or git history.

## Import System

- Syntax: `@path/to/import` for including other files
- Supports relative paths from AGENTS.md location
- Use imports for detailed specs to keep main file concise

## Size Guidelines

| File | Target Lines | Max Lines |
|------|--------------|-----------|
| Root AGENTS.md | 150-200 | 500 |
| Subtree AGENTS.md | 50-75 | 150 |

If exceeding limits, use imports to split content.
