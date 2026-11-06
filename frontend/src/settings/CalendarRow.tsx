import { useTranslation } from 'react-i18next';
import type { Person, SourceCalendar } from './settingsApi';

type Props = {
    calendar: SourceCalendar;
    people: Person[];
    familyColor: string;
    canEnable: boolean;
    onChange: (change: Partial<Pick<SourceCalendar, 'person_id' | 'color' | 'visible' | 'enabled'>>) => void;
};

// One calendar: shown at all (iCloud), whose it is, its colour, shown or hidden
export default function CalendarRow({ calendar, people, familyColor, canEnable, onChange }: Props) {
    const { t } = useTranslation();
    const person = people.find((p) => p.id === calendar.person_id);
    const color = calendar.color ?? person?.color ?? familyColor;
    return (
        <li className="flex flex-wrap items-center gap-3 border-t border-white/5 py-2">
            {canEnable && (
                <label className="flex min-h-12 items-center gap-2">
                    <input type="checkbox" className="h-5 w-5" checked={calendar.enabled}
                           onChange={(e) => onChange({ enabled: e.target.checked })} />
                    <span className="sr-only">{t('settings.enabled')}</span>
                </label>
            )}
            <span className="min-w-32 flex-1 text-base">{calendar.name}</span>
            <label className="text-sm text-slate-400">
                {t('settings.whose')}
                <select className="ml-2 min-h-12 rounded-lg border border-white/10 bg-slate-800 px-2 text-base text-slate-100"
                        value={calendar.person_id ?? ''} disabled={!calendar.enabled}
                        onChange={(e) => onChange({ person_id: e.target.value ? Number(e.target.value) : null })}>
                    <option value="">{t('settings.family')}</option>
                    {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-400">
                {t('settings.color')}
                <input type="color" className="h-12 w-12 rounded" value={color} disabled={!calendar.enabled}
                       onChange={(e) => onChange({ color: e.target.value })} />
            </label>
            {calendar.color && (
                <button type="button" className="min-h-12 rounded-lg bg-white/5 px-3 text-sm" onClick={() => onChange({ color: null })}>
                    {t('settings.colorReset')}
                </button>
            )}
            <label className="flex min-h-12 items-center gap-2 text-base">
                <input type="checkbox" className="h-5 w-5" checked={calendar.visible} disabled={!calendar.enabled}
                       onChange={(e) => onChange({ visible: e.target.checked })} />
                {t('settings.visible')}
            </label>
        </li>
    );
}
