import { useEffect } from 'react';
import { startOfDay } from 'date-fns';
import { fetchConfig } from '../api';

export const RELOAD_HOUR = 3;
export const CHECK_MS = 60_000;

const reloadPage = () => window.location.reload();

// The wall reloads itself once a night, around 03:00, to pick up a new version (spec "The wall"). Only once the NAS
// answers: a reload while it is off would leave Safari's error page instead of the last loaded week.
export function useNightlyReload(enabled: boolean, reload: () => void = reloadPage,
                                 probe: () => Promise<unknown> = fetchConfig) {
    useEffect(() => {
        if (!enabled) return;
        const loadedDay = startOfDay(new Date()).getTime();
        let trying = false;
        let done = false;
        const check = () => {
            const now = new Date();
            if (done || trying || startOfDay(now).getTime() <= loadedDay || now.getHours() < RELOAD_HOUR) return;
            trying = true;
            probe().then(() => { done = true; reload(); }, () => {}).finally(() => { trying = false; });
        };
        const timer = window.setInterval(check, CHECK_MS);
        return () => window.clearInterval(timer);
    }, [enabled, reload, probe]);
}
