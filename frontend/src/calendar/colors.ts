import type { CalendarInfo, Occurrence } from '../types';

// The colours of an event: one per calendar it is in (an invite in two calendars shows both)
export function colorsOf(o: Occurrence, calendars: Map<number, CalendarInfo>): string[] {
    const colors = o.calendarIds.map((id) => calendars.get(id)?.color).filter((c): c is string => !!c);
    return colors.length ? colors : ['#64748b'];
}

// A soft fill in the first colour, readable on the dark background
export const fill = (color: string) => `${color}33`;

// Black or white, whichever is easier to read on the colour: a parent picks any colour for a calendar, and white on a
// light one (yellow, light green) was hard to read (accessibility review 2026-11-08)
export function textOn(color: string): string {
    const hex = /^#([0-9a-f]{6})$/i.exec(color)?.[1];
    if (!hex) return '#ffffff';
    const channel = (i: number) => {
        const c = parseInt(hex.slice(i, i + 2), 16) / 255;
        return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    };
    const luminance = 0.2126 * channel(0) + 0.7152 * channel(2) + 0.0722 * channel(4);
    // The contrast with white against the one with black
    return 1.05 / (luminance + 0.05) >= (luminance + 0.05) / 0.05 ? '#ffffff' : '#000000';
}
