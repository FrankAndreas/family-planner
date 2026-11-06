import { format, isSameMonth, isToday } from 'date-fns';
import type { CalendarInfo, Occurrence } from '../types';
import { monthGrid, onDay } from './dates';
import { colorsOf } from './colors';
import { useDateLocale } from './locale';

type Props = { day: Date; occurrences: Occurrence[]; calendars: Map<number, CalendarInfo>; onOpenDay: (day: Date) => void };

const PER_DAY = 3;

export default function MonthGrid({ day, occurrences, calendars, onOpenDay }: Props) {
    const locale = useDateLocale();
    const grid = monthGrid(day);
    return (
        <div className="flex h-full flex-col">
            <div className="grid grid-cols-7 border-b border-white/10">
                {grid[0].map((d) => (
                    <div key={d.toISOString()} className="px-2 py-1 text-base font-semibold text-slate-400">
                        {format(d, 'EEEEEE', { locale })}
                    </div>
                ))}
            </div>
            <div className="grid flex-1 grid-cols-7 grid-rows-6">
                {grid.flat().map((d) => {
                    const here = occurrences.filter((o) => onDay(o, d));
                    return (
                        <button key={d.toISOString()} type="button" data-testid="month-day" onClick={() => onOpenDay(d)}
                                className={`flex min-h-0 flex-col overflow-hidden border-b border-l border-white/10 p-1 text-left
                                    ${isSameMonth(d, day) ? '' : 'opacity-40'} ${isToday(d) ? 'bg-white/5' : ''}`}>
                            <span className={`text-base font-semibold ${isToday(d) ? 'text-rose-400' : 'text-slate-300'}`}>
                                {format(d, 'd')}
                            </span>
                            {here.slice(0, PER_DAY).map((o) => (
                                <span key={o.key} className="flex items-center gap-1 truncate text-base leading-snug">
                                    <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: colorsOf(o, calendars)[0] }} />
                                    <span className="truncate">{o.title}</span>
                                </span>
                            ))}
                            {here.length > PER_DAY && <span className="text-sm text-slate-400">+{here.length - PER_DAY}</span>}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
