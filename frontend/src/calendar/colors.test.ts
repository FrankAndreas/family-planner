import { describe, expect, it } from 'vitest';
import { textOn } from './colors';

describe('textOn', () => {
    it('picks the easier to read of black and white', () => {
        expect(textOn('#1e3a8a')).toBe('#ffffff');
        expect(textOn('#dc2626')).toBe('#ffffff');
        expect(textOn('#facc15')).toBe('#000000');
        expect(textOn('#a3e635')).toBe('#000000');
    });
    it('falls back to white for anything that is not #rrggbb', () => {
        expect(textOn('red')).toBe('#ffffff');
    });
});
