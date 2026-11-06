import { useState } from 'react';
import { format } from 'date-fns';
import { useTranslation } from 'react-i18next';
import i18n from '../i18n';
import { errorMessage } from '../api';
import CalendarRow from './CalendarRow';
import SourceForm from './SourceForm';
import { changeCalendar, deleteSource, syncSource, type Person, type Source } from './settingsApi';

type Props = { sources: Source[]; people: Person[]; familyColor: string; onChanged: () => void };

// The backend's error codes in words (errors.source_* in the locales)
const sourceError = (code: string) =>
    i18n.exists(`errors.${code}`) ? i18n.t(`errors.${code}` as 'errors.generic') : i18n.t('errors.generic');

export default function SourceList({ sources, people, familyColor, onChanged }: Props) {
    const { t } = useTranslation();
    const [editing, setEditing] = useState<number | null>(null);
    const [busy, setBusy] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);

    const run = async (id: number, action: () => Promise<unknown>) => {
        setBusy(id);
        setError(null);
        try {
            await action();
            onChanged();
        } catch (err) {
            setError(errorMessage(err));
        } finally {
            setBusy(null);
        }
    };

    if (!sources.length) return <p className="text-base text-slate-400">{t('settings.noSources')}</p>;
    return (
        <div className="space-y-4">
            {error && <p role="alert" className="text-base text-rose-400">{error}</p>}
            {sources.map((source) => (
                <section key={source.id} className="glass-card p-4">
                    {editing === source.id ? (
                        <SourceForm source={source} onCancel={() => setEditing(null)}
                                    onSaved={() => { setEditing(null); onChanged(); }} />
                    ) : (
                        <>
                            <div className="flex flex-wrap items-center gap-2">
                                <h3 className="flex-1 text-lg">
                                    {source.name}
                                    <span className="ml-2 text-sm font-normal text-slate-400">{t(`settings.kinds.${source.kind}`)}</span>
                                </h3>
                                <button type="button" className="min-h-12 rounded-lg bg-white/5 px-3" disabled={busy === source.id}
                                        onClick={() => run(source.id, () => syncSource(source.id))}>{t('settings.syncNow')}</button>
                                <button type="button" className="min-h-12 rounded-lg bg-white/5 px-3"
                                        onClick={() => setEditing(source.id)}>{t('settings.edit')}</button>
                                <button type="button" className="min-h-12 rounded-lg bg-white/5 px-3 text-rose-300"
                                        onClick={() => { if (window.confirm(t('settings.confirmDelete', { name: source.name }))) void run(source.id, () => deleteSource(source.id)); }}>
                                    {t('settings.delete')}
                                </button>
                            </div>
                            <p className="mt-1 text-sm text-slate-400">
                                {t('settings.credentialStored')}
                                {' · '}
                                {source.last_success_at
                                    ? t('settings.lastSync', { time: format(new Date(`${source.last_success_at}Z`), 'dd.MM.yyyy HH:mm') })
                                    : t('settings.neverSynced')}
                            </p>
                            {source.last_error && <p className="mt-1 text-base text-amber-400">{sourceError(source.last_error)}</p>}
                            {source.kind === 'icloud_caldav' && <p className="mt-2 text-sm text-slate-400">{t('settings.pickCalendars')}</p>}
                            <ul className="mt-2">
                                {source.calendars.map((calendar) => (
                                    <CalendarRow key={calendar.id} calendar={calendar} people={people} familyColor={familyColor}
                                                 canEnable={source.kind === 'icloud_caldav'}
                                                 onChange={(change) => run(source.id, () => changeCalendar(calendar.id, change))} />
                                ))}
                            </ul>
                        </>
                    )}
                </section>
            ))}
        </div>
    );
}
