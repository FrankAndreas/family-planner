// An event as the screens show it (GET /api/events, mapped from snake_case in api.ts). Timed start/end carry their
// offset ("2026-11-19T17:30:00+01:00"); all-day ones are dates ("2026-11-20"), end exclusive as in iCalendar
export type Occurrence = {
    key: string;
    title: string;
    start: string;
    end: string;
    allDay: boolean;
    location?: string;
    description?: string;
    calendarIds: number[];
};

export type CalendarInfo = {
    id: number;
    name: string;
    color: string;
    person: { id: number; name: string } | null;
    visible: boolean;
    ok: boolean;
    lastSuccessAt: string | null;
};

export type View = 'day' | '3day' | 'week' | 'month' | 'agenda';
