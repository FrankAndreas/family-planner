import type { CalendarInfo, Occurrence } from '../types';

type Props = { from: Date; occurrences: Occurrence[]; calendars: Map<number, CalendarInfo>; onOpen: (o: Occurrence) => void };

export default function Agenda(props: Props) {
    void props;
    return null;
}
