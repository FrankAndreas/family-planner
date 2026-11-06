import { expect, test } from '@playwright/test';
import { ensureSource } from './helpers';

test.beforeEach(async ({ request }) => ensureSource(request));

test('a phone opens on the agenda', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('agenda-day').first()).toHaveText('Today');
    await expect(page.getByText('Zahnarzt')).toBeVisible();
    await expect(page.getByText('Pizza bei Omi')).toBeVisible();
});
