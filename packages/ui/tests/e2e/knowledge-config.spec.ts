import { test, expect } from '@playwright/test';

test.describe('Knowledge Config Panel', () => {
  const blueprint = 'devassist';

  test.beforeEach(async ({ page }) => {
    await page.goto(`/${blueprint}`);
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: /ask anything/i }).waitFor({ state: 'visible', timeout: 30000 });
  });

  test('should show disabled knowledge config button before session starts', async ({ page }) => {
    const knowledgeButton = page.locator('button').filter({ has: page.locator('svg.lucide-book-open') }).first();
    await expect(knowledgeButton).toBeVisible();
    await expect(knowledgeButton).toBeDisabled();
  });

  test('should enable knowledge config button after session starts', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /ask anything/i });
    await textarea.fill('Hello');
    await textarea.press('Enter');
    await page.waitForURL(/session=/);

    const knowledgeButton = page.locator('button').filter({ has: page.locator('svg.lucide-book-open') }).first();
    await expect(knowledgeButton).toBeEnabled();
  });

  test('should open knowledge config dialog on click', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /ask anything/i });
    await textarea.fill('Hello');
    await textarea.press('Enter');
    await page.waitForURL(/session=/);

    const knowledgeButton = page.locator('button').filter({ has: page.locator('svg.lucide-book-open') }).first();
    await expect(knowledgeButton).toBeEnabled();
    await knowledgeButton.click();

    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Knowledge Sources' })).toBeVisible();
    await expect(page.getByText('Configure which knowledge sources this session uses for RAG')).toBeVisible();
  });

  test('should show Agent Knowledge and My Documents toggles', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /ask anything/i });
    await textarea.fill('Hello');
    await textarea.press('Enter');
    await page.waitForURL(/session=/);

    const knowledgeButton = page.locator('button').filter({ has: page.locator('svg.lucide-book-open') }).first();
    await expect(knowledgeButton).toBeEnabled();
    await knowledgeButton.click();

    await expect(page.locator('svg.lucide-loader2')).toBeHidden({ timeout: 10000 });

    await expect(page.getByText('Agent Knowledge')).toBeVisible();
    await expect(page.getByText('Use knowledge scopes defined by the agent')).toBeVisible();
    
    await expect(page.getByText('My Documents')).toBeVisible();
    await expect(page.getByText("Include documents you've uploaded")).toBeVisible();
  });

  test('should toggle Agent Knowledge switch', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /ask anything/i });
    await textarea.fill('Hello');
    await textarea.press('Enter');
    await page.waitForURL(/session=/);

    const knowledgeButton = page.locator('button').filter({ has: page.locator('svg.lucide-book-open') }).first();
    await expect(knowledgeButton).toBeEnabled();
    await knowledgeButton.click();

    await expect(page.locator('svg.lucide-loader2')).toBeHidden({ timeout: 10000 });

    const switches = page.getByRole('switch');
    const agentKnowledgeSwitch = switches.first();

    await expect(agentKnowledgeSwitch).toBeChecked();

    await agentKnowledgeSwitch.click();
    await page.waitForTimeout(500);
    await expect(agentKnowledgeSwitch).not.toBeChecked();

    await agentKnowledgeSwitch.click();
    await page.waitForTimeout(500);
    await expect(agentKnowledgeSwitch).toBeChecked();
  });

  test('should show active count badge on button', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /ask anything/i });
    await textarea.fill('Hello');
    await textarea.press('Enter');
    await page.waitForURL(/session=/);

    const badge = page.locator('button').filter({ has: page.locator('svg.lucide-book-open') }).locator('.absolute');
    await expect(badge).toBeVisible();
    await expect(badge).toHaveText('2');
  });
});

test.describe('Knowledge Scope Indicator', () => {
  const blueprint = 'devassist';

  test.beforeEach(async ({ page }) => {
    await page.goto(`/${blueprint}`);
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: /ask anything/i }).waitFor({ state: 'visible', timeout: 30000 });
  });

  test('should not show indicator before session starts', async ({ page }) => {
    const indicator = page.locator('div').filter({ hasText: 'Sources:' }).first();
    await expect(indicator).toBeHidden();
  });

  test('should show indicator after session starts', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /ask anything/i });
    await textarea.fill('Hello');
    await textarea.press('Enter');
    await page.waitForURL(/session=/);
    await page.waitForTimeout(1000);

    const sourcesText = page.getByText('Sources:');
    await expect(sourcesText).toBeVisible({ timeout: 10000 });
  });

  test('should show Agent KB badge when agent scopes enabled', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /ask anything/i });
    await textarea.fill('Hello');
    await textarea.press('Enter');
    await page.waitForURL(/session=/);
    await page.waitForTimeout(1000);

    await expect(page.getByText('Agent KB')).toBeVisible({ timeout: 10000 });
  });

  test('should show My Docs badge when user docs enabled', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /ask anything/i });
    await textarea.fill('Hello');
    await textarea.press('Enter');
    await page.waitForURL(/session=/);
    await page.waitForTimeout(1000);

    await expect(page.getByText('My Docs')).toBeVisible({ timeout: 10000 });
  });

  test('should update indicator when config changes', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /ask anything/i });
    await textarea.fill('Hello');
    await textarea.press('Enter');
    await page.waitForURL(/session=/);

    await expect(page.getByText('Agent KB')).toBeVisible({ timeout: 10000 });

    const knowledgeButton = page.locator('button').filter({ has: page.locator('svg.lucide-book-open') }).first();
    await knowledgeButton.click();
    
    await expect(page.locator('svg.lucide-loader2')).toBeHidden({ timeout: 10000 });

    const switches = page.getByRole('switch');
    const agentKnowledgeSwitch = switches.first();
    await agentKnowledgeSwitch.click();

    await page.keyboard.press('Escape');
    await page.waitForTimeout(1000);

    await expect(page.getByText('Agent KB')).toBeHidden({ timeout: 5000 });
  });

  test('should show "No knowledge sources active" when all disabled', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /ask anything/i });
    await textarea.fill('Hello');
    await textarea.press('Enter');
    await page.waitForURL(/session=/);

    await expect(page.getByText('Sources:')).toBeVisible({ timeout: 10000 });

    const knowledgeButton = page.locator('button').filter({ has: page.locator('svg.lucide-book-open') }).first();
    await knowledgeButton.click();
    
    await expect(page.locator('svg.lucide-loader2')).toBeHidden({ timeout: 10000 });

    const switches = page.getByRole('switch');
    await switches.first().click();
    await page.waitForTimeout(300);
    await switches.nth(1).click();
    
    await page.keyboard.press('Escape');
    await page.waitForTimeout(1000);

    await expect(page.getByText('No knowledge sources active')).toBeVisible({ timeout: 5000 });
  });
});
