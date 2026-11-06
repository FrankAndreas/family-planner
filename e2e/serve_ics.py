"""A calendar feed for the browser tests, served on port 8140 like a Google secret address.

Its events are around today, so the wall's week view shows them whenever the tests run. Invented events only."""

import http.server
import sys
from datetime import date, timedelta
from pathlib import Path

folder = Path(sys.argv[1])
folder.mkdir(parents=True, exist_ok=True)
today = date.today()
tomorrow = today + timedelta(days=1)
day = lambda d: d.strftime("%Y%m%d")  # noqa: E731
events = [
    ("zahnarzt@e2e", f"DTSTART;TZID=Europe/Zurich:{day(today)}T100000", f"DTEND;TZID=Europe/Zurich:{day(today)}T110000", "Zahnarzt"),
    ("pizza@e2e", f"DTSTART;TZID=Europe/Zurich:{day(tomorrow)}T180000", f"DTEND;TZID=Europe/Zurich:{day(tomorrow)}T200000", "Pizza bei Omi"),
    ("ferien@e2e", f"DTSTART;VALUE=DATE:{day(today)}", f"DTEND;VALUE=DATE:{day(today + timedelta(days=2))}", "Herbstlager"),
]
lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//e2e//planner//DE"]
for uid, start, end, summary in events:
    lines += ["BEGIN:VEVENT", f"UID:{uid}", "DTSTAMP:20261101T000000Z", start, end, f"SUMMARY:{summary}", "END:VEVENT"]
lines.append("END:VCALENDAR")
(folder / "family.ics").write_text("\r\n".join(lines) + "\r\n")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(folder), **kwargs)

    def log_message(self, *args):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", 8140), Handler).serve_forever()
