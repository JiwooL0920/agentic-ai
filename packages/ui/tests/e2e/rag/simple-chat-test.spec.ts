import { test, expect } from '@playwright/test';

test.describe('Simple Chat Test', () => {
  const blueprint = 'devassist';

  test('send message and check response', async ({ page }) => {
    console.log('Navigating to chat...');
    await page.goto(`/${blueprint}`);
    await page.waitForLoadState('networkidle');
    
    console.log('Filling message...');
    const textarea = page.locator('textarea[placeholder*="Ask anything"]');
    await textarea.fill('Hello, how are you?');
    
    console.log('Sending message...');
    await textarea.press('Enter');
    
    // Wait for loading to complete
    await page.waitForTimeout(3000);
    
    console.log('Waiting for assistant response...');
    const assistantMessage = page.locator('[class*="message-assistant"]').last();
    await expect(assistantMessage).toBeVisible({ timeout: 30000 });
    
    const messageText = await assistantMessage.textContent();
    console.log('Response:', messageText);
    
    // Check if response is just "0"
    const contentOnly = messageText?.replace(/\s+/g, ' ').trim();
    console.log('Cleaned response:', contentOnly);
    
    if (contentOnly === '0' || contentOnly?.includes('AI 0')) {
      console.log('❌ BUG CONFIRMED: Response is "0"');
      await page.screenshot({ path: 'test-results/chat-zero-bug.png', fullPage: true });
    }
    
    expect(contentOnly).not.toBe('0');
    expect(contentOnly?.length).toBeGreaterThan(5);
  });

  test('check API response directly', async ({ request }) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    
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
