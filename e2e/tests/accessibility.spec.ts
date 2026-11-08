import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { ensureSource, loginAsAdmin } from './helpers';

// Accessibility review 2026-11-08: axe finds nothing in any view, the event's details or the settings, on the tablet
// and a phone (playwright.config.ts runs this file in both)
async function noViolations(page: Page, state: string) {
    const { violations } = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
        .analyze();
    expect(violations.map(v => `${v.id}: ${v.nodes.map(n => n.target.join(' ')).join(', ')}`), state).toEqual([]);
}

test.beforeEach(async ({ request }) => ensureSource(request));

test('the wall: every view and an event', async ({ page }) => {
    await page.goto('/display');
    await expect(page.getByText('Zahnarzt').first()).toBeVisible();
    await expect(page).toHaveTitle('Family calendar');
    await noViolations(page, 'week');
    for (const view of ['Day', '3 days', 'Month', 'Agenda']) {
        const button = page.getByRole('button', { name: view, exact: true });
        await button.click();
        // The view shown is said, not only coloured
        await expect(button).toHaveAttribute('aria-pressed', 'true');
        await noViolations(page, view);
    }
    await expect(page.getByRole('button', { name: 'Week', exact: true })).toHaveAttribute('aria-pressed', 'false');

    // The details: a dialog with the focus in it, closed by Escape, the focus back on the event
    const event = page.getByRole('button', { name: /Pizza bei Omi/ }).first();
    await event.click();
    const dialog = page.getByRole('dialog', { name: 'Pizza bei Omi' });
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeFocused();
    await noViolations(page, 'event');
    await page.keyboard.press('Tab');
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(event).toBeFocused();
});

test('the settings', async ({ page, request }) => {
    await loginAsAdmin(page, request);
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
    await expect(page).toHaveTitle('Settings · Family calendar');
    await noViolations(page, 'settings');
    await page.getByRole('button', { name: 'Add source' }).click();
    await noViolations(page, 'adding a source');
});
