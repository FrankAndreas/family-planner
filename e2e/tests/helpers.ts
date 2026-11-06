import path from 'node:path';
import { expect, request as playwrightRequest, type APIRequestContext, type Page } from '@playwright/test';

// The Python with the backend's packages; a path is made absolute (Python warns about relative ones with "..")
const configured = process.env.E2E_PYTHON ?? 'python3';
export const PYTHON = configured.includes('/') ? path.resolve(configured) : configured;

export const API = 'http://localhost:8100/api';
export const HUB = 'http://localhost:8130';
export const FRONTEND = 'http://localhost:3100';
export const FEED = 'http://127.0.0.1:8140/family.ics';
export const ADMIN_PIN = '1111';
// The hub takes changes only with its own header, and the manage cookie of the login
const HUB_HEADERS = { 'X-Requested-With': 'hub' };

// A login at the hub, in a throwaway API context: logging out would end the login, so the cookies are only read
async function hubCookies(name: string, pin: string): Promise<{ token: string; cookies: string }> {
    const context = await playwrightRequest.newContext();
    try {
        const response = await context.post(`${HUB}/api/login`, { data: { name, pin }, headers: HUB_HEADERS });
        expect(response.ok(), await response.text()).toBeTruthy();
        const found = response.headersArray()
            .filter(h => h.name.toLowerCase() === 'set-cookie' && /^hub_(session|manage)=/.test(h.value))
            .map(h => h.value.split(';')[0]);
        const session = found.find(c => c.startsWith('hub_session='));
        expect(session, 'the hub sets hub_session').toBeTruthy();
        return { token: session!.slice('hub_session='.length), cookies: found.join('; ') };
    } finally {
        await context.dispose();
    }
}

async function asHubAdmin<T = any>(request: APIRequestContext, method: string, url: string, data?: unknown): Promise<T> {
    const { cookies } = await hubCookies('Admin', ADMIN_PIN);
    const response = await request.fetch(`${HUB}${url}`, { method, data, headers: { ...HUB_HEADERS, Cookie: cookies } });
    expect(response.ok(), `${method} ${url}: ${await response.text()}`).toBeTruthy();
    return response.json();
}

// The planner's tile in the hub, with the key "planner" and Admin ticked (made on first use)
export async function plannerTile(request: APIRequestContext): Promise<void> {
    const tiles = await asHubAdmin<{ app_key: string | null }[]>(request, 'GET', '/api/tiles/manage');
    if (tiles.some(t => t.app_key === 'planner')) return;
    const admin = (await asHubAdmin<{ id: number; name: string }[]>(request, 'GET', '/api/people')).find(p => p.name === 'Admin')!;
    await asHubAdmin(request, 'POST', '/api/tiles', { name: 'Kalender', local_url: FRONTEND, app_key: 'planner', people: [admin.id] });
}

export async function adminToken(request: APIRequestContext): Promise<string> {
    await plannerTile(request);
    return (await hubCookies('Admin', ADMIN_PIN)).token;
}

// The test feed as a Google source (added once; the tests share one backend)
export async function ensureSource(request: APIRequestContext): Promise<void> {
    const headers = { Authorization: `Bearer ${await adminToken(request)}` };
    const sources = await (await request.get(`${API}/sources`, { headers })).json();
    if (sources.length) return;
    const response = await request.post(`${API}/sources`, { headers, data: { kind: 'google_ical', name: 'Familie', url: FEED } });
    expect(response.ok(), await response.text()).toBeTruthy();
}

// The page with Admin's hub cookie, as at home after logging in at the hub; errors in the browser console are collected
export async function loginAsAdmin(page: Page, request: APIRequestContext): Promise<string[]> {
    const errors: string[] = [];
    page.on('pageerror', e => errors.push(String(e)));
    page.on('dialog', d => d.accept());
    const token = await adminToken(request);
    await page.context().addCookies([{ name: 'hub_session', value: token, url: FRONTEND }]);
    return errors;
}
