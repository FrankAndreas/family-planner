import { expect, test } from '@playwright/test';
import { ensureSource } from './helpers';

test.beforeEach(async ({ request }) => ensureSource(request));

test('the wall rests on this week with the family\'s events, no login', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto('/display');
    await expect(page.getByText('Zahnarzt')).toBeVisible();
    await expect(page.getByTestId('allday-bars').getByText('Herbstlager')).toBeVisible();
    await expect(page.getByText(/Week \d+/)).toBeVisible();
    await expect(page.getByTestId('day-header')).toHaveCount(7);
    expect(errors).toEqual([]);
});

test('switching views, an event\'s details, and back to the week after a while untouched', async ({ page }) => {
    await page.goto('/display?idle=2500');
    await page.getByRole('button', { name: 'Month' }).click();
    await expect(page.getByTestId('month-day')).toHaveCount(42);
    await page.getByRole('button', { name: 'Agenda' }).click();
    await page.getByText('Pizza bei Omi').click();
    await expect(page.getByRole('dialog', { name: 'Pizza bei Omi' })).toBeVisible();
    await expect(page).toHaveURL(/view=week/, { timeout: 10_000 });
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.getByTestId('day-header')).toHaveCount(7);
});
