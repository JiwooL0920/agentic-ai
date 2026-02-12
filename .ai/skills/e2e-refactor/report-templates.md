# Report Templates

Templates for presenting findings and fix plans in a structured, actionable format.

## Finding Report Template

```markdown
# E2E Refactor Analysis Report

**Generated**: [ISO timestamp]
**Scope**: [analyzed paths]
**Files Analyzed**: [count]
**Duration**: [time taken]

---

## Executive Summary

| Severity | Count | Top Categories |
|----------|-------|----------------|
| CRITICAL | N | Type errors, Security |
| HIGH | N | Async issues, Error handling |
| MEDIUM | N | Best practices, Code quality |
| LOW | N | Style, Documentation |

**Health Score**: [X/100] based on issue density and severity weighting.

---

## Critical Issues (Immediate Action Required)

### CRIT-001: [Issue Title]

| Field | Value |
|-------|-------|
| **Location** | `path/to/file.py:42` |
| **Category** | Type Safety / Security / Error Handling |
| **Source** | mypy / ruff / AST / LSP |
| **Impact** | [What breaks if not fixed] |

**Code**:
\`\`\`python
# Current (problematic)
def process(data):  # Missing return type, missing param type
    return data["value"]
\`\`\`

**Official Pattern**:
> From FastAPI docs: "Always use type hints for dependency injection to work correctly"

**Suggested Fix**:
\`\`\`python
def process(data: Dict[str, Any]) -> str:
    return data["value"]
\`\`\`

**Effort**: ~2 min | **Risk**: Low

---

### CRIT-002: [Next Issue]
[Same format]

---

## High Priority Issues

### HIGH-001: [Issue Title]
[Same format as Critical]

---

## Medium Priority Issues

### MED-001: [Issue Title]

| Field | Value |
|-------|-------|
| **Location** | `path/to/file.tsx:128` |
| **Category** | Best Practices |
| **Source** | ESLint |

**Issue**: [Brief description]
**Fix**: [Brief solution]
**Effort**: ~5 min

---

## Low Priority Issues (Optional)

| ID | Location | Issue | Fix |
|----|----------|-------|-----|
| LOW-001 | `file.py:10` | Missing docstring | Add docstring |
| LOW-002 | `file.tsx:25` | Console.log | Remove debug |
| LOW-003 | `file.py:42` | Magic number | Extract constant |

---

## Documentation Gaps

| File/Module | Issue | Reference |
|-------------|-------|-----------|
| `agents/base.py` | Not following agent-squad patterns | [Link to docs] |
| `api/routes/chat.py` | FastAPI exception handling | [Link to docs] |

---

## Metrics Comparison (Optional)

If previous analysis exists:

| Metric | Previous | Current | Change |
|--------|----------|---------|--------|
| CRITICAL | 5 | 3 | -2 |
| HIGH | 12 | 8 | -4 |
| Type coverage | 78% | 85% | +7% |

---

## Approval Section

I've completed the analysis. Summary:

- **CRITICAL**: [N] issues requiring immediate fix
- **HIGH**: [N] issues to fix before release
- **MEDIUM**: [N] best practice improvements
- **LOW**: [N] optional enhancements

### Options

1. **Approve All** → Create fix plan for all [N] issues
2. **Approve Critical+High Only** → Focus on [N] high-impact issues
3. **Approve by Category** → "Fix only type safety issues"
4. **Review Specific Issue** → "Tell me more about CRIT-002"
5. **Cancel** → No changes will be made

What would you like to do?
```

---

## Fix Plan Template

```markdown
# Fix Plan

**Based on**: Analysis Report [timestamp]
**Approved Scope**: [what user approved]
**Estimated Time**: [total estimate]

---

## Execution Order

Fixes are grouped to minimize conflicts and verify incrementally.

### Batch 1: Critical Fixes
**Estimated**: 10 min | **Files**: 3 | **Risk**: Low

| # | Issue | File | Fix Summary |
|---|-------|------|-------------|
| 1 | CRIT-001 | `api/routes/chat.py:42` | Add type annotations |
| 2 | CRIT-002 | `agents/base.py:88` | Add error handling |
| 3 | CRIT-003 | `api/dependencies/auth.py:15` | Fix async pattern |

**Verification after batch**:
\`\`\`bash
cd packages/core && make check
\`\`\`

---

### Batch 2: High Priority Fixes
**Estimated**: 15 min | **Files**: 5 | **Risk**: Low-Medium

| # | Issue | File | Fix Summary |
|---|-------|------|-------------|
| 4 | HIGH-001 | `components/chat.tsx:156` | Add error boundary |
| 5 | HIGH-002 | `hooks/useChat.ts:42` | Fix promise handling |
| ... | ... | ... | ... |

**Verification after batch**:
\`\`\`bash
cd packages/ui && pnpm lint && pnpm build
\`\`\`

---

### Batch 3: Medium Priority Fixes
**Estimated**: 20 min | **Files**: 12 | **Risk**: Low

[Same format]

---

## Dependencies

Some fixes must be applied in order:

```
CRIT-001 → HIGH-003 (HIGH-003 uses types from CRIT-001)
CRIT-002 → MED-005 (MED-005 depends on error handling from CRIT-002)
```

---

## Skipped Items

| Issue | Reason |
|-------|--------|
| MED-012 | Requires architectural decision |
| HIGH-008 | External dependency, flagged for manual review |

---

## Rollback Plan

If issues arise:
\`\`\`bash
git stash  # Before starting
git stash pop  # If need to rollback
\`\`\`

---

Ready to execute?
```

---

## Execution Report Template

```markdown
# Execution Report

**Started**: [timestamp]
**Completed**: [timestamp]
**Duration**: [time]

---

## Results Summary

| Status | Count |
|--------|-------|
| Fixed | N |
| Partially Fixed | N |
| Skipped | N |
| Failed | N |

---

## Fixed Issues

| Issue | File | Action Taken |
|-------|------|--------------|
| CRIT-001 | `api/routes/chat.py` | Added type annotations |
| CRIT-002 | `agents/base.py` | Added exception handler |
| HIGH-001 | `components/chat.tsx` | Added ErrorBoundary wrapper |

---

## Verification Results

### Python (packages/core)

| Check | Result |
|-------|--------|
| ruff lint | PASS (0 errors) |
| mypy types | PASS (0 errors) |
| pytest | PASS (47 passed) |

### TypeScript (packages/ui)

| Check | Result |
|-------|--------|
| ESLint | PASS (0 errors) |
| tsc --noEmit | PASS |
| next build | PASS |

---

## Issues Requiring Manual Attention

| Issue | Reason | Suggested Action |
|-------|--------|------------------|
| HIGH-008 | Requires dependency upgrade | Run `pnpm update X` separately |
| MED-012 | Architecture decision needed | Discuss with team |

---

## Changes Made

\`\`\`bash
# View all changes
git diff

# Files modified
git diff --name-only
\`\`\`

**Files changed**: [count]

---

## Next Steps

1. Review changes: `git diff`
2. Run full test suite: `make test`
3. Commit when satisfied: `git add . && git commit -m "refactor: fix [N] code quality issues"`
4. (Optional) Re-run analysis to verify improvement: `/refactor:verify`
```

---

## Issue Card Template (Compact)

For inline presentation of individual issues:

```markdown
> **CRIT-001** | `api/routes/chat.py:42` | Type Safety
> 
> Missing return type annotation on public API endpoint.
> 
> ```python
> # Before
> async def chat_stream(request: ChatRequest):
> 
> # After  
> async def chat_stream(request: ChatRequest) -> StreamingResponse:
> ```
> 
> **Source**: mypy | **Effort**: 1 min | **Risk**: None
```

---

## Progress Indicator Template

For showing real-time progress during execution:

```markdown
## Execution Progress

[████████████░░░░░░░░] 60% (12/20 issues)

**Current**: Fixing HIGH-005 in `hooks/useChat.ts`
**Completed**: 12 | **Remaining**: 8 | **Failed**: 0

Last completed:
- ✅ CRIT-001: Added type annotations
- ✅ CRIT-002: Fixed exception handler
- ✅ HIGH-001: Added error boundary
```
