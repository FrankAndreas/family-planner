import { format } from 'date-fns';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import type { View } from '../types';
import { isoWeek } from './dates';
import { useDateLocale } from './locale';

const VIEWS: View[] = ['day', '3day', 'week', 'month', 'agenda'];

type Props = {
    view: View;
    day: Date;
    problem: boolean;
    onView: (view: View) => void;
    onStep: (direction: -1 | 1) => void;
    onToday: () => void;
};

const button = 'min-h-12 min-w-12 rounded-lg px-3 text-base font-medium';

export default function TopBar({ view, day, problem, onView, onStep, onToday }: Props) {
    const { t } = useTranslation();
    const locale = useDateLocale();
    return (
        <header className="flex flex-wrap items-center gap-2 border-b border-white/10 px-3 py-2">
            <h1 className="mr-2 text-xl font-bold">
                {format(day, 'LLLL yyyy', { locale })}
                {view !== 'month' && view !== 'agenda' && (
                    <span className="ml-2 text-base font-medium text-slate-400">{t('calendar.week', { n: isoWeek(day) })}</span>
                )}
            </h1>
            <div className="flex items-center gap-1">
                <button type="button" className={`${button} bg-white/5`} aria-label={t('calendar.back')} onClick={() => onStep(-1)}>‹</button>
                <button type="button" className={`${button} bg-white/5`} onClick={onToday}>{t('calendar.today')}</button>
                <button type="button" className={`${button} bg-white/5`} aria-label={t('calendar.forward')} onClick={() => onStep(1)}>›</button>
            </div>
            <div className="flex-1" />
            {problem && (
                <span className="text-xl text-amber-400" role="img" aria-label={t('calendar.problem')} title={t('calendar.problem')}>⚠</span>
            )}
            <nav className="flex gap-1">
                {VIEWS.map((v) => (
                    <button key={v} type="button" onClick={() => onView(v)}
                            className={`${button} ${v === view ? 'bg-indigo-500 text-white' : 'bg-white/5 text-slate-200'}`}>
                        {t(`calendar.views.${v}`)}
                    </button>
                ))}
            </nav>
            <Link to="/settings" className={`${button} flex items-center bg-white/5`} aria-label={t('calendar.settings')}>⚙</Link>
        </header>
    );
}
