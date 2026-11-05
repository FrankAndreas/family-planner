# family-planner

The family calendar on the wall: the family's Google and iCloud calendars in one week view on an iPad, coloured by
person, and the same calendar on everyone's phone. Self-hosted on a NAS next to the other family apps (family-hub,
family-chore, family-meal-planner, ...), same stack and look. German by default, English as well.

- **One calendar from several:** 2–4 Google calendars through their secret iCal address and 1–2 iCloud accounts
  through CalDAV (app-specific password). Each calendar belongs to a family member (their colour from the hub) or to
  "Familie". An invite that is in two calendars shows once, with both colours.
- **On the wall:** the week, Monday to Sunday, all-day events on top, a line at the current time. Day, 3 days, month
  and agenda are a tap away; after 3 minutes untouched it goes back to this week. No login to look.
- **On the phone:** the same address opens on the agenda: today and the coming two weeks.
- **Read-only:** v1 shows events, it doesn't create or change them.
- **Up to date:** every source is read every 5 minutes; a change in Google or iCloud reaches the wall within about
  10 minutes (Google's feed itself may lag behind).
- **Settings for parents:** add and remove sources, say whose each calendar is, colours, shown or hidden, and see when
  each source last updated. The login is the family hub's.
- **Credentials stay secret:** secret addresses and app passwords are encrypted (AES-256-GCM) with a key of your own,
  never logged and never sent to a browser.
- **Home only:** the planner answers nothing that comes through the Cloudflare tunnel.

Chores, meals and shopping lists live in family-chore and family-meal-planner; clock, weather and the photo frame come
to the family hub ([family-hub#18](https://github.com/FrankAndreas/family-hub/issues/18)).

Design: [docs/superpowers/specs/2026-11-05-family-planner-design.md](docs/superpowers/specs/2026-11-05-family-planner-design.md).
Running it on the NAS: [README_DOCKER.md](README_DOCKER.md).

## Development

```bash
python3 -m venv venv && venv/bin/pip install -r backend/requirements.txt -r tests/requirements.txt
venv/bin/pytest                       # backend tests
mkdir -p secrets && head -c 32 /dev/urandom | base64 > secrets/enc_key
ENC_KEY_FILE=../secrets/enc_key scripts/dev-backend.sh   # API on :8000, logins from a hub on :8086
cd frontend && npm install && npm run dev               # app on :5173, /api forwarded to :8000
cd frontend && npm run lint && npm test                 # frontend checks
# Browser tests: a family-hub checkout next to this repo; the venv needs the hub's packages too
venv/bin/pip install -r ../family-hub/backend/requirements.txt
cd e2e && npm install && E2E_PYTHON=../venv/bin/python npm test
```

The repository is public: tests and docs use invented people and placeholders (`<domain>`, `<NAS_IP>`), never a real
calendar address.

## License

MIT, see [LICENSE](LICENSE).
