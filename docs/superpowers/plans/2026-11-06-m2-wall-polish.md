# M2 Wall Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The wall keeps working when the NAS can't be reached and picks up new versions by itself, and the minors
deferred from the M1 review are fixed.

**Architecture:** No new services. The frontend keeps the last successful load in `localStorage` and shows
"zuletzt aktualisiert HH:MM" while the API can't be reached. The wall reloads itself once a night, but only after
checking that the NAS answers. Backend fixes stay in the modules that own the behaviour. No schema change: the
timestamp fix is a SQLAlchemy type that reads and writes the same column.

**Tech Stack:** As in M1: Python 3.14, FastAPI, SQLAlchemy 2, httpx, icalendar, recurring-ical-events; React 19,
TypeScript, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-05-family-planner-design.md` (sections "The wall", "Phones", "Calendar sync",
"Security and operations"; roadmap item M2).

## What M1 already delivered from the M2 roadmap line

Checked against the code on `main` (123b4dd); these need no task:

- **Shared events once with both colours:** `occurrences.between` merges by UID + start, and `Stripes` draws one
  stripe per calendar.
- **Live updates:** `useCalendarData` reloads every 60 s (`REFRESH_MS`), within a minute of a sync as the spec asks.
- **Failing-source icon:** `TopBar` shows ⚠ when a calendar's source has an error or the API can't be reached.
- **Phone agenda:** below 768 px the page opens on the agenda.

## Global Constraints

- Read-only, calendar only, no login to view from home; everything in M1's Global Constraints still holds.
- Wall: back to this week's week view after 180 s untouched; event titles ≥ 18 px; touch targets ≥ 48 px.
- Offline: "the wall keeps the last loaded week and shows 'zuletzt aktualisiert HH:MM'. The last loaded range is kept
  in the browser."
- Nightly reload "around 03:00", on the wall (`/display`) only.
- Browser storage: every `localStorage` read and write in try/catch; the page works without it.
- Error codes stay codes (`source_invalid` and so on); no URL or password in a log, error or response.
- Texts in `locales/de.ts` and `locales/en.ts`; `npm run check-texts` stays green.
- Invented people and placeholders only (public repo).

## Review Focus

1. **The API fails on the very first load** (the nightly reload while the NAS reboots): the wall must show the cached
   week, not an empty grid. Pinned in Task 4.
2. **Cached data from another range** (cache holds last week, the wall now asks for this week): it must not show last
   week's events in this week's columns. Pinned in Task 4.
3. **`localStorage` throws or holds garbage** (private mode, an older format): the page loads normally. Pinned in Task 4.
4. **The nightly reload while the NAS is down:** no reload into Safari's error page; it tries again later. Pinned in
   Task 5.
5. **A manual "Jetzt aktualisieren" while the scheduler syncs the same source:** no false `source_invalid`.
   Pinned in Task 2.

---

## File structure

```
backend/app/
  ics.py              # Task 1: BOM, first_start of unbounded series with earlier overrides / RDATEs
  google.py           # Task 1: httpx.InvalidURL
  caldav.py           # Task 1: httpx.InvalidURL
  settings_api.py     # Task 1: SourcePatch limits
  importer.py         # Task 2: one sync per source at a time
  scheduler.py        # Task 2: stop() waits for a running sync
  models.py           # Task 2: unknown hub role; Task 3: UtcDateTime
  hub_people.py, auth.py  # Task 2: unknown hub role
docker-compose.yml    # Task 2: stop_grace_period
frontend/src/
  calendar/useCalendarData.ts   # Task 4: cache, lastLoaded
  calendar/cache.ts             # Task 4: new
  calendar/LastUpdated.tsx      # Task 4: new
  calendar/useNightlyReload.ts  # Task 5: new
  calendar/TopBar.tsx           # Task 4, Task 6
  calendar/TimeGrid.tsx         # Task 6: first scroll position
  settings/ColorInput.tsx       # Task 7: new
  settings/CalendarRow.tsx, pages/SettingsPage.tsx  # Task 7
  pages/CalendarPage.tsx        # Task 4, 5
e2e/tests/wall.spec.ts, phone.spec.ts  # Task 8
README_DOCKER.md      # Task 8
```

---

### Task 1: Import fixes (BOM, early overrides, bad addresses)

**Files:**
- Modify: `backend/app/ics.py`, `backend/app/google.py`, `backend/app/caldav.py`, `backend/app/settings_api.py`
- Test: `tests/test_ics.py`, `tests/test_google.py`, `tests/test_settings_api.py`

**Interfaces:**
- Consumes: `ics.parse(text, window) -> list[SeriesData]`, `occurrences.between(db, start, end)`.
- Produces: no new names.

- [ ] **Step 1: Write the failing tests**

  - `test_ics.py::test_utf8_bom_is_read`: `parse("﻿" + <a one-event VCALENDAR>, window)` returns one series.
  - `test_ics.py::test_unbounded_series_with_override_before_first_start`: weekly `RRULE:FREQ=WEEKLY` (no end),
    `DTSTART;TZID=Europe/Zurich:20261110T180000`; an override `RECURRENCE-ID;TZID=Europe/Zurich:20261110T180000` with
    `DTSTART;TZID=Europe/Zurich:20261108T180000`. Assert `series.first_start == datetime(2026, 11, 8, 17, 0)` (naive
    UTC), and via `add_calendar` + `occurrences.between(db, date(2026, 11, 8), date(2026, 11, 9))` one entry starting
    `2026-11-08T18:00:00+01:00`.
  - `test_ics.py::test_unbounded_series_with_rdate_before_first_start`: the same with `RDATE;TZID=Europe/Zurich:
    20261105T180000` instead of the override → `first_start == datetime(2026, 11, 5, 17, 0)`.
  - `test_google.py::test_invalid_url_is_source_invalid`: `google.check("https://exa mple.com/\x00.ics")` raises
    `SourceError` with code `source_invalid` (not an `httpx.InvalidURL`).
  - `test_settings_api.py::test_adding_an_invalid_url_is_422_source_invalid`: POST `/api/sources` (parent) with that
    URL → 422, `detail == "source_invalid"`, no source saved.
  - `test_settings_api.py::test_source_patch_limits`: PATCH with `url` of 2001 characters → 422; `apple_id` of 201 →
    422; `password` of 201 → 422; `name` of `""` → 422.

- [ ] **Step 2: Run them to verify they fail**

  Run: `cd backend && python -m pytest ../tests/test_ics.py ../tests/test_google.py ../tests/test_settings_api.py -q`
  (from the repo root, as in M1). Expected: the six new tests FAIL (NotACalendar; first_start on 10 Nov; InvalidURL
  traceback / 500; 200 or 422 from the source check instead of validation).

- [ ] **Step 3: Implement**

  - `ics._read`: strip a leading `"﻿"` before the `BEGIN:VCALENDAR` check and before `Calendar.from_ical`.
  - `ics._series`, unbounded branch: `first_start` = the minimum of `_utc` over the master's DTSTART, every override's
    DTSTART and every RDATE value (RDATE may be a list of `vDDDLists`; walk `.dts`). A period-valued RDATE uses its
    start.
  - `google.download` and `caldav._request`: catch `httpx.InvalidURL` (it isn't an `httpx.HTTPError`). In `google`
    it becomes `source_invalid`; in `caldav` `source_unreachable` (the URL there is built by the app, so a bad one
    means a bad server answer).
  - `SourcePatch`: `url: Annotated[str, Field(min_length=1, max_length=2000)] | None`, `apple_id` 3–200,
    `password` 1–200, the same as `GoogleIn` / `ICloudIn`.

- [ ] **Step 4: Run the tests to verify they pass**

  Run the same command. Expected: all PASS. Then the whole backend suite: `python -m pytest ../tests -q` → all pass.

- [ ] **Step 5: Commit**

  `git commit -m "fix(backend): BOM feeds, overrides before a series' start, bad addresses, patch limits"`

### Task 2: One sync at a time, clean shutdown, unknown hub roles

**Files:**
- Modify: `backend/app/importer.py`, `backend/app/scheduler.py`, `backend/app/models.py`, `backend/app/hub_people.py`,
  `backend/app/auth.py`, `docker-compose.yml`
- Test: `tests/test_google.py` (or a new `tests/test_sync.py`), new `tests/test_scheduler.py`, `tests/test_hub_login.py`

**Interfaces:**
- Produces: `models.Role.from_hub(value: str) -> Role`; `scheduler.STOP_TIMEOUT_SECONDS = 30`.

- [ ] **Step 1: Write the failing tests**

  - `test_sync.py::test_two_syncs_of_one_source_run_one_after_the_other`: a Google source whose fake download blocks
    on a `threading.Event` the first time. Start `importer.sync_source` for it in a thread (own `SessionLocal`), wait
    until the download is entered, start a second `sync_source(force=True)` in another thread, release the event,
    join both. Assert `source.last_error is None` and the calendar has the feed's series once (no duplicate,
    no IntegrityError recorded as `source_invalid`). Assert the second download only began after the first ended
    (record enter/leave order in the fake).
  - `test_scheduler.py::test_stop_waits_for_a_running_sync`: monkeypatch `scheduler._sync_all` with a function that
    sets `entered`, sleeps 0.3 s, then sets `finished`. In an `asyncio` test: `scheduler.start()`, wait for `entered`,
    `await scheduler.stop()`, assert `finished.is_set()`. (Use `pytest-asyncio` if the tests already have it;
    otherwise `asyncio.run` inside the test, which is enough. `SYNC_DISABLED` must be unset for this test.)
  - `test_scheduler.py::test_stop_gives_up_after_the_timeout`: `_sync_all` sleeps 2 s, `STOP_TIMEOUT_SECONDS`
    monkeypatched to 0.2 → `stop()` returns within 1 s.
  - `test_hub_login.py::test_unknown_hub_role_counts_as_child`: `family_hub.add("Gast", role="GUEST")` → GET
    `/api/sources` with Gast's token is 403 `parents_only` (not 500); `/api/people` as the admin parent lists Gast.

- [ ] **Step 2: Run them to verify they fail**

  Expected: the sync test records `source_invalid` or a duplicate (or deadlocks without the lock, so give the joins a
  5 s timeout and fail on it); stop returns before `finished`; the role test gets 500 (`ValueError`).

- [ ] **Step 3: Implement**

  - `importer.sync_source`: a module-level `dict[int, threading.Lock]` guarded by one `threading.Lock`; hold the
    source's lock for the whole sync. A sync that waited re-reads the source (`db.refresh(source)`) before it runs.
  - `scheduler`: replace `cancel()` with an `asyncio.Event` the loop waits on instead of `asyncio.sleep`
    (`asyncio.wait_for(event.wait(), SYNC_SECONDS)`); `stop()` sets it and awaits the task for at most
    `STOP_TIMEOUT_SECONDS`, then cancels. The event is created in `start()` (it needs the running loop).
  - `models.Role.from_hub`: the matching member, `Role.CHILD` for anything else. Use it in `hub_people._apply` and
    `auth._resolve` instead of `models.Role(...)`.
  - `docker-compose.yml`, backend: `stop_grace_period: 40s` (longer than the 30 s the scheduler waits), with a
    one-line comment.

- [ ] **Step 4: Run the tests to verify they pass**, then the whole backend suite.

- [ ] **Step 5: Commit**

  `git commit -m "fix(backend): one sync per source at a time, wait for it on shutdown, unknown hub roles"`

### Task 3: Timestamps with their time zone

The settings page shows "zuletzt aktualisiert" from `last_success_at`, which the API sends as naive UTC
(`2026-11-06T05:55:35`); browsers read that as local time, one hour off in winter.

**Files:**
- Modify: `backend/app/models.py`
- Test: `tests/test_settings_api.py`, `tests/test_events_api.py`

**Interfaces:**
- Produces: `models.UtcDateTime` (a `TypeDecorator` over `DateTime`): writes naive UTC, reads aware UTC.

- [ ] **Step 1: Write the failing tests**

  - `test_settings_api.py::test_sync_times_carry_utc`: after a successful sync, `/api/sources` item
    `last_success_at` ends with `+00:00`.
  - `test_events_api.py::test_calendars_and_config_times_carry_utc`: `/api/calendars` item `last_success_at` and
    `/api/config` `synced_at` end with `+00:00`.

- [ ] **Step 2: Run them to verify they fail.** Expected: no offset in the strings.

- [ ] **Step 3: Implement** `UtcDateTime` and use it for `Source.last_success_at` and `Source.last_error_at` only
  (`Series.first_start`/`last_end` stay naive: they are compared with naive values in queries). Binding an aware value
  converts it to naive UTC; binding a naive one keeps it. `/api/config`'s `func.max(...)` bypasses the type: wrap that
  value with the same conversion (a small `models.as_utc(value)` used by both). No migration (same column type).

- [ ] **Step 4: Run the tests to verify they pass**, then the whole backend suite (the backup and migration tests
  read these columns too).

- [ ] **Step 5: Commit** `git commit -m "fix(backend): sync times carry their time zone"`

### Task 4: Offline wall: keep the last week, say how old it is

**Files:**
- Create: `frontend/src/calendar/cache.ts`, `frontend/src/calendar/LastUpdated.tsx`
- Modify: `frontend/src/calendar/useCalendarData.ts`, `frontend/src/calendar/TopBar.tsx`,
  `frontend/src/pages/CalendarPage.tsx`, `frontend/src/locales/de.ts`, `frontend/src/locales/en.ts`
- Test: `frontend/src/calendar/cache.test.ts`, `frontend/src/calendar/useCalendarData.test.tsx`,
  `frontend/src/calendar/LastUpdated.test.tsx`

**Interfaces:**
- Produces:
  - `cache.ts`: `type Snapshot = { from: string; to: string; occurrences: Occurrence[]; calendars: CalendarInfo[];
    loadedAt: string }`; `saveSnapshot(s: Snapshot): void`; `loadSnapshot(from: string, to: string): Snapshot | null`.
    Key `planner:last`, value `{ v: 1, ...snapshot }`; one snapshot (the last successful load).
  - `useCalendarData(view, day)` returns `{ occurrences, calendars, failed, loadedAt: Date | null }`.
  - `LastUpdated({ at }: { at: Date | null })`.
- Texts: `calendar.lastUpdated`: de `'zuletzt aktualisiert {{time}}'`, en `'last updated {{time}}'`.

- [ ] **Step 1: Write the failing tests**

  - `cache.test.ts`:
    - `a saved snapshot comes back for the same range`
    - `another range gets nothing` (saved 2026-11-02..2026-11-09, asked 2026-11-09..2026-11-16 → `null`)
    - `garbage or an older format gets nothing` (`localStorage.setItem('planner:last', '{nope')` and `{"v":0}` →
      `null`)
    - `a throwing localStorage is ignored` (`vi.spyOn(Storage.prototype, 'getItem'/'setItem')` throwing → no throw,
      `null`)
  - `useCalendarData.test.tsx` (mock `../api`; `vi.useFakeTimers()`):
    - `a successful load is saved and loadedAt set`
    - `when the first load fails, the saved week is shown` (snapshot for the asked range → `occurrences` from it,
      `failed === true`, `loadedAt` = the snapshot's time)
    - `when a later load fails, what is shown stays` (first load OK, second rejects after `REFRESH_MS` → same
      occurrences, `failed === true`, `loadedAt` unchanged)
  - `LastUpdated.test.tsx` (TZ Europe/Zurich, system time 2026-11-06 14:30):
    - `today shows the time`: at 2026-11-06T13:05 local → text `zuletzt aktualisiert 13:05`
    - `another day shows the weekday too`: 2026-11-05T22:10 → `zuletzt aktualisiert Do 22:10`
    - `nothing loaded yet shows nothing`: `at={null}` → renders nothing

- [ ] **Step 2: Run them to verify they fail**

  Run: `cd frontend && npx vitest run src/calendar`. Expected: the new tests FAIL (modules missing).

- [ ] **Step 3: Implement**

  - `cache.ts` as in Interfaces; every storage access in try/catch; validate the shape (`v === 1`, arrays, strings).
  - `useCalendarData`: on success set state, `loadedAt = new Date()`, `saveSnapshot`. On failure, if nothing has been
    loaded for this range yet, use `loadSnapshot(from, to)` when there is one; always set `failed`. Reset what is
    shown when the range changes only once the new range has data (so a failed range switch keeps the old view out of
    the wrong columns: if neither the API nor the cache has the new range, show empty plus the stamp).
  - `LastUpdated`: `HH:mm` when `at` is today, else `EEEEEE HH:mm` with the date-fns locale (`Do 22:10`).
  - Test hook: `?refresh=<ms>` overrides `REFRESH_MS` (like `?idle=`), passed from `CalendarPage` to
    `useCalendarData(view, day, refreshMs)`; Task 8's browser test uses it.
  - `TopBar`: new prop `lastUpdated: Date | null`, rendered next to ⚠ only when `problem` is from `failed` (the API
    can't be reached), not for a failing source. `CalendarPage` passes `failed ? loadedAt : null`.

- [ ] **Step 4: Run the tests to verify they pass**, then `npm run lint`, `npx vitest run`, `npm run check-texts`.

- [ ] **Step 5: Commit** `git commit -m "feat(wall): keep the last loaded week offline and show when it was loaded"`

### Task 5: Nightly reload

**Files:**
- Create: `frontend/src/calendar/useNightlyReload.ts`
- Modify: `frontend/src/pages/CalendarPage.tsx`
- Test: `frontend/src/calendar/useNightlyReload.test.tsx`

**Interfaces:**
- Produces: `useNightlyReload(enabled: boolean, reload?: () => void, probe?: () => Promise<unknown>)`;
  `RELOAD_HOUR = 3`; `CHECK_MS = 60_000`. Defaults: `reload = () => window.location.reload()`,
  `probe = fetchConfig`.

- [ ] **Step 1: Write the failing tests** (`vi.useFakeTimers()`, TZ Europe/Zurich)

  - `reloads once after 03:00 the next night`: system time 2026-11-06T20:00; advance to 2026-11-07T03:01 → `probe`
    called, then `reload` called once.
  - `not before 03:00`: advance to 2026-11-07T02:59 → `reload` not called.
  - `not on the evening it was loaded`: loaded 2026-11-07T03:30, advance 30 min → `reload` not called (it waits for
    the next night).
  - `waits while the NAS doesn't answer`: `probe` rejects at 03:01 → no reload; probe resolves at 03:06 → reload.
  - `off when not enabled`: `enabled = false` → never probes.

- [ ] **Step 2: Run them to verify they fail.** Expected: module missing.

- [ ] **Step 3: Implement**: remember the load day; every `CHECK_MS`, if today is after the load day and the hour is
  ≥ `RELOAD_HOUR`, `probe()` then `reload()`; a rejected probe waits for the next check. `CalendarPage`:
  `useNightlyReload(onWall)`.

- [ ] **Step 4: Run the tests to verify they pass**, then lint and the whole Vitest suite.

- [ ] **Step 5: Commit** `git commit -m "feat(wall): reload once a night when the NAS answers"`

### Task 6: Phone top bar and the first scroll position

**Files:**
- Modify: `frontend/src/calendar/TopBar.tsx`, `frontend/src/calendar/TimeGrid.tsx`
- Test: `frontend/src/calendar/TimeGrid.test.tsx`; the phone layout is checked in Task 8 (jsdom has no layout)

**Interfaces:**
- Produces: `TimeGrid` exports `firstScrollHour(days: Date[], occurrences: Occurrence[], now: Date): number`.

- [ ] **Step 1: Write the failing tests** (`TimeGrid.test.tsx`)

  - `the week opens at the earliest timed event of the shown days`: week 2026-11-02..08, events Tue 06:30 and Thu
    09:00, now Thu 20:00 → `6`.
  - `without early events it opens at 07:00`: events at 10:00 only → `7`.
  - `an evening with no events still opens at 07:00`: day view of today, no events, now 20:00 → `7`.
  - `all-day events don't count`: an all-day event only → `7`.

  Ruling recorded here: the M1 code scrolled to "the hour before now" in the evening, which hid tomorrow's and the
  rest of the week's morning events in the week view (deferred minor). The week is for looking ahead, so the first
  position shows the earliest timed event of the shown days, and never later than 07:00. The red line can be below
  the fold late in the evening; scrolling shows it.

- [ ] **Step 2: Run them to verify they fail.** Expected: `firstScrollHour` missing.

- [ ] **Step 3: Implement**
  - `firstScrollHour`: `min(7, earliest local hour of a timed occurrence that starts on one of `days`)`, clamped to ≥ 0.
    Use it for the first scroll (replacing the `showsToday` rule); scrolling again only when `days` changes.
  - `TopBar` below 768 px (`max-md:` Tailwind variants): row 1 is the title (month/year only, no KW), ⚠, the stamp
    and ⚙; row 2 is ‹ Heute › and the views. The view buttons get `px-2` and the views' short labels on narrow screens
    (`calendar.viewsShort`: de `Tag`, `3T`, `Wo`, `Mo`, `Liste`; en `Day`, `3D`, `Wk`, `Mo`, `List`), each still
    ≥ 48 × 48 px. Wide screens unchanged.

- [ ] **Step 4: Run the tests to verify they pass**, then lint, Vitest, check-texts.

- [ ] **Step 5: Commit** `git commit -m "fix(wall): week opens at the morning's first event; two-row top bar on phones"`

### Task 7: Colour pickers save once

**Files:**
- Create: `frontend/src/settings/ColorInput.tsx`
- Modify: `frontend/src/settings/CalendarRow.tsx`, `frontend/src/pages/SettingsPage.tsx`
- Test: `frontend/src/settings/ColorInput.test.tsx`

**Interfaces:**
- Produces: `ColorInput({ value, disabled, label, onCommit }: { value: string; disabled?: boolean; label: string;
  onCommit: (color: string) => void })`; `COMMIT_MS = 500`.

- [ ] **Step 1: Write the failing tests** (`vi.useFakeTimers()`)

  - `dragging through colours saves only the last one`: three `fireEvent.input`/`change` calls 100 ms apart
    (`#111111`, `#222222`, `#333333`), advance 500 ms → `onCommit` called once with `#333333`.
  - `shows the new colour at once`: after one change the input's value is the new colour before the commit.
  - `follows a new value from outside`: rerender with `value="#444444"` → input shows it.

- [ ] **Step 2: Run them to verify they fail.** Expected: module missing.

- [ ] **Step 3: Implement**: local state for the shown colour; a timer reset on each change; commit `COMMIT_MS` after
  the last change; on unmount commit a pending change. Replace both `<input type="color">` with it.

- [ ] **Step 4: Run the tests to verify they pass**, then lint and Vitest.

- [ ] **Step 5: Commit** `git commit -m "fix(settings): a colour picker saves once, not on every step"`

### Task 8: Browser tests and docs

**Files:**
- Modify: `e2e/tests/wall.spec.ts`, `e2e/tests/phone.spec.ts`, `README_DOCKER.md`

- [ ] **Step 1: Write the browser tests**

  - `wall.spec.ts`: `the wall keeps its week when the NAS can't be reached`: open `/display`, see an event, then
    `page.route('**/api/**', r => r.abort())` and `page.reload()` is *not* used (index.html would fail too); instead
    open with `?refresh=1000` (Task 4's hook) and wait for the next refresh → the event is still there and "zuletzt aktualisiert" is visible. Then
    `page.unroute('**/api/**')` → after the next refresh the stamp is gone.
  - `phone.spec.ts`: `the phone top bar takes at most two rows`: at 375 × 812, `header` bounding box height ≤ 2 × 56 +
    padding (≤ 128 px) and no horizontal scroll (`document.documentElement.scrollWidth <= 375`).

- [ ] **Step 2: Run them** (`cd e2e && npx playwright test`). Expected: the new tests pass with Tasks 4 and 6 in;
  if written before the hook exists, the wall test fails on the missing stamp.

- [ ] **Step 3: Docs**: `README_DOCKER.md` gets a short "When the NAS is off" paragraph: the wall keeps the last loaded
  week with "zuletzt aktualisiert", reloads itself around 03:00 once the NAS answers; leave the iPad on the page.

- [ ] **Step 4: Full verification**: backend `python -m pytest ../tests -q`; frontend `npm run lint`,
  `npx vitest run`, `npm run build`, `npm run check-texts`; e2e `npx playwright test`. All green.

- [ ] **Step 5: Commit** `git commit -m "test(e2e): offline wall and phone top bar; docs for the NAS being off"`
