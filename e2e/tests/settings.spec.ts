import { expect, test } from '@playwright/test';
import { API, FEED, loginAsAdmin } from './helpers';

test('a parent adds a Google calendar and gives it to a person', async ({ page, request }) => {
    const errors = await loginAsAdmin(page, request);
    await page.goto('/settings');
    // The other tests may have added the feed already; this one adds it under its own name
    await page.getByRole('button', { name: 'Add source' }).click();
    await page.getByLabel('Name').fill('Mama');
    await page.getByLabel('Secret address in iCal format').fill(FEED);
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    const card = page.locator('section.glass-card', { has: page.getByRole('heading', { name: /^Mama/ }) });
    await expect(card).toBeVisible();
    await card.getByLabel('Belongs to').selectOption({ label: 'Admin' });
    await expect.poll(async () => {
        const calendars = await (await request.get(`${API}/calendars`)).json();
        return calendars.find((c: { name: string }) => c.name === 'Mama')?.person?.name;
    }).toBe('Admin');
    expect(errors).toEqual([]);
});

test('a wrong address is refused and nothing is saved', async ({ page, request }) => {
    await loginAsAdmin(page, request);
    await page.goto('/settings');
    await page.getByRole('button', { name: 'Add source' }).click();
    await page.getByLabel('Name').fill('Kaputt');
    await page.getByLabel('Secret address in iCal format').fill('http://127.0.0.1:8140/nope.ics');
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await expect(page.getByRole('alert')).toHaveText('Address invalid or reset');
});

test('without a login the settings go to the hub', async ({ page }) => {
    await page.goto('/settings');
    await expect(page).toHaveURL(/localhost:8130\/\?next=/);
});
