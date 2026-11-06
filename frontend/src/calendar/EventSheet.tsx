import { addDays, format } from 'date-fns';
import { useTranslation } from 'react-i18next';
import type { CalendarInfo, Occurrence } from '../types';
import { parseMoment } from './dates';
import { useDateLocale } from './locale';

type Props = { o: Occurrence; calendars: Map<number, CalendarInfo>; onClose: () => void };

// An event's details, read-only (v1 doesn't change events)
export default function EventSheet({ o, calendars, onClose }: Props) {
    const { t } = useTranslation();
    const locale = useDateLocale();
    const start = parseMoment(o.start);
    const end = parseMoment(o.end);
    // All-day ends are exclusive: "20.–21. Nov" for 2026-11-20..2026-11-22
    const when = o.allDay
        ? [start, addDays(end, -1)].map((d) => format(d, 'EEEE d. MMMM', { locale }))
              .filter((text, i, all) => all.indexOf(text) === i).join(' – ')
        : `${format(start, 'EEEE d. MMMM, HH:mm', { locale })} – ${format(end, 'HH:mm')}`;
    return (
        <div className="fixed inset-0 z-20 flex items-end justify-center bg-black/50 sm:items-center" onClick={onClose}>
            <div role="dialog" aria-label={o.title}
                 className="w-full max-w-xl rounded-t-2xl bg-slate-900 p-6 shadow-xl transition-opacity duration-150 sm:rounded-2xl"
                 onClick={(event) => event.stopPropagation()}>
                <h2 className="text-2xl">{o.title}</h2>
                <p className="mt-2 text-lg text-slate-300">{when}</p>
                {o.location && <p className="mt-2 text-lg">{o.location}</p>}
                {o.description && <p className="mt-3 whitespace-pre-line text-base text-slate-300">{o.description}</p>}
                <ul className="mt-4 flex flex-wrap gap-2">
                    {o.calendarIds.map((id) => {
                        const calendar = calendars.get(id);
                        return calendar ? (
                            <li key={id} className="rounded-full px-3 py-1 text-sm text-white" style={{ backgroundColor: calendar.color }}>
                                {calendar.person?.name ?? calendar.name}
                            </li>
                        ) : null;
                    })}
                </ul>
                <button type="button" className="btn-primary mt-6 min-h-12 w-full" onClick={onClose}>{t('calendar.close')}</button>
            </div>
        </div>
    );
}
