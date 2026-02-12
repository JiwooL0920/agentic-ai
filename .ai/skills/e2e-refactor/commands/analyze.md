---
description: Run comprehensive codebase analysis and present findings report
---

# /refactor:analyze

Run multi-layer analysis on the codebase, synthesize findings, and present a prioritized report.

## Usage

```bash
/refactor:analyze                    # Full codebase analysis
/refactor:analyze packages/core      # Backend only
/refactor:analyze packages/ui        # Frontend only
/refactor:analyze src/agents         # Specific module
```

## Workflow

### Step 1: Determine Scope

```bash
# If no path specified, analyze full codebase
SCOPE="${1:-packages/core packages/ui}"

# Enumerate files
find $SCOPE -name "*.py" -o -name "*.ts" -o -name "*.tsx" | \
  grep -v node_modules | \
  grep -v __pycache__ | \
  grep -v .next | \
  grep -v dist
```

Report: "Analyzing [N] files in [scope]..."

### Step 2: Run Static Analysis (Parallel)

**Python**:
```bash
cd packages/core
source ../../venv/bin/activate
ruff check src/ --output-format=json 2>&1
mypy src/ --json 2>&1
```

**TypeScript**:
```bash
cd packages/ui
pnpm eslint . --format=json 2>&1
pnpm tsc --noEmit 2>&1 | grep -E "error TS"
```

### Step 3: Run LSP Diagnostics

For each key file:
```typescript
lsp_diagnostics({ filePath: "packages/core/src/api/app.py", severity: "all" })
lsp_diagnostics({ filePath: "packages/core/src/agents/base.py", severity: "all" })
lsp_diagnostics({ filePath: "packages/ui/app/page.tsx", severity: "all" })
// ... other key files
```

### Step 4: Run AST Pattern Detection

```typescript
// Python anti-patterns
ast_grep_search({ pattern: "except: $$$", lang: "python", paths: ["packages/core"] })
ast_grep_search({ pattern: "# type: ignore", lang: "python", paths: ["packages/core"] })
ast_grep_search({ pattern: "print($$$)", lang: "python", paths: ["packages/core"] })

// TypeScript anti-patterns
ast_grep_search({ pattern: "as any", lang: "typescript", paths: ["packages/ui"] })
ast_grep_search({ pattern: "@ts-ignore", lang: "typescript", paths: ["packages/ui"] })
ast_grep_search({ pattern: "console.log($$$)", lang: "typescript", paths: ["packages/ui"] })
```

### Step 5: Fetch Documentation (Background)

Launch librarian agents for key frameworks:

```typescript
// FastAPI
task(subagent_type="librarian", run_in_background=true, ...)

// Pydantic
task(subagent_type="librarian", run_in_background=true, ...)

// Next.js 14
task(subagent_type="librarian", run_in_background=true, ...)
```

### Step 6: Synthesize Findings

1. **Collect** all results from steps 2-5
2. **Deduplicate**: Same issue from multiple sources → keep one, note sources
3. **Categorize**: Map to severity (CRITICAL/HIGH/MEDIUM/LOW)
4. **Prioritize**: Within severity, rank by impact
5. **Generate IDs**: CRIT-001, HIGH-001, MED-001, LOW-001

### Step 7: Generate Report

Use template from @report-templates.md to create structured report.

### Step 8: Present and Await Approval

**CRITICAL**: Do not proceed past this step without user approval.

Present the report with approval options:
1. Approve all
2. Approve by severity
3. Review specific issue
4. Cancel

## Output

### On Success

```markdown
# E2E Refactor Analysis Report

[Full report content]

---

## Approval Required

I've identified [N] issues. What would you like to do?
```

### On Error

```markdown
Analysis failed.

**Error**: [error message]
**Phase**: [which step failed]
**Partial Results**: [any findings before failure]

Retry with `/refactor:analyze` or narrow scope.
```

## Notes

- Analysis typically takes 1-3 minutes depending on codebase size
- Background librarian tasks may complete after initial report; findings update accordingly
- Large codebases (>500 files) may hit tool limits; use scoped analysis
