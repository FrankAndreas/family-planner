import type { CalendarInfo, Occurrence } from '../types';

type Props = { day: Date; occurrences: Occurrence[]; calendars: Map<number, CalendarInfo>; onOpenDay: (day: Date) => void };

export default function MonthGrid(props: Props) {
    void props;
    return null;
}
