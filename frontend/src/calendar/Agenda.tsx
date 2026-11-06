import { format, isToday, isTomorrow } from 'date-fns';
import { useTranslation } from 'react-i18next';
import type { CalendarInfo, Occurrence } from '../types';
import { AGENDA_DAYS, days, onDay, parseMoment } from './dates';
import { colorsOf } from './colors';
import { useDateLocale } from './locale';

type Props = { from: Date; occurrences: Occurrence[]; calendars: Map<number, CalendarInfo>; onOpen: (o: Occurrence) => void };

// The coming days as a list, made for phones: grouped by day, all-day entries first, empty days left out
export default function Agenda({ from, occurrences, calendars, onOpen }: Props) {
    const { t } = useTranslation();
    const locale = useDateLocale();
    const groups = days(from, AGENDA_DAYS)
        .map((day) => ({
            day,
            items: occurrences
                .filter((o) => onDay(o, day))
                .sort((a, b) => Number(b.allDay) - Number(a.allDay) || parseMoment(a.start).getTime() - parseMoment(b.start).getTime()),
        }))
        .filter((group) => group.items.length);
    const label = (day: Date) =>
        isToday(day) ? t('calendar.today') : isTomorrow(day) ? t('calendar.tomorrow') : format(day, 'EEEE, d. MMMM', { locale });

    if (!groups.length) return <p className="p-6 text-lg text-slate-400">{t('calendar.nothing')}</p>;
    return (
        <div className="h-full overflow-y-auto px-4 pb-6">
            {groups.map(({ day, items }) => (
                <section key={day.toISOString()}>
                    <h2 data-testid="agenda-day" className="sticky top-0 bg-slate-900/95 pb-1 pt-4 text-base font-semibold text-slate-400">
                        {label(day)}
                    </h2>
                    <ul>
                        {items.map((o) => (
                            <li key={o.key}>
                                <button type="button" onClick={() => onOpen(o)}
                                        className="flex min-h-12 w-full items-center gap-3 border-b border-white/5 py-2 text-left">
                                    <span className="w-24 shrink-0 text-base tabular-nums text-slate-400">
                                        {o.allDay ? t('calendar.allDay') : format(parseMoment(o.start), 'HH:mm')}
                                    </span>
                                    <span className="flex shrink-0 gap-1">
                                        {colorsOf(o, calendars).map((color, i) => (
                                            <span key={i} className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
                                        ))}
                                    </span>
                                    <span data-testid="agenda-title" className="truncate text-lg">{o.title}</span>
                                </button>
                            </li>
                        ))}
                    </ul>
                </section>
            ))}
        </div>
    );
}
