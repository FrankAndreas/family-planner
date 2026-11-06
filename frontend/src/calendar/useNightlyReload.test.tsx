import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useNightlyReload } from './useNightlyReload';

// Moves the clock to a local time, letting the minute checks run on the way
const until = (moment: Date) => act(async () => { await vi.advanceTimersByTimeAsync(moment.getTime() - Date.now()); });

describe('useNightlyReload', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it('reloads once after 03:00 the next night', async () => {
        vi.setSystemTime(new Date(2026, 10, 6, 20, 0));
        const reload = vi.fn();
        const probe = vi.fn().mockResolvedValue({});
        renderHook(() => useNightlyReload(true, reload, probe));
        await until(new Date(2026, 10, 7, 3, 1));
        expect(probe).toHaveBeenCalled();
        expect(reload).toHaveBeenCalledTimes(1);
    });

    it('not before 03:00', async () => {
        vi.setSystemTime(new Date(2026, 10, 6, 20, 0));
        const reload = vi.fn();
        renderHook(() => useNightlyReload(true, reload, vi.fn().mockResolvedValue({})));
        await until(new Date(2026, 10, 7, 2, 59));
        expect(reload).not.toHaveBeenCalled();
    });

    it('not on the night it was loaded', async () => {
        vi.setSystemTime(new Date(2026, 10, 7, 3, 30));
        const reload = vi.fn();
        renderHook(() => useNightlyReload(true, reload, vi.fn().mockResolvedValue({})));
        await until(new Date(2026, 10, 7, 4, 0));
        expect(reload).not.toHaveBeenCalled();
    });

    it('waits while the NAS doesn\'t answer', async () => {
        vi.setSystemTime(new Date(2026, 10, 6, 20, 0));
        const reload = vi.fn();
        const probe = vi.fn().mockRejectedValue(new Error('offline'));
        renderHook(() => useNightlyReload(true, reload, probe));
        await until(new Date(2026, 10, 7, 3, 1));
        expect(probe).toHaveBeenCalled();
        expect(reload).not.toHaveBeenCalled();
        probe.mockResolvedValue({});
        await until(new Date(2026, 10, 7, 3, 6));
        expect(reload).toHaveBeenCalledTimes(1);
    });

    it('off when not enabled', async () => {
        vi.setSystemTime(new Date(2026, 10, 6, 20, 0));
        const probe = vi.fn().mockResolvedValue({});
        renderHook(() => useNightlyReload(false, vi.fn(), probe));
        await until(new Date(2026, 10, 7, 3, 30));
        expect(probe).not.toHaveBeenCalled();
    });
});
