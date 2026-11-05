# Family planner: the family calendar on the wall

Date: 2026-11-05. Starts from the spec "Family Planner App – Specification" (Claude Doc, 2026-11-05) and narrows it after
looking at family-hub and the sibling apps. Points marked **(my call)** were settled by Claude; the rest the user decided.

## Why

The family wants the smart wall calendar it saw in a shop (15.6" touchscreen, Google and iCloud sync, colour per person)
without a vendor cloud or app account. They already run a family of self-hosted apps on a Synology DS720+, with one
family login (family-hub). The calendar becomes one more of those apps.

## What it is, and what it isn't

**The planner is the family calendar and nothing else.** It reads the family's Google and iCloud calendars and shows
them as one calendar, coloured by person, on a wall iPad and on phones.

Everything else from the original spec lives elsewhere, and the hub's start page links the apps together:

| Feature from the spec | Goes to |
| --- | --- |
| Chores, routines, points for kids | family-chore |
| Weekly meal plan, recipes | family-meal-planner |
| Shopping lists | family-meal-planner (its design lists the shopping list as "later"; no issue yet) |
| Clock, weather, photo frame, night mode | family-hub, [family-hub#18](https://github.com/FrankAndreas/family-hub/issues/18) |
| Tasks / to-dos | not planned |

### Goals (v1)

1. A unified, read-only calendar from 2–4 Google and 1–2 iCloud calendars.
2. Each calendar belongs to a family member (their colour) or to "Familie"; each can be shown or hidden.
3. Day, 3-day, week, month and agenda views. All-day, multi-day and recurring events (RRULE, exceptions, moved and
   cancelled occurrences) are shown correctly.
4. The same event in two calendars (an invite) is shown once, with both colours.
5. Viewing needs no login at home. Only the settings need the hub login, as a parent.
6. German first; English as well. Locale-aware dates: Monday-first weeks, 24 h, Europe/Zurich.
7. A change in Google / iCloud shows on the wall within about 10 minutes.

### Non-goals

- Creating, editing or deleting events (later: Google OAuth through a Cloudflare hostname; iCloud by CalDAV PUT/DELETE).
  Nothing in v1 should make that hard: keep each source's own UID and its CalDAV href/etag.
- Access from outside the home network.
- Hiding private events or calendars from viewers without a login. The user: "fine for the home network, no hiding
  needed for now".
- Clock, weather, photo frame, night mode, chores, lists, meals (see the table above).
- Native apps, voice assistants, Home Assistant, Outlook / Exchange.
- French and Italian. The text files are set up for more languages; adding them is a later step **(my call; peers do DE/EN)**.

### Anti-goals (would make it a failure even if it works)

- A calendar credential (a secret iCal URL, an app-specific password) showing up in a log, an API response, the
  frontend or an error message.
- The wall showing a half-updated calendar, or going blank because the NAS or a source is down.
- A slow, janky wall on the old iPad.

## Who uses it, and how

- **The wall iPad**, about 5 years old, entry-level, landscape, saved to the home screen from Safari, Guided Access,
  never locks. Later a Raspberry Pi with a touch screen (1920 × 1080) in Chromium kiosk mode replaces it. Both open the
  same page, `/display`.
- **Phones** on the home Wi-Fi, usually opened from the planner's tile on the hub's start page.
- **A parent** in the settings, from a phone or a laptop.
- Children and guests only look; they never log in here.

## Behaviour

### The wall (`/display`)

The user picked the week view as what the wall shows when nobody touches it (mockup A in the brainstorm).

- **Week view by default:** Monday–Sunday as seven columns; today highlighted; a red line at the current time; all-day
  and multi-day events as bars across the top of their days; timed events as blocks coloured by their person.
- A bar at the top: month and ISO week number ("KW 45"), the view buttons (Tag, 3 Tage, Woche, Monat, Agenda), back / today /
  forward.
- **After 3 minutes untouched** it returns to this week's week view **(my call)**.
- **An event in several calendars** (same iCal UID, same start) shows once, with a stripe of each person's colour.
- **Tap an event:** a sheet with its title, time, place, description (as text) and whose calendars it is in. Read-only.
- **Readable from 2–3 m:** event titles ≥ 18 px, touch targets ≥ 48 px, landscape first (iPad now, 1920 × 1080 later).
- **Light:** few animations, a small DOM per view, nothing heavy to download. Test on the iPad's actual Safari version.
- **Live:** a newly synced change shows without a reload, within a minute of the sync **(my call: push or polling is the
  builder's call)**.
- **Offline:** if the NAS can't be reached, the wall keeps the last loaded week and shows "zuletzt aktualisiert HH:MM".
  The last loaded range is kept in the browser.
- **A failing source** shows a small icon on the wall (no details, no credential); the details are in the settings.
- **Reloads itself once a night** (around 03:00) to pick up new versions.
- **Language:** the wall has no login, so it uses `DEFAULT_LANGUAGE` (de).

### Phones

The same app and address. On a narrow screen it opens on the **agenda** (today and the coming days, grouped by day);
the other views stay available. No login to look.

### Settings (parents only)

Reached from a gear on any view; a parent logs in through the hub. Children who get there see "only parents".

- **Sources:**
  - *Google:* paste a calendar's secret iCal address (`https://calendar.google.com/calendar/ical/…/private-…/basic.ics`),
    give it a name. A short help text says where to find it (Google Calendar web → Settings → the calendar → Integrate
    calendar → Secret address in iCal format) and that it is a password.
  - *iCloud:* Apple ID e-mail + app-specific password (help: account.apple.com → Sign-In and Security → App-Specific
    Passwords). The app discovers the account's calendars (including those shared with that Apple ID) and the parent
    ticks the ones to show. The shard host (`pXX-caldav.icloud.com`) found at discovery is stored.
  - A new source is tried at once; a wrong URL or password says so right away and isn't saved.
  - Change the credential, rename, delete. A credential is never shown again after saving, only "gespeichert".
- **Calendars:** for each, its person (a family member from the hub, or "Familie"), shown or hidden, and an optional
  colour of its own.
- **Colours:** a person's colour is the hub's colour for them **(my call)**; "Familie" has a colour set here. A calendar's
  own colour, if set, wins.
- **Sync status:** per source and calendar, the last successful sync and the last error in plain words ("Adresse
  ungültig oder zurückgesetzt", "Passwort falsch"), and a "jetzt aktualisieren" button. A failing source shows a banner
  at the top of the settings.
- **Log out** sends the browser to the hub's `/logout?next=<the planner>`.

## Calendar sync

- **Google** through the secret iCal address: download every 5 minutes **(my call, spec said 5–10)**; when the
  download's hash is unchanged, nothing else happens.
- **iCloud** through CalDAV, read-only: every 5 minutes check each calendar's ctag (or sync token); fetch events only
  when it changed.
- **The sources are the truth.** The app keeps a cache in SQLite for fast rendering.
- **One import = one transaction:** each import replaces one calendar's events at once, so no view sees a half-updated
  calendar.
- **Recurring events** are stored as the master + its RRULE/RDATE/EXDATE + its overridden occurrences
  (RECURRENCE-ID), and expanded for the visible range when asked.
- **Time zones:** keep the original TZID; show in Europe/Zurich. All-day events stay dates, not midnight UTC.
- **Range:** only events from 3 months back to 13 months ahead are kept and shown **(my call)**.
- **A failing source** keeps its last good events and its error; other sources keep syncing. After a failure retry on
  the normal schedule; no tight loops.
- **Freshness caveat:** Google may serve the feed with a delay. M1 includes testing how long a change takes to appear.
- **Expected volume:** 3–6 calendars, a few hundred events each, maybe a few years of recurrence history.

## Login and people (family-hub)

Follows family-hub's "For apps" section and the sibling apps' hub login (e.g. family-meal-planner,
`docs/superpowers/specs/2026-10-30-hub-login-design.md`); copy their `hub.py` / `hub_people.py` patterns.

- **App key in the hub:** `planner` **(my call)**, with every family member ticked (`HUB_APP_KEY`).
- **Viewing** (all calendar and status reads) needs no login, for requests from home.
- **From outside:** any request carrying `Cf-Connecting-Ip` gets 403. There is no tunnel route for the planner, so this is
  defence in depth.
- **Settings and every change** need a hub login with access to `planner` and role `parent`:
  - The token is the `hub_session` cookie (or `Authorization: Bearer` for tests and scripts).
  - The backend asks `GET <HUB_URL>/api/session?app=planner`, caching a valid answer and "no valid login" for 60 s
    (at most 1000 tokens, by SHA-256); "no access" is never cached.
  - A change through the cookie needs `X-Requested-With: planner`.
  - Errors carry a JSON `code`: 401 `not_logged_in`, 403 `no_access`, 403 `parents_only`, 503 `hub_unavailable`, 403
    `csrf`.
  - On 401 the frontend sends the browser to `<HUB_PUBLIC_URL>/?next=<current address>`.
- **People:** the list comes from `GET <HUB_URL>/api/apps/planner/people`. The display has no login, so the list is
  refreshed with the token of a parent using the settings, at most once a minute, and kept in SQLite (`hub_id`, name,
  role, colour, active). Someone the hub no longer lists is hidden: their calendars fall back to "Familie" until a parent
  maps them again.
- **The hub cookie only reaches `*.local.<domain>`,** so the planner must be served at
  `https://<name>.local.<domain>` (e.g. `kalender.local.<domain>`) through the DSM reverse proxy with a certificate,
  like the other apps. This replaces the spec's plain `http://<NAS-IP>:8090`. The hub's tile for the planner links there.
- No tokens or cookies in logs.

## Tech stack (my call: same as the sibling apps)

The spec left TypeScript or Python open until the hub repos were seen. Every sibling app (family-hub, family-chore,
family-meal-planner, family-budget-dashboard, family-job-tracking) uses the stack below, so the planner does too.

| Part | Choice |
| --- | --- |
| Backend | Python 3.14, FastAPI, uvicorn, SQLAlchemy 2, Alembic, pydantic; pinned like family-hub's `requirements.txt` |
| Calendar parsing | `icalendar` + `recurring-ical-events` for expansion; `caldav` (or plain `httpx` + `icalendar`) for iCloud: builder's call |
| Secrets at rest | `cryptography` AES-256-GCM, key from a Docker secret file |
| Database | SQLite, WAL mode, one file in `./data` |
| Scheduling | in-process (a background task or APScheduler like family-chore): builder's call |
| Frontend | React 19, Vite, TypeScript, Tailwind 4, i18next / react-i18next, react-router, axios, date-fns |
| Tests | pytest with a fake hub and fake Google / CalDAV servers; Vitest; Playwright e2e at iPad landscape and phone size |
| Images | backend + nginx frontend, `ghcr.io/frankandreas/family-planner/{backend,frontend}`, linux/amd64 |

Layout follows the siblings: `backend/app/…`, `backend/app/migrations/`, `frontend/`, `tests/`, `e2e/`, `scripts/`,
`docker-compose.yml`, `README.md`, `README_DOCKER.md`, MIT licence. The repository is meant to be public, like the
others: tests and docs use invented people and placeholders (`<domain>`, `<NAS_IP>`), never a real iCal URL.

## Data (outline; the builder shapes it)

- `person`: hub_id, name, role, colour, active (a copy of the hub's list).
- `source`: kind (`google_ical` / `icloud_caldav`), name, encrypted credential (URL, or Apple ID + app password),
  discovered CalDAV base URL, last success, last error.
- `calendar`: source, remote id / href, name, ctag or content hash, person (or Familie), own colour, visible.
- `event`: calendar, UID, RECURRENCE-ID, start/end with TZID or date, all-day flag, RRULE/RDATE/EXDATE, status, title,
  location, description, CalDAV href + etag, content hash.
- `setting`: Familie colour and the like.

## API (outline)

- `GET /api/events?from=&to=`: expanded occurrences in the range, merged across calendars (one entry per shared event,
  listing its calendars), visible calendars only. No login.
- `GET /api/calendars`: names, colours, persons, sync state without errors' details. No login.
- `GET /api/config`: default language, the hub's login URL.
- Settings, parents only: CRUD for sources (credential write-only), `POST /api/sources/{id}/sync`, calendar mapping and
  visibility, iCloud discovery.
- `GET /health` for the container health check.

## Security and operations

- **Credentials** (iCal URLs, Apple ID + app password) encrypted with AES-256-GCM using `enc_key` from a Docker secret;
  never logged, never returned by the API, never in exception text (scrub URLs from HTTP library errors). The key is 32
  random bytes, base64, in `./secrets/enc_key`, mounted as the Docker secret `/run/secrets/enc_key` **(my call)**; without
  it the backend refuses to start.
- Keep a copy of `enc_key` outside the NAS (password manager): without it the stored credentials can't be read after a
  restore. README_DOCKER.md says so.
- Containers run as non-root (PUID/PGID like the siblings), no Docker socket, `restart: unless-stopped`, memory limits
  (backend 256 MB, target < 150 MB idle).
- **Backups:** a nightly SQLite backup (`VACUUM INTO`) to `./data/backups`, keep 14; an automatic one before migrations
  run at start. Hyper Backup covers the app folder.
- **Restore:** compose file + `enc_key` + data folder.
- JSON logs to stdout (seen in Container Manager), no telemetry.
- **Port:** `${PORT:-8090}` on the NAS, behind the DSM reverse proxy (siblings use 8081–8086).

## Performance

- The month view with 3–6 calendars renders in under 1 s on the wall iPad.
- API p95 under 200 ms on the LAN.

## Roadmap

1. **M1, read-only calendar:** the containers on the NAS, Google iCal and iCloud CalDAV import, encrypted credentials,
   the week view on the wall plus day / 3-day / month / agenda, settings behind the hub login, calendar-to-person
   mapping. Measure how fast a Google change appears.
2. **M2, wall polish:** shared events once with both colours, offline "zuletzt aktualisiert", live updates, the failing
   source icon, nightly reload, the phone agenda.
3. **Later:** creating and editing events; French and Italian; showing the next events on the hub's wall view if
   family-hub#18 wants them (`GET /api/events` already serves it).

## Left to the builder

- Push (WebSocket / SSE) or polling for live updates; the iCloud client library; the scheduler.
- Exact layout details within the rules above: event overlap layout, how many all-day rows before "+2", colours of the
  "today" highlight.
- The test fixtures' ICS and CalDAV samples, which must cover the recurrence cases in goal 3.
