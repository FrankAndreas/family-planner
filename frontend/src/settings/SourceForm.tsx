import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { errorMessage } from '../api';
import { addSource, changeSource, type NewSource, type Source } from './settingsApi';

type Props = { source?: Source; onSaved: (source: Source) => void; onCancel: () => void };

const field = 'mt-1 block min-h-12 w-full rounded-lg border border-white/10 bg-slate-800 px-3 text-base';

// Adding a source, or giving an existing one a new address or password. The credential is tried before it is saved
export default function SourceForm({ source, onSaved, onCancel }: Props) {
    const { t } = useTranslation();
    const [kind, setKind] = useState<NewSource['kind']>(source?.kind ?? 'google_ical');
    const [name, setName] = useState(source?.name ?? '');
    const [url, setUrl] = useState('');
    const [appleId, setAppleId] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);

    const submit = async (event: FormEvent) => {
        event.preventDefault();
        setBusy(true);
        setError(null);
        try {
            let saved: Source;
            if (source) {
                const change = kind === 'google_ical'
                    ? { name, ...(url ? { url } : {}) }
                    : { name, ...(appleId ? { apple_id: appleId } : {}), ...(password ? { password } : {}) };
                saved = await changeSource(source.id, change);
            } else {
                saved = await addSource(kind === 'google_ical'
                    ? { kind, name, url }
                    : { kind, name, apple_id: appleId, password });
            }
            onSaved(saved);
        } catch (err) {
            setError(errorMessage(err));
        } finally {
            setBusy(false);
        }
    };

    return (
        <form onSubmit={submit} className="glass-card space-y-4 p-5">
            {!source && (
                <fieldset className="flex gap-4">
                    <legend className="mb-2 text-base font-semibold">{t('settings.kind')}</legend>
                    {(['google_ical', 'icloud_caldav'] as const).map((k) => (
                        <label key={k} className="flex min-h-12 items-center gap-2 text-base">
                            <input type="radio" name="kind" checked={kind === k} onChange={() => setKind(k)} className="h-5 w-5" />
                            {t(`settings.kinds.${k}`)}
                        </label>
                    ))}
                </fieldset>
            )}
            <label className="block text-base">
                {t('settings.name')}
                <input className={field} value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} />
            </label>
            {kind === 'google_ical' ? (
                <>
                    <label className="block text-base">
                        {t('settings.googleUrl')}
                        <input className={field} value={url} onChange={(e) => setUrl(e.target.value)} required={!source}
                               type="url" autoComplete="off" spellCheck={false}
                               placeholder={source ? t('settings.stored') : 'https://calendar.google.com/calendar/ical/…/basic.ics'} />
                    </label>
                    <p className="text-sm text-slate-400">{t('settings.googleHelp')}</p>
                </>
            ) : (
                <>
                    <label className="block text-base">
                        {t('settings.appleId')}
                        <input className={field} value={appleId} onChange={(e) => setAppleId(e.target.value)} required={!source}
                               type="email" autoComplete="off" placeholder={source ? t('settings.stored') : undefined} />
                    </label>
                    <label className="block text-base">
                        {t('settings.applePassword')}
                        <input className={field} value={password} onChange={(e) => setPassword(e.target.value)} required={!source}
                               type="password" autoComplete="new-password" placeholder={source ? t('settings.stored') : undefined} />
                    </label>
                    <p className="text-sm text-slate-400">{t('settings.appleHelp')}</p>
                </>
            )}
            {error && <p role="alert" className="text-base text-rose-400">{error}</p>}
            <div className="flex gap-2">
                <button type="submit" className="btn-primary min-h-12" disabled={busy}>
                    {source ? t('settings.save') : t('settings.add')}
                </button>
                <button type="button" className="min-h-12 rounded-lg bg-white/5 px-4" onClick={onCancel}>{t('settings.cancel')}</button>
            </div>
        </form>
    );
}
