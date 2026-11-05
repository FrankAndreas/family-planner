import { useEffect } from 'react';

const ACTIVITY = ['pointerdown', 'touchstart', 'keydown', 'wheel'] as const;

// After `ms` without a touch, call onIdle (the wall goes back to this week's week view)
export function useIdleReturn(ms: number, enabled: boolean, onIdle: () => void) {
    useEffect(() => {
        if (!enabled) return;
        let timer = window.setTimeout(onIdle, ms);
        const reset = () => {
            window.clearTimeout(timer);
            timer = window.setTimeout(onIdle, ms);
        };
        ACTIVITY.forEach((name) => window.addEventListener(name, reset, { passive: true }));
        return () => {
            window.clearTimeout(timer);
            ACTIVITY.forEach((name) => window.removeEventListener(name, reset));
        };
    }, [ms, enabled, onIdle]);
}
