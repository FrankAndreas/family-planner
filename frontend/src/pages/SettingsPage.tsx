import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { errorCode, errorMessage, fetchConfig, goToHub, goToHubLogout } from '../api';
import { applyLanguage } from '../i18n';
import SourceForm from '../settings/SourceForm';
import SourceList from '../settings/SourceList';
import ColorInput from '../settings/ColorInput';
import { usePageTitle } from '../pageTitle';
import { getMe, getPeople, getSources, setFamilyColor, type Person, type Source } from '../settings/settingsApi';

type State =
    | { kind: 'loading' }
    | { kind: 'blocked'; code: 'parents_only' | 'no_access' | 'hub_unavailable' | 'other'; message?: string }
    | { kind: 'ready'; sources: Source[]; people: Person[]; familyColor: string };

export default function SettingsPage() {
    const { t } = useTranslation();
    usePageTitle(t('settings.title'));
    const [state, setState] = useState<State>({ kind: 'loading' });
    const [adding, setAdding] = useState(false);
    const [hubUrl, setHubUrl] = useState<string | null>(null);

    const load = useCallback(() => {
        (async () => {
            try {
                const me = await getMe();
                if (!me) return;
                applyLanguage(me.language === 'en' ? 'en' : 'de');
                if (me.role !== 'PARENT') {
                    setState({ kind: 'blocked', code: 'parents_only' });
                    return;
                }
                const [sources, people, config] = await Promise.all([getSources(), getPeople(), fetchConfig()]);
                setState({ kind: 'ready', sources, people, familyColor: config.family_color });
            } catch (err) {
                const code = errorCode(err);
                if (code === 'not_logged_in') {
                    void goToHub();
                    return;
                }
                setState(code === 'parents_only' || code === 'no_access' || code === 'hub_unavailable'
                    ? { kind: 'blocked', code } : { kind: 'blocked', code: 'other', message: errorMessage(err) });
            }
        })();
    }, []);

    useEffect(() => {
        load();
        fetch('/api/hub').then((r) => r.json()).then((links) => setHubUrl(links.login_url)).catch(() => {});
    }, [load]);

    const header = (
        <header className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
            <Link to="/" className="flex min-h-12 items-center rounded-lg bg-white/5 px-3">‹ {t('settings.back')}</Link>
            <h1 className="flex-1 text-xl">{t('settings.title')}</h1>
            {state.kind === 'ready' && (
                <button type="button" className="min-h-12 rounded-lg bg-white/5 px-3" onClick={() => void goToHubLogout()}>
                    {t('settings.logout')}
                </button>
            )}
        </header>
    );

    if (state.kind === 'loading') return <div>{header}</div>;
    if (state.kind === 'blocked') {
        return (
            <div>
                {header}
                <div className="space-y-4 p-6 text-lg">
                    <p>{state.code === 'other' ? state.message : t(`settings.blocked.${state.code}`)}</p>
                    {state.code === 'hub_unavailable' && (
                        <button type="button" className="btn-primary min-h-12" onClick={load}>{t('settings.retry')}</button>
                    )}
                    {(state.code === 'no_access' || state.code === 'parents_only') && (
                        <button type="button" className="min-h-12 rounded-lg bg-white/5 px-4" onClick={() => void goToHubLogout()}>
                            {t('settings.otherLogin')}
                        </button>
                    )}
                </div>
            </div>
        );
    }

    const failing = state.sources.some((s) => s.last_error);
    return (
        <div className="min-h-dvh">
            {header}
            <main className="mx-auto max-w-4xl space-y-6 p-4">
                {failing && (
                    <p role="status" className="rounded-lg border border-amber-500/50 bg-amber-500/10 p-3 text-base text-amber-300">
                        {t('settings.failingBanner')}
                    </p>
                )}
                <section className="space-y-3">
                    <div className="flex items-center">
                        <h2 className="flex-1 text-lg">{t('settings.sources')}</h2>
                        {!adding && <button type="button" className="btn-primary min-h-12" onClick={() => setAdding(true)}>{t('settings.addSource')}</button>}
                    </div>
                    {adding && <SourceForm onCancel={() => setAdding(false)} onSaved={() => { setAdding(false); load(); }} />}
                    <SourceList sources={state.sources} people={state.people} familyColor={state.familyColor} onChanged={load} />
                </section>
                <section className="glass-card flex flex-wrap items-center gap-3 p-4">
                    <label className="flex flex-1 items-center gap-3 text-base">
                        {t('settings.familyColor')}
                        <ColorInput value={state.familyColor} label={t('settings.familyColor')}
                                    onCommit={(color) => { void setFamilyColor(color).then(load); }} />
                    </label>
                    <p className="text-sm text-slate-400">
                        {t('settings.hubNote')}{' '}
                        {hubUrl && <a className="text-indigo-300 underline" href={hubUrl}>{t('settings.toHub')}</a>}
                    </p>
                </section>
            </main>
        </div>
    );
}
