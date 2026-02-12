# E2E Verification Guidelines

## Failure Investigation Patterns

### Pattern 1: Element Not Found

**Symptoms:**
- `locator.click: Timeout 30000ms exceeded`
- `waiting for locator('...')`
- `strict mode violation: locator resolved to N elements`

**Investigation Steps:**
1. Check if element exists in DOM (use dev-browser snapshot)
2. Verify selector accuracy (class names, test-ids, roles)
3. Check if element is hidden/invisible
4. Check timing (element may appear after API call)

**Common Fixes:**
- Add `waitForLoadState('networkidle')` before interaction
- Use more specific selector (data-testid, role)
- Add explicit `waitForSelector()` before action
- Check if element is inside iframe

### Pattern 2: Assertion Failed

**Symptoms:**
- `expect(received).toBe(expected)`
- `expect(locator).toHaveText(...) - expected "X" but got "Y"`

**Investigation Steps:**
1. Log actual value vs expected
2. Check if data is loading (API response timing)
3. Check if data format changed
4. Check for race conditions

**Common Fixes:**
- Use `toHaveText({ timeout: 10000 })` for async content
- Verify API response format matches expected
- Add polling with `expect.poll()`
- Check for off-by-one, case sensitivity

### Pattern 3: Timeout / Slow Response

**Symptoms:**
- `page.goto: Timeout 30000ms exceeded`
- `Navigation timeout of 30000ms exceeded`

**Investigation Steps:**
1. Check backend server is running
2. Check for long-running API calls
3. Check for infinite loading states
4. Check network conditions in trace

**Common Fixes:**
- Increase timeout for specific operations
- Mock slow API endpoints in tests
- Fix backend performance issue
- Add loading state assertions

### Pattern 4: Network/API Errors

**Symptoms:**
- `net::ERR_CONNECTION_REFUSED`
- `404 Not Found` in network trace
- CORS errors in console

**Investigation Steps:**
1. Verify backend is running on expected port
2. Check API endpoint URL construction
3. Check authentication headers
4. Review CORS configuration

**Common Fixes:**
- Start backend before tests (`webServer` in playwright config)
- Fix API URL in frontend code
- Add missing auth headers
- Configure CORS for test origin

### Pattern 5: Flaky Tests

**Symptoms:**
- Test passes locally, fails in CI
- Test fails intermittently
- Different results on reruns

**Investigation Steps:**
1. Check for race conditions (multiple async operations)
2. Check for test isolation issues (shared state)
3. Check for timing-dependent assertions
4. Check for external dependencies (APIs, databases)

**Common Fixes:**
- Use deterministic waits (`waitForResponse`, `waitForLoadState`)
- Reset state between tests
- Mock external dependencies
- Add retry logic for flaky network calls

## Diagnostic Collection Checklist

When investigating a failure, collect:

- [ ] Screenshot at failure point
- [ ] Full trace file (includes timeline, DOM, network)
- [ ] Console logs (errors, warnings)
- [ ] Network requests (failed requests, response bodies)
- [ ] Test code context (what the test was trying to do)
- [ ] Recent code changes (git diff)

## Fix Proposal Template

```markdown
## Diagnosis

**Test:** `tests/e2e/rag/[test-file].spec.ts`
**Failure Type:** [Element Not Found | Assertion Failed | Timeout | Network Error | Flaky]
**Error Message:** 
\`\`\`
[paste error]
\`\`\`

## Root Cause

[Explain why the test failed based on investigation]

## Evidence

- Screenshot: [describe what it shows]
- Trace: [relevant findings from trace]
- Console: [any JS errors]
- Network: [any failed requests]

## Proposed Fix

### Option A (Recommended)
[Primary fix approach]

\`\`\`typescript
// Code change
\`\`\`

### Option B (Alternative)
[Backup approach if Option A doesn't work]

## Files to Modify

| File | Change |
|------|--------|
| `path/to/file.ts` | [description] |

## Validation

1. Run failing test: \`pnpm playwright test [test-file]\`
2. Run related tests: \`pnpm playwright test --grep "[feature]"\`
3. Run full suite: \`pnpm playwright test\`

## Risk Assessment

- **Scope:** [Isolated | Moderate | Wide-ranging]
- **Confidence:** [High | Medium | Low]
- **Rollback:** [Easy | Moderate | Complex]
```

## Decision Tree

```
Test Failed
    │
    ├── Is error message clear?
    │   ├── Yes → Apply direct fix
    │   └── No → Collect full diagnostics
    │
    ├── Is failure reproducible?
    │   ├── Yes → Investigate systematically
    │   └── No → Likely flaky, focus on stability
    │
    ├── Did test pass before recent changes?
    │   ├── Yes → Regression, check git diff
    │   └── No → Pre-existing issue or new test
    │
    └── After 3 fix attempts
        ├── Still failing → Escalate to user
        └── Passing → Run smoke tests, report success
```

## Anti-Patterns to Avoid

1. **Don't increase timeout blindly** - Find root cause first
2. **Don't add random waits** - Use deterministic conditions
3. **Don't disable failing tests** - Fix or mark as known issue
4. **Don't ignore flaky tests** - They indicate real problems
5. **Don't fix symptoms** - Address root causes
