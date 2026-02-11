import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Complete RAG Flow - End to End', () => {
  const blueprint = 'devassist';

  test('full RAG flow: upload → chat → view sources', async ({ page }) => {
    console.log('\n=== STEP 1: Navigate to Knowledge Page ===');
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');
    
    // Check for errors in console
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
        console.log('❌ Console Error:', msg.text());
      }
    });

    // Verify page loaded without errors
    await expect(page.getByRole('heading', { name: /knowledge base/i })).toBeVisible();
    console.log('✓ Knowledge page loaded');

    // Check if there are any listDocuments errors
    await page.waitForTimeout(2000);
    const hasListDocError = consoleErrors.some(err => err.includes('listDocuments'));
    if (hasListDocError) {
      console.log('❌ listDocuments error detected!');
      console.log('Errors:', consoleErrors);
    } else {
      console.log('✓ No listDocuments errors');
    }

    console.log('\n=== STEP 2: Upload a Test Document ===');
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    // Wait for upload to complete
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 15000 });
    console.log('✓ Document uploaded successfully');

    // Wait for document list to update
    await page.waitForTimeout(2000);

    // Check if document appears in list
    const docExists = await page.getByText('test-document.md').isVisible();
    console.log(docExists ? '✓ Document appears in list' : '❌ Document not visible in list');

    console.log('\n=== STEP 3: Navigate to Chat ===');
    await page.goto(`/${blueprint}`);
    await page.waitForLoadState('networkidle');
    console.log('✓ Chat page loaded');

    console.log('\n=== STEP 4: Send Message Related to Uploaded Doc ===');
    const textarea = page.locator('textarea[placeholder*="Ask anything"]');
    await textarea.fill('How do I deploy with Kubernetes?');
    await textarea.press('Enter');
    console.log('✓ Message sent');

    // Wait for assistant response to complete
    console.log('Waiting for AI response...');
    await page.waitForTimeout(3000);
    
    // Wait for prose content (actual response text)
    await page.locator('[class*="message-assistant"] .prose').waitFor({ timeout: 30000 });
    console.log('✓ Response received');

    // Additional wait to ensure RAG context chunk arrives
    await page.waitForTimeout(3000);

    console.log('\n=== STEP 5: Check for RAG Indicators ===');
    
    // Check for source badge (📚 X sources)
    const sourceBadge = page.locator('text=/\\d+ sources?/');
    const hasBadge = await sourceBadge.isVisible().catch(() => false);
    console.log(hasBadge ? '✓ Source count badge found' : '❌ No source count badge');

    // Check for "View Sources" button
    const viewSourcesButton = page.locator('button', { hasText: /view.*knowledge.*sources?/i });
    const hasButton = await viewSourcesButton.isVisible().catch(() => false);
    console.log(hasButton ? '✓ View Sources button found' : '❌ No View Sources button');

    // Take a screenshot of the final state
    await page.screenshot({ path: 'test-results/rag-flow-complete.png', fullPage: true });

    console.log('\n=== STEP 6: Check Console Logs for RAG ===');
    
    // Filter console for RAG-related logs
    const ragLogs = consoleErrors.filter(log => 
      log.includes('RAG') || log.includes('rag_context') || log.includes('SSE Chunk')
    );
    
    if (ragLogs.length > 0) {
      console.log('RAG-related console logs:');
      ragLogs.forEach(log => console.log('  -', log));
    } else {
      console.log('⚠️  No RAG-related console logs found');
    }

    console.log('\n=== STEP 7: Get Page HTML for Inspection ===');
    const lastMessage = page.locator('[class*="message-assistant"]').last();
    const messageHTML = await lastMessage.innerHTML();
    
    console.log('\nMessage HTML (first 500 chars):');
    console.log(messageHTML.substring(0, 500));
    
    const hasViewSourcesInHTML = messageHTML.includes('View') && messageHTML.includes('Knowledge');
    console.log(hasViewSourcesInHTML ? '\n✓ "View Knowledge Sources" found in HTML' : '\n❌ "View Knowledge Sources" NOT in HTML');

    // Final verdict
    console.log('\n=== FINAL VERDICT ===');
    if (hasButton) {
      console.log('✅ RAG UI is working! View Sources button is present');
      
      // Try clicking it
      await viewSourcesButton.click();
      console.log('✓ Clicked View Sources button');
      
      // Check if sources expanded
      await page.waitForTimeout(500);
      const sourceCards = page.locator('[class*="rounded-lg border bg-muted"]');
      const sourceCount = await sourceCards.count();
      console.log(`✓ ${sourceCount} source cards displayed`);
      
      await page.screenshot({ path: 'test-results/rag-sources-expanded.png', fullPage: true });
    } else {
      console.log('❌ RAG UI not working - Sources button missing');
      console.log('Possible issues:');
      console.log('  1. RAG context not received from backend');
      console.log('  2. SSE parsing issue');
      console.log('  3. State not updating correctly');
    }
  });

  test('inspect console logs during chat', async ({ page, context }) => {
    // Capture all console messages
    const messages: any[] = [];
    page.on('console', msg => {
      messages.push({
        type: msg.type(),
        text: msg.text(),
      });
    });

    await page.goto(`/${blueprint}`);
    
    const textarea = page.locator('textarea[placeholder*="Ask anything"]');
    await textarea.fill('What is Kubernetes?');
    await textarea.press('Enter');
    
    // Wait for response
    await page.locator('[class*="message-assistant"] .prose').waitFor({ timeout: 30000 });
    await page.waitForTimeout(3000);

    console.log('\n=== ALL CONSOLE MESSAGES ===');
    messages.forEach(msg => {
      if (msg.text.includes('SSE') || msg.text.includes('RAG') || msg.text.includes('rag_context')) {
        console.log(`[${msg.type}]`, msg.text);
      }
    });

    // Check if any RAG logs present
    const hasRAGLogs = messages.some(m => m.text.toLowerCase().includes('rag'));
    console.log(hasRAGLogs ? '\n✓ RAG logs found in console' : '\n❌ No RAG logs found');
  });
});
