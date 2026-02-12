# E2E Test Templates

Use these templates when generating new E2E tests. Only generate tests when:
1. No existing test covers the feature
2. A regression fix needs to be locked in
3. User explicitly requests a new test

## Template 1: Basic Page Load Test

```typescript
import { test, expect } from '@playwright/test';

test.describe('[Feature Name]', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/[route]');
    await page.waitForLoadState('networkidle');
  });

  test('should render correctly', async ({ page }) => {
    // Verify main elements exist
    await expect(page.getByRole('heading', { name: '[Title]' })).toBeVisible();
    await expect(page.getByRole('button', { name: '[Action]' })).toBeVisible();
  });
});
```

## Template 2: Form Interaction Test

```typescript
import { test, expect } from '@playwright/test';

test.describe('[Form Name]', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/[route]');
    await page.waitForLoadState('networkidle');
  });

  test('should submit form successfully', async ({ page }) => {
    // Fill form fields
    await page.getByLabel('[Field Label]').fill('[value]');
    await page.getByRole('combobox', { name: '[Select Label]' }).selectOption('[option]');
    await page.getByRole('checkbox', { name: '[Checkbox Label]' }).check();
    
    // Submit
    await page.getByRole('button', { name: 'Submit' }).click();
    
    // Wait for response
    await page.waitForResponse(resp => 
      resp.url().includes('/api/[endpoint]') && resp.status() === 200
    );
    
    // Verify success
    await expect(page.getByText('Success')).toBeVisible();
  });

  test('should show validation errors', async ({ page }) => {
    // Submit empty form
    await page.getByRole('button', { name: 'Submit' }).click();
    
    // Verify error messages
    await expect(page.getByText('[Error message]')).toBeVisible();
  });
});
```

## Template 3: Chat Interaction Test

```typescript
import { test, expect } from '@playwright/test';

test.describe('[Chat Feature]', () => {
  const blueprint = 'devassist';

  test.beforeEach(async ({ page }) => {
    await page.goto(`/${blueprint}`);
    await page.waitForLoadState('networkidle');
  });

  test('should send message and receive response', async ({ page }) => {
    // Find and fill chat input
    const textarea = page.locator('textarea[placeholder*="Ask anything"]');
    await textarea.fill('[User message]');
    
    // Send message
    await textarea.press('Enter');
    
    // Wait for loading to complete
    await page.waitForSelector('[data-loading="false"]', { timeout: 30000 });
    
    // Verify response
    const assistantMessage = page.locator('[class*="message-assistant"]').last();
    await expect(assistantMessage).toBeVisible();
    
    // Verify response content
    const messageText = await assistantMessage.textContent();
    expect(messageText?.length).toBeGreaterThan(10);
  });
});
```

## Template 4: Sidebar/Navigation Test

```typescript
import { test, expect } from '@playwright/test';

test.describe('[Sidebar Feature]', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/[route]');
    await page.waitForLoadState('networkidle');
  });

  test('should toggle sidebar visibility', async ({ page }) => {
    // Check initial state
    const sidebar = page.getByRole('complementary');
    await expect(sidebar).toBeVisible();
    
    // Toggle closed
    await page.getByRole('button', { name: 'Close sidebar' }).click();
    await expect(sidebar).toBeHidden();
    
    // Toggle open
    await page.getByRole('button', { name: 'Open sidebar' }).click();
    await expect(sidebar).toBeVisible();
  });

  test('should navigate via sidebar items', async ({ page }) => {
    // Click sidebar item
    await page.getByRole('link', { name: '[Item Name]' }).click();
    
    // Verify navigation
    await expect(page).toHaveURL(/[expected-pattern]/);
    await expect(page.getByRole('heading', { name: '[Page Title]' })).toBeVisible();
  });
});
```

## Template 5: API Direct Test

```typescript
import { test, expect } from '@playwright/test';

test.describe('[API Endpoint]', () => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

  test('should return correct data', async ({ request }) => {
    const response = await request.get(`${apiUrl}/api/[endpoint]`);
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty('[expected_property]');
    expect(body.[expected_property]).toBeDefined();
  });

  test('should create resource', async ({ request }) => {
    const response = await request.post(`${apiUrl}/api/[endpoint]`, {
      data: {
        [field]: '[value]',
      },
    });
    
    expect(response.status()).toBe(201);
    
    const body = await response.json();
    expect(body.id).toBeDefined();
  });

  test('should handle errors gracefully', async ({ request }) => {
    const response = await request.get(`${apiUrl}/api/[endpoint]/nonexistent`);
    
    expect(response.status()).toBe(404);
    
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });
});
```

## Template 6: Session/State Persistence Test

```typescript
import { test, expect } from '@playwright/test';

test.describe('[State Persistence]', () => {
  test('should persist state across page reload', async ({ page }) => {
    await page.goto('/[route]');
    await page.waitForLoadState('networkidle');
    
    // Create some state
    await page.getByRole('button', { name: '[Action]' }).click();
    await expect(page.getByText('[State indicator]')).toBeVisible();
    
    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Verify state persists
    await expect(page.getByText('[State indicator]')).toBeVisible();
  });

  test('should restore session from URL', async ({ page }) => {
    // Navigate with query param
    await page.goto('/[route]?session=[session-id]');
    await page.waitForLoadState('networkidle');
    
    // Verify session loaded
    await expect(page.getByText('[Session content]')).toBeVisible();
  });
});
```

## Template 7: Streaming Response Test

```typescript
import { test, expect } from '@playwright/test';

test.describe('[Streaming Feature]', () => {
  test('should display streaming content progressively', async ({ page }) => {
    await page.goto('/[route]');
    await page.waitForLoadState('networkidle');
    
    // Trigger streaming
    await page.getByRole('button', { name: '[Trigger]' }).click();
    
    // Wait for streaming to start
    const streamContainer = page.locator('[data-streaming]');
    await expect(streamContainer).toHaveAttribute('data-streaming', 'true');
    
    // Capture initial content
    const initialText = await streamContainer.textContent();
    
    // Wait for more content
    await page.waitForTimeout(2000);
    
    // Verify content has grown
    const laterText = await streamContainer.textContent();
    expect(laterText?.length).toBeGreaterThan(initialText?.length ?? 0);
    
    // Wait for streaming to complete
    await expect(streamContainer).toHaveAttribute('data-streaming', 'false', { timeout: 30000 });
  });
});
```

## Template 8: Keyboard Shortcuts Test

```typescript
import { test, expect } from '@playwright/test';

test.describe('[Keyboard Shortcuts]', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/[route]');
    await page.waitForLoadState('networkidle');
  });

  test('should toggle with keyboard shortcut', async ({ page }) => {
    // Initial state
    const element = page.locator('[data-testid="target"]');
    await expect(element).toBeVisible();
    
    // Press shortcut (Cmd+B on Mac, Ctrl+B on Windows/Linux)
    await page.keyboard.press('Meta+b');
    
    // Verify toggle
    await expect(element).toBeHidden();
    
    // Press again to restore
    await page.keyboard.press('Meta+b');
    await expect(element).toBeVisible();
  });
});
```

## Naming Conventions

| Pattern | Example |
|---------|---------|
| Test file | `[feature-name].spec.ts` |
| Test suite | `[Feature Name]` |
| Test case | `should [expected behavior]` |

## Selector Priority

1. **Role-based** (best): `getByRole('button', { name: 'Submit' })`
2. **Label-based**: `getByLabel('Email')`
3. **Text-based**: `getByText('Welcome')`
4. **Test ID**: `getByTestId('submit-button')`
5. **CSS class** (last resort): `locator('.submit-btn')`

## Wait Strategy Priority

1. **Implicit waits** (best): Built into `expect` assertions
2. **Response waits**: `waitForResponse()`
3. **Selector waits**: `waitForSelector()`
4. **Load state**: `waitForLoadState('networkidle')`
5. **Timeout** (last resort): `waitForTimeout()` - avoid when possible

## Common Assertions

```typescript
// Visibility
await expect(element).toBeVisible();
await expect(element).toBeHidden();

// Text content
await expect(element).toHaveText('Expected text');
await expect(element).toContainText('partial');

// Attributes
await expect(element).toHaveAttribute('data-state', 'active');
await expect(element).toHaveClass(/active/);

// Count
await expect(page.locator('.item')).toHaveCount(5);

// URL
await expect(page).toHaveURL(/pattern/);

// Values
await expect(input).toHaveValue('expected');
```
