import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import '../i18n';
import MonthGrid from './MonthGrid';
import type { CalendarInfo, Occurrence } from '../types';

const calendars = new Map<number, CalendarInfo>([[1, { id: 1, name: 'C', color: '#e11d48', person: null, visible: true,
    ok: true, lastSuccessAt: null }]]);
const at = (key: string, hour: number): Occurrence => ({ key, title: key, allDay: false, calendarIds: [1],
    start: `2026-11-05T${String(hour).padStart(2, '0')}:00:00+01:00`, end: `2026-11-05T${String(hour + 1).padStart(2, '0')}:00:00+01:00` });

describe('MonthGrid', () => {
    it('November 2026: six Mon-first weeks from 26 October', () => {
        render(<MonthGrid day={new Date(2026, 10, 17)} occurrences={[]} calendars={calendars} onOpenDay={() => {}} />);
        const cells = screen.getAllByTestId('month-day');
        expect(cells).toHaveLength(42);
        expect(cells[0]).toHaveTextContent('26');
        expect(cells[41]).toHaveTextContent('6');
    });
    it('up to three entries a day, then "+n"', () => {
        const many = [at('A', 8), at('B', 9), at('C', 10), at('D', 11), at('E', 12)];
        render(<MonthGrid day={new Date(2026, 10, 17)} occurrences={many} calendars={calendars} onOpenDay={() => {}} />);
        expect(screen.getByText('A')).toBeInTheDocument();
        expect(screen.queryByText('D')).toBeNull();
        expect(screen.getByText('+2')).toBeInTheDocument();
    });
    it('tapping a day opens it', () => {
        const onOpenDay = vi.fn();
        render(<MonthGrid day={new Date(2026, 10, 17)} occurrences={[]} calendars={calendars} onOpenDay={onOpenDay} />);
        fireEvent.click(screen.getAllByTestId('month-day')[10]);
        expect(onOpenDay).toHaveBeenCalledWith(new Date(2026, 10, 5));
    });
});
