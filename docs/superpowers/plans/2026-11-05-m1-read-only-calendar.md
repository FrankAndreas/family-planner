# M1 Read-only Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The family calendar from Google (secret iCal URL) and iCloud (CalDAV) on the wall iPad and phones, read-only,
with parents' settings behind the family-hub login, deployable on the NAS.

**Architecture:** A FastAPI backend imports each calendar into SQLite every 5 minutes (one transaction per calendar),
stores each event series as its raw iCalendar text plus indexed range columns, and expands recurrences for the asked
range. A React frontend (served by nginx, which forwards `/api`) shows week / day / 3-day / month / agenda. Viewing
needs no login; settings ask family-hub who is logged in, like the sibling apps.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy 2, Alembic, pydantic, httpx, icalendar, recurring-ical-events,
cryptography; React 19, Vite 8, TypeScript, Tailwind 4, i18next, react-router 7, axios, date-fns; pytest, Vitest,
Playwright.

**Spec:** `docs/superpowers/specs/2026-11-05-family-planner-design.md`

**Reference implementation for patterns:** `../meal-planer` (GitHub `FrankAndreas/family-meal-planner`). Where a task
says "copy from meal-planer", copy the file and change only what the task names.

## Global Constraints

- Calendar only: no chores, meals, lists, clock, weather, photos, night mode.
- Read-only: no event creation, editing or deleting. Keep each event's UID and, for CalDAV, its href and etag.
- No login to view from home. Any request carrying `Cf-Connecting-Ip` gets 403 `outside`.
- Settings and every change: hub login, access to app key `planner` (`HUB_APP_KEY`), role `PARENT`, and with the cookie the header `X-Requested-With: planner`.
- Error codes (JSON `detail`): 401 `not_logged_in`, 403 `no_access`, 403 `parents_only`, 503 `hub_unavailable`, 403 `csrf`, 403 `outside`.
- Credentials (iCal URLs, Apple ID + app password) AES-256-GCM encrypted with the 32-byte key in `ENC_KEY_FILE` (default `/run/secrets/enc_key`, base64); never logged, never in an API response, never in a stored error. No key → the backend refuses to start.
- Sync every 300 s. Keep and show events from 3 months back to 13 months ahead.
- Times: keep the original TZID; show in `Europe/Zurich` (`TZ`). All-day events are dates, never midnight UTC.
- Languages: `de` (default, `DEFAULT_LANGUAGE`) and `en`. Monday-first weeks, ISO week numbers ("KW 45"), 24 h.
- Wall: rests on the week view; back to this week's week view after 180 s untouched; event titles ≥ 18 px; touch targets ≥ 48 px; few animations.
- Phone (viewport width < 768 px): opens on the agenda.
- Containers non-root (PUID/PGID, default 999:999), no Docker socket, `restart: unless-stopped`, backend `mem_limit: 256m`; NAS port `${PORT:-8090}`.
- Backups: nightly `VACUUM INTO` to `./data/backups`, keep 14; one before migrations run at start.
- Public repo: invented people and placeholders (`<domain>`, `<NAS_IP>`) only, never a real iCal URL.
- Images: `ghcr.io/frankandreas/family-planner/backend` and `.../frontend`, linux/amd64.

## Review Focus

1. **All-day and multi-day events around the DST switch** (2026-10-25, 2027-03-28): an all-day event must stay on its own date(s) and not bleed into the next day. Pinned in Task 5 and Task 11.
2. **Recurring series with exceptions**: an EXDATE, a moved occurrence (RECURRENCE-ID override) and a cancelled override (`STATUS:CANCELLED`) must show exactly as in Google/Apple. Pinned in Task 5.
3. **A source that answers 200 with something that isn't a calendar** (Google's HTML sign-in page, an empty body): the calendar keeps its last good events and gets error `source_invalid`; a valid but empty VCALENDAR does empty it. Pinned in Task 6.
4. **A credential leaking through an error**: httpx exceptions put the URL in their message; nothing stored or logged may contain the URL's secret part or the password. Pinned in Task 6 and Task 7.
5. **An event ending exactly at midnight** (e.g. 22:00–00:00, or an all-day DTEND that is the next date): shows on its own day only, not as a sliver on the next. Pinned in Task 11.

---

## File structure

```
backend/
  Dockerfile                      # copy from meal-planer
  requirements.txt
  app/
    main.py                       # app, routers, lifespan (scheduler), /health
    config.py                     # env(), data_dir(), default_language(), tz(), window()
    database.py                   # engine (WAL, foreign keys), SessionLocal, get_db
    database_setup.py             # migrations at start + pre-migration backup
    errors.py                     # api_error(status, code)
    crypto.py                     # encrypt/decrypt with enc_key
    hub.py, hub_people.py, auth.py  # family-hub login (copied and adapted)
    models.py
    migrations/ (env.py, script.py.mako, versions/0001_initial.py)
    fetch.py                      # one httpx client, swappable transport for tests
    ics.py                        # parse a VCALENDAR into series rows
    google.py                     # import one secret-iCal source
    caldav.py                     # iCloud discovery and import
    importer.py                   # replace one calendar's series in one transaction; sync_source, sync_all
    occurrences.py                # expand + merge for a range
    scheduler.py                  # every 300 s sync; 03:00 backup
    backup.py
    public_api.py                 # /api/events, /api/calendars, /api/config, /api/hub
    settings_api.py               # parents: sources, calendars, family colour, sync now, people
frontend/                         # Vite app (see Tasks 10-14)
tests/                            # pytest; fake_hub.py, fake_sources.py, fixtures/*.ics
e2e/                              # Playwright, real family-hub checkout + static .ics server
docker-compose.yml, README.md, README_DOCKER.md, LICENSE, pyproject.toml, pytest.ini
.github/workflows/{pr-checks,pull-request,ci-cd}.yml, .github/dependabot.yml
scripts/dev-backend.sh
```

---

### Task 1: Backend skeleton, database and health

**Files:**
- Create: `backend/requirements.txt`, `backend/app/{__init__,config,database,database_setup,errors,main}.py`, `backend/app/migrations/{env.py,script.py.mako}`, `backend/app/migrations/versions/0001_initial.py` (empty upgrade for now; Task 4 fills it), `pyproject.toml`, `pytest.ini`, `tests/requirements.txt`, `tests/conftest.py`, `tests/test_health.py`, `scripts/dev-backend.sh`, `LICENSE` (MIT, copy)
- Copy from meal-planer: `pyproject.toml`, `pytest.ini`, `database.py`, `database_setup.py`, `errors.py`, `migrations/env.py`, `script.py.mako`, `scripts/dev-backend.sh`

**Interfaces:**
- Produces: `config.env(name, default="") -> str`, `config.data_dir() -> Path`, `config.default_language() -> Literal["de","en"]`, `config.tz() -> ZoneInfo`, `config.window(now: datetime) -> tuple[datetime, datetime]` (now − 3 months, now + 13 months, tz-aware), `database.engine`, `database.SessionLocal`, `database.get_db`, `errors.api_error(status, code, **params) -> HTTPException`, `database_setup.HEAD = "0001"`, `database_setup.setup(engine)`.

- [ ] **Step 1:** `backend/requirements.txt`: the pins family-hub uses for fastapi, uvicorn, sqlalchemy, pydantic, alembic, tzdata, cryptography; add `httpx`, `icalendar`, `recurring-ical-events` pinned with `==` to the current release. `tests/requirements.txt`: copy from meal-planer.
- [ ] **Step 2:** `database.py`: default `DATABASE_URL` `sqlite:///./data/planner.db`; on connect also `PRAGMA journal_mode=WAL`.
- [ ] **Step 3: Write failing tests** in `tests/test_health.py`:

```python
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}

def test_wal_mode(db):
    assert db.execute(text("PRAGMA journal_mode")).scalar() == "wal"

def test_window_is_3_months_back_13_ahead():
    start, end = config.window(datetime(2026, 11, 5, 12, tzinfo=ZoneInfo("Europe/Zurich")))
    assert (start.date(), end.date()) == (date(2026, 8, 5), date(2027, 12, 5))
```

`conftest.py`: like meal-planer's (temp `DATABASE_URL`, `DATA_DIR`, `DEFAULT_LANGUAGE=de`), plus `ENC_KEY_FILE` pointing at a temp file holding a random base64 key, and `SYNC_DISABLED=1`. Fixtures `fresh_db` (drop/create all), `db`, `client`.
- [ ] **Step 4:** Run `venv/bin/pytest tests/test_health.py` → FAIL (no app).
- [ ] **Step 5:** Implement `main.py` (logging, `database_setup.setup`, `FastAPI(title="Family Planner API")`, `/health`) and `config.window` (use `dateutil`-free month arithmetic: clamp the day to the month's length).
- [ ] **Step 6:** Run → PASS.
- [ ] **Step 7:** Commit `feat(backend): skeleton, SQLite in WAL mode, health`.

### Task 2: Encrypted credentials

**Files:** Create `backend/app/crypto.py`, `tests/test_crypto.py`; modify `backend/app/main.py`.

**Interfaces:**
- Produces: `crypto.load_key() -> bytes` (reads `ENC_KEY_FILE`, base64, must be 32 bytes, else `crypto.KeyMissing` with a message naming the file and how to make one), `crypto.encrypt(plain: str) -> str` (`"v1:" + base64(nonce12 + ciphertext)`), `crypto.decrypt(token: str) -> str`.

- [ ] **Step 1: Failing tests:**

```python
def test_round_trip():
    token = crypto.encrypt("https://calendar.google.com/calendar/ical/x/private-abc/basic.ics")
    assert token.startswith("v1:") and "private-abc" not in token
    assert crypto.decrypt(token).endswith("private-abc/basic.ics")

def test_two_encryptions_differ():
    assert crypto.encrypt("a") != crypto.encrypt("a")

def test_wrong_key_fails(tmp_path, monkeypatch):
    token = crypto.encrypt("a")
    other = tmp_path / "k"; other.write_text(base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setenv("ENC_KEY_FILE", str(other))
    with pytest.raises(crypto.CannotDecrypt):
        crypto.decrypt(token)

@pytest.mark.parametrize("content", [None, "", "dG9vIHNob3J0"])
def test_missing_or_short_key(tmp_path, monkeypatch, content): ...  # raises crypto.KeyMissing
```

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement with `cryptography.hazmat.primitives.ciphers.aead.AESGCM`; read the key on each call (tests change it). In `main.py`, call `crypto.load_key()` at import and let `KeyMissing` stop the start with its message logged.
- [ ] **Step 4:** Run → PASS. Commit `feat(backend): credentials encrypted with enc_key`.

### Task 3: Family-hub login and people

**Files:**
- Copy from meal-planer and adapt: `backend/app/hub.py` (default key `planner`), `backend/app/hub_people.py`, `backend/app/auth.py`, `tests/fake_hub.py`, `tests/helpers.py` (only `bearer`, `login`)
- Create: `tests/test_hub_login.py`, `tests/test_outside.py`; modify `backend/app/main.py`, `tests/conftest.py`

**Interfaces:**
- Produces: `models.Person` (table `people`: `id`, `hub_id` unique, `name`, `role` PARENT/CHILD, `color` nullable, `language` nullable, `is_active`), `auth.get_current_user`, `auth.require_parent` (FastAPI dependencies returning `models.Person`), `auth.CSRF_VALUE = "planner"`, `hub.public_url()`, `hub_people.refresh(db, login, force=False)`.

Adaptations:
- `hub_people._apply`: no name linking at a switch (this app starts with the hub); store `color` from the hub. No `name_key` uniqueness: names are display only.
- An outside guard as middleware in `main.py`: any request (including `/api/events`) with `Cf-Connecting-Ip` → 403 `{"detail": "outside"}`, except `/health`. So `auth` needs no Cloudflare branch: drop `outside_ip` handling from `auth.request_login` (keep `hub.Login` as is).
- Put `Person` in `models.py` now; Task 4 adds the other tables and writes the migration for all.

- [ ] **Step 1: Failing tests** (`test_hub_login.py`), with a throwaway parents-only route registered in the test (`@app.get("/api/_test/parent", dependencies=[Depends(auth.require_parent)])`) until Task 9 brings real ones:
  - `test_no_login_401_not_logged_in`, `test_child_403_parents_only`, `test_parent_ok_and_person_row_has_hub_color` (fake hub person with `color="#e11d48"`), `test_no_access_403`, `test_hub_down_503_hub_unavailable`, `test_cookie_change_without_header_403_csrf`, `test_cookie_change_with_header_x_requested_with_planner_ok`, `test_person_dropped_by_hub_becomes_inactive`.
  - `test_outside.py`: `test_outside_header_403_on_events_and_settings` (`/api/events`, `/api/_test/parent`), `test_health_answers_outside`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement as above; extend `FakeHub.add(name, role, access=True, language="de", color=None)`.
- [ ] **Step 4:** Run → PASS. Commit `feat(backend): family-hub login for settings, outside requests refused`.

### Task 4: Data model and migration

**Files:** Modify `backend/app/models.py`, `backend/app/migrations/versions/0001_initial.py`; create `tests/test_migrations.py`.

**Interfaces — Produces (SQLAlchemy models):**
- `Source`: `id`, `kind` (`"google_ical" | "icloud_caldav"`), `name`, `credential` (encrypted text: the URL, or JSON `{"apple_id","password"}`), `base_url` (CalDAV home after discovery, nullable), `content_hash` (Google), `last_success_at`, `last_error` (a code, nullable), `last_error_at`.
- `Calendar`: `id`, `source_id` FK cascade, `remote_id` (Google: `"ics"`; CalDAV: the calendar href), `name`, `ctag` nullable, `person_id` FK `people.id` SET NULL nullable (None = Familie), `color` nullable (own colour), `visible` bool default True, `enabled` bool default True (iCloud calendars ticked in settings).
- `Series`: `id`, `calendar_id` FK cascade, `uid`, `ics` (text: one VCALENDAR with the master and its overrides, plus the VTIMEZONEs they use), `first_start` (UTC datetime), `last_end` (UTC datetime, NULL = recurs without end), `href`, `etag` (CalDAV, nullable). Unique (`calendar_id`, `uid`). Index (`calendar_id`, `first_start`).
- `Setting` single row id 1: `family_color` default `"#7c3aed"`.

- [ ] **Step 1: Failing test** `test_migrations.py`: migrating an empty file DB to head creates exactly the tables `people, sources, calendars, series, settings, alembic_version`, and `metadata.create_all` vs. migrated schema columns match (copy meal-planer's comparison test approach).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Write the models and `0001_initial.py`. **Step 4:** PASS. Commit `feat(backend): sources, calendars, series`.

### Task 5: Parsing iCalendar into series

**Files:** Create `backend/app/ics.py`, `tests/test_ics.py`, `tests/fixtures/*.ics` (invented events).

**Interfaces:**
- Produces: `@dataclass SeriesData(uid: str, ics: str, first_start: datetime, last_end: datetime | None)`; `ics.parse(text: str, window: tuple[datetime, datetime]) -> list[SeriesData]` raising `ics.NotACalendar` when the text isn't a VCALENDAR; `ics.expand(series_ics: str, start: datetime, end: datetime) -> list[Occurrence]`, `@dataclass Occurrence(uid, start: datetime | date, end: datetime | date, all_day: bool, title, location, description, recurrence_id: str | None)`.

Rules: group VEVENTs by UID (master + RECURRENCE-ID overrides) into one VCALENDAR string with the VTIMEZONEs they reference; drop series that end before the window or start after it; `last_end = None` for an RRULE without UNTIL/COUNT; a missing DTEND means DURATION, or for a DATE start one day, for a DATE-TIME start zero length; floating times are `TZ`; a non-Olson TZID ("W. Europe Standard Time") falls back to its VTIMEZONE, else `TZ`. `expand` uses `recurring_ical_events.of(cal).between(start, end)`, which applies EXDATE, overrides and drops `STATUS:CANCELLED` overrides; all-day results stay `date`.

- [ ] **Step 1: Failing tests** (fixtures named after what they contain):
  - `test_weekly_with_exdate_and_moved_occurrence`: weekly Thu 16:00 Fussball; EXDATE 2026-11-12; 2026-11-19 moved to 17:30 → between 2026-11-01 and 2026-11-30: starts `[05 16:00, 19 17:30, 26 16:00]` Zurich.
  - `test_cancelled_override_disappears`.
  - `test_all_day_over_dst_change`: `DTSTART;VALUE=DATE:20261024`, `DTEND;VALUE=DATE:20261026` → one occurrence, `start == date(2026,10,24)`, `end == date(2026,10,26)`, `all_day`.
  - `test_missing_dtend_and_duration`, `test_floating_time_is_zurich`, `test_windows_tzid_name`.
  - `test_unbounded_rrule_last_end_none`, `test_series_outside_window_dropped`.
  - `test_html_raises_not_a_calendar` (`"<html>…"`), `test_empty_body_raises`, `test_empty_vcalendar_gives_empty_list`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. Commit `feat(backend): parse and expand iCalendar series`.

### Task 6: Importing a Google calendar, one transaction per calendar

**Files:** Create `backend/app/fetch.py`, `backend/app/importer.py`, `backend/app/google.py`, `tests/fake_sources.py`, `tests/test_google.py`.

**Interfaces:**
- Produces: `fetch.client() -> httpx.Client` (timeout 20 s, redirects followed, `User-Agent: family-planner`, transport from `fetch.transport`, which tests replace with an `httpx.MockTransport`); `class SourceError(Exception)` in `importer.py` with `.code` in `{"source_unreachable", "source_auth", "source_not_found", "source_invalid"}` and **no other text**; `importer.replace_series(db, calendar: Calendar, series: list[SeriesData]) -> None` (delete + insert inside one `with db.begin_nested()`/commit, also updates `calendar.ctag`); `importer.sync_source(db, source: Source, force: bool = False) -> None` (dispatches by kind; on `SourceError` stores `last_error`/`last_error_at` and leaves events untouched; on success clears it and sets `last_success_at`); `importer.sync_all(db) -> None` (each source on its own, one failing never stops the others); `google.sync(db, source, force) -> None`; `google.check(url: str) -> list[SeriesData]` (for "add source").
- `webcal://` URLs become `https://`.

- [ ] **Step 1: Failing tests:**
  - `test_first_import_creates_calendar_and_series`.
  - `test_unchanged_hash_skips_parse` (patch `ics.parse` to fail; second sync with same body passes).
  - `test_html_200_keeps_old_events_and_sets_source_invalid`.
  - `test_empty_vcalendar_empties_calendar`.
  - `test_404_source_not_found_410_too`, `test_401_403_source_auth`, `test_connect_error_source_unreachable`.
  - `test_error_never_contains_secret(caplog)`: URL `https://calendar.google.com/calendar/ical/a%40example.com/private-s3cr3t/basic.ics`, transport raises `httpx.ConnectError` whose message includes the URL → `"s3cr3t" not in source.last_error`, not in `caplog.text`.
  - `test_import_is_atomic`: make the insert of the 2nd series fail → the calendar still has exactly its old series.
  - `test_one_failing_source_others_sync`.
  - `test_webcal_scheme`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. Log only the source id and the error code. **Step 4:** PASS. Commit `feat(backend): Google secret-iCal import`.

### Task 7: iCloud CalDAV

**Files:** Create `backend/app/caldav.py`, `tests/test_caldav.py`; extend `tests/fake_sources.py` with a fake CalDAV server (an `httpx.MockTransport` handler answering PROPFIND/REPORT with canned multistatus XML).

**Interfaces:**
- Produces: `@dataclass RemoteCalendar(href: str, name: str, ctag: str | None)`; `caldav.discover(apple_id: str, password: str) -> tuple[str, list[RemoteCalendar]]` (base URL incl. the `pXX-caldav.icloud.com` shard, and the VEVENT calendars); `caldav.sync(db, source, force) -> None` (for each `enabled` calendar: PROPFIND `getctag`; unchanged and not forced → skip; else REPORT `calendar-query` with `time-range` = `config.window`, parse each `calendar-data` with `ics.parse`, keep href/etag, `importer.replace_series`). New remote calendars found at sync are added with `enabled=False`; removed ones are deleted.

Discovery: PROPFIND `current-user-principal` on `https://caldav.icloud.com/` (Basic auth) → PROPFIND `calendar-home-set` on the principal → PROPFIND Depth 1 on the home for `displayname`, `resourcetype`, `CS:getctag`, `supported-calendar-component-set`; keep collections that are calendars supporting VEVENT. Use `xml.etree.ElementTree`; namespaces `DAV:`, `urn:ietf:params:xml:ns:caldav`, `http://calendarserver.org/ns/`.

- [ ] **Step 1: Failing tests:** `test_discover_follows_shard_and_lists_event_calendars` (a VTODO-only "Erinnerungen" collection excluded), `test_unchanged_ctag_skips_report`, `test_changed_ctag_replaces_events`, `test_new_remote_calendar_added_disabled`, `test_401_source_auth_with_normal_password`, `test_password_never_in_error_or_log(caplog)`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. Commit `feat(backend): iCloud CalDAV import`.

### Task 8: Public read API: occurrences, calendars, config

**Files:** Create `backend/app/occurrences.py`, `backend/app/public_api.py`, `tests/test_events_api.py`.

**Interfaces:**
- Produces (no login):
  - `GET /api/events?from=YYYY-MM-DD&to=YYYY-MM-DD` (to exclusive, at most 62 days, else 422 `range_too_long`) → `[{"key": str, "uid", "title", "start": ISO, "end": ISO, "all_day": bool, "location", "description", "calendar_ids": [int]}]`, sorted by start. Timed values are ISO with offset in `TZ`; all-day are dates. Only `visible` and `enabled` calendars. Same `uid` and same start in several calendars → one entry with every calendar id (sorted). `key` = `uid` + start, stable across reloads.
  - `GET /api/calendars` → `[{"id", "name", "color": str (own colour, else the person's hub colour, else the family colour), "person": {"id","name"} | null, "visible", "ok": bool, "last_success_at"}]`; no error codes, no source details.
  - `GET /api/config` → `{"language": default_language(), "family_color", "synced_at": newest last_success_at | null}`.
  - `GET /api/hub` → `{"login_url", "logout_url"}` (copy from meal-planer).
- `occurrences.between(db, start: date, end: date) -> list[dict]`: select series with `first_start < end` and (`last_end IS NULL` or `last_end > start`), `ics.expand` each, merge.

- [ ] **Step 1: Failing tests:** `test_week_range_returns_expanded_occurrences`, `test_hidden_calendar_left_out`, `test_shared_invite_once_with_both_calendars`, `test_all_day_is_date_string`, `test_range_over_62_days_422`, `test_calendar_color_precedence` (own > person > family), `test_calendars_hide_error_details` (a failing source: `ok false`, no `last_error` key).
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. Commit `feat(backend): events, calendars and config for the screens`.

### Task 9: Settings API, scheduler and backups

**Files:** Create `backend/app/settings_api.py`, `backend/app/scheduler.py`, `backend/app/backup.py`, `tests/test_settings_api.py`, `tests/test_backup.py`; modify `main.py` (lifespan starts the scheduler unless `SYNC_DISABLED`), `database_setup.py` (backup before upgrading an existing DB whose revision isn't `HEAD`).

**Interfaces — Produces (all `require_parent`):**
- `GET /api/me` → the person (any logged-in person, for the frontend).
- `GET /api/sources` → `[{"id","kind","name","has_credential": true,"last_success_at","last_error","calendars":[{"id","name","enabled"}]}]`.
- `POST /api/sources` `{"kind":"google_ical","name","url"}` or `{"kind":"icloud_caldav","name","apple_id","password"}` → tried at once (`google.check` / `caldav.discover`); a `SourceError` → 422 with its code, nothing saved; success → 201, imported once.
- `PATCH /api/sources/{id}` `{name?, url?}` / `{name?, apple_id?, password?}` (credential re-tried before saving); `DELETE /api/sources/{id}`; `POST /api/sources/{id}/sync` (forced, synchronous, returns the source).
- `PATCH /api/calendars/{id}` `{person_id?: int|null, color?: str|null, visible?: bool, enabled?: bool}`; colours must match `^#[0-9a-f]{6}$` (422 `bad_color`); `person_id` must be an active person.
- `GET /api/people` → active people `[{"id","name","color"}]`.
- `PATCH /api/settings` `{"family_color"}`.
- `scheduler.start() / stop()`: an asyncio task running `importer.sync_all` in a thread every 300 s, and `backup.nightly()` when the Zurich clock passes 03:00. `backup.make(reason: str) -> Path` (`VACUUM INTO data/backups/planner-<reason>-<YYYYmmdd-HHMMSS>.db`), `backup.prune(keep=14)`.
- An inactive person's calendars count as Familie (`/api/calendars` gives `person: null`).

- [ ] **Step 1: Failing tests:** `test_add_google_source_checks_url_first` (bad URL → 422 `source_not_found`, no row), `test_responses_never_contain_credentials` (walk every settings response JSON for the URL secret and password), `test_add_icloud_lists_calendars_disabled` (every discovered calendar starts disabled; the parent ticks the ones to show), `test_patch_calendar_person_and_bad_color`, `test_sync_now`, `test_child_gets_parents_only`, `test_inactive_person_falls_back_to_family`, `test_backup_keeps_14`, `test_backup_before_migration`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS (whole suite). Commit `feat(backend): settings, sync every 5 minutes, nightly backups`.

### Task 10: Frontend skeleton

**Files:** Copy from meal-planer and trim: `frontend/{package.json,eslint.config.js,index.html,postcss.config.js,tailwind.config.js,tsconfig*.json,vite.config.ts,Dockerfile,nginx.conf,security-headers.conf,scripts/check-texts.mjs}`, `frontend/src/{main.tsx,i18n.ts,i18next.d.ts,api.ts,hubAddress.ts,hubAddress.test.ts,index.css}`; create `frontend/src/App.tsx`, `frontend/src/locales/{de,en}.json`.

- `package.json` name `planner-frontend`; drop `@dnd-kit/core`. `api.ts` header `X-Requested-With: planner`; the 401 redirect only for settings calls (viewing never logs in).
- `nginx.conf`: drop the 26 MB body and 120 s timeout lines.
- `App.tsx` routes: `/` and `/display` → `CalendarPage`, `/settings` → `SettingsPage` (placeholders for now). `i18n` language = `/api/config` language, or the logged-in person's on settings.
- `<meta name="apple-mobile-web-app-capable" content="yes">` and a home-screen icon, so "Add to Home Screen" opens full screen.

- [ ] **Step 1:** `npm install`, `npm run lint`, `npm test`, `npm run build` all pass. Commit `feat(frontend): skeleton`.

### Task 11: Calendar date logic (pure, tested)

**Files:** Create `frontend/src/calendar/{dates.ts,layout.ts,dates.test.ts,layout.test.ts}`, `frontend/src/types.ts`.

**Interfaces — Produces:**
- `type Occurrence = { key: string; title: string; start: string; end: string; allDay: boolean; location?: string; description?: string; calendarIds: number[] }` (mapped from the API's snake_case in `api.ts`).
- `weekStart(d: Date): Date` (Monday), `isoWeek(d: Date): number`, `days(start: Date, n: number): Date[]`, `monthGrid(d: Date): Date[][]` (Mon-first, 6 rows), `range(view: View, d: Date): { from: string; to: string }` with `type View = 'day' | '3day' | 'week' | 'month' | 'agenda'` (agenda: today + 14 days).
- `onDay(o: Occurrence, day: Date): boolean` — an end exactly at 00:00 (or an all-day end date) belongs to the previous day.
- `layoutTimed(occ: Occurrence[], day: Date): { o: Occurrence; top: number; height: number; col: number; cols: number }[]` (top/height in minutes from 00:00, clipped to the day; overlapping events share the width in columns).
- `allDayBars(occ: Occurrence[], days: Date[]): { o: Occurrence; startCol: number; span: number; row: number }[]` (timed events spanning midnight count as bars too).

- [ ] **Step 1: Failing tests:** `isoWeek(2026-11-05) === 45`, `isoWeek(2027-01-01) === 53`; `weekStart(Sun 2026-11-08)` is Mon 2026-11-02; `onDay` for 22:00–00:00 on 05 is true, on 06 false; all-day 2026-10-24..26 (DST) is on 24 and 25, not 26; two overlapping 16:00–17:00 events → `cols 2`, `col 0/1`; a 3-day all-day bar starting Sat in a Mon-first week → `startCol 5, span 2` in that week.
- [ ] **Step 2:** FAIL. **Step 3:** Implement with date-fns (`Europe/Zurich` is the device zone on the iPad; parse API strings with their offset). **Step 4:** PASS. Commit `feat(frontend): calendar date logic`.

### Task 12: Week, day and 3-day views on the wall

**Files:** Create `frontend/src/pages/CalendarPage.tsx`, `frontend/src/calendar/{TopBar,TimeGrid,EventSheet,useCalendarData,useIdleReturn}.tsx`.

- `CalendarPage` keeps `view` and `date` in the URL (`?view=week&date=2026-11-05`); default view `week` at ≥ 768 px, `agenda` below. Loads `/api/calendars` and `/api/events` for `range(view, date)`; refetches every 60 s.
- `TopBar`: month + "KW n", buttons Tag / 3 Tage / Woche / Monat / Agenda, back / Heute / forward, gear → `/settings`. Buttons ≥ 48 px.
- `TimeGrid` (`days: 1 | 3 | 7`): all-day bars on top, hours 06–22 visible (scrollable to 00–24), today's column tinted, red now-line, scrolls to now on load. Event block: title ≥ 18 px, time, a left stripe per calendar colour (several for shared events).
- `EventSheet`: tap → title, time, place, description as plain text, calendar names.
- `useIdleReturn(180_000)`: on `/display` only, after 180 s with no pointer/touch, navigate to `?view=week` with today and close the sheet.
- No transitions beyond a 150 ms opacity on the sheet.

- [ ] **Step 1:** A Vitest + Testing Library test `TimeGrid.test.tsx`: renders two calendars' shared event once with two stripes; title font size class gives ≥ 18 px.
- [ ] **Step 2:** FAIL → implement → PASS. Commit `feat(frontend): week, day and 3-day views`.

### Task 13: Month and agenda views

**Files:** Create `frontend/src/calendar/{MonthGrid,Agenda}.tsx` + tests.

- `MonthGrid`: `monthGrid` rows, per day up to 3 entries then "+n"; tapping a day opens the day view for it.
- `Agenda`: today + 14 days, grouped by day ("Heute", "Morgen", then "Sa 7. Nov"), all-day first, time column, colour dots; empty days left out.
- [ ] **Step 1:** Tests: month for 2026-11 starts Mon 2026-10-26 and has 6 rows; agenda groups and labels "Heute"/"Morgen" (de). **Step 2:** FAIL → implement → PASS. Commit `feat(frontend): month and agenda views`.

### Task 14: Settings page

**Files:** Create `frontend/src/pages/SettingsPage.tsx`, `frontend/src/settings/{SourceForm,SourceList,CalendarRow}.tsx`.

- On open, `GET /api/me`; 401 → hub login (via `goToHub`), 403 `parents_only` → "Nur für Eltern" with a back link, `no_access` / `hub_unavailable` as in meal-planer.
- Banner when any source has `last_error`. Per source: name, kind, last sync, error in words (`errors.source_*` in the locales: `source_not_found` "Adresse ungültig oder zurückgesetzt", `source_auth` "Passwort falsch", `source_unreachable` "Nicht erreichbar", `source_invalid` "Kein Kalender unter dieser Adresse"), "Jetzt aktualisieren", rename, change credential, delete (confirm).
- Add Google: name + secret address, with the help text from the spec and "Diese Adresse ist ein Passwort". Add iCloud: name, Apple ID, app-specific password, help text; then the discovered calendars with checkboxes.
- Per calendar: person dropdown (people + "Familie"), colour (own or the person's), visible toggle.
- Family colour. "Sprache und PIN sind im Familien-Hub" with a link. Log out → `goToHubLogout`.
- Saved credentials are never shown: "gespeichert".
- [ ] **Step 1:** Test `SourceForm.test.tsx`: a 422 `source_auth` shows "Passwort falsch" and keeps the form. **Step 2:** FAIL → implement → PASS. Commit `feat(frontend): settings for sources and calendars`.

### Task 15: Docker, CI, e2e and docs

**Files:** Create `backend/Dockerfile` (copy), `docker-compose.yml`, `.github/workflows/{pr-checks,pull-request,ci-cd}.yml`, `.github/dependabot.yml` (copy from meal-planer, drop the worker job), `e2e/` (copy meal-planer's setup: real hub from a `family-hub` checkout on 8130, backend 8100, frontend 3100; plus a static file server on 8140 serving `e2e/fixtures/family.ics`), `e2e/tests/{wall,phone,settings}.spec.ts`, `README.md`, `README_DOCKER.md`.

- `docker-compose.yml`: as meal-planer's, container names `planner-backend` / `planner-frontend`, `DATABASE_URL=sqlite:///./data/planner.db`, `HUB_URL`, `HUB_PUBLIC_URL`, `HUB_APP_KEY=planner`, `DEFAULT_LANGUAGE`, `TZ`, `ENC_KEY_FILE=/run/secrets/enc_key`, `secrets: enc_key: file: ./secrets/enc_key`, `mem_limit: 256m` on the backend, port `${PORT:-8090}:8080`.
- e2e: `wall.spec.ts` (tablet 1180×820): week view shows the fixture's events in Familie colour, "KW" label, switching views, idle return with a shortened `?idle=2000` test hook; `phone.spec.ts`: opens on the agenda; `settings.spec.ts`: Admin logs in at the hub (PIN 1111), adds the Google source with the 8140 URL, maps it to a person, the event takes their colour.
- `README_DOCKER.md`: folders (`docker/familyplanner/{data,secrets}`), `head -c 32 /dev/urandom | base64 > secrets/enc_key` and **keep a copy in the password manager**, PUID/PGID, DSM reverse proxy for `https://kalender.local.<domain>` → `localhost:8090`, the hub tile with key `planner`, iPad setup (Add to Home Screen, Auto-Lock never, Guided Access), where to get the Google secret address and the Apple app-specific password, updates and restore (compose + enc_key + data).
- [ ] **Step 1:** `docker compose build` succeeds; image sizes < 200 MB each (`docker image ls`).
- [ ] **Step 2:** `docker compose up -d` with a test key; `curl localhost:8090/api/config` answers; `docker stats --no-stream planner-backend` < 150 MB.
- [ ] **Step 3:** `cd e2e && npm test` passes. Commit `feat: Docker images, CI, browser tests and NAS docs`.
- [ ] **Step 4:** Measure on the real NAS once deployed: add a Google event, note how many minutes until the wall shows it; write the number into README_DOCKER.md.
