import axios from 'axios';
import i18n from './i18n';
import { loginAddress, renewNow, type HubLinks } from './hubAddress';
import type { CalendarInfo, Occurrence } from './types';

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

// The browser's storage, if it may be used (blocked site data, private windows: null)
function storage(): Storage | null {
    try {
        return window.localStorage;
    } catch {
        return null;
    }
}

// The hub login is in its last week: through the hub once (hubAddress.renewNow), which sends the browser back here
export function renewsAtHub(headers: Record<string, unknown>): boolean {
    if (!renewNow(headers, storage())) return false;
    void goToHub();
    return true;
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

// --- What the screens read (no login) ---


type ApiOccurrence = {
    key: string; title: string; start: string; end: string; all_day: boolean; location: string; description: string;
    calendar_ids: number[];
};
type ApiCalendar = Omit<CalendarInfo, 'lastSuccessAt'> & { last_success_at: string | null };

export async function fetchEvents(from: string, to: string): Promise<Occurrence[]> {
    const { data } = await api.get<ApiOccurrence[]>('/api/events', { params: { from, to } });
    return data.map((o) => ({
        key: o.key, title: o.title, start: o.start, end: o.end, allDay: o.all_day,
        location: o.location || undefined, description: o.description || undefined, calendarIds: o.calendar_ids,
    }));
}

export async function fetchCalendars(): Promise<CalendarInfo[]> {
    const { data } = await api.get<ApiCalendar[]>('/api/calendars');
    return data.map(({ last_success_at, ...rest }) => ({ ...rest, lastSuccessAt: last_success_at }));
}

export type PublicConfig = { language: 'de' | 'en'; family_color: string; synced_at: string | null };

export async function fetchConfig(): Promise<PublicConfig> {
    return (await api.get<PublicConfig>('/api/config')).data;
}
