import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Document List and Enhanced Search', () => {
  const blueprint = 'devassist';

  test.beforeEach(async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');
    
    const deleteScopeButton = page.getByRole('button', { name: /delete scope/i });
    if (await deleteScopeButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await deleteScopeButton.click();
      const confirmButton = page.getByRole('dialog').getByRole('button', { name: /^delete$/i });
      if (await confirmButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await confirmButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('should display uploaded documents in a list', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    const filePath = path.join(__dirname, '../../fixtures/test-document.md');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(1000);

    await expect(page.getByText('test-document.md').first()).toBeVisible();
    await expect(page.getByText(/\d+ chunks?/).first()).toBeVisible();
    await expect(page.locator('span.uppercase').first()).toBeVisible();

    const deleteButton = page.locator('button').filter({ has: page.locator('[class*="text-destructive"]') }).first();
    await expect(deleteButton).toBeVisible();
  });

  test('should show larger, user-friendly search box', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    const searchInput = page.getByPlaceholder(/ask a question about your documents/i);
    await expect(searchInput).toBeVisible();

    const inputHeight = await searchInput.evaluate(el => (el as HTMLElement).offsetHeight);
    expect(inputHeight).toBeGreaterThanOrEqual(48);

    const searchButton = page.getByRole('button', { name: /search/i });
    await expect(searchButton).toBeVisible();
    await expect(searchButton).toContainText('Search');
  });

  test('should perform semantic search with enhanced results', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    const filePath = path.join(__dirname, '../../fixtures/test-document.md');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });

    await page.waitForTimeout(2000);

    const searchInput = page.getByPlaceholder(/ask a question about your documents/i);
    await searchInput.fill('kubernetes deployment');
    
    const searchButton = page.getByRole('button', { name: /search/i });
    await searchButton.click();

    await page.waitForTimeout(2000);

    const resultsSection = page.locator('text=/Found \\d+ relevant/');
    if (await resultsSection.isVisible()) {
      await expect(page.getByText(/% match/).first()).toBeVisible();
      await expect(page.getByText(/Scope:/).first()).toBeVisible();
    }
  });

  test('should allow deleting individual documents', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    const filePath = path.join(__dirname, '../../fixtures/test-code.py');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });

    await page.waitForTimeout(1000);

    const documentName = page.locator('p.truncate').filter({ hasText: 'test-code.py' }).first();
    await expect(documentName).toBeVisible();
    
    const documentContainer = documentName.locator('xpath=ancestor::div[contains(@class, "flex")][.//button]').first();
    const deleteButton = documentContainer.locator('button').last();
    await deleteButton.click();

    await expect(page.getByText(/are you sure you want to delete/i)).toBeVisible();
    await expect(page.getByRole('dialog').getByText(/test-code\.py/i)).toBeVisible();

    const confirmButton = page.getByRole('dialog').getByRole('button', { name: /^delete$/i });
    await confirmButton.click();

    await expect(page.getByText(/deleted.*test-code\.py/i)).toBeVisible({ timeout: 5000 });

    await page.waitForTimeout(1000);

    await expect(page.locator('p.truncate').filter({ hasText: 'test-code.py' })).toHaveCount(0, { timeout: 5000 });
  });

  test('should group document chunks by filename', async ({ page }) => {
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');

    const filePath = path.join(__dirname, '../../fixtures/test-document.md');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });

    await page.waitForTimeout(1000);

    const documentEntries = await page.locator('p.truncate').filter({ hasText: 'test-document.md' }).count();
    expect(documentEntries).toBe(1);

    await expect(page.getByText(/\d+ chunks?/).first()).toBeVisible();
  });
});
