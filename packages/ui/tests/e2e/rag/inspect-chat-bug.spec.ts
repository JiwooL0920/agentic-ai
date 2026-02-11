import { test } from '@playwright/test';

test('inspect chat HTML structure for "0" bug', async ({ page }) => {
  const blueprint = 'devassist';
  
  await page.goto(`/${blueprint}`);
  await page.waitForLoadState('networkidle');
  
  const textarea = page.locator('textarea[placeholder*="Ask anything"]');
  await textarea.fill('Hello');
  await textarea.press('Enter');
  
  // Wait for loading to start
  await page.waitForTimeout(1000);
  
  // Wait for loading to finish (prose content appears)
  await page.locator('[class*="message-assistant"] .prose').waitFor({ timeout: 30000 });
  
  // Get the last assistant message
  const assistantMessage = page.locator('[class*="message-assistant"]').last();
  
  // Get the HTML structure
  const html = await assistantMessage.innerHTML();
  console.log('\n=== FULL HTML ===');
  console.log(html);
  
  // Get text content
  const textContent = await assistantMessage.textContent();
  console.log('\n=== TEXT CONTENT ===');
  console.log(textContent);
  
  // Look for the prose div specifically
  const proseDiv = assistantMessage.locator('.prose');
  const proseText = await proseDiv.textContent();
  console.log('\n=== PROSE DIV TEXT ===');
  console.log(proseText);
  
  // Check if there are any unexpected elements
  const allText = await assistantMessage.allTextContents();
  console.log('\n=== ALL TEXT CONTENTS ===');
  console.log(allText);
  
  // Take a screenshot
  await assistantMessage.screenshot({ path: 'test-results/message-structure.png' });
  
  // Look for any elements that might contain "0"
  const elementsWithZero = await page.locator('text=/^0$/').all();
  console.log('\n=== ELEMENTS WITH JUST "0" ===');
  console.log('Count:', elementsWithZero.length);
  
  for (const el of elementsWithZero) {
    const tagName = await el.evaluate(node => node.tagName);
    const className = await el.evaluate(node => node.className);
    const parent = await el.evaluate(node => node.parentElement?.className || 'no parent');
    console.log(`Tag: ${tagName}, Class: ${className}, Parent: ${parent}`);
  }
});
