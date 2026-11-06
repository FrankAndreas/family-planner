import { format, isToday } from 'date-fns';
import { useTranslation } from 'react-i18next';
import { useDateLocale } from './locale';

// "zuletzt aktualisiert 13:05" (another day: "Do 22:10"): how old the shown events are while the NAS can't be reached
export default function LastUpdated({ at }: { at: Date | null }) {
    const { t } = useTranslation();
    const locale = useDateLocale();
    if (!at) return null;
    const time = format(at, isToday(at) ? 'HH:mm' : 'EEEEEE HH:mm', { locale });
    return <span className="text-sm text-amber-300">{t('calendar.lastUpdated', { time })}</span>;
}
