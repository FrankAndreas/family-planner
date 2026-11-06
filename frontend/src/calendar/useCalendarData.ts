import { useEffect, useMemo, useState } from 'react';
import { fetchCalendars, fetchEvents } from '../api';
import type { CalendarInfo, Occurrence, View } from '../types';
import { loadSnapshot, saveSnapshot } from './cache';
import { range } from './dates';

// Newly synced changes show within a minute (the backend syncs every 5 minutes)
export const REFRESH_MS = 60_000;

type Loaded = { from: string; to: string; occurrences: Occurrence[]; calendars: CalendarInfo[]; loadedAt: Date };

// The events of the shown range, refreshed every minute. When the NAS can't be reached the last loaded events stay,
// or the browser's copy of them after a reload; `loadedAt` says when they were loaded.
export function useCalendarData(view: View, day: Date, refreshMs: number = REFRESH_MS) {
    const [loaded, setLoaded] = useState<Loaded | null>(null);
    const [failed, setFailed] = useState(false);
    const { from, to } = range(view, day);

    useEffect(() => {
        let alive = true;
        const load = () => {
            Promise.all([fetchEvents(from, to), fetchCalendars()])
                .then(([occurrences, calendars]) => {
                    if (!alive) return;
                    const loadedAt = new Date();
                    setLoaded({ from, to, occurrences, calendars, loadedAt });
                    setFailed(false);
                    saveSnapshot({ from, to, occurrences, calendars, loadedAt: loadedAt.toISOString() });
                })
                .catch(() => {
                    if (!alive) return;
                    setFailed(true);
                    // Nothing of this range loaded yet (e.g. right after the nightly reload): the browser's copy
                    setLoaded((current) => {
                        if (current?.from === from && current.to === to) return current;
                        const saved = loadSnapshot(from, to);
                        return saved ? { ...saved, loadedAt: new Date(saved.loadedAt) } : current;
                    });
                });
        };
        load();
        const timer = window.setInterval(load, refreshMs);
        return () => {
            alive = false;
            window.clearInterval(timer);
        };
    }, [from, to, refreshMs]);

    const calendarList = loaded?.calendars;
    const calendars = useMemo(() => new Map((calendarList ?? []).map((c) => [c.id, c])), [calendarList]);
    // Events of another range never show in this one's columns
    const current = loaded?.from === from && loaded.to === to;
    return {
        occurrences: current ? loaded.occurrences : [],
        calendars,
        failed,
        loadedAt: loaded?.loadedAt ?? null,
    };
}
