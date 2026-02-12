---
description: Generate a prioritized fix plan from approved findings
---

# /refactor:plan

Generate a detailed, ordered fix plan based on user-approved findings.

## Usage

```bash
/refactor:plan                     # Plan for all approved findings
/refactor:plan critical            # Plan for critical issues only
/refactor:plan critical,high       # Plan for critical and high
/refactor:plan type-safety         # Plan for specific category
```

## Prerequisites

- Analysis must have been run (`/refactor:analyze`)
- User must have approved findings

If no approval exists:
```
No approved findings. Run `/refactor:analyze` first and approve the results.
```

## Workflow

### Step 1: Load Approved Findings

Retrieve findings from the analysis phase that user approved.

Filter by user's scope selection:
- "all" → include everything
- "critical" → CRITICAL only
- "critical,high" → CRITICAL + HIGH
- "[category]" → filter by category (type-safety, security, etc.)

### Step 2: Analyze Fix Dependencies

Some fixes depend on others:

```python
# Example dependency graph
dependencies = {
    "HIGH-003": ["CRIT-001"],  # HIGH-003 uses types from CRIT-001
    "MED-005": ["CRIT-002"],   # MED-005 depends on error handling
}
```

Build dependency order using topological sort.

### Step 3: Group into Batches

Group fixes by:
1. **File locality**: Fixes in same file → same batch (avoid conflicts)
2. **Verification boundaries**: Python vs TypeScript in separate batches
3. **Risk level**: High-risk changes isolated

### Step 4: Estimate Effort

| Fix Type | Estimate |
|----------|----------|
| Add type annotation | 1 min |
| Add error handling | 2 min |
| Refactor function | 5 min |
| Restructure module | 10 min |

### Step 5: Generate Fix Plan

Use template from @report-templates.md:

```markdown
# Fix Plan

**Approved Scope**: [what user approved]
**Total Issues**: [count]
**Estimated Time**: [sum of estimates]

## Batch 1: Critical Fixes
...

## Batch 2: High Priority
...
```

### Step 6: Create Todo List

```typescript
todowrite({
  todos: [
    { id: "fix-crit-001", content: "Fix CRIT-001: [summary]", status: "pending", priority: "high" },
    { id: "fix-crit-002", content: "Fix CRIT-002: [summary]", status: "pending", priority: "high" },
    { id: "fix-high-001", content: "Fix HIGH-001: [summary]", status: "pending", priority: "medium" },
    // ...
  ]
})
```

### Step 7: Present Plan

```markdown
[Fix Plan content]

---

## Ready to Execute?

The plan will modify [N] files across [M] batches.

Options:
1. **Execute all** → Apply all fixes with verification
2. **Execute batch N** → Apply specific batch only
3. **Review fix [ID]** → See detailed fix for specific issue
4. **Cancel** → No changes

What would you like to do?
```

## Output

### On Success

```markdown
# Fix Plan

[Plan content]

Ready to execute?
```

### On No Findings

```markdown
No findings to plan.

Either:
- Run `/refactor:analyze` first
- Approve some findings from the analysis
```

## Batch Structure

Each batch includes:

| Field | Description |
|-------|-------------|
| Batch ID | Sequential (1, 2, 3...) |
| Priority | Based on highest severity in batch |
| Files | List of files modified |
| Issues | List of issue IDs |
| Estimate | Sum of individual estimates |
| Risk | Low / Medium / High |
| Verification | Commands to run after batch |

## Skipped Items

Some issues cannot be auto-fixed:

| Reason | Action |
|--------|--------|
| Requires architectural decision | Flag for user |
| External dependency issue | Note in report |
| Ambiguous fix | Ask user |
| High-risk change | Require explicit approval |

## Notes

- Plan is deterministic given same findings
- Batches respect file boundaries to avoid merge conflicts
- Each batch has verification step before proceeding to next
- User can modify plan before execution
