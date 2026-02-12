# E2E Refactor Guidelines

Comprehensive guidelines for analyzing codebases, identifying issues, and executing refactors.

## Analysis Principles

### 1. Evidence-Based Findings

Every finding MUST have:
- **Location**: Exact file path and line number
- **Source**: Which tool/check identified it
- **Evidence**: Actual code snippet or error message
- **Reference**: Link to official docs or best practice

**DO NOT**: Report vague issues like "code could be cleaner" without specifics.

### 2. Prioritization Matrix

| Severity | Impact | Action |
|----------|--------|--------|
| CRITICAL | Bugs, security, data loss | Must fix immediately |
| HIGH | Performance, major anti-patterns | Fix before release |
| MEDIUM | Best practice violations | Fix when time permits |
| LOW | Style, documentation | Optional improvements |

### 3. False Positive Handling

Before reporting an issue, verify:
1. Is it actually a problem in this context?
2. Is it intentional (check for comments explaining why)?
3. Is the "fix" worse than the issue?

**Examples of false positives:**
- `# noqa` or `# type: ignore` with explanation comment
- Intentional `any` for dynamic plugin systems
- Unused imports that are re-exported

## Issue Categories

### Category 1: Type Safety

**Python (mypy)**
| Issue | Severity | Pattern |
|-------|----------|---------|
| Missing return type | MEDIUM | `def func(x):` without `-> ReturnType` |
| Implicit Any | HIGH | Untyped parameters in public APIs |
| Type ignore without comment | MEDIUM | `# type: ignore` alone |
| Incompatible types | CRITICAL | Type mismatch in assignments |

**TypeScript**
| Issue | Severity | Pattern |
|-------|----------|---------|
| `as any` assertion | HIGH | Type escape hatch |
| `@ts-ignore` | HIGH | Suppressing type errors |
| Implicit any parameter | MEDIUM | Untyped function parameters |
| Non-null assertion `!` | MEDIUM | Potentially unsafe access |

### Category 2: Error Handling

**Python**
| Issue | Severity | Pattern |
|-------|----------|---------|
| Bare `except:` | CRITICAL | Catches everything including SystemExit |
| `except Exception:` without logging | HIGH | Silent failures |
| Missing error response codes | MEDIUM | HTTP 500 for all errors |

**TypeScript**
| Issue | Severity | Pattern |
|-------|----------|---------|
| Empty catch block | CRITICAL | `catch(e) {}` |
| `catch(e: any)` | MEDIUM | Untyped error handling |
| Missing error boundaries | HIGH | Unhandled React errors |

### Category 3: Async Patterns

**Python**
| Issue | Severity | Pattern |
|-------|----------|---------|
| Blocking call in async | CRITICAL | `time.sleep()` instead of `await asyncio.sleep()` |
| Missing `await` | CRITICAL | Unawaited coroutine |
| Sync ORM in async handler | HIGH | Blocking database calls |

**TypeScript**
| Issue | Severity | Pattern |
|-------|----------|---------|
| Unhandled promise rejection | CRITICAL | `.then()` without `.catch()` |
| Missing `await` in async function | CRITICAL | Floating promise |
| Sync operation in server component | MEDIUM | Could block rendering |

### Category 4: Security

| Issue | Severity | Pattern |
|-------|----------|---------|
| Hardcoded secrets | CRITICAL | API keys, passwords in code |
| SQL injection risk | CRITICAL | String interpolation in queries |
| XSS vulnerability | CRITICAL | Unescaped user input in HTML |
| Insecure deserialization | HIGH | `pickle.loads()` on untrusted data |
| Overly permissive CORS | MEDIUM | `allow_origins=["*"]` |

### Category 5: Performance

| Issue | Severity | Pattern |
|-------|----------|---------|
| N+1 query | HIGH | Loop with database query inside |
| Missing pagination | MEDIUM | Unbounded result sets |
| Synchronous in async context | HIGH | Blocking the event loop |
| Unnecessary re-renders | MEDIUM | Missing React.memo/useMemo |
| Large bundle import | LOW | Importing entire library for one function |

### Category 6: Code Quality

| Issue | Severity | Pattern |
|-------|----------|---------|
| Cyclomatic complexity >10 | MEDIUM | Functions with too many branches |
| Function >50 lines | LOW | Should be split |
| Duplicate code blocks | MEDIUM | Copy-pasted logic |
| Dead code | LOW | Unreachable or unused code |
| Magic numbers | LOW | Unexplained numeric constants |

### Category 7: Documentation

| Issue | Severity | Pattern |
|-------|----------|---------|
| Public API without docstring | MEDIUM | Missing documentation |
| Stale docstring | LOW | Docs don't match implementation |
| Missing README | MEDIUM | New module without explanation |
| Outdated examples | LOW | Code samples that don't work |

## AST Patterns for Detection

### Python Anti-Patterns

```yaml
# Bare except (catches SystemExit, KeyboardInterrupt)
- pattern: "except: $$$"
  severity: CRITICAL
  message: "Bare except catches all exceptions including SystemExit"
  fix: "except Exception as e:"

# Print statements (should use logging)
- pattern: "print($$$)"
  severity: LOW
  message: "Use structlog logger instead of print"
  fix: "logger.info(...)"

# Type ignore without explanation
- pattern: "# type: ignore"
  severity: MEDIUM
  message: "Add explanation comment for type ignore"
  fix: "# type: ignore[error-code]  # reason"

# Mutable default argument
- pattern: "def $FUNC($$$, $ARG=[], $$$):"
  severity: HIGH
  message: "Mutable default argument can cause unexpected behavior"
  fix: "def func(..., arg=None): arg = arg or []"

# Sync sleep in async
- pattern: "time.sleep($$$)"
  severity: CRITICAL
  context: "async def"
  message: "Use await asyncio.sleep() in async context"
```

### TypeScript Anti-Patterns

```yaml
# Type assertion to any
- pattern: "as any"
  severity: HIGH
  message: "Type assertion to 'any' bypasses type checking"
  fix: "Define proper type or use type guard"

# Non-null assertion
- pattern: "$EXPR!"
  severity: MEDIUM
  message: "Non-null assertion can cause runtime errors"
  fix: "Use optional chaining or explicit null check"

# Console.log in production
- pattern: "console.log($$$)"
  severity: LOW
  message: "Remove debug logging"
  fix: "Remove or use proper logging service"

# useEffect with missing deps
- pattern: "useEffect($FUNC, [])"
  severity: MEDIUM
  message: "Empty dependency array may hide missing dependencies"
  fix: "Add all dependencies used in effect"

# Index as React key
- pattern: "key={$INDEX}"
  severity: MEDIUM
  message: "Using index as key can cause rendering issues"
  fix: "Use unique identifier from data"
```

## Documentation Verification

### Key Libraries to Check

| Library | What to Verify |
|---------|----------------|
| **FastAPI** | Route decorators, dependency injection, exception handlers |
| **Pydantic** | Model definitions, validators, field constraints |
| **structlog** | Logger configuration, bound loggers, processors |
| **Next.js 14** | App Router patterns, server/client components, metadata |
| **React 18** | Hooks rules, Suspense boundaries, concurrent features |
| **shadcn/ui** | Component props, composition patterns, accessibility |

### Verification Checklist

For each major framework:
1. [ ] Are we following the recommended project structure?
2. [ ] Are we using current API patterns (not deprecated)?
3. [ ] Are we handling errors as recommended?
4. [ ] Are we following performance best practices?
5. [ ] Are we using types/schemas correctly?

## Fix Strategies

### Safe Fixes (Auto-apply)

| Fix Type | Example |
|----------|---------|
| Add missing type annotation | `def func(x)` → `def func(x: str)` |
| Remove unused import | Delete import line |
| Add missing `await` | `func()` → `await func()` |
| Replace deprecated API | Old API → New API (1:1) |
| Add error logging | Empty catch → catch with log |

### Risky Fixes (Require Review)

| Fix Type | Risk |
|----------|------|
| Refactor function signature | May break callers |
| Change async/sync | May affect entire call chain |
| Update dependency | May have breaking changes |
| Restructure modules | May break imports |

### Fixes to Flag, Not Auto-Apply

| Fix Type | Reason |
|----------|--------|
| Algorithm changes | Business logic decisions |
| Architecture restructure | Major design change |
| Dependency upgrade | Requires testing |
| Database schema | Requires migration |

## Verification After Fixes

### Python Verification

```bash
# Run in order
cd packages/core
source ../../venv/bin/activate

# 1. Lint check
ruff check src/

# 2. Type check
mypy src/

# 3. Tests
pytest tests/ -v
```

### TypeScript Verification

```bash
cd packages/ui

# 1. Lint check
pnpm lint

# 2. Type check
pnpm tsc --noEmit

# 3. Build
pnpm build

# 4. Tests (if available)
pnpm test
```

### LSP Verification

After each fix, run `lsp_diagnostics` on modified files to ensure:
- No new errors introduced
- Warnings reduced or unchanged
- Types resolve correctly

## Anti-Patterns in Refactoring

### DON'T

1. **Fix unrelated issues** - Stay focused on approved scope
2. **Refactor while fixing bugs** - One concern at a time
3. **Change formatting broadly** - Use formatter, not manual edits
4. **Add features during refactor** - Refactor only
5. **Skip verification** - Always verify after changes

### DO

1. **Fix one category at a time** - Batch similar changes
2. **Verify incrementally** - Check after each batch
3. **Preserve behavior** - Refactor should not change functionality
4. **Document decisions** - Explain non-obvious choices
5. **Ask when uncertain** - Escalate ambiguous cases to user
