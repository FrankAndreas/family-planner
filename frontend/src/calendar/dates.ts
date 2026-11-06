import { addDays, format, getISOWeek, startOfDay, startOfMonth, startOfWeek } from 'date-fns';
import type { Occurrence, View } from '../types';

// Mon-first weeks, ISO week numbers (spec: locale-aware dates). The device's zone is the family's (Europe/Zurich)

export const weekStart = (day: Date): Date => startOfWeek(day, { weekStartsOn: 1 });
export const isoWeek = (day: Date): number => getISOWeek(day);
export const days = (start: Date, n: number): Date[] => Array.from({ length: n }, (_, i) => addDays(startOfDay(start), i));
export const isoDate = (day: Date): string => format(day, 'yyyy-MM-dd');

// A date "2026-11-20" is that day's local midnight; a time carries its offset
export function parseMoment(value: string): Date {
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        const [y, m, d] = value.split('-').map(Number);
        return new Date(y, m - 1, d);
    }
    return new Date(value);
}

export const startOf = (o: Occurrence): Date => parseMoment(o.start);
export const endOf = (o: Occurrence): Date => parseMoment(o.end);

// Whether an occurrence shows on a day. Ends are exclusive, so one ending exactly at midnight (or an all-day end date)
// belongs to the day before; one without length is on the day it starts
export function onDay(o: Occurrence, day: Date): boolean {
    const dayStart = startOfDay(day);
    const dayEnd = addDays(dayStart, 1);
    const start = startOf(o);
    const end = endOf(o);
    if (end <= start) return start >= dayStart && start < dayEnd;
    return start < dayEnd && end > dayStart;
}

export function monthGrid(day: Date): Date[][] {
    const first = weekStart(startOfMonth(day));
    return Array.from({ length: 6 }, (_, row) => days(addDays(first, row * 7), 7));
}

export const AGENDA_DAYS = 14;

// What the API is asked for in each view (to exclusive)
export function range(view: View, day: Date): { from: string; to: string } {
    const span = (start: Date, n: number) => ({ from: isoDate(start), to: isoDate(addDays(start, n)) });
    switch (view) {
        case 'day':
            return span(startOfDay(day), 1);
        case '3day':
            return span(startOfDay(day), 3);
        case 'week':
            return span(weekStart(day), 7);
        case 'month':
            return span(monthGrid(day)[0][0], 42);
        case 'agenda':
            return span(startOfDay(day), AGENDA_DAYS);
    }
}
