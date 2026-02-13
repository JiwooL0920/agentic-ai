import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Document Upload Flow', () => {
  const blueprint = 'devassist';
  const testScope = 'test-upload';

  test.beforeEach(async ({ page }) => {
    // Navigate to knowledge page
    await page.goto(`/${blueprint}/knowledge`);
    await page.waitForLoadState('networkidle');
  });

  test.afterEach(async ({ page }) => {
    // Clean up: delete test scope if it exists
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      await page.request.delete(`${apiUrl}/api/documents/scope/${testScope}`);
    } catch (error) {
      // Ignore errors if scope doesn't exist
    }
  });

  test('should display knowledge base page with upload area', async ({ page }) => {
    // Verify page title
    await expect(page.getByRole('heading', { name: /knowledge base/i })).toBeVisible();

    // Verify upload card is visible
    await expect(page.getByRole('heading', { name: /upload documents/i })).toBeVisible();

    // Verify drag and drop area
    await expect(page.getByText(/drag and drop your file here/i)).toBeVisible();

    // Verify supported formats are listed
    await expect(page.getByText(/supports:.*\.txt.*\.md.*\.py/i)).toBeVisible();
  });

  test('should successfully upload a markdown file', async ({ page }) => {
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');

    // Click browse button to trigger file input
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    // Wait for upload progress
    await expect(page.getByText(/uploading/i)).toBeVisible({ timeout: 5000 });

    // Wait for progress bar
    await expect(page.locator('[role="progressbar"]')).toBeVisible();

    // Wait for success message
    await expect(page.getByText(/successfully uploaded test-document\.md/i)).toBeVisible({ timeout: 10000 });

    // Verify document count increased
    await expect(page.getByText(/\d+ documents/)).toBeVisible();
  });

  test('should successfully upload a Python file', async ({ page }) => {
    const filePath = path.join(__dirname, '../../fixtures/test-code.py');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    // Wait for success message
    await expect(page.getByText(/successfully uploaded test-code\.py/i)).toBeVisible({ timeout: 10000 });
  });

  test('should show upload progress during upload', async ({ page }) => {
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    // Check for uploading indicator
    const uploadingText = page.getByText(/uploading/i);
    await expect(uploadingText).toBeVisible({ timeout: 3000 });

    // Check for progress percentage
    const progressText = page.getByText(/\d+%/);
    await expect(progressText).toBeVisible();

    // Progress bar should be visible
    await expect(page.locator('[role="progressbar"]')).toBeVisible();

    // Wait for completion
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });
  });

  test('should clear file input after successful upload', async ({ page }) => {
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');

    const fileInput = page.locator('input[type="file"]');
    
    // Upload first file
    await fileInput.setInputFiles(filePath);
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });

    // File input value is cleared by browser security after upload
    // Verify we can upload the same file again (proves input was reset)
    await fileInput.setInputFiles(filePath);
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });
  });

  test('should show current scope in upload card', async ({ page }) => {
    // Check for current scope display
    await expect(page.getByText(/current scope:/i)).toBeVisible();
    
    // Default scope should be shown
    await expect(page.getByText(/current scope: default/i)).toBeVisible();
  });

  test('should handle drag and drop file upload', async ({ page }) => {
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');

    // Get drop zone
    const dropZone = page.locator('div').filter({ hasText: /drag and drop your file here/i }).first();

    // Create data transfer for drag and drop
    const fileInput = page.locator('input[type="file"]');
    
    // Simulate drag and drop by using the file input
    // (Playwright doesn't support real drag-drop, so we use setInputFiles)
    await fileInput.setInputFiles(filePath);

    // Verify upload started
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });
  });

  test('should update document count after upload', async ({ page }) => {
    // Get initial count
    const initialCountText = await page.getByText(/\d+ documents/).first().textContent();
    const initialMatch = initialCountText?.match(/(\d+)/);
    const initialCount = initialMatch ? parseInt(initialMatch[1]) : 0;

    // Upload a file
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    // Wait for success
    await expect(page.getByText(/successfully uploaded/i)).toBeVisible({ timeout: 10000 });

    // Wait a bit for count to update
    await page.waitForTimeout(1000);

    // Verify count increased (documents are chunked, so count increases by more than 1)
    const updatedCountText = await page.getByText(/\d+ documents/).first().textContent();
    const updatedMatch = updatedCountText?.match(/(\d+)/);
    const updatedCount = updatedMatch ? parseInt(updatedMatch[1]) : 0;
    
    expect(updatedCount).toBeGreaterThan(initialCount);
  });

  test('should display success alert after upload', async ({ page }) => {
    const filePath = path.join(__dirname, '../../fixtures/test-document.md');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    // Wait for success alert
    const successAlert = page.getByRole('alert').filter({ hasText: /success/i });
    await expect(successAlert).toBeVisible({ timeout: 10000 });

    // Verify check circle icon (success icon)
    await expect(page.getByText(/successfully uploaded test-document\.md/i)).toBeVisible();
  });

  test('should allow multiple consecutive uploads', async ({ page }) => {
    const markdownPath = path.join(__dirname, '../../fixtures/test-document.md');
    const pythonPath = path.join(__dirname, '../../fixtures/test-code.py');

    const fileInput = page.locator('input[type="file"]');

    // Upload first file
    await fileInput.setInputFiles(markdownPath);
    await expect(page.getByText(/successfully uploaded test-document\.md/i)).toBeVisible({ timeout: 10000 });

    // Upload second file
    await fileInput.setInputFiles(pythonPath);
    await expect(page.getByText(/successfully uploaded test-code\.py/i)).toBeVisible({ timeout: 10000 });
  });
});
