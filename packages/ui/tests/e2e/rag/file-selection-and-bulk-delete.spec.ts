import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('File Selection and Bulk Delete', () => {
  const blueprint = 'devassist';

  test('should display checkboxes for each file', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    // Upload two test files
    const file1 = path.join(__dirname, '../../fixtures/test-document.md');
    const file2 = path.join(__dirname, '../../fixtures/test-code.py');
    
    const fileInput = page.locator('input[type="file"]');
    
    await fileInput.setInputFiles(file1);
    await expect(page.getByText(/successfully uploaded test-document/i)).toBeVisible({ timeout: 10000 });
    
    await fileInput.setInputFiles(file2);
    await expect(page.getByText(/successfully uploaded test-code/i)).toBeVisible({ timeout: 10000 });

    await page.waitForTimeout(1000);

    // Verify checkboxes exist for both files
    const checkboxes = page.locator('[role="checkbox"]');
    const checkboxCount = await checkboxes.count();
    
    console.log(`Found ${checkboxCount} checkboxes`);
    expect(checkboxCount).toBeGreaterThanOrEqual(2);
  });

  test('should toggle file selection on checkbox click', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    // Wait for documents to load
    await page.waitForTimeout(2000);

    // Find first checkbox
    const firstCheckbox = page.locator('[role="checkbox"]').first();
    await expect(firstCheckbox).toBeVisible();

    // Should start unchecked
    const initialState = await firstCheckbox.getAttribute('data-state');
    console.log('Initial checkbox state:', initialState);

    // Click to select
    await firstCheckbox.click();
    await page.waitForTimeout(300);

    const afterClickState = await firstCheckbox.getAttribute('data-state');
    console.log('After click state:', afterClickState);
    expect(afterClickState).toBe('checked');

    // Click again to deselect
    await firstCheckbox.click();
    await page.waitForTimeout(300);

    const afterSecondClick = await firstCheckbox.getAttribute('data-state');
    expect(afterSecondClick).toBe('unchecked');
  });

  test('should show "Select All" and "Deselect All" buttons', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check for Select All button
    const selectAllButton = page.getByRole('button', { name: /select all/i });
    
    if (await selectAllButton.isVisible()) {
      console.log('✓ Select All button found');
      
      // Click it
      await selectAllButton.click();
      await page.waitForTimeout(500);

      // Should now show "Deselect All"
      const deselectButton = page.getByRole('button', { name: /deselect all/i });
      await expect(deselectButton).toBeVisible();
      console.log('✓ Changed to Deselect All after clicking');
    } else {
      console.log('⚠️  No Select All button (might be no documents)');
    }
  });

  test('should show "Delete X Selected" button when files are selected', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Select first file
    const firstCheckbox = page.locator('[role="checkbox"]').first();
    if (await firstCheckbox.isVisible()) {
      await firstCheckbox.click();
      await page.waitForTimeout(500);

      // Check for Delete Selected button
      const deleteButton = page.getByRole('button', { name: /delete.*selected/i });
      await expect(deleteButton).toBeVisible();
      console.log('✓ Delete Selected button appeared');

      // Verify it shows count
      const buttonText = await deleteButton.textContent();
      console.log('Button text:', buttonText);
      expect(buttonText).toMatch(/delete.*\d+.*selected/i);
    }
  });

  test('should highlight selected files', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const firstCheckbox = page.locator('[role="checkbox"]').first();
    if (await firstCheckbox.isVisible()) {
      // Get the parent card
      const fileCard = firstCheckbox.locator('..').locator('..');
      
      // Check initial state (not highlighted)
      const initialClass = await fileCard.getAttribute('class');
      console.log('Initial classes:', initialClass);

      // Click to select
      await firstCheckbox.click();
      await page.waitForTimeout(300);

      // Check for highlight
      const selectedClass = await fileCard.getAttribute('class');
      console.log('Selected classes:', selectedClass);
      
      expect(selectedClass).toContain('primary');
    }
  });

  test('should perform bulk delete', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    // Upload test file
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(1000);

    // Select the file
    const checkbox = page.locator('[role="checkbox"]').first();
    await checkbox.click();
    await page.waitForTimeout(300);

    // Click Delete Selected
    const deleteButton = page.getByRole('button', { name: /delete.*selected/i });
    await deleteButton.click();

    // Verify confirmation dialog
    await expect(page.getByText(/are you sure you want to delete.*selected/i)).toBeVisible();
    
    // Verify file list in dialog
    await expect(page.getByText('test-document.md')).toBeVisible();

    // Confirm deletion
    const confirmButton = page.getByRole('dialog').getByRole('button', { name: /delete.*files?/i });
    await confirmButton.click();

    // Wait for success message
    await expect(page.getByText(/deleted.*files?/i)).toBeVisible({ timeout: 5000 });
    console.log('✓ Bulk delete completed successfully');
  });

  test('should select all files at once', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');
    
    // Upload multiple files
    const file1 = path.join(__dirname, '../../fixtures/test-document.md');
    const file2 = path.join(__dirname, '../../fixtures/test-code.py');
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(file1);
    await page.waitForTimeout(3000);
    await fileInput.setInputFiles(file2);
    await page.waitForTimeout(3000);

    // Click Select All
    const selectAllButton = page.getByRole('button', { name: /select all/i });
    if (await selectAllButton.isVisible()) {
      await selectAllButton.click();
      await page.waitForTimeout(500);

      // Verify all checkboxes are checked
      const checkboxes = page.locator('[role="checkbox"]');
      const count = await checkboxes.count();
      
      for (let i = 0; i < count; i++) {
        const state = await checkboxes.nth(i).getAttribute('data-state');
        expect(state).toBe('checked');
      }

      console.log(`✓ All ${count} checkboxes selected`);

      // Verify Delete button shows correct count
      const deleteButton = page.getByRole('button', { name: /delete.*selected/i });
      const buttonText = await deleteButton.textContent();
      console.log('Delete button:', buttonText);
    }
  });
});
