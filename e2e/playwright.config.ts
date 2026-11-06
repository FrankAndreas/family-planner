import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { PYTHON as python } from './tests/helpers';

// The tests start their own family hub (from a family-hub checkout: logins and people, Admin PIN 1111), backend
// (fresh SQLite database and key), frontend and a calendar feed on ports of their own, so a dev server on 8000/5173
// and its data are never touched. E2E_PYTHON: the Python with the backend's packages. HUB_DIR: a family-hub checkout
// (default: next to this repo); HUB_PYTHON: the Python with the hub's packages (default: E2E_PYTHON).
export const BACKEND = 'http://localhost:8100';
export const FRONTEND = 'http://localhost:3100';
export const HUB = 'http://localhost:8130';
const tmp = path.resolve(__dirname, '.tmp');
const database = path.join(tmp, 'e2e.db');
const hubData = path.join(tmp, 'hub');
const hubDir = path.resolve(process.env.HUB_DIR ?? path.join(__dirname, '..', '..', 'family-hub'));
const hubPython = process.env.HUB_PYTHON ? path.resolve(process.env.HUB_PYTHON) : python;

export default defineConfig({
    testDir: './tests',
    // One backend and database for all tests
    workers: 1,
    retries: process.env.CI ? 1 : 0,
    reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
    use: {
        baseURL: FRONTEND,
        // The tests find elements by their English texts (DEFAULT_LANGUAGE=en below)
        locale: 'en-US',
        timezoneId: 'Europe/Zurich',
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
    },
    projects: [
        // The wall: an iPad in landscape
        { name: 'tablet', testIgnore: /phone\.spec\.ts/, use: { ...devices['Desktop Chrome'], viewport: { width: 1180, height: 820 }, hasTouch: true } },
        { name: 'phone', use: { ...devices['Pixel 7'] }, testMatch: /phone\.spec\.ts/ },
    ],
    webServer: [
        {
            command: `rm -rf "${hubData}" && mkdir -p "${hubData}" && "${hubPython}" -m uvicorn app.main:app --port 8130`,
            cwd: path.join(hubDir, 'backend'),
            url: `${HUB}/health`,
            env: {
                DATABASE_URL: `sqlite:///${hubData}/hub.db`,
                DATA_DIR: hubData,
                INITIAL_ADMIN_PIN: '1111',
                DEFAULT_LANGUAGE: 'en',
                // Plain http in the tests: a Secure cookie would never come back
                COOKIE_INSECURE: '1',
            },
            reuseExistingServer: false,
            timeout: 60_000,
        },
        {
            command: `"${python}" -I "${path.join(__dirname, 'serve_ics.py')}" "${path.join(tmp, 'feed')}"`,
            url: 'http://127.0.0.1:8140/family.ics',
            reuseExistingServer: false,
            timeout: 30_000,
        },
        {
            command: `mkdir -p "${tmp}" && rm -f "${database}"* && head -c 32 /dev/urandom | base64 > "${tmp}/enc_key" && "${python}" -m uvicorn app.main:app --port 8100`,
            cwd: path.resolve(__dirname, '..', 'backend'),
            url: `${BACKEND}/health`,
            env: {
                DATABASE_URL: `sqlite:///${database}`,
                DATA_DIR: tmp,
                ENC_KEY_FILE: path.join(tmp, 'enc_key'),
                HUB_URL: HUB,
                HUB_PUBLIC_URL: HUB,
                DEFAULT_LANGUAGE: 'en',
                // The tests sync on purpose ("Update now"); no background sync in between
                SYNC_DISABLED: '1',
            },
            reuseExistingServer: false,
            timeout: 60_000,
        },
        {
            command: 'npx vite --port 3100 --strictPort',
            cwd: path.resolve(__dirname, '..', 'frontend'),
            url: FRONTEND,
            // Vite forwards /api to the test backend, so the hub's cookie is the page's own (as with nginx)
            env: { API_PROXY: BACKEND },
            reuseExistingServer: false,
            timeout: 60_000,
        },
    ],
});
