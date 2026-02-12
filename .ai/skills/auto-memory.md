# Auto-Memory Skill

## Purpose
Keep `.ai/AGENTS.md` in sync as the codebase evolves. When you make significant changes, update the relevant sections.

## When to Update AGENTS.md

Update `.ai/AGENTS.md` when you:
- Add new commands, scripts, or make targets
- Create new modules, packages, or significant files
- Change build/test/lint commands
- Add new dependencies or tools
- Modify project structure
- Establish new patterns or conventions

**Do NOT update for:**
- Bug fixes within existing code
- Minor refactors
- Test additions for existing features
- Documentation-only changes

## Update Process

1. After completing a feature/change, check if it affects project knowledge
2. If yes, edit the relevant section in `.ai/AGENTS.md`
3. Keep updates concise — focus on what an AI agent needs to know
4. Preserve existing structure and formatting

## AGENTS.md Sections

| Section | Update When |
|---------|-------------|
| **Build & Development Commands** | New make targets, scripts, commands |
| **Project Structure** | New directories, significant file reorganization |
| **Coding Standards** | New patterns, conventions, style rules |
| **Tech Stack** | New dependencies, tools, frameworks |
| **Common Gotchas** | Discovered pitfalls, non-obvious behaviors |

## Example Update

After adding a new `make deploy` command:

```markdown
### Backend (packages/core)

```bash
make deploy              # Deploy to production (NEW)
```
```

## Slash Command

Use `/update-agents` to trigger a review of recent changes and update `.ai/AGENTS.md` accordingly.
