import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AxiosError, AxiosHeaders } from 'axios';
import '../i18n';
import SourceForm from './SourceForm';
import * as settingsApi from './settingsApi';

const rejected = (code: string) => {
    const config = { headers: new AxiosHeaders() };
    return new AxiosError('failed', 'ERR_BAD_REQUEST', config, null,
        { status: 422, statusText: '', headers: {}, config, data: { detail: code } });
};

describe('SourceForm', () => {
    it('a wrong app-specific password shows "Passwort falsch" and keeps the form', async () => {
        const add = vi.spyOn(settingsApi, 'addSource').mockRejectedValue(rejected('source_auth'));
        const saved = vi.fn();
        render(<SourceForm onSaved={saved} onCancel={() => {}} />);
        fireEvent.click(screen.getByLabelText('iCloud'));
        fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'iCloud Familie' } });
        fireEvent.change(screen.getByLabelText('Apple-ID (E-Mail)'), { target: { value: 'familie@example.com' } });
        fireEvent.change(screen.getByLabelText('App-spezifisches Passwort'), { target: { value: 'falsch' } });
        fireEvent.click(screen.getByRole('button', { name: 'Hinzufügen' }));
        await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Passwort falsch'));
        expect(add).toHaveBeenCalledWith({ kind: 'icloud_caldav', name: 'iCloud Familie', apple_id: 'familie@example.com',
            password: 'falsch' });
        expect(saved).not.toHaveBeenCalled();
        expect(screen.getByLabelText('Apple-ID (E-Mail)')).toHaveValue('familie@example.com');
    });

    it('a Google address goes in as url and calls onSaved', async () => {
        const source = { id: 1, kind: 'google_ical', name: 'Mama', has_credential: true, last_success_at: null,
            last_error: null, calendars: [] } as settingsApi.Source;
        vi.spyOn(settingsApi, 'addSource').mockResolvedValue(source);
        const saved = vi.fn();
        render(<SourceForm onSaved={saved} onCancel={() => {}} />);
        fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Mama' } });
        fireEvent.change(screen.getByLabelText('Geheime Adresse im iCal-Format'), { target: { value: 'https://calendar.google.com/x.ics' } });
        fireEvent.click(screen.getByRole('button', { name: 'Hinzufügen' }));
        await waitFor(() => expect(saved).toHaveBeenCalledWith(source));
    });
});
