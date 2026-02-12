---
description: Re-run analysis after fixes to verify improvements and check for regressions
---

# /refactor:verify

Re-run analysis on previously fixed areas to verify improvements and ensure no regressions were introduced.

## Usage

```bash
/refactor:verify                     # Verify all previous fix areas
/refactor:verify packages/core       # Verify specific scope
/refactor:verify --compare           # Compare with previous analysis
```

## Workflow

### Step 1: Load Previous Context

Check for previous analysis/fix context:

```typescript
// Look for previous findings in conversation context
// Or re-scan the same scope as last /refactor:analyze
```

If no previous context exists:
```markdown
No previous analysis found. Run `/refactor:analyze` first to establish baseline.
```

### Step 2: Re-Run Analysis

Execute same analysis pipeline as `/refactor:analyze`:

1. **Static Analysis**: ruff, ESLint, mypy, tsc
2. **LSP Diagnostics**: On files that were modified
3. **AST Patterns**: Check for remaining anti-patterns
4. **Type Coverage**: Verify type annotations are complete

### Step 3: Compare Results

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Critical Issues | N | N | -X |
| High Issues | N | N | -X |
| Medium Issues | N | N | -X |
| Low Issues | N | N | -X |
| **Total** | N | N | **-X** |

### Step 4: Check for Regressions

Identify any NEW issues that didn't exist before:

```typescript
// Compare current findings against baseline
const regressions = currentFindings.filter(f => !baselineFindings.includes(f))
```

### Step 5: Run Build Verification

```bash
# Python
cd packages/core
source ../../venv/bin/activate
make check  # lint + type-check + test

# TypeScript
cd packages/ui
pnpm lint
pnpm build
```

### Step 6: Generate Verification Report

## Output

### On Success (All Issues Fixed)

```markdown
# Verification Report

## Summary

All previously identified issues have been resolved.

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Critical | 5 | 0 | -100% |
| High | 12 | 0 | -100% |
| Medium | 23 | 8 | -65% |
| Low | 45 | 30 | -33% |

## Build Status

- Python lint: PASS
- Python types: PASS
- Python tests: PASS
- TypeScript lint: PASS
- TypeScript build: PASS

## Regressions

None detected.

## Remaining Issues

[List any intentionally unfixed items]

## Next Steps

- Review changes: `git diff`
- Commit when satisfied
- Consider running `/e2e:verify` for E2E test validation
```

### On Partial Success

```markdown
# Verification Report

## Summary

[X/Y] issues resolved. [Z] issues remaining.

## Fixed Issues

- [x] CRIT-001: Fixed unhandled exception
- [x] HIGH-003: Added missing type annotations

## Remaining Issues

- [ ] MED-005: Unused imports in 3 files (low impact)
- [ ] LOW-012: Missing docstrings (optional)

## Regressions

None detected.

## Recommendation

Continue with remaining fixes using `/refactor:fix` or accept current state.
```

### On Regression Detected

```markdown
# Verification Report - REGRESSIONS DETECTED

## Summary

Fixes introduced [N] new issues.

## Regressions

| Issue | File | Description |
|-------|------|-------------|
| REG-001 | `api/routes.py:45` | New type error after refactor |
| REG-002 | `components/Chat.tsx:120` | Missing import |

## Recommendation

1. Review regressions above
2. Fix regressions: `/refactor:fix --regressions`
3. Re-verify: `/refactor:verify`

Do NOT commit until regressions are resolved.
```

### On Error

```markdown
Verification failed.

**Error**: [error message]
**Phase**: [which step failed]

Check build logs and retry with `/refactor:verify`.
```

## Flags

| Flag | Description |
|------|-------------|
| `--compare` | Show detailed before/after comparison |
| `--quick` | Skip documentation verification (faster) |
| `--strict` | Fail if ANY issues remain (including LOW) |

## Integration

### After Successful Verification

Optionally run E2E tests:
```
/e2e:verify
```

Update documentation if architecture changed:
```
/auto-memory:sync
```

## Notes

- Verification uses the same analysis tools as `/refactor:analyze`
- Always verify before committing refactoring changes
- If regressions are detected, resolve them before proceeding
- Use `--strict` flag for pre-release verification
