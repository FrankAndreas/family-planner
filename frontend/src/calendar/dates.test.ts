import { describe, expect, it } from 'vitest';
import { days, isoWeek, monthGrid, onDay, range, weekStart } from './dates';
import type { Occurrence } from '../types';

const d = (y: number, m: number, day: number) => new Date(y, m - 1, day);
const occ = (start: string, end: string, allDay = false): Occurrence =>
    ({ key: start, title: 'x', start, end, allDay, calendarIds: [1] });

describe('weeks', () => {
    it('ISO week numbers', () => {
        expect(isoWeek(d(2026, 11, 5))).toBe(45);
        expect(isoWeek(d(2027, 1, 1))).toBe(53);
    });
    it('weeks start on Monday', () => {
        expect(weekStart(d(2026, 11, 8))).toEqual(d(2026, 11, 2));
        expect(weekStart(d(2026, 11, 2))).toEqual(d(2026, 11, 2));
    });
    it('days', () => {
        expect(days(d(2026, 10, 24), 3)).toEqual([d(2026, 10, 24), d(2026, 10, 25), d(2026, 10, 26)]);
    });
});

describe('onDay', () => {
    it('an event ending at midnight belongs to its own day only', () => {
        const late = occ('2026-11-05T22:00:00+01:00', '2026-11-06T00:00:00+01:00');
        expect(onDay(late, d(2026, 11, 5))).toBe(true);
        expect(onDay(late, d(2026, 11, 6))).toBe(false);
    });
    it('all-day over the DST change stays on its dates', () => {
        const ferien = occ('2026-10-24', '2026-10-26', true);
        expect(onDay(ferien, d(2026, 10, 24))).toBe(true);
        expect(onDay(ferien, d(2026, 10, 25))).toBe(true);
        expect(onDay(ferien, d(2026, 10, 26))).toBe(false);
        expect(onDay(ferien, d(2026, 10, 23))).toBe(false);
    });
    it('an event without length is on its day', () => {
        const point = occ('2026-11-05T00:00:00+01:00', '2026-11-05T00:00:00+01:00');
        expect(onDay(point, d(2026, 11, 5))).toBe(true);
        expect(onDay(point, d(2026, 11, 4))).toBe(false);
    });
});

describe('month grid and ranges', () => {
    it('November 2026 starts on Monday 26 October and has 6 rows', () => {
        const grid = monthGrid(d(2026, 11, 17));
        expect(grid).toHaveLength(6);
        expect(grid[0][0]).toEqual(d(2026, 10, 26));
        expect(grid.every((row) => row.length === 7)).toBe(true);
    });
    it('ranges per view', () => {
        const day = d(2026, 11, 5);
        expect(range('day', day)).toEqual({ from: '2026-11-05', to: '2026-11-06' });
        expect(range('3day', day)).toEqual({ from: '2026-11-05', to: '2026-11-08' });
        expect(range('week', day)).toEqual({ from: '2026-11-02', to: '2026-11-09' });
        expect(range('month', day)).toEqual({ from: '2026-10-26', to: '2026-12-07' });
        expect(range('agenda', day)).toEqual({ from: '2026-11-05', to: '2026-11-19' });
    });
});
