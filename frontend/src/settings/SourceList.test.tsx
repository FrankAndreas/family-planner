import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import '../i18n';
import SourceList from './SourceList';
import type { Source } from './settingsApi';

const source = (lastSuccessAt: string): Source => ({
    id: 1, kind: 'google_ical', name: 'Mama', has_credential: true, last_success_at: lastSuccessAt, last_error: null,
    calendars: [],
});

describe('SourceList', () => {
    it('shows the last sync in local time (the API sends UTC with its offset)', () => {
        render(<SourceList sources={[source('2026-11-06T05:55:35+00:00')]} people={[]} familyColor="#7c3aed" onChanged={() => {}} />);
        expect(screen.getByText(/zuletzt aktualisiert 06\.11\.2026 06:55/)).toBeInTheDocument();
    });
});
