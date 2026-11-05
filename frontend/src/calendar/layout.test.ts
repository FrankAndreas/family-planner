import { describe, expect, it } from 'vitest';
import { allDayBars, layoutTimed } from './layout';
import { days } from './dates';
import type { Occurrence } from '../types';

const d = (y: number, m: number, day: number) => new Date(y, m - 1, day);
const occ = (key: string, start: string, end: string, allDay = false): Occurrence =>
    ({ key, title: key, start, end, allDay, calendarIds: [1] });

describe('layoutTimed', () => {
    it('overlapping events share the width', () => {
        const placed = layoutTimed([
            occ('a', '2026-11-05T16:00:00+01:00', '2026-11-05T17:00:00+01:00'),
            occ('b', '2026-11-05T16:00:00+01:00', '2026-11-05T17:00:00+01:00'),
            occ('c', '2026-11-05T18:00:00+01:00', '2026-11-05T19:00:00+01:00'),
        ], d(2026, 11, 5));
        const by = Object.fromEntries(placed.map((p) => [p.o.key, p]));
        expect([by.a.col, by.a.cols, by.b.col, by.b.cols]).toEqual([0, 2, 1, 2]);
        expect([by.c.col, by.c.cols]).toEqual([0, 1]);
        expect([by.a.top, by.a.height]).toEqual([16 * 60, 60]);
    });
    it('leaves out all-day and other days\' events, keeps one ending at midnight', () => {
        const placed = layoutTimed([
            occ('allday', '2026-11-05', '2026-11-06', true),
            occ('tomorrow', '2026-11-06T09:00:00+01:00', '2026-11-06T10:00:00+01:00'),
            occ('late', '2026-11-05T22:00:00+01:00', '2026-11-06T00:00:00+01:00'),
        ], d(2026, 11, 5));
        expect(placed.map((p) => [p.o.key, p.top, p.height])).toEqual([['late', 22 * 60, 120]]);
    });
});

describe('allDayBars', () => {
    const week = days(d(2026, 11, 2), 7);
    it('a 3-day event from Saturday fills the last two columns of its week', () => {
        const [bar] = allDayBars([occ('lager', '2026-11-07', '2026-11-10', true)], week);
        expect([bar.startCol, bar.span, bar.row]).toEqual([5, 2, 0]);
    });
    it('a timed event over midnight is a bar too; overlapping bars stack', () => {
        const bars = allDayBars([
            occ('reise', '2026-11-03T20:00:00+01:00', '2026-11-04T08:00:00+01:00'),
            occ('ferien', '2026-11-02', '2026-11-06', true),
        ], week);
        const by = Object.fromEntries(bars.map((b) => [b.o.key, b]));
        expect([by.ferien.startCol, by.ferien.span, by.ferien.row]).toEqual([0, 4, 0]);
        expect([by.reise.startCol, by.reise.span, by.reise.row]).toEqual([1, 2, 1]);
    });
    it('a timed event ending at midnight is no bar', () => {
        expect(allDayBars([occ('late', '2026-11-05T22:00:00+01:00', '2026-11-06T00:00:00+01:00')], week)).toEqual([]);
    });
});
