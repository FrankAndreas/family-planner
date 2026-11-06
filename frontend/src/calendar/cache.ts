import type { CalendarInfo, Occurrence } from '../types';

// The last successful load, kept in the browser so the wall still shows its week when the NAS can't be reached
// (spec "Offline"). One snapshot only; every storage access may throw (private mode, blocked storage).
export type Snapshot = { from: string; to: string; occurrences: Occurrence[]; calendars: CalendarInfo[]; loadedAt: string };

const KEY = 'planner:last';
const VERSION = 1;

export function saveSnapshot(snapshot: Snapshot): void {
    try {
        localStorage.setItem(KEY, JSON.stringify({ v: VERSION, ...snapshot }));
    } catch {
        // Without storage the wall just has nothing to fall back on
    }
}

export function loadSnapshot(from: string, to: string): Snapshot | null {
    try {
        const raw = localStorage.getItem(KEY);
        if (!raw) return null;
        const { v, ...snapshot } = JSON.parse(raw);
        const valid = v === VERSION && typeof snapshot.loadedAt === 'string' && Array.isArray(snapshot.occurrences)
            && Array.isArray(snapshot.calendars);
        return valid && snapshot.from === from && snapshot.to === to ? (snapshot as Snapshot) : null;
    } catch {
        return null;
    }
}
