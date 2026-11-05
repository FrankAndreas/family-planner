"""Invented iCalendar texts for the tests (the repository is public: no real calendars)."""

ZURICH_TZ = """BEGIN:VTIMEZONE
TZID:Europe/Zurich
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


def vcal(*events: str, timezones: str = ZURICH_TZ) -> str:
    body = "\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//test//planner//DE", timezones, *events,
                      "END:VCALENDAR"])
    return body.replace("\n", "\r\n") + "\r\n"


def vevent(uid: str, *lines: str, summary: str = "Termin") -> str:
    return "\n".join(["BEGIN:VEVENT", f"UID:{uid}", "DTSTAMP:20261101T000000Z", f"SUMMARY:{summary}", *lines,
                      "END:VEVENT"])


FUSSBALL = vcal(
    vevent("fussball@test", "DTSTART;TZID=Europe/Zurich:20261001T160000", "DTEND;TZID=Europe/Zurich:20261001T173000",
           "RRULE:FREQ=WEEKLY;BYDAY=TH", "EXDATE;TZID=Europe/Zurich:20261112T160000", summary="Fussball"),
    vevent("fussball@test", "RECURRENCE-ID;TZID=Europe/Zurich:20261119T160000",
           "DTSTART;TZID=Europe/Zurich:20261119T173000", "DTEND;TZID=Europe/Zurich:20261119T190000",
           summary="Fussball (später)"),
)
