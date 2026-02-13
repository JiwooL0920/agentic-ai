import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Debug Chat Issue', () => {
  const blueprint = 'devassist';

  test('reproduce chat returning "0" after document upload', async ({ page }) => {
    // Step 1: Upload a document
    console.log('Step 1: Uploading document...');
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    const filePath = path.join(__dirname, '../../fixtures/test-document.md');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    // Wait for success
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });
    console.log('✓ Document uploaded successfully');

    // Step 2: Test semantic search
    console.log('Step 2: Testing semantic search...');
    const searchInput = page.getByPlaceholder(/ask a question about your documents/i);
    await searchInput.fill('kubernetes deployment');
    await page.getByRole('button', { name: /search/i }).click();
    
    // Wait for search results or no results message
    await page.waitForTimeout(2000);
    console.log('✓ Search executed');

    // Step 3: Go back to chat
    console.log('Step 3: Navigating to chat...');
    await page.goto(`/${blueprint}`);
    await page.waitForLoadState('networkidle');
    console.log('✓ Chat page loaded');

    // Step 4: Send a message
    console.log('Step 4: Sending chat message...');
    const textarea = page.locator('textarea');
    await textarea.fill('How do I deploy with Kubernetes?');
    
    // Submit the message
    await page.keyboard.press('Enter');
    
    // Wait for response
    console.log('Waiting for response...');
    await page.waitForTimeout(5000);

    // Check what we got back
    const messages = await page.locator('[class*="message-assistant"]').all();
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      const messageText = await lastMessage.textContent();
      console.log('Response received:', messageText);

      // Check if response is just "0"
      if (messageText?.trim() === '0') {
        console.log('❌ BUG REPRODUCED: Response is just "0"');
        
        // Take a screenshot
        await page.screenshot({ path: 'test-results/chat-zero-response.png', fullPage: true });
        
        // Check network traffic
        console.log('Checking network requests...');
      } else {
        console.log('✓ Got a proper response');
      }
    } else {
      console.log('⚠️  No assistant message found');
    }

    // Keep browser open to inspect
    await page.waitForTimeout(2000);
  });

  test('check chat API endpoint directly', async ({ page, request }) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    console.log('Testing chat API endpoint directly...');
    
    const response = await request.post(`${apiUrl}/api/blueprints/${blueprint}/chat`, {
      data: {
        message: 'How do I deploy with Kubernetes?',
        stream: false,
      },
      timeout: 30000,
    });

    console.log('Response status:', response.status());
    const body = await response.json();
    console.log('Response body:', JSON.stringify(body, null, 2));

    expect(response.status()).toBe(200);
  });
});
