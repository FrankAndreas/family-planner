import axios from 'axios';
import i18n from './i18n';
import { loginAddress, type HubLinks } from './hubAddress';

// Same origin: Vite (dev, browser tests) or nginx (Docker) forwards /api to the backend. Viewing needs no login; the
// settings use the family hub's cookie, which the browser sends by itself. The backend takes changes made with the
// cookie only with this header (another site can make a browser send the cookie, but not the header)
const api = axios.create({ withCredentials: true, headers: { 'X-Requested-With': 'planner' } });

async function hubLinks(): Promise<HubLinks> {
    return (await api.get<HubLinks>('/api/hub')).data;
}

// To the hub's login; the hub sends the browser back here afterwards
export async function goToHub(next: string | null = window.location.href): Promise<void> {
    const address = loginAddress(await hubLinks(), next);
    if (address) window.location.href = address;
}

// "Log out": the hub ends the login for the planner and every other family app, then shows its login (back here after)
export async function goToHubLogout(): Promise<void> {
    const { logout_url } = await hubLinks();
    window.location.href = `${logout_url}?next=${encodeURIComponent(window.location.origin + '/settings')}`;
}

// The code of an error the app acts on (not_logged_in, parents_only, no_access, hub_unavailable, source_*)
export function errorCode(error: unknown): string | undefined {
    const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
    return typeof detail === 'string' ? detail : undefined;
}

export function errorMessage(error: unknown): string {
    const code = errorCode(error);
    if (code && i18n.exists(`errors.${code}`)) return i18n.t(`errors.${code}` as 'errors.generic');
    if (axios.isAxiosError(error) && !error.response) return i18n.t('errors.network');
    return i18n.t('errors.generic');
}

export default api;
