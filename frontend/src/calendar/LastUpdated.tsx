import { differenceInCalendarDays, format, isToday } from 'date-fns';
import { useTranslation } from 'react-i18next';
import { useDateLocale } from './locale';

// How old the shown events are while the NAS can't be reached: "zuletzt aktualisiert 13:05", another day of the last
// week "Do 22:10", older "29. Okt. 22:10". `short` ("Stand 13:05") fits the phone's top bar.
export default function LastUpdated({ at, short = false }: { at: Date | null; short?: boolean }) {
    const { t, i18n } = useTranslation();
    const locale = useDateLocale();
    if (!at) return null;
    const pattern = isToday(at) ? 'HH:mm'
        : differenceInCalendarDays(new Date(), at) < 7 ? 'EEEEEE HH:mm'
        : i18n.language === 'en' ? 'd MMM HH:mm' : 'd. MMM HH:mm';
    const time = format(at, pattern, { locale });
    return (
        <span className="text-sm text-amber-300">
            {t(short ? 'calendar.lastUpdatedShort' : 'calendar.lastUpdated', { time })}
        </span>
    );
}
