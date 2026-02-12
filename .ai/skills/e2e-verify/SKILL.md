---
name: e2e-verify
description: Verify implemented features via Playwright E2E tests. Runs tests, investigates failures, proposes fixes, and auto-corrects issues.
---

# E2E Verification Skill

Hybrid verification skill that runs Playwright tests first, then falls back to dev-browser for ad-hoc debugging when needed.

## Guidelines

@guidelines.md

## When to Trigger

- User says "verify", "test this", "check if it works", "run e2e", "run playwright"
- After implementing a feature (when user asks to verify)
- When debugging a failing test
- When user says "investigate why X is failing"
- Explicit command: `/e2e:verify`, `/e2e:run`, `/e2e:investigate`

## Algorithm

### Phase 1: Scope Detection

1. **Identify changed files** from git diff or user context:
   ```bash
   git diff --name-only HEAD~1
   # OR from conversation context about what was just implemented
   ```

2. **Map changes to test scope**:
   | Changed Path | Test Scope |
   |--------------|------------|
   | `packages/ui/app/[blueprint]/` | `tests/e2e/rag/*.spec.ts` |
   | `packages/ui/components/chat/` | `tests/e2e/rag/*chat*.spec.ts` |
   | `packages/ui/components/session/` | `tests/e2e/rag/*session*.spec.ts` |
   | `packages/ui/hooks/` | Full suite (hooks affect multiple areas) |
   | `packages/core/src/api/` | Full suite (API changes affect everything) |

3. **If scope unclear**: Run full `tests/e2e/` suite

### Phase 2: Test Execution

1. **Run scoped Playwright tests**:
   ```bash
   cd packages/ui
   pnpm playwright test [scope] --reporter=line
   ```

2. **On success**: Report green status, done.

3. **On failure**: Proceed to Phase 3.

### Phase 3: Failure Investigation

1. **Rerun failing tests with full diagnostics**:
   ```bash
   cd packages/ui
   pnpm playwright test [failing-test] --workers=1 --trace=on --video=on
   ```

2. **Collect artifacts**:
   - Screenshot at failure point: `test-results/*/test-failed-*.png`
   - Trace file: `test-results/*/*.zip`
   - Console logs from trace
   - Network requests from trace

3. **Analyze failure**:
   - Element not found → Check selector, DOM structure, timing
   - Assertion failed → Check expected vs actual values
   - Timeout → Check API response, loading states
   - Network error → Check backend, CORS, endpoints

4. **If artifacts insufficient, use dev-browser**:
   - Load dev-browser skill
   - Navigate to failing page
   - Capture ARIA snapshot
   - Inspect specific elements
   - Check console/network manually

### Phase 4: Fix Proposal

Structure fix proposals as:

```markdown
## Root Cause
[What went wrong and why]

## Fix
[Specific code changes needed]

## Files to Modify
- `path/to/file.ts`: [change description]

## Validation
1. Run: `pnpm -C packages/ui playwright test [test-file]`
2. Expected: All tests pass
```

### Phase 5: Auto-Fix Loop

1. Apply the proposed fix
2. Rerun ONLY the failing tests
3. If still failing: Investigate again (max 3 attempts)
4. If passing: Run broader smoke test for confidence
5. Report final status

### Phase 6: Test Generation (Only When Needed)

Generate new tests ONLY when:
- No existing test covers the implemented feature
- A regression fix needs to be locked in
- User explicitly requests a new test

Use templates from @test-templates.md

## Commands

| Command | Description |
|---------|-------------|
| `/e2e:verify` | Run relevant E2E tests based on recent changes |
| `/e2e:verify [feature]` | Run tests matching feature keyword |
| `/e2e:run` | Run full E2E test suite |
| `/e2e:run [file]` | Run specific test file |
| `/e2e:investigate` | Investigate last failing test with full diagnostics |
| `/e2e:fix` | Auto-fix mode: investigate + propose + apply fix |
| `/e2e:generate [feature]` | Generate new E2E test for feature |

## Environment

```bash
# Test runner location
cd packages/ui

# Run all tests
pnpm playwright test

# Run specific test
pnpm playwright test tests/e2e/rag/simple-chat-test.spec.ts

# Run with grep
pnpm playwright test --grep "chat"

# Run with UI mode (debugging)
pnpm playwright test --ui

# Run with trace
pnpm playwright test --trace=on

# View report
pnpm playwright show-report
```

## Escalation Triggers

- **>2 consecutive flaky failures**: Treat as test stability issue, not product bug
- **Cannot determine scope**: Run full test suite
- **>3 fix attempts failed**: Escalate to user with full diagnostic report
- **New feature, no tests exist**: Propose test generation

## Integration with dev-browser

When Playwright runner diagnostics are insufficient:

1. Load dev-browser skill: `skill("dev-browser")`
2. Navigate to the page where test failed
3. Use `getAISnapshot()` to inspect current DOM state
4. Compare with expected state from failing assertion
5. Check console for JavaScript errors
6. Check network tab for failed requests

This provides interactive debugging capabilities beyond what test artifacts show.
