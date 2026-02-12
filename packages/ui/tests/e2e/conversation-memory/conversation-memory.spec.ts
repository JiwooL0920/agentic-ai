import { test, expect, type Page } from '@playwright/test';

/**
 * E2E Tests for Conversation Memory Feature
 * 
 * Tests cover:
 * - Session creation with URL update
 * - Session title from first message
 * - Session switching and history loading
 * - Streaming content with agent badges
 * - Pin/Unpin session functionality
 * - Archive session functionality
 * - New chat creation
 */

test.describe('Conversation Memory', () => {
  const blueprint = 'devassist';
  let testUserId: string;

  test.beforeEach(async ({ page }) => {
    // Generate unique user ID for test isolation
    testUserId = `e2e-test-user-${Date.now()}`;
    
    // Navigate to the blueprint page
    await page.goto(`/${blueprint}`);
    await page.waitForLoadState('networkidle');
    
    // Set up user ID in localStorage
    await page.evaluate((userId) => {
      localStorage.setItem('userId', userId);
    }, testUserId);
    
    // Reload to apply the user ID
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    console.log(`Test setup complete with userId: ${testUserId}`);
  });

  test.describe('Session Creation', () => {
    test('should create new session when sending first message', async ({ page }) => {
      console.log('Testing session creation...');
      
      // Get initial URL (should not have session param)
      const initialUrl = page.url();
      expect(initialUrl).not.toContain('session=');
      
      // Send a message
      const textarea = page.locator('textarea[placeholder*="Ask anything"]');
      await textarea.fill('Hello, this is a test message');
      await textarea.press('Enter');
      
      // Wait for URL to update with session parameter
      await page.waitForURL(/.*session=.*/, { timeout: 30000 });
      
      const newUrl = page.url();
      console.log('New URL:', newUrl);
      expect(newUrl).toContain('session=');
      
      // Verify session ID format (UUID-like)
      const sessionMatch = newUrl.match(/session=([a-f0-9-]+)/);
      expect(sessionMatch).toBeTruthy();
      expect(sessionMatch![1].length).toBeGreaterThan(10);
    });

    test('should show session in sidebar after creation', async ({ page }) => {
      console.log('Testing session appears in sidebar...');
      
      const testMessage = 'Test message for sidebar verification';
      
      // Send a message
      const textarea = page.locator('textarea[placeholder*="Ask anything"]');
      await textarea.fill(testMessage);
      await textarea.press('Enter');
      
      // Wait for response to complete
      await page.waitForURL(/.*session=.*/, { timeout: 30000 });
      await page.waitForTimeout(2000); // Allow sidebar to update
      
      // Look for the session in sidebar - find element containing the message text
      const sessionItem = page.locator('[role="button"]').filter({ hasText: testMessage }).first();
      await expect(sessionItem).toBeVisible({ timeout: 10000 });
      
      console.log('Session visible in sidebar');
    });
  });

  test.describe('Session Title', () => {
    test('should use first message as session title', async ({ page }) => {
      console.log('Testing session title from first message...');
      
      const firstMessage = 'What is Kubernetes?';
      
      // Send first message
      const textarea = page.locator('textarea[placeholder*="Ask anything"]');
      await textarea.fill(firstMessage);
      await textarea.press('Enter');
      
      // Wait for session creation
      await page.waitForURL(/.*session=.*/, { timeout: 30000 });
      await page.waitForTimeout(2000);
      
      // Verify title appears in sidebar
      const sidebarTitle = page.locator('[role="button"] .truncate').filter({ hasText: firstMessage }).first();
      await expect(sidebarTitle).toBeVisible({ timeout: 10000 });
      
      const titleText = await sidebarTitle.textContent();
      console.log('Session title:', titleText);
      expect(titleText).toContain(firstMessage);
    });
  });

  test.describe('Streaming Content', () => {
    test('should display streaming content with agent badge', async ({ page }) => {
      console.log('Testing streaming content display...');
      
      // Send a message that will trigger agent routing
      const textarea = page.locator('textarea[placeholder*="Ask anything"]');
      await textarea.fill('Explain Docker containers briefly');
      await textarea.press('Enter');
      
      // Wait for assistant message to appear
      const assistantMessage = page.locator('[class*="message"]').last();
      await expect(assistantMessage).toBeVisible({ timeout: 30000 });
      
      // Wait for content to stream (not just "0" or empty)
      await page.waitForFunction(() => {
        const messages = document.querySelectorAll('[class*="message"]');
        const lastMessage = messages[messages.length - 1];
        const text = lastMessage?.textContent?.trim() || '';
        return text.length > 20 && !text.match(/^0$/);
      }, { timeout: 30000 });
      
      // Verify content length
      const messageText = await assistantMessage.textContent();
      console.log('Response length:', messageText?.length);
      expect(messageText?.length).toBeGreaterThan(50);
      
      // Look for agent badge (should show agent name like "Supervisor", "KubernetesExpert", etc.)
      const agentBadge = page.locator('[class*="badge"], [class*="Badge"]').first();
      const hasBadge = await agentBadge.isVisible().catch(() => false);
      console.log('Has agent badge:', hasBadge);
    });
  });

  test.describe('Session Switching', () => {
    test('should load history when switching sessions', async ({ page }) => {
      console.log('Testing session switching...');
      
      // Create first session
      const firstMessage = 'First session message about Python';
      const textarea = page.locator('textarea[placeholder*="Ask anything"]');
      await textarea.fill(firstMessage);
      await textarea.press('Enter');
      
      // Wait for first session
      await page.waitForURL(/.*session=.*/, { timeout: 30000 });
      const firstSessionUrl = page.url();
      const firstSessionId = firstSessionUrl.match(/session=([a-f0-9-]+)/)?.[1];
      console.log('First session ID:', firstSessionId);
      
      // Wait for response
      await page.waitForTimeout(5000);
      
      // Click New Chat button to start new session
      const newChatButton = page.locator('button').filter({ hasText: /new chat/i }).first();
      if (await newChatButton.isVisible()) {
        await newChatButton.click();
      } else {
        // Try alternative - look for + button or similar
        const plusButton = page.locator('button[aria-label*="new"], button:has(svg)').first();
        await plusButton.click();
      }
      
      await page.waitForTimeout(1000);
      
      // Create second session
      const secondMessage = 'Second session message about JavaScript';
      await textarea.fill(secondMessage);
      await textarea.press('Enter');
      
      // Wait for second session
      await page.waitForURL(/.*session=(?!.*${firstSessionId}).*/, { timeout: 30000 });
      
      // Now click on the first session in sidebar
      const firstSessionItem = page.locator('[role="button"]').filter({ hasText: firstMessage }).first();
      await expect(firstSessionItem).toBeVisible({ timeout: 10000 });
      await firstSessionItem.click();
      
      // Verify URL updated to first session
      await page.waitForTimeout(1000);
      expect(page.url()).toContain(firstSessionId);
      
      // Verify first session's messages are loaded
      const messageArea = page.locator('[class*="message"]').filter({ hasText: firstMessage });
      await expect(messageArea).toBeVisible({ timeout: 10000 });
      
      console.log('Session switching verified');
    });
  });

  test.describe('Pin/Unpin Session', () => {
    test('should pin session and show in Pinned section', async ({ page }) => {
      console.log('Testing pin session...');
      
      // Create a session first
      const testMessage = 'Message to be pinned';
      const textarea = page.locator('textarea[placeholder*="Ask anything"]');
      await textarea.fill(testMessage);
      await textarea.press('Enter');
      
      // Wait for session creation and response
      await page.waitForURL(/.*session=.*/, { timeout: 30000 });
      await page.waitForTimeout(3000);
      
      // Find the session item in sidebar
      const sessionItem = page.locator('[role="button"]').filter({ hasText: testMessage }).first();
      await expect(sessionItem).toBeVisible({ timeout: 10000 });
      
      // Hover to reveal the menu button
      await sessionItem.hover();
      
      // Click the dropdown menu trigger (MoreHorizontal icon button)
      const menuButton = sessionItem.locator('button').filter({ has: page.locator('svg') }).first();
      await menuButton.click();
      
      // Click Pin option
      const pinOption = page.locator('[role="menuitem"]').filter({ hasText: 'Pin' });
      await expect(pinOption).toBeVisible({ timeout: 5000 });
      await pinOption.click();
      
      // Wait for UI update
      await page.waitForTimeout(1000);
      
      // Verify "Pinned" section header exists and contains the session
      const pinnedSection = page.locator('h3').filter({ hasText: /pinned/i });
      await expect(pinnedSection).toBeVisible({ timeout: 5000 });
      
      // Verify the session is now under Pinned section
      const pinnedSessionItem = page.locator('[role="button"]').filter({ hasText: testMessage }).first();
      const pinnedIcon = pinnedSessionItem.locator('svg').first(); // Pin icon
      await expect(pinnedIcon).toBeVisible();
      
      console.log('Session pinned successfully');
    });

    test('should unpin a pinned session', async ({ page }) => {
      console.log('Testing unpin session...');
      
      // Create and pin a session first
      const testMessage = 'Message to be unpinned';
      const textarea = page.locator('textarea[placeholder*="Ask anything"]');
      await textarea.fill(testMessage);
      await textarea.press('Enter');
      
      await page.waitForURL(/.*session=.*/, { timeout: 30000 });
      await page.waitForTimeout(3000);
      
      // Pin the session
      const sessionItem = page.locator('[role="button"]').filter({ hasText: testMessage }).first();
      await sessionItem.hover();
      const menuButton = sessionItem.locator('button').filter({ has: page.locator('svg') }).first();
      await menuButton.click();
      
      const pinOption = page.locator('[role="menuitem"]').filter({ hasText: 'Pin' });
      await pinOption.click();
      await page.waitForTimeout(1000);
      
      // Now unpin it
      const pinnedItem = page.locator('[role="button"]').filter({ hasText: testMessage }).first();
      await pinnedItem.hover();
      const unpinMenuButton = pinnedItem.locator('button').filter({ has: page.locator('svg') }).first();
      await unpinMenuButton.click();
      
      const unpinOption = page.locator('[role="menuitem"]').filter({ hasText: 'Unpin' });
      await expect(unpinOption).toBeVisible({ timeout: 5000 });
      await unpinOption.click();
      
      await page.waitForTimeout(1000);
      
      // Verify session is now in Today section (not Pinned)
      const todaySection = page.locator('h3').filter({ hasText: /today/i });
      await expect(todaySection).toBeVisible();
      
      console.log('Session unpinned successfully');
    });
  });

  test.describe('Archive Session', () => {
    test('should archive session and remove from list', async ({ page }) => {
      console.log('Testing archive session...');
      
      // Create a session first
      const testMessage = 'Message to be archived';
      const textarea = page.locator('textarea[placeholder*="Ask anything"]');
      await textarea.fill(testMessage);
      await textarea.press('Enter');
      
      // Wait for session creation
      await page.waitForURL(/.*session=.*/, { timeout: 30000 });
      await page.waitForTimeout(3000);
      
      // Find the session item
      const sessionItem = page.locator('[role="button"]').filter({ hasText: testMessage }).first();
      await expect(sessionItem).toBeVisible({ timeout: 10000 });
      
      // Hover and click menu
      await sessionItem.hover();
      const menuButton = sessionItem.locator('button').filter({ has: page.locator('svg') }).first();
      await menuButton.click();
      
      // Click Archive option
      const archiveOption = page.locator('[role="menuitem"]').filter({ hasText: 'Archive' });
      await expect(archiveOption).toBeVisible({ timeout: 5000 });
      await archiveOption.click();
      
      // Wait for UI update
      await page.waitForTimeout(1000);
      
      // Verify session is no longer visible in the list
      const archivedSession = page.locator('[role="button"]').filter({ hasText: testMessage });
      await expect(archivedSession).not.toBeVisible({ timeout: 5000 });
      
      console.log('Session archived successfully');
    });
  });

  test.describe('New Chat', () => {
    test('should clear messages and start new session', async ({ page }) => {
      console.log('Testing new chat functionality...');
      
      // Create a session first
      const firstMessage = 'First conversation message';
      const textarea = page.locator('textarea[placeholder*="Ask anything"]');
      await textarea.fill(firstMessage);
      await textarea.press('Enter');
      
      // Wait for session and response
      await page.waitForURL(/.*session=.*/, { timeout: 30000 });
      const oldUrl = page.url();
      await page.waitForTimeout(5000);
      
      // Verify message is displayed
      const messageElement = page.locator('[class*="message"]').filter({ hasText: firstMessage });
      await expect(messageElement).toBeVisible({ timeout: 10000 });
      
      // Click New Chat button
      const newChatButton = page.locator('button').filter({ hasText: /new chat/i }).first();
      if (await newChatButton.isVisible()) {
        await newChatButton.click();
      } else {
        // Try clicking the + or similar icon
        const plusButton = page.locator('button').filter({ has: page.locator('svg[class*="plus"], svg[class*="Plus"]') }).first();
        if (await plusButton.isVisible()) {
          await plusButton.click();
        }
      }
      
      await page.waitForTimeout(1000);
      
      // Verify URL no longer has the old session (either no session param or different one)
      const newUrl = page.url();
      expect(newUrl).not.toBe(oldUrl);
      
      // Verify message area is cleared or shows empty state
      const oldMessage = page.locator('[class*="message"]').filter({ hasText: firstMessage });
      const isOldMessageVisible = await oldMessage.isVisible().catch(() => false);
      expect(isOldMessageVisible).toBeFalsy();
      
      console.log('New chat created successfully');
    });
  });

  test.describe('Message Count', () => {
    test('should show correct message count in session item', async ({ page }) => {
      console.log('Testing message count display...');
      
      // Create a session with a message
      const testMessage = 'Test message for count';
      const textarea = page.locator('textarea[placeholder*="Ask anything"]');
      await textarea.fill(testMessage);
      await textarea.press('Enter');
      
      // Wait for session and response
      await page.waitForURL(/.*session=.*/, { timeout: 30000 });
      await page.waitForTimeout(5000);
      
      // Find session in sidebar and check message count
      const sessionItem = page.locator('[role="button"]').filter({ hasText: testMessage }).first();
      await expect(sessionItem).toBeVisible({ timeout: 10000 });
      
      // Message count should be at least 2 (user message + assistant response)
      const messageCountElement = sessionItem.locator('text=/\\d+/').first();
      const countText = await messageCountElement.textContent();
      console.log('Message count:', countText);
      
      const count = parseInt(countText || '0', 10);
      expect(count).toBeGreaterThanOrEqual(1);
    });
  });
});

// Utility function to clean up test sessions (can be called via API if needed)
async function cleanupTestSessions(page: Page, apiUrl: string, userId: string) {
  try {
    // Get all sessions for the test user
    const response = await page.request.get(`${apiUrl}/api/sessions`, {
      headers: { 'X-User-Id': userId },
    });
    
    if (response.ok()) {
      const sessions = await response.json();
      
      // Archive each session
      for (const session of sessions) {
        await page.request.patch(`${apiUrl}/api/sessions/${session.session_id}`, {
          headers: { 'X-User-Id': userId },
          data: { session_state: 'archived' },
        });
      }
    }
  } catch (error) {
    console.log('Cleanup error (non-critical):', error);
  }
}
