import { test, expect } from '@playwright/test';

test.describe('Simple Chat Test', () => {
  const blueprint = 'devassist';

  test('send message and check response', async ({ page }) => {
    test.setTimeout(90000);
    await page.goto(`/${blueprint}`);
    await page.waitForLoadState('networkidle');
    
    const textarea = page.locator('textarea[placeholder*="Ask anything"]');
    await expect(textarea).toBeVisible({ timeout: 10000 });
    
    await textarea.fill('Hello, how are you?');
    await textarea.press('Enter');
    
    const userMessage = page.locator('[class*="message-user"]').first();
    await userMessage.waitFor({ state: 'visible', timeout: 10000 });
    
    const assistantMessage = page.locator('[class*="message-assistant"]').first();
    await assistantMessage.waitFor({ state: 'visible', timeout: 60000 });
    
    const proseDiv = assistantMessage.locator('.prose');
    await proseDiv.waitFor({ state: 'visible', timeout: 60000 });
    
    await page.waitForFunction(
      (selector) => {
        const el = document.querySelector(selector);
        return el && el.textContent && el.textContent.trim().length > 5;
      },
      '[class*="message-assistant"] .prose',
      { timeout: 60000 }
    );
    
    const messageText = await proseDiv.textContent();
    expect(messageText?.trim().length).toBeGreaterThan(5);
  });

  test('check API response directly', async ({ request }) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    console.log('\nTesting API endpoint directly...');
    const response = await request.post(`${apiUrl}/api/blueprints/${blueprint}/chat`, {
      data: {
        message: 'Hello, how are you?',
        stream: false,
      },
    });

    const status = response.status();
    console.log('Status:', status);
    
    const body = await response.json();
    console.log('Response:', JSON.stringify(body, null, 2));
    
    expect(status).toBe(200);
    expect(body.response).toBeDefined();
    expect(body.response).not.toBe('0');
  });
});
