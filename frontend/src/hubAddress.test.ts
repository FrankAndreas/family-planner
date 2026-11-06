import { describe, expect, it } from 'vitest';
import { loginAddress } from './hubAddress';

const home = { login_url: 'https://home.local.example.ch', logout_url: 'https://home.local.example.ch/logout' };
const outside = { login_url: 'https://home.local.example.ch', logout_url: '/cdn-cgi/access/logout' };

describe('loginAddress', () => {
    it('at home the hub\'s login, back here afterwards', () => {
        expect(loginAddress(home, 'https://kalender.local.example.ch/plan'))
            .toBe('https://home.local.example.ch/?next=https%3A%2F%2Fkalender.local.example.ch%2Fplan');
        expect(loginAddress(home, null)).toBe('https://home.local.example.ch');
    });
    it('outside none: the hub\'s home address is out of reach, Cloudflare Access is the login there', () => {
        expect(loginAddress(outside, 'https://kalender.example.ch/')).toBeNull();
    });
});
