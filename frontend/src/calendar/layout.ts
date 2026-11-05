import { addDays, differenceInMinutes, startOfDay } from 'date-fns';
import type { Occurrence } from '../types';
import { endOf, onDay, startOf } from './dates';

export type PlacedEvent = { o: Occurrence; top: number; height: number; col: number; cols: number };
export type Bar = { o: Occurrence; startCol: number; span: number; row: number };

// Overlap is judged with at least this length, so short events next to each other don't sit on top of one another
const MIN_MINUTES = 30;

// Whether a timed event runs into another day (then it is a bar on top, like an all-day event)
export function crossesMidnight(o: Occurrence): boolean {
    if (o.allDay) return false;
    const start = startOf(o);
    const end = endOf(o);
    return end > start && startOfDay(new Date(end.getTime() - 1)).getTime() !== startOfDay(start).getTime();
}

// Timed events of one day, placed in minutes from 00:00; overlapping ones share the width in columns
export function layoutTimed(occurrences: Occurrence[], day: Date): PlacedEvent[] {
    const dayStart = startOfDay(day);
    const dayMinutes = differenceInMinutes(addDays(dayStart, 1), dayStart);
    const items = occurrences
        .filter((o) => !o.allDay && !crossesMidnight(o) && onDay(o, day))
        .map((o) => {
            const top = Math.max(0, differenceInMinutes(startOf(o), dayStart));
            const bottom = Math.min(dayMinutes, differenceInMinutes(endOf(o), dayStart));
            return { o, top, height: Math.max(0, bottom - top), until: Math.max(bottom, top + MIN_MINUTES) };
        })
        .sort((a, b) => a.top - b.top || b.until - a.until);

    const placed: PlacedEvent[] = [];
    let cluster: { item: (typeof items)[number]; col: number }[] = [];
    let clusterEnd = -1;
    const close = () => {
        const cols = Math.max(1, ...cluster.map((c) => c.col + 1));
        for (const { item, col } of cluster) placed.push({ o: item.o, top: item.top, height: item.height, col, cols });
        cluster = [];
    };
    for (const item of items) {
        if (cluster.length && item.top >= clusterEnd) close();
        const busy = new Set(cluster.filter((c) => c.item.until > item.top).map((c) => c.col));
        let col = 0;
        while (busy.has(col)) col++;
        cluster.push({ item, col });
        clusterEnd = Math.max(clusterEnd, item.until);
    }
    if (cluster.length) close();
    return placed;
}

// All-day events and timed ones over midnight, as bars across the days they cover; overlapping bars stack in rows
export function allDayBars(occurrences: Occurrence[], days: Date[]): Bar[] {
    const spans = occurrences
        .filter((o) => o.allDay || crossesMidnight(o))
        .map((o) => {
            const cols = days.map((day, i) => (onDay(o, day) ? i : -1)).filter((i) => i >= 0);
            return cols.length ? { o, startCol: cols[0], span: cols[cols.length - 1] - cols[0] + 1 } : null;
        })
        .filter((s): s is { o: Occurrence; startCol: number; span: number } => s !== null)
        .sort((a, b) => a.startCol - b.startCol || b.span - a.span);
    const rowEnds: number[] = [];
    return spans.map((s) => {
        let row = rowEnds.findIndex((end) => end <= s.startCol);
        if (row < 0) row = rowEnds.length;
        rowEnds[row] = s.startCol + s.span;
        return { ...s, row };
    });
}
