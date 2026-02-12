---
description: Execute approved fix plan with verification
---

# /refactor:fix

Execute the approved fix plan, applying changes with incremental verification.

## Usage

```bash
/refactor:fix                      # Execute full plan
/refactor:fix batch-1              # Execute specific batch
/refactor:fix CRIT-001             # Fix specific issue
/refactor:fix --dry-run            # Show what would change without applying
```

## Prerequisites

- Fix plan must exist (`/refactor:plan`)
- User must have approved the plan

If no plan exists:
```
No fix plan found. Run `/refactor:plan` first.
```

## Workflow

### Step 1: Load Fix Plan

Retrieve the approved fix plan from planning phase.

Validate:
- [ ] All referenced files still exist
- [ ] No conflicting changes since planning
- [ ] Dependencies still valid

### Step 2: Prepare Rollback Point

```bash
# Stash any uncommitted changes
git stash --include-untracked -m "pre-refactor-backup"

# Or create savepoint
git rev-parse HEAD > .refactor-checkpoint
```

### Step 3: Execute Batches

For each batch in order:

#### 3.1 Mark Batch In Progress

```typescript
todowrite({ todos: [
  { id: "fix-batch-1", content: "Batch 1: Critical Fixes", status: "in_progress", priority: "high" },
  // ...
]})
```

#### 3.2 Apply Fixes in Batch

For each fix in the batch:

```typescript
// 1. Read current file
read({ filePath: "path/to/file.py" })

// 2. Apply fix using appropriate tool
edit({
  filePath: "path/to/file.py",
  oldString: "...",
  newString: "..."
})

// OR for pattern-based fixes
ast_grep_replace({
  pattern: "except: $$$",
  rewrite: "except Exception as e: $$$",
  lang: "python",
  paths: ["path/to/file.py"],
  dryRun: false
})

// 3. Verify with LSP
lsp_diagnostics({ filePath: "path/to/file.py", severity: "error" })

// 4. Mark todo complete
todowrite({ todos: [
  { id: "fix-crit-001", status: "completed", ... }
]})
```

#### 3.3 Verify Batch

After all fixes in batch:

**Python batch**:
```bash
cd packages/core
source ../../venv/bin/activate
ruff check src/  # Should pass
mypy src/        # Should pass or improve
```

**TypeScript batch**:
```bash
cd packages/ui
pnpm lint        # Should pass
pnpm tsc --noEmit  # Should pass
```

#### 3.4 Report Batch Status

```markdown
## Batch 1 Complete

| Issue | Status | Notes |
|-------|--------|-------|
| CRIT-001 | Fixed | Added return type |
| CRIT-002 | Fixed | Added exception handler |
| CRIT-003 | Skipped | Requires manual review |

**Verification**: PASS

Proceeding to Batch 2...
```

### Step 4: Run Full Verification

After all batches:

```bash
# Python
cd packages/core
make check  # lint + type + test

# TypeScript
cd packages/ui
pnpm lint && pnpm build
```

### Step 5: Generate Execution Report

Use template from @report-templates.md:

```markdown
# Execution Report

**Duration**: [time]
**Fixed**: [count]
**Skipped**: [count]
**Failed**: [count]

## Verification Results
...

## Next Steps
...
```

## Failure Handling

### Single Fix Failure

```markdown
**Fix CRIT-003 failed**

Error: [error message]

Options:
1. Skip and continue
2. Retry with different approach
3. Stop execution
```

### Batch Verification Failure

```markdown
**Batch 2 verification failed**

Command: `pnpm lint`
Exit code: 1
Output: [error output]

Options:
1. Rollback batch and stop
2. Review and fix manually
3. Continue anyway (not recommended)
```

### >3 Consecutive Failures

**STOP execution automatically.**

```markdown
**Execution halted**

3 consecutive failures detected. This indicates a systematic issue.

**Last 3 failures**:
1. [issue]: [error]
2. [issue]: [error]
3. [issue]: [error]

**Action required**: Review manually before continuing.

To resume: `/refactor:fix --continue`
To rollback: `git stash pop`
```

## Dry Run Mode

`/refactor:fix --dry-run` shows what would change without applying:

```markdown
# Dry Run Report

## Would Apply

| Issue | File | Change Preview |
|-------|------|----------------|
| CRIT-001 | `api/chat.py:42` | +return type |
| CRIT-002 | `agents/base.py:88` | +exception handler |

## Would Skip

| Issue | Reason |
|-------|--------|
| HIGH-008 | External dependency |

No files were modified.
```

## Output

### On Success

```markdown
# Execution Complete

All fixes applied successfully.

**Fixed**: 15/15
**Verification**: PASS

## Next Steps
1. Review: `git diff`
2. Test: `make test`
3. Commit: `git add . && git commit -m "refactor: ..."`
```

### On Partial Success

```markdown
# Execution Partially Complete

**Fixed**: 12/15
**Skipped**: 2
**Failed**: 1

## Manual Action Required

| Issue | Status | Action |
|-------|--------|--------|
| HIGH-005 | Skipped | Requires architectural decision |
| MED-003 | Failed | See error below |

[Error details]
```

## Notes

- Each fix is atomic: either fully applied or not at all
- Verification runs after each batch, not each fix
- Rollback restores to pre-execution state
- Progress persists: can resume interrupted execution
- LSP diagnostics verify no new errors introduced
