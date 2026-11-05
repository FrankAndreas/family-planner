import api from '../api';

// The parents' settings API (all need the hub login as a parent). Credentials go in and never come back

export type SourceCalendar = { id: number; name: string; enabled: boolean; visible: boolean; person_id: number | null; color: string | null };
export type Source = {
    id: number;
    kind: 'google_ical' | 'icloud_caldav';
    name: string;
    has_credential: true;
    last_success_at: string | null;
    last_error: string | null;
    calendars: SourceCalendar[];
};
export type Person = { id: number; name: string; color: string | null; role?: string; language?: string | null };
export type NewSource =
    | { kind: 'google_ical'; name: string; url: string }
    | { kind: 'icloud_caldav'; name: string; apple_id: string; password: string };
export type SourceChange = { name?: string; url?: string; apple_id?: string; password?: string };

export const getMe = async () => (await api.get<Person & { role: string }>('/api/me')).data;
export const getSources = async () => (await api.get<Source[]>('/api/sources')).data;
export const getPeople = async () => (await api.get<Person[]>('/api/people')).data;
export const addSource = async (body: NewSource) => (await api.post<Source>('/api/sources', body)).data;
export const changeSource = async (id: number, body: SourceChange) => (await api.patch<Source>(`/api/sources/${id}`, body)).data;
export const deleteSource = async (id: number) => { await api.delete(`/api/sources/${id}`); };
export const syncSource = async (id: number) => (await api.post<Source>(`/api/sources/${id}/sync`)).data;
export const changeCalendar = async (id: number, body: Partial<Pick<SourceCalendar, 'person_id' | 'color' | 'visible' | 'enabled'>>) =>
    (await api.patch<SourceCalendar>(`/api/calendars/${id}`, body)).data;
export const setFamilyColor = async (family_color: string) => (await api.patch('/api/settings', { family_color })).data;
