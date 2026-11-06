import { useEffect, useRef, useState } from 'react';

export const COMMIT_MS = 500;

type Props = { value: string; disabled?: boolean; label: string; onCommit: (color: string) => void };

// A colour picker that saves once: dragging through the picker fires a change on every step, so the colour shows at
// once and is saved COMMIT_MS after the last step (or when the picker goes away).
export default function ColorInput({ value, disabled, label, onCommit }: Props) {
    const [shown, setShown] = useState(value);
    const [outside, setOutside] = useState(value);
    if (value !== outside) {
        // A new value from the server (after saving, or another parent's change)
        setOutside(value);
        setShown(value);
    }
    const timer = useRef<number | undefined>(undefined);
    const pending = useRef<string | null>(null);
    const commit = useRef(onCommit);
    useEffect(() => {
        commit.current = onCommit;
    }, [onCommit]);

    const flush = () => {
        window.clearTimeout(timer.current);
        if (pending.current !== null) {
            const color = pending.current;
            pending.current = null;
            commit.current(color);
        }
    };
    useEffect(() => flush, []);

    return (
        <input type="color" className="h-12 w-12 rounded" aria-label={label} value={shown} disabled={disabled}
               onChange={(e) => {
                   setShown(e.target.value);
                   pending.current = e.target.value;
                   window.clearTimeout(timer.current);
                   timer.current = window.setTimeout(flush, COMMIT_MS);
               }} />
    );
}
