import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import ColorInput, { COMMIT_MS } from './ColorInput';

describe('ColorInput', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it('dragging through colours saves only the last one', () => {
        const commit = vi.fn();
        render(<ColorInput value="#000000" label="Farbe" onCommit={commit} />);
        for (const color of ['#111111', '#222222', '#333333']) {
            fireEvent.change(screen.getByLabelText('Farbe'), { target: { value: color } });
            act(() => { vi.advanceTimersByTime(100); });
        }
        expect(commit).not.toHaveBeenCalled();
        act(() => { vi.advanceTimersByTime(COMMIT_MS); });
        expect(commit).toHaveBeenCalledTimes(1);
        expect(commit).toHaveBeenCalledWith('#333333');
    });

    it('shows the new colour at once', () => {
        render(<ColorInput value="#000000" label="Farbe" onCommit={() => {}} />);
        fireEvent.change(screen.getByLabelText('Farbe'), { target: { value: '#111111' } });
        expect(screen.getByLabelText('Farbe')).toHaveValue('#111111');
    });

    it('follows a new value from outside', () => {
        const { rerender } = render(<ColorInput value="#000000" label="Farbe" onCommit={() => {}} />);
        rerender(<ColorInput value="#444444" label="Farbe" onCommit={() => {}} />);
        expect(screen.getByLabelText('Farbe')).toHaveValue('#444444');
    });

    it('a change still pending when the row goes away is saved', () => {
        const commit = vi.fn();
        const { unmount } = render(<ColorInput value="#000000" label="Farbe" onCommit={commit} />);
        fireEvent.change(screen.getByLabelText('Farbe'), { target: { value: '#555555' } });
        unmount();
        expect(commit).toHaveBeenCalledWith('#555555');
    });
});
