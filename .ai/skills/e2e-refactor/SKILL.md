---
name: e2e-refactor
description: Deep codebase analysis for issues, optimization opportunities, best practice violations, and documentation drift. Reviews implementations against official docs, generates prioritized findings report, and executes fixes after user approval.
---

# E2E Refactor Skill

Comprehensive codebase review skill that analyzes implementations in depth, compares against official documentation and industry best practices, and generates actionable improvement plans.

## Guidelines

@guidelines.md

## When to Trigger

- User says "refactor", "review code", "analyze codebase", "check best practices"
- User says "audit code", "find issues", "code review", "technical debt"
- When preparing for major refactoring effort
- Before code freeze or release milestone
- Explicit commands: `/refactor:analyze`, `/refactor:plan`, `/refactor:fix`

## Algorithm Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         E2E REFACTOR FLOW                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 1: SCOPE DETECTION                                           │
│  └── Identify target files/modules                                  │
│                                                                     │
│  Phase 2: MULTI-LAYER ANALYSIS (Parallel)                          │
│  ├── Layer A: Static Analysis (ruff, ESLint, mypy, tsc)           │
│  ├── Layer B: LSP Diagnostics (real-time errors/warnings)         │
│  ├── Layer C: AST Pattern Analysis (anti-patterns, code smells)   │
│  └── Layer D: Documentation Verification (Context7/librarian)      │
│                                                                     │
│  Phase 3: FINDINGS SYNTHESIS                                        │
│  └── Dedupe, categorize, prioritize by severity + impact           │
│                                                                     │
│  Phase 4: REPORT PRESENTATION ─────────────┐                       │
│  └── Present to user with outline          │                       │
│                                             ▼                       │
│                                    ┌───────────────┐                │
│                                    │ USER APPROVAL │                │
│                                    │   REQUIRED    │                │
│                                    └───────┬───────┘                │
│                                             │                       │
│  Phase 5: FIX PLANNING ◄────────────────────┘                       │
│  └── Generate prioritized fix plan with tasks                       │
│                                                                     │
│  Phase 6: EXECUTION                                                 │
│  └── Apply fixes with verification, report results                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Phase 1: Scope Detection

### 1.1 Determine Analysis Scope

```bash
# Full codebase (default)
BACKEND_PATH="packages/core/src"
FRONTEND_PATH="packages/ui"

# Or user-specified scope
# /refactor:analyze packages/core/src/agents
```

### 1.2 Enumerate Target Files

```bash
# Python files
find packages/core/src -name "*.py" -type f | grep -v __pycache__ | grep -v .pyc

# TypeScript/React files
find packages/ui -name "*.ts" -o -name "*.tsx" | grep -v node_modules | grep -v .next
```

### 1.3 Identify Key Dependencies

From `pyproject.toml` and `package.json`:
- **Backend**: FastAPI, Pydantic, agent-squad, ollama, structlog
- **Frontend**: Next.js, React, shadcn/ui, Tailwind

## Phase 2: Multi-Layer Analysis

Run all analysis layers in parallel for efficiency.

### Layer A: Static Analysis

```bash
# Python (ruff)
cd packages/core
source ../../venv/bin/activate
ruff check src/ --output-format=json

# TypeScript (ESLint)
cd packages/ui
pnpm eslint . --format=json
```

### Layer B: Type Checking

```bash
# Python (mypy)
cd packages/core
source ../../venv/bin/activate
mypy src/ --show-error-codes --json

# TypeScript (tsc)
cd packages/ui
pnpm tsc --noEmit --pretty false 2>&1
```

### Layer C: LSP Diagnostics

```typescript
// Use lsp_diagnostics tool on key files
lsp_diagnostics({ filePath: "packages/core/src/api/app.py", severity: "all" })
lsp_diagnostics({ filePath: "packages/ui/app/page.tsx", severity: "all" })
```

### Layer D: AST Pattern Analysis

Use `ast_grep_search` to find anti-patterns:

```typescript
// Python anti-patterns
ast_grep_search({ pattern: "except: $$$", lang: "python" })  // Bare except
ast_grep_search({ pattern: "# type: ignore", lang: "python" })  // Type ignores
ast_grep_search({ pattern: "print($$$)", lang: "python" })  // Debug prints

// TypeScript anti-patterns
ast_grep_search({ pattern: "as any", lang: "typescript" })  // Type assertion to any
ast_grep_search({ pattern: "@ts-ignore", lang: "typescript" })  // TS ignores
ast_grep_search({ pattern: "// eslint-disable", lang: "typescript" })  // ESLint disables
ast_grep_search({ pattern: "console.log($$$)", lang: "typescript" })  // Debug logs
```

### Layer E: Documentation Verification

Use librarian agent to fetch official documentation:

```typescript
task(
  subagent_type="librarian",
  run_in_background=true,
  load_skills=[],
  description="Fetch FastAPI best practices",
  prompt="[CONTEXT]: Analyzing FastAPI implementation patterns in packages/core/src/api/
[GOAL]: Verify our implementation follows official FastAPI best practices
[DOWNSTREAM]: Compare our dependency injection, route organization, and error handling against docs
[REQUEST]: Find: FastAPI official docs on app structure, dependencies, exception handlers, middleware. Return concrete patterns we should follow."
)
```

Key frameworks to verify:
- **FastAPI**: Dependency injection, route organization, exception handling
- **Pydantic**: Model validation, field definitions, settings management
- **Next.js 14**: App Router patterns, server components, data fetching
- **React**: Hook patterns, component composition, state management
- **shadcn/ui**: Component usage, theming, accessibility

## Phase 3: Findings Synthesis

### 3.1 Categorize Issues

| Category | Description | Examples |
|----------|-------------|----------|
| **CRITICAL** | Bugs, security issues, data corruption risks | Unhandled exceptions, SQL injection, type errors |
| **HIGH** | Performance issues, major anti-patterns | N+1 queries, memory leaks, blocking I/O |
| **MEDIUM** | Best practice violations, code smells | Missing types, unused imports, complexity |
| **LOW** | Style issues, minor improvements | Naming conventions, documentation gaps |

### 3.2 Deduplicate Findings

Same issue reported by multiple tools → keep highest severity, combine evidence.

### 3.3 Prioritize by Impact

Within each severity level, rank by:
1. **Blast radius**: How many files/features affected?
2. **Fix complexity**: Simple fix vs. major refactor?
3. **Risk**: Breaking change potential?

## Phase 4: Report Presentation

Generate structured report using @report-templates.md

### Report Format

```markdown
# E2E Refactor Analysis Report

**Scope**: [analyzed paths]
**Files Analyzed**: [count]
**Analysis Date**: [timestamp]

## Summary

| Severity | Count | Categories |
|----------|-------|------------|
| CRITICAL | N | [list] |
| HIGH | N | [list] |
| MEDIUM | N | [list] |
| LOW | N | [list] |

## Critical Issues (Must Fix)

### [Issue Title]
- **Location**: `path/to/file.py:42`
- **Source**: [ruff | mypy | AST | LSP | docs]
- **Description**: [what's wrong]
- **Evidence**: [code snippet or error message]
- **Official Pattern**: [what the docs say]
- **Suggested Fix**: [how to fix]

## High Priority Issues
[Same format]

## Medium Priority Issues
[Same format]

## Low Priority Issues (Optional)
[Same format]
```

### Await User Approval

**STOP and present report to user. Do NOT proceed to Phase 5 without explicit approval.**

```markdown
---

## Approval Required

I've identified [N] issues across [M] files. The breakdown:
- CRITICAL: [count] (recommend immediate fix)
- HIGH: [count] (recommend fixing before release)
- MEDIUM: [count] (recommend fixing when time permits)
- LOW: [count] (optional improvements)

**Options:**
1. Approve all → I'll create a fix plan and execute
2. Approve by severity → Specify which levels to fix
3. Review specific issues → Ask about any finding
4. Cancel → No changes will be made

What would you like to do?
```

## Phase 5: Fix Planning

After user approval, generate detailed fix plan:

### 5.1 Group Related Fixes

Fixes that affect same files → batch together to avoid conflicts.

### 5.2 Order by Dependencies

```
1. Fix type errors first (they may cause other issues)
2. Fix import issues
3. Fix structural issues
4. Fix pattern violations
5. Fix style issues
```

### 5.3 Generate Todo List

```typescript
todowrite({
  todos: [
    { id: "fix-1", content: "Fix: [Critical Issue 1]", status: "pending", priority: "high" },
    { id: "fix-2", content: "Fix: [Critical Issue 2]", status: "pending", priority: "high" },
    // ...
  ]
})
```

### 5.4 Present Fix Plan

```markdown
## Fix Plan

### Batch 1: Critical Fixes (estimated: 10 min)
- [ ] Fix unhandled exception in `api/routes/chat.py`
- [ ] Add missing type annotation in `agents/base.py`

### Batch 2: High Priority (estimated: 15 min)
- [ ] Replace `as any` with proper types in 3 files
- [ ] Add error boundaries to React components

### Batch 3: Medium Priority (estimated: 20 min)
- [ ] Remove unused imports across 12 files
- [ ] Add missing docstrings to public APIs

Proceed with execution?
```

## Phase 6: Execution

### 6.1 Apply Fixes

For each fix:
1. Read current file state
2. Apply fix using appropriate tool (edit, ast_grep_replace, etc.)
3. Run `lsp_diagnostics` to verify no new issues introduced
4. Mark todo as complete

### 6.2 Verify After Each Batch

```bash
# After Python fixes
cd packages/core && make check

# After TypeScript fixes
cd packages/ui && pnpm lint && pnpm build
```

### 6.3 Report Results

```markdown
## Execution Complete

### Successfully Fixed
- [x] [Issue 1]: Fixed in `path/file.py`
- [x] [Issue 2]: Fixed in `path/file.tsx`

### Verification
- Python lint: PASS
- Python types: PASS
- TypeScript lint: PASS
- TypeScript build: PASS

### Remaining Issues
- [ ] [Issue requiring manual fix]: Reason

### Next Steps
- Review changes with `git diff`
- Run full test suite: `make test`
- Commit when satisfied
```

## Commands

| Command | Description |
|---------|-------------|
| `/refactor:analyze` | Run full analysis, present findings report |
| `/refactor:analyze [path]` | Analyze specific path only |
| `/refactor:plan` | Generate fix plan from existing findings |
| `/refactor:fix` | Execute approved fix plan |
| `/refactor:fix [category]` | Fix only specific category (critical, high, etc.) |
| `/refactor:verify` | Re-run analysis to check improvements |

## Escalation Triggers

- **>50 critical issues**: Warn user about codebase health, suggest incremental approach
- **External dependency issues**: Flag but don't attempt to fix
- **Conflicting patterns**: Ask user to clarify which pattern to follow
- **>3 failed fix attempts**: Stop and report, await user guidance

## Integration with Other Skills

### With e2e-verify
After fixes, optionally run E2E tests to ensure no regressions:
```
skill("e2e-verify") → /e2e:verify
```

### With auto-memory
If refactoring changes architecture or patterns:
```
skill("auto-memory") → /auto-memory:sync
```
