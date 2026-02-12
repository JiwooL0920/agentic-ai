# E2E Verification Skill

## Overview

OpenCode skill that automatically verifies implemented features via Playwright E2E tests, investigates failures, proposes fixes, and auto-corrects issues.

**Status**: ✅ IMPLEMENTED
**Location**: `.ai/skills/e2e-verify/`
**Architecture**: Hybrid (Playwright runner primary, dev-browser fallback)

## Design Decision

Consulted Oracle and chose **Option C (Hybrid)** approach:

| Option | Approach | Chosen |
|--------|----------|--------|
| A | Extend dev-browser with verification commands | ❌ |
| B | Standalone skill with custom Playwright scripts | ❌ |
| C | Hybrid: Playwright runner + dev-browser fallback | ✅ |

**Rationale:**
- dev-browser remains a general-purpose "interactive debugger"
- Playwright runner gives reproducible CI-like results
- dev-browser provides targeted inspection when tests fail ambiguously
- Leverages existing `playwright.config.ts` and 11 existing tests

## Skill Structure

```
.ai/skills/e2e-verify/
├── SKILL.md           # Main skill definition with triggers, algorithm, commands
├── guidelines.md      # Failure investigation patterns and fix templates
└── test-templates.md  # Templates for generating new E2E tests
```

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

## Algorithm Summary

### Phase 1: Scope Detection
- Use `git diff` to identify changed files
- Map changes to relevant test paths:
  - `app/[blueprint]/` → `tests/e2e/rag/*.spec.ts`
  - `components/chat/` → `tests/e2e/rag/*chat*.spec.ts`
  - `components/session/` → `tests/e2e/rag/*session*.spec.ts`

### Phase 2: Test Execution
- Run `pnpm playwright test [scope]` in `packages/ui`
- On success: Report green status
- On failure: Proceed to investigation

### Phase 3: Failure Investigation
1. Rerun with `--trace=on --video=on`
2. Collect screenshots, traces, console logs, network requests
3. Analyze failure pattern (element not found, assertion failed, timeout, etc.)
4. If artifacts insufficient, use dev-browser for interactive inspection

### Phase 4: Fix Proposal
Structure: Root Cause → Fix → Files to Modify → Validation Steps

### Phase 5: Auto-Fix Loop
1. Apply fix
2. Rerun failing tests (max 3 attempts)
3. On success, run broader smoke tests
4. Report final status

### Phase 6: Test Generation
Only when no existing test covers the feature. Use templates from `test-templates.md`.

## Failure Patterns Covered

| Pattern | Symptoms | Common Fixes |
|---------|----------|--------------|
| Element Not Found | Timeout on locator | Add waits, fix selectors |
| Assertion Failed | Expected vs actual mismatch | Fix data, add timeouts |
| Timeout | Navigation timeout | Check backend, increase timeout |
| Network Error | Connection refused, 404 | Fix API URL, start server |
| Flaky Test | Intermittent failures | Use deterministic waits |

## Integration with Existing Infrastructure

### Playwright Config
Location: `packages/ui/playwright.config.ts`
- testDir: `./tests/e2e`
- Reporter: HTML
- Traces: On first retry

### Existing Tests
Location: `packages/ui/tests/e2e/rag/`
- 11 test files covering RAG features
- Example: `simple-chat-test.spec.ts`

### dev-browser Skill
Used as fallback for:
- Interactive DOM inspection
- ARIA snapshots
- Console/network debugging
- Manual reproduction of failures

## Test Templates

8 templates provided for common patterns:
1. Basic Page Load
2. Form Interaction
3. Chat Interaction
4. Sidebar/Navigation
5. API Direct Test
6. Session/State Persistence
7. Streaming Response
8. Keyboard Shortcuts

## Escalation Triggers

- >2 consecutive flaky failures → Treat as test stability issue
- Cannot determine scope → Run full test suite
- >3 fix attempts failed → Escalate to user with diagnostic report
- New feature, no tests exist → Propose test generation

## Usage Examples

```bash
# After implementing a chat feature
> /e2e:verify chat

# Running output
Running: pnpm playwright test --grep "chat"
✓ simple-chat-test.spec.ts (2 tests)
All tests passed!

# If a test fails
> /e2e:investigate

## Diagnosis
**Test:** tests/e2e/rag/simple-chat-test.spec.ts
**Failure Type:** Assertion Failed
**Error:** expect(received).toHaveText(expected)

## Root Cause
Session hydration loading skeleton is showing stale text

## Proposed Fix
...
```

## Next Steps

1. Test the skill with actual feature verification
2. Add session-specific tests for conversation memory feature
3. Consider adding test tagging convention (`@feature:xyz`)
4. Integrate with CI/CD pipeline
