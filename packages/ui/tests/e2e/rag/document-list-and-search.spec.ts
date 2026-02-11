import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Document List and Enhanced Search', () => {
  const blueprint = 'devassist';

  test('should display uploaded documents in a list', async ({ page }) => {
    // Navigate to knowledge page
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    // Upload a test document
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    // Wait for upload success
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });

    // Wait a moment for the document list to update
    await page.waitForTimeout(1000);

    // Verify document appears in the list
    await expect(page.getByText('test-document.md')).toBeVisible();

    // Verify file metadata is shown
    await expect(page.getByText(/\d+ chunks?/)).toBeVisible();
    await expect(page.getByText(/MD/i)).toBeVisible(); // File type

    // Verify delete button exists
    const deleteButton = page.locator('button').filter({ has: page.locator('svg').filter({ hasText: '' }) }).last();
    await expect(deleteButton).toBeVisible();
  });

  test('should show larger, user-friendly search box', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    // Check search input size
    const searchInput = page.getByPlaceholder(/ask a question about your documents/i);
    await expect(searchInput).toBeVisible();

    // Verify it has larger styling (h-12 class should make it bigger)
    const inputHeight = await searchInput.evaluate(el => el.offsetHeight);
    expect(inputHeight).toBeGreaterThanOrEqual(48); // h-12 = 3rem = 48px

    // Verify search button has text label
    const searchButton = page.getByRole('button', { name: /search/i });
    await expect(searchButton).toBeVisible();
    await expect(searchButton).toContainText('Search');
  });

  test('should perform semantic search with enhanced results', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    // Upload a document first
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });

    // Wait for document to be indexed
    await page.waitForTimeout(2000);

    // Perform search
    const searchInput = page.getByPlaceholder(/ask a question about your documents/i);
    await searchInput.fill('kubernetes deployment');
    
    const searchButton = page.getByRole('button', { name: /search/i });
    await searchButton.click();

    // Wait for results
    await page.waitForTimeout(2000);

    // Verify enhanced search results display
    const resultsSection = page.locator('text=/Found \\d+ relevant/');
    if (await resultsSection.isVisible()) {
      // Verify result cards show more info
      await expect(page.getByText(/% match/)).toBeVisible();
      await expect(page.getByText(/Scope:/)).toBeVisible();
    }
  });

  test('should allow deleting individual documents', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    // Upload a document
    const filePath = path.join(__dirname, '../../fixtures/test-code.py');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });

    await page.waitForTimeout(1000);

    // Find and click delete button for the document
    const documentRow = page.locator('div').filter({ hasText: 'test-code.py' }).first();
    await expect(documentRow).toBeVisible();

    const deleteButton = documentRow.locator('button').last();
    await deleteButton.click();

    // Verify confirmation dialog appears
    await expect(page.getByText(/are you sure you want to delete/i)).toBeVisible();
    await expect(page.getByText(/test-code\.py/i)).toBeVisible();

    // Confirm deletion
    const confirmButton = page.getByRole('dialog').getByRole('button', { name: /delete/i });
    await confirmButton.click();

    // Verify success message
    await expect(page.getByText(/deleted test-code\.py/i)).toBeVisible({ timeout: 5000 });

    // Verify document is removed from list
    await page.waitForTimeout(1000);
    const docStillExists = await page.locator('text=test-code.py').count();
    expect(docStillExists).toBe(0);
  });

  test('should group document chunks by filename', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    // Upload a document that will be chunked
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });

    await page.waitForTimeout(1000);

    // Verify only one entry for the file (chunks are grouped)
    const documentEntries = await page.locator('text=test-document.md').count();
    expect(documentEntries).toBe(1);

    // Verify chunk count is shown
    await expect(page.getByText(/\d+ chunks?/)).toBeVisible();
  });
});
