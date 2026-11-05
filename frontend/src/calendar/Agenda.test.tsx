import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '../i18n';
import Agenda from './Agenda';
import type { CalendarInfo, Occurrence } from '../types';

const calendars = new Map<number, CalendarInfo>([[1, { id: 1, name: 'C', color: '#e11d48', person: null, visible: true,
    ok: true, lastSuccessAt: null }]]);
const items: Occurrence[] = [
    { key: 'a', title: 'Team-Call', start: '2026-11-05T08:00:00+01:00', end: '2026-11-05T09:00:00+01:00', allDay: false, calendarIds: [1] },
    { key: 'b', title: 'Homeoffice', start: '2026-11-06', end: '2026-11-07', allDay: true, calendarIds: [1] },
    { key: 'c', title: 'Pizza', start: '2026-11-06T18:00:00+01:00', end: '2026-11-06T20:00:00+01:00', allDay: false, calendarIds: [1] },
    { key: 'd', title: 'Geburtstag', start: '2026-11-07T10:00:00+01:00', end: '2026-11-07T12:00:00+01:00', allDay: false, calendarIds: [1] },
];

describe('Agenda', () => {
    beforeEach(() => {
        vi.useFakeTimers({ toFake: ['Date'] });
        vi.setSystemTime(new Date(2026, 10, 5, 7, 0));
    });
    afterEach(() => vi.useRealTimers());

    it('groups by day with Heute and Morgen, all-day first, empty days left out', () => {
        render(<Agenda from={new Date(2026, 10, 5)} occurrences={[items[2], items[0], items[3], items[1]]}
                       calendars={calendars} onOpen={() => {}} />);
        expect(screen.getAllByTestId('agenda-day').map((d) => d.textContent)).toEqual(['Heute', 'Morgen', 'Samstag, 7. November']);
        expect(screen.getAllByTestId('agenda-title').map((t) => t.textContent)).toEqual(
            ['Team-Call', 'Homeoffice', 'Pizza', 'Geburtstag']);
    });
    it('says so when nothing is planned', () => {
        render(<Agenda from={new Date(2026, 10, 5)} occurrences={[]} calendars={calendars} onOpen={() => {}} />);
        expect(screen.getByText('Nichts geplant')).toBeInTheDocument();
    });
});
