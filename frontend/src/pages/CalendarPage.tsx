import { useCallback, useEffect, useState } from 'react';
import { addDays, addMonths, startOfDay } from 'date-fns';
import { useLocation, useSearchParams } from 'react-router-dom';
import { fetchConfig } from '../api';
import { applyLanguage } from '../i18n';
import type { Occurrence, View } from '../types';
import TopBar from '../calendar/TopBar';
import TimeGrid from '../calendar/TimeGrid';
import EventSheet from '../calendar/EventSheet';
import { days, isoDate, parseMoment, weekStart } from '../calendar/dates';
import { useCalendarData } from '../calendar/useCalendarData';
import { useIdleReturn } from '../calendar/useIdleReturn';
import MonthGrid from '../calendar/MonthGrid';
import Agenda from '../calendar/Agenda';

// Back to this week's week view after 3 minutes untouched (on the wall)
export const IDLE_MS = 180_000;
const VIEWS: View[] = ['day', '3day', 'week', 'month', 'agenda'];

const narrow = () => window.matchMedia?.('(max-width: 767px)').matches ?? false;

function step(view: View, day: Date, direction: -1 | 1): Date {
    switch (view) {
        case 'day': return addDays(day, direction);
        case '3day': return addDays(day, 3 * direction);
        case 'week': return addDays(day, 7 * direction);
        case 'month': return addMonths(day, direction);
        case 'agenda': return addDays(day, 14 * direction);
    }
}

export default function CalendarPage() {
    const [params, setParams] = useSearchParams();
    const { pathname } = useLocation();
    const onWall = pathname === '/display';
    const view: View = VIEWS.includes(params.get('view') as View) ? (params.get('view') as View) : narrow() ? 'agenda' : 'week';
    const dateParam = params.get('date');
    const day = dateParam && /^\d{4}-\d{2}-\d{2}$/.test(dateParam) ? parseMoment(dateParam) : startOfDay(new Date());
    const [open, setOpen] = useState<Occurrence | null>(null);
    // The browser tests shorten the refresh with ?refresh=<ms>
    const refreshMs = Number(params.get('refresh')) || undefined;
    const { occurrences, calendars, failed, loadedAt } = useCalendarData(view, day, refreshMs);

    useEffect(() => {
        fetchConfig().then((config) => applyLanguage(config.language)).catch(() => {});
    }, []);

    const go = useCallback((next: { view?: View; day?: Date | null }) => {
        const p = new URLSearchParams(params);
        if (next.view) p.set('view', next.view);
        if (next.day === null) p.delete('date');
        else if (next.day) p.set('date', isoDate(next.day));
        setParams(p, { replace: true });
    }, [params, setParams]);

    // The browser tests shorten the wait with ?idle=<ms>
    const idleMs = Number(params.get('idle')) || IDLE_MS;
    const backToWeek = useCallback(() => {
        setOpen(null);
        go({ view: 'week', day: null });
    }, [go]);
    useIdleReturn(idleMs, onWall, backToWeek);

    const problem = failed || [...calendars.values()].some((c) => !c.ok);
    const shownDays = view === 'day' ? days(day, 1) : view === '3day' ? days(day, 3) : days(weekStart(day), 7);

    return (
        <div className="flex h-dvh flex-col">
            <TopBar view={view} day={day} problem={problem} lastUpdated={failed ? loadedAt : null}
                    onView={(v) => go({ view: v })}
                    onStep={(direction) => go({ day: step(view, day, direction) })} onToday={() => go({ day: null })} />
            <main className="min-h-0 flex-1">
                {view === 'month' ? (
                    <MonthGrid day={day} occurrences={occurrences} calendars={calendars} onOpenDay={(d) => go({ view: 'day', day: d })} />
                ) : view === 'agenda' ? (
                    <Agenda from={day} occurrences={occurrences} calendars={calendars} onOpen={setOpen} />
                ) : (
                    <TimeGrid days={shownDays} occurrences={occurrences} calendars={calendars} onOpen={setOpen} />
                )}
            </main>
            {open && <EventSheet o={open} calendars={calendars} onClose={() => setOpen(null)} />}
        </div>
    );
}
