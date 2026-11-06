import { format } from 'date-fns';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import type { View } from '../types';
import { isoWeek } from './dates';
import { useDateLocale } from './locale';
import LastUpdated from './LastUpdated';

const VIEWS: View[] = ['day', '3day', 'week', 'month', 'agenda'];

type Props = {
    view: View;
    day: Date;
    problem: boolean;
    // When the events were loaded, shown while the NAS can't be reached
    lastUpdated: Date | null;
    onView: (view: View) => void;
    onStep: (direction: -1 | 1) => void;
    onToday: () => void;
};

const button = 'min-h-12 min-w-12 rounded-lg px-3 text-base font-medium';

// Below 768 px (phones) the bar takes two rows: ‹ month › … ⚠ ⚙, then Heute and the views with short labels.
// Offline, a short stamp ("Stand 13:05") takes the place of ⚠, so it stays two rows.
// The arrows' group dissolves (max-md:contents) so its buttons can take their places through `order`.
export default function TopBar({ view, day, problem, lastUpdated, onView, onStep, onToday }: Props) {
    const { t } = useTranslation();
    const locale = useDateLocale();
    return (
        <header className="flex flex-wrap items-center gap-2 border-b border-white/10 px-3 py-2 max-md:gap-1">
            <h1 className="mr-2 text-xl font-bold max-md:order-2 max-md:mx-1">
                <span className="max-md:hidden">{format(day, 'LLLL yyyy', { locale })}</span>
                <span className="md:hidden">{format(day, 'LLL yyyy', { locale })}</span>
                {view !== 'month' && view !== 'agenda' && (
                    <span className="ml-2 text-base font-medium text-slate-400 max-md:hidden">{t('calendar.week', { n: isoWeek(day) })}</span>
                )}
            </h1>
            <div className="flex items-center gap-1 max-md:contents">
                <button type="button" className={`${button} bg-white/5 max-md:order-1`} aria-label={t('calendar.back')} onClick={() => onStep(-1)}>‹</button>
                <button type="button" className={`${button} bg-white/5 max-md:order-9`} onClick={onToday}>{t('calendar.today')}</button>
                <button type="button" className={`${button} bg-white/5 max-md:order-3`} aria-label={t('calendar.forward')} onClick={() => onStep(1)}>›</button>
            </div>
            <div className="flex-1 max-md:order-4" />
            <span className="max-md:hidden"><LastUpdated at={lastUpdated} /></span>
            <span className="max-md:order-5 md:hidden"><LastUpdated at={lastUpdated} short /></span>
            {problem && (
                <span className={`text-xl text-amber-400 max-md:order-6 ${lastUpdated ? 'max-md:hidden' : ''}`} role="img" aria-label={t('calendar.problem')} title={t('calendar.problem')}>⚠</span>
            )}
            <div className="h-0 basis-full max-md:order-8 md:hidden" />
            <nav className="flex gap-1 max-md:order-10">
                {VIEWS.map((v) => (
                    <button key={v} type="button" onClick={() => onView(v)} aria-label={t(`calendar.views.${v}`)}
                            className={`${button} max-md:px-2 ${v === view ? 'bg-indigo-500 text-white' : 'bg-white/5 text-slate-200'}`}>
                        <span className="md:hidden">{t(`calendar.viewsShort.${v}`)}</span>
                        <span className="max-md:hidden">{t(`calendar.views.${v}`)}</span>
                    </button>
                ))}
            </nav>
            <Link to="/settings" className={`${button} flex items-center bg-white/5 max-md:order-7`} aria-label={t('calendar.settings')}>⚙</Link>
        </header>
    );
}
