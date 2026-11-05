import { useEffect, useState } from 'react';
import { fetchCalendars, fetchEvents } from '../api';
import type { CalendarInfo, Occurrence, View } from '../types';
import { range } from './dates';

// Newly synced changes show within a minute (the backend syncs every 5 minutes)
export const REFRESH_MS = 60_000;

export function useCalendarData(view: View, day: Date) {
    const [occurrences, setOccurrences] = useState<Occurrence[]>([]);
    const [calendars, setCalendars] = useState<Map<number, CalendarInfo>>(new Map());
    const [failed, setFailed] = useState(false);
    const { from, to } = range(view, day);

    useEffect(() => {
        let alive = true;
        const load = () => {
            Promise.all([fetchEvents(from, to), fetchCalendars()])
                .then(([events, cals]) => {
                    if (!alive) return;
                    setOccurrences(events);
                    setCalendars(new Map(cals.map((c) => [c.id, c])));
                    setFailed(false);
                })
                // Keep what is shown; the NAS may be restarting
                .catch(() => alive && setFailed(true));
        };
        load();
        const timer = window.setInterval(load, REFRESH_MS);
        return () => {
            alive = false;
            window.clearInterval(timer);
        };
    }, [from, to]);

    return { occurrences, calendars, failed };
}
