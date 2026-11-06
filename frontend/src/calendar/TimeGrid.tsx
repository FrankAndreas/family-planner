import { useEffect, useRef, useState } from 'react';
import { format, isSameDay, isToday } from 'date-fns';
import type { CalendarInfo, Occurrence } from '../types';
import { allDayBars, firstScrollHour, layoutTimed } from './layout';
import { Stripes } from './EventBlock';
import { colorsOf, fill } from './colors';
import { useDateLocale } from './locale';

// Pixels per hour: a 30-minute event still has room for an 18 px title
export const HOUR_PX = 56;
const BAR_PX = 40;

type Props = {
    days: Date[];
    occurrences: Occurrence[];
    calendars: Map<number, CalendarInfo>;
    onOpen: (o: Occurrence) => void;
};

function useNow(): Date {
    const [now, setNow] = useState(() => new Date());
    useEffect(() => {
        const timer = window.setInterval(() => setNow(new Date()), 60_000);
        return () => window.clearInterval(timer);
    }, []);
    return now;
}

export default function TimeGrid({ days, occurrences, calendars, onOpen }: Props) {
    const locale = useDateLocale();
    const now = useNow();
    const scroller = useRef<HTMLDivElement>(null);
    const bars = allDayBars(occurrences, days);
    const barRows = bars.reduce((rows, bar) => Math.max(rows, bar.row + 1), 0);
    const columns = `3.5rem repeat(${days.length}, minmax(0, 1fr))`;

    // Opens at the morning's first event (at the latest 07:00); again only when other days are shown, not on every
    // refresh, so a hand that scrolled isn't undone
    const firstHour = firstScrollHour(days, occurrences);
    const shownDays = days.map((day) => day.getTime()).join();
    const scrolledFor = useRef<string | null>(null);
    useEffect(() => {
        if (!scroller.current || scrolledFor.current === shownDays) return;
        scroller.current.scrollTop = firstHour * HOUR_PX;
        // Before the events are loaded the first position is a guess: scroll again once they are there
        if (occurrences.length) scrolledFor.current = shownDays;
    }, [shownDays, firstHour, occurrences.length]);

    return (
        <div className="flex h-full min-h-0 flex-col">
            <div className="grid border-b border-white/10" style={{ gridTemplateColumns: columns }}>
                <div />
                {days.map((day) => (
                    <div key={day.toISOString()} data-testid="day-header"
                         className={`px-2 py-1 text-base font-semibold ${isToday(day) ? 'text-rose-400' : 'text-slate-300'}`}>
                        {format(day, 'EEEEEE d', { locale })}
                    </div>
                ))}
            </div>
            <div data-testid="allday-bars" className="relative grid border-b border-white/10"
                 style={{ gridTemplateColumns: columns, minHeight: barRows ? barRows * BAR_PX + 8 : 8 }}>
                {bars.map(({ o, startCol, span, row }) => {
                    const colors = colorsOf(o, calendars);
                    return (
                        <button key={`${o.key}-${startCol}`} type="button" onClick={() => onOpen(o)}
                                className="absolute flex items-stretch overflow-hidden rounded-md text-left"
                                style={{
                                    left: `calc(3.5rem + (100% - 3.5rem) * ${startCol} / ${days.length} + 2px)`,
                                    width: `calc((100% - 3.5rem) * ${span} / ${days.length} - 4px)`,
                                    top: row * BAR_PX + 4, height: BAR_PX - 4, backgroundColor: fill(colors[0]),
                                }}>
                            <Stripes colors={colors} />
                            <span className="truncate px-2 py-1 text-lg font-medium text-slate-50">{o.title}</span>
                        </button>
                    );
                })}
            </div>
            <div ref={scroller} data-testid="time-scroller" className="min-h-0 flex-1 overflow-y-auto">
                <div className="relative grid" style={{ gridTemplateColumns: columns, height: 24 * HOUR_PX }}>
                    <div className="relative">
                        {Array.from({ length: 24 }, (_, hour) => (
                            <div key={hour} className="absolute right-2 text-sm text-slate-500"
                                 style={{ top: hour * HOUR_PX - 8 }}>
                                {hour > 0 ? `${String(hour).padStart(2, '0')}:00` : ''}
                            </div>
                        ))}
                    </div>
                    {days.map((day) => (
                        <div key={day.toISOString()}
                             className={`relative border-l border-white/10 ${isToday(day) ? 'bg-white/5' : ''}`}
                             style={{ backgroundImage: `repeating-linear-gradient(to bottom, rgba(255,255,255,0.06) 0 1px, transparent 1px ${HOUR_PX}px)` }}>
                            {layoutTimed(occurrences, day).map(({ o, top, height, col, cols }) => {
                                const colors = colorsOf(o, calendars);
                                return (
                                    <button key={o.key} type="button" onClick={() => onOpen(o)}
                                            className="absolute flex items-stretch overflow-hidden rounded-md text-left"
                                            style={{
                                                top: (top / 60) * HOUR_PX + 1,
                                                height: Math.max((height / 60) * HOUR_PX - 2, 30),
                                                left: `calc(${(100 * col) / cols}% + 2px)`,
                                                width: `calc(${100 / cols}% - 4px)`,
                                                backgroundColor: fill(colors[0]),
                                            }}>
                                        <Stripes colors={colors} />
                                        <span className="flex min-w-0 flex-col px-2 py-0.5">
                                            <span className="truncate text-lg font-medium leading-tight text-slate-50">{o.title}</span>
                                            <span className="truncate text-sm text-slate-300">
                                                {format(new Date(o.start), 'HH:mm')}–{format(new Date(o.end), 'HH:mm')}
                                            </span>
                                        </span>
                                    </button>
                                );
                            })}
                            {isSameDay(day, now) && (
                                <div className="pointer-events-none absolute inset-x-0 h-0.5 bg-rose-500"
                                     style={{ top: ((now.getHours() * 60 + now.getMinutes()) / 60) * HOUR_PX }} />
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
