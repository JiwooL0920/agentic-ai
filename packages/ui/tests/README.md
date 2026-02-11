# E2E Tests for RAG Features

This directory contains comprehensive end-to-end tests for the RAG (Retrieval-Augmented Generation) frontend features using Playwright.

## Test Coverage

### 1. Document Upload (`e2e/rag/document-upload.spec.ts`)

Tests the document upload functionality:
- Display of upload interface
- Successful file uploads (markdown, Python)
- Upload progress indicators
- File input clearing after upload
- Drag and drop functionality
- Document count updates
- Success notifications
- Multiple consecutive uploads

### 2. Error Handling (`e2e/rag/error-handling.spec.ts`)

Tests error states and edge cases:
- Unsupported file type rejection
- Error alert display
- Upload prevention during ongoing upload
- Empty file handling
- Error clearing after successful upload
- Backend unavailability handling
- Network timeout handling
- Malformed API response handling

### 3. Semantic Search (`e2e/rag/semantic-search.spec.ts`)

Tests the semantic search functionality:
- Search interface display
- Search execution and results
- Match score display
- Document filename and content preview
- Enter key search trigger
- Empty/irrelevant query handling
- Results clearing on new search
- Search button states
- Loading indicators
- Scrollable results area
- Scope-specific searching

### 4. Scope Management (`e2e/rag/scope-management.spec.ts`)

Tests document scope organization:
- Scope card display
- Empty state handling
- Scope tab creation and display
- Document count in tabs
- Tab switching
- Scope information display
- Delete scope confirmation dialog
- Scope deletion cancellation
- Successful scope deletion
- Count updates after deletion
- "How it works" information
- Current scope display updates

### 5. Chat with RAG (`e2e/rag/chat-with-rag.spec.ts`)

Tests RAG integration in chat interface:
- Knowledge base button in header
- Navigation to knowledge page
- Tooltip on knowledge button
- RAG source badge display
- Source citations below messages
- Match percentage in citations
- Source badge tooltip
- External link icons
- Source display limits (+X more)
- Proper handling when no documents used
- Agent badge alongside RAG badge
- Book icon in RAG badge
- RAG sources persistence after streaming
- Badge styling
- Graceful handling of no sources
- Metadata updates from stream

## Test Fixtures

Test files located in `tests/fixtures/`:
- `test-document.md` - Kubernetes deployment guide
- `test-code.py` - Python Fibonacci implementation
- `test-invalid.exe` - Invalid file for error testing

## Prerequisites

Before running tests, ensure:
1. Backend is running on `http://localhost:8001`
2. Frontend is running on `http://localhost:3000`
3. PostgreSQL with pgvector is available
4. Ollama is running with `nomic-embed-text` model
5. Test blueprint "devassist" exists

## Running Tests

### Run all tests:
```bash
pnpm test:e2e
```

### Run specific test file:
```bash
pnpm playwright test tests/e2e/rag/document-upload.spec.ts
```

### Run tests in UI mode (interactive):
```bash
pnpm playwright test --ui
```

### Run tests in headed mode (see browser):
```bash
pnpm playwright test --headed
```

### Run specific test by name:
```bash
pnpm playwright test -g "should successfully upload a markdown file"
```

### Debug a test:
```bash
pnpm playwright test --debug tests/e2e/rag/document-upload.spec.ts
```

### View test report:
```bash
pnpm playwright show-report
```

## Test Configuration

Configuration is in `playwright.config.ts`:
- Base URL: `http://localhost:3000`
- Browser: Chromium (default)
- Screenshots: On failure
- Videos: On failure
- Traces: On first retry
- Parallel execution: Enabled

## Test Structure

Each test suite follows this pattern:

```typescript
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: Navigate to page, prepare state
  });

  test.afterEach(async ({ page }) => {
    // Cleanup: Delete test data
  });

  test('should do something', async ({ page }) => {
    // Arrange: Set up test conditions
    // Act: Perform actions
    // Assert: Verify outcomes
  });
});
```

## Best Practices

1. **Isolation**: Tests clean up after themselves (delete scopes/documents)
2. **Waiting**: Use `waitForLoadState`, `waitForTimeout`, and explicit waits
3. **Assertions**: Use Playwright's built-in assertions with timeouts
4. **Selectors**: Prefer role-based selectors over CSS selectors
5. **Test Data**: Use fixtures for consistent test data
6. **Error Handling**: Tests handle both success and failure cases

## Debugging Tips

### Test Fails Intermittently
- Increase timeouts for slow operations (embeddings, uploads)
- Check for race conditions in async operations
- Verify backend is fully started before tests run

### Element Not Found
- Use `page.pause()` to inspect the page state
- Check selector specificity
- Verify element is visible with `waitForSelector`

### API Errors
- Check backend logs for errors
- Verify Ollama is running and models are loaded
- Ensure database is accessible

### Cleanup Issues
- Verify afterEach hooks are running
- Check for lingering test data with manual API calls
- Clear database between test runs if needed

## CI/CD Integration

Tests are configured for CI/CD:
- Retries: 2 retries on CI
- Workers: 1 worker on CI (sequential)
- Reporter: HTML report for artifacts

## Environment Variables

Tests use:
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8001)
- `CI`: Set to true in CI environments for special behavior

## Troubleshooting

### Ollama Connection Issues
```bash
# Check Ollama status
make ollama-status

# Restart Ollama
make ollama-start
```

### Database Issues
```bash
# Check PostgreSQL is running
psql -h localhost -U postgres -d agentic

# Check tables exist
\dt
```

### Port Conflicts
```bash
# Check if ports are in use
lsof -i :3000
lsof -i :8001

# Kill processes if needed
kill -9 <PID>
```

## Contributing

When adding new tests:
1. Follow existing test structure and naming
2. Add cleanup in `afterEach` hooks
3. Use descriptive test names
4. Add comments for complex test logic
5. Update this README with new coverage

## Test Metrics

Current test coverage:
- **Total tests**: 60+
- **Test files**: 5
- **User flows**: 5 major flows
- **Assertions**: 150+
- **Expected runtime**: ~5-10 minutes (depending on backend speed)

## Known Issues

1. **Embedding delays**: Semantic search tests may be slow due to Ollama embedding generation
2. **Race conditions**: Some tests may fail if backend is slow to respond
3. **Cleanup**: Manual cleanup may be needed if tests fail during execution

## Future Improvements

- [ ] Add mobile viewport tests
- [ ] Add performance benchmarks
- [ ] Add visual regression tests
- [ ] Mock Ollama for faster tests
- [ ] Add accessibility tests
- [ ] Add cross-browser tests (Firefox, Safari)
