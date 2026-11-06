import { expect, test } from '@playwright/test';
import { ensureSource } from './helpers';

test.beforeEach(async ({ request }) => ensureSource(request));

test('a phone opens on the agenda', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('agenda-day').first()).toHaveText('Today');
    await expect(page.getByText('Zahnarzt')).toBeVisible();
    await expect(page.getByText('Pizza bei Omi')).toBeVisible();
});

test('the phone top bar takes at most two rows', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/?view=week');
    await expect(page.getByRole('button', { name: 'Week' })).toBeVisible();
    const header = await page.locator('header').boundingBox();
    expect(header!.height).toBeLessThanOrEqual(128);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
});
