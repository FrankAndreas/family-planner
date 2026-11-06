import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadSnapshot, saveSnapshot, type Snapshot } from './cache';

const week: Snapshot = {
    from: '2026-11-02', to: '2026-11-09', loadedAt: '2026-11-06T13:05:00.000Z',
    occurrences: [{ key: 'a|1', title: 'Zahnarzt', start: '2026-11-02T07:30:00+01:00', end: '2026-11-02T08:30:00+01:00',
        allDay: false, calendarIds: [1] }],
    calendars: [{ id: 1, name: 'Mama', color: '#e11d48', person: null, visible: true, ok: true, lastSuccessAt: null }],
};

describe('cache', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        localStorage.clear();
    });

    it('a saved snapshot comes back for the same range', () => {
        saveSnapshot(week);
        expect(loadSnapshot('2026-11-02', '2026-11-09')).toEqual(week);
    });

    it('another range gets nothing', () => {
        saveSnapshot(week);
        expect(loadSnapshot('2026-11-09', '2026-11-16')).toBeNull();
    });

    it('garbage or an older format gets nothing', () => {
        localStorage.setItem('planner:last', '{nope');
        expect(loadSnapshot('2026-11-02', '2026-11-09')).toBeNull();
        localStorage.setItem('planner:last', JSON.stringify({ v: 0, ...week }));
        expect(loadSnapshot('2026-11-02', '2026-11-09')).toBeNull();
        localStorage.setItem('planner:last', JSON.stringify({ v: 1, ...week, occurrences: 'x' }));
        expect(loadSnapshot('2026-11-02', '2026-11-09')).toBeNull();
    });

    it('a throwing localStorage is ignored', () => {
        vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('private mode'); });
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('private mode'); });
        expect(() => saveSnapshot(week)).not.toThrow();
        expect(loadSnapshot('2026-11-02', '2026-11-09')).toBeNull();
    });
});
