import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import * as api from '../api';
import { saveSnapshot } from './cache';
import { REFRESH_MS, useCalendarData } from './useCalendarData';

const DAY = new Date(2026, 10, 6);
const event = (title: string) => ({ key: `${title}|1`, title, start: '2026-11-05T09:00:00+01:00',
    end: '2026-11-05T10:00:00+01:00', allDay: false, calendarIds: [1] });
const calendar = { id: 1, name: 'Mama', color: '#e11d48', person: null, visible: true, ok: true, lastSuccessAt: null };

// Lets the mocked requests settle under fake timers
const settle = () => act(async () => { await vi.advanceTimersByTimeAsync(0); });

describe('useCalendarData', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date(2026, 10, 6, 14, 30));
    });
    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
        localStorage.clear();
    });

    it('a successful load is saved and loadedAt set', async () => {
        vi.spyOn(api, 'fetchEvents').mockResolvedValue([event('Yoga')]);
        vi.spyOn(api, 'fetchCalendars').mockResolvedValue([calendar]);
        const { result } = renderHook(() => useCalendarData('week', DAY));
        await settle();
        expect(result.current.occurrences.map((o) => o.title)).toEqual(['Yoga']);
        expect(result.current.loadedAt).toEqual(new Date(2026, 10, 6, 14, 30));
        expect(JSON.parse(localStorage.getItem('planner:last')!).occurrences[0].title).toBe('Yoga');
    });

    it('when the first load fails, the saved week is shown', async () => {
        saveSnapshot({ from: '2026-11-02', to: '2026-11-09', occurrences: [event('Gespeichert')], calendars: [calendar],
            loadedAt: new Date(2026, 10, 5, 22, 10).toISOString() });
        vi.spyOn(api, 'fetchEvents').mockRejectedValue(new Error('offline'));
        vi.spyOn(api, 'fetchCalendars').mockRejectedValue(new Error('offline'));
        const { result } = renderHook(() => useCalendarData('week', DAY));
        await settle();
        expect(result.current.occurrences.map((o) => o.title)).toEqual(['Gespeichert']);
        expect(result.current.calendars.get(1)?.name).toBe('Mama');
        expect(result.current.failed).toBe(true);
        expect(result.current.loadedAt).toEqual(new Date(2026, 10, 5, 22, 10));
    });

    it('when a later load fails, what is shown stays', async () => {
        const events = vi.spyOn(api, 'fetchEvents').mockResolvedValue([event('Yoga')]);
        vi.spyOn(api, 'fetchCalendars').mockResolvedValue([calendar]);
        const { result } = renderHook(() => useCalendarData('week', DAY));
        await settle();
        events.mockRejectedValue(new Error('offline'));
        await act(async () => { await vi.advanceTimersByTimeAsync(REFRESH_MS); });
        expect(result.current.occurrences.map((o) => o.title)).toEqual(['Yoga']);
        expect(result.current.failed).toBe(true);
        expect(result.current.loadedAt).toEqual(new Date(2026, 10, 6, 14, 30));
    });

    it('a new range that can\'t be loaded shows nothing rather than the old range', async () => {
        const events = vi.spyOn(api, 'fetchEvents').mockResolvedValue([event('Yoga')]);
        vi.spyOn(api, 'fetchCalendars').mockResolvedValue([calendar]);
        const { result, rerender } = renderHook(({ day }) => useCalendarData('week', day), { initialProps: { day: DAY } });
        await settle();
        events.mockRejectedValue(new Error('offline'));
        rerender({ day: new Date(2026, 10, 13) });
        await settle();
        expect(result.current.occurrences).toEqual([]);
        expect(result.current.failed).toBe(true);
    });
});
