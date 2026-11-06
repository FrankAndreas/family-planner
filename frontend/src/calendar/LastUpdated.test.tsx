import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '../i18n';
import LastUpdated from './LastUpdated';

describe('LastUpdated', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date(2026, 10, 6, 14, 30));
    });
    afterEach(() => vi.useRealTimers());

    it('today shows the time', () => {
        render(<LastUpdated at={new Date(2026, 10, 6, 13, 5)} />);
        expect(screen.getByText('zuletzt aktualisiert 13:05')).toBeInTheDocument();
    });

    it('another day shows the weekday too', () => {
        render(<LastUpdated at={new Date(2026, 10, 5, 22, 10)} />);
        expect(screen.getByText('zuletzt aktualisiert Do 22:10')).toBeInTheDocument();
    });

    it('nothing loaded yet shows nothing', () => {
        const { container } = render(<LastUpdated at={null} />);
        expect(container).toBeEmptyDOMElement();
    });
});
