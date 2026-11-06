import type { CalendarInfo, Occurrence } from '../types';

// The colours of an event: one per calendar it is in (an invite in two calendars shows both)
export function colorsOf(o: Occurrence, calendars: Map<number, CalendarInfo>): string[] {
    const colors = o.calendarIds.map((id) => calendars.get(id)?.color).filter((c): c is string => !!c);
    return colors.length ? colors : ['#64748b'];
}

// A soft fill in the first colour, readable on the dark background
export const fill = (color: string) => `${color}33`;
