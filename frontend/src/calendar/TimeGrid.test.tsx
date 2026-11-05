import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import '../i18n';
import TimeGrid from './TimeGrid';
import { days } from './dates';
import type { CalendarInfo, Occurrence } from '../types';

const cal = (id: number, color: string): CalendarInfo =>
    ({ id, name: `C${id}`, color, person: null, visible: true, ok: true, lastSuccessAt: null });
const calendars = new Map([[1, cal(1, '#e11d48')], [2, cal(2, '#2563eb')]]);
const shared: Occurrence = {
    key: 'e|1', title: 'Elternabend', start: '2026-11-05T19:00:00+01:00', end: '2026-11-05T21:00:00+01:00',
    allDay: false, calendarIds: [1, 2],
};
const ferien: Occurrence = { key: 'f|1', title: 'Herbstferien', start: '2026-11-02', end: '2026-11-04', allDay: true,
    calendarIds: [2] };
const week = days(new Date(2026, 10, 2), 7);

describe('TimeGrid', () => {
    it('shows an event in two calendars once, with a stripe of each colour', () => {
        render(<TimeGrid days={week} occurrences={[shared]} calendars={calendars} onOpen={() => {}} />);
        const events = screen.getAllByText('Elternabend');
        expect(events).toHaveLength(1);
        const stripes = screen.getAllByTestId('stripe').map((s) => s.style.backgroundColor);
        expect(stripes).toEqual(['rgb(225, 29, 72)', 'rgb(37, 99, 235)']);
    });
    it('event titles are at least 18 px (text-lg)', () => {
        render(<TimeGrid days={week} occurrences={[shared]} calendars={calendars} onOpen={() => {}} />);
        expect(screen.getByText('Elternabend').className).toMatch(/\btext-(lg|xl|2xl)\b/);
    });
    it('all-day events are bars on top, and tapping opens the event', () => {
        const onOpen = vi.fn();
        render(<TimeGrid days={week} occurrences={[ferien]} calendars={calendars} onOpen={onOpen} />);
        fireEvent.click(screen.getByText('Herbstferien'));
        expect(onOpen).toHaveBeenCalledWith(ferien);
        expect(screen.getByTestId('allday-bars')).toContainElement(screen.getByText('Herbstferien'));
    });
    it('shows the ISO weekday headers Monday first', () => {
        render(<TimeGrid days={week} occurrences={[]} calendars={calendars} onOpen={() => {}} />);
        expect(screen.getAllByTestId('day-header').map((h) => h.textContent)).toEqual(
            ['Mo 2', 'Di 3', 'Mi 4', 'Do 5', 'Fr 6', 'Sa 7', 'So 8']);
    });
});
