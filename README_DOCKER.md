# Deploying the family planner on a Synology NAS (or any Docker system)

The app runs as two containers from images on GitHub Container Registry (GHCR):

- **backend** (`ghcr.io/frankandreas/family-planner/backend`): the API and the calendar sync, with the SQLite database
  and its backups in `./data`
- **frontend** (`ghcr.io/frankandreas/family-planner/frontend`): nginx serving the app on port 8080 inside the
  container, forwarding `/api` to the backend

It sits next to the other family apps on one NAS (budget 8081, job tracking 8082, chores 8084, meal planner 8085,
hub 8086, planner **8090**). The DS720+ is x86-64; the images are linux/amd64. The backend is capped at 256 MB and uses
about 80 MB.

## Prerequisites

- A Synology NAS with **Container Manager** (DSM 7.2 or later) and SSH access.
- The family hub (FrankAndreas/family-hub) running, with HTTPS at home (`https://home.local.<domain>`).
- If the repository or its packages are private, a GitHub token with `read:packages` (`sudo docker login ghcr.io`).

## Installation

1. **Choose the user the app runs as:** the DSM user of the other family apps, e.g. `id familyapps` →
   `uid=1031 gid=100`. Without one, the image's own user (999:999).
2. **Prepare the folder** `/volume1/docker/family-planner`, upload `docker-compose.yml` into it **renamed to
   `compose.yaml`**, and create the data folder for that user:
   ```bash
   cd /volume1/docker/family-planner
   sudo mkdir -p data secrets
   sudo chown -R 1031:100 data
   ```
3. **Make the encryption key.** The calendar credentials are encrypted with it:
   ```bash
   head -c 32 /dev/urandom | base64 | sudo tee secrets/enc_key > /dev/null
   sudo chown 1031:100 secrets/enc_key && sudo chmod 400 secrets/enc_key
   sudo cat secrets/enc_key    # copy it into your password manager
   ```
   **Keep a copy outside the NAS.** Without it, a restored database can't read its stored addresses and passwords
   (each source then shows "Der gespeicherte Zugang lässt sich nicht lesen" until it is entered again). Without the
   file the backend doesn't start, and its log says why.
4. **Create `.env`:**
   ```bash
   printf 'PUID=1031\nPGID=100\nPORT=8090\nHUB_URL=http://<NAS_IP>:8086\nHUB_PUBLIC_URL=https://home.local.<domain>\nHUB_APP_KEY=kalender\nALLOWED_HOSTS=kalender.local.<domain>\n' | sudo tee .env
   sudo chmod 600 .env
   ```
   `HUB_APP_KEY` is the planner's key in the family hub: the hub tile's **App-Schlüssel** must be exactly the same
   (see "The family hub" below). `ALLOWED_HOSTS` lists the names the planner answers under. Any other name gets nothing, so a web page opened at
   home can't point a name of its own at the NAS and read the calendar (the wall needs no login).
5. **Start it:** `sudo docker-compose pull && sudo docker-compose up -d` (or as a Project in Container Manager).

## HTTPS at home (needed)

The family hub's login cookie only reaches addresses under `local.<domain>`, so the planner needs one too:

1. **DNS:** `kalender.local.<domain>` points to the NAS's LAN IP (give the NAS a fixed IP in the router).
2. **Control Panel → Login Portal → Advanced → Reverse Proxy → Create:** source HTTPS, `kalender.local.<domain>`,
   port 443, **Enable HSTS**; destination HTTP, `localhost`, port 8090.
3. **Certificate:** the `*.local.<domain>` certificate the hub uses covers it (Control Panel → Security → Certificate →
   Settings: assign it to the new entry).

**Never** add a Cloudflare tunnel route or a router port forward for the planner: it is for the home network only, and
answers nothing that comes through the tunnel.

## The family hub

In the hub's **Einstellungen → Apps**, add a tile for the planner:

- **Adresse:** `https://kalender.local.<domain>`
- **App-Schlüssel:** `kalender`, exactly the value of `HUB_APP_KEY` in the planner's `.env`. The planner asks the hub
  "may this person use the app `kalender`?", and the hub answers yes only for the tile with that key.
- **Personen:** tick everyone. Only the people ticked here appear in the planner (to give calendars to), and only the
  ticked parents can open its settings.

Viewing needs no login; only parents open the settings, after logging in at the hub. People, their colours and
languages come from the hub.

**"Du hast keinen Zugang zum Familienkalender"** in the settings, even as a parent, means the hub found no tile for the
planner's key, or you aren't ticked on it. Check that the tile's App-Schlüssel and `HUB_APP_KEY` are the same (a
change to `.env` needs `sudo docker-compose up -d backend`), and that you are ticked. The planner remembers the hub's
answer for about a minute, so reload once more after that.

## Adding calendars

Open **⚙ Einstellungen → Quelle hinzufügen** as a parent.

- **Google:** Google Calendar on the web → Settings → the calendar → **Integrate calendar** → **Secret address in iCal
  format**. Paste it in. It is a password: anyone with it sees every event. Resetting it in Google stops the old one.
  It exists only for calendars you own or can manage.
- **iCloud:** account.apple.com → **Sign-In and Security** → **App-Specific Passwords** → create one for the planner.
  Enter the Apple ID and that password (the normal Apple ID password is refused). Then tick the calendars to show; a
  calendar someone else shared is read through the Apple ID that accepted the share.

Then say whose each calendar is (or "Familie"). Each source shows when it last updated, and in words what went wrong;
a failing source keeps its last events, and the wall shows a small ⚠.

## The wall iPad

1. Safari → `https://kalender.local.<domain>/display` → **Share → Add to Home Screen**, so it opens full screen.
2. **Settings → Display & Brightness → Auto-Lock: Never**; keep it on power.
3. **Settings → Accessibility → Guided Access**, to keep it on the planner.

Later a Raspberry Pi with a touch screen: Chromium in kiosk mode on the same `/display` address.

**When the NAS is off** (an update, a restart, a power cut): leave the iPad on the page. It keeps showing the last
loaded week with "zuletzt aktualisiert HH:MM" and picks up again by itself once the NAS answers. Once a night, around
03:00, the wall reloads itself to get a new version, but only when the NAS answers, so it never ends up on Safari's
error page.

## Updating, backups, restore

- **Update:** automatically with `nas-update.sh` (below), or by hand: `sudo docker-compose pull && sudo docker-compose
  up -d`. Migrations run at start, after an automatic backup (`data/backups/planner-before-migration-*.db`).
- **Backups:** every night after 03:00 to `data/backups/planner-nightly-*.db`, the newest 14 kept. Hyper Backup on
  `docker/family-planner` covers them.
- **Restore:** `compose.yaml` + `.env` + `secrets/enc_key` + the `data` folder, on any Docker host.

## Automatic updates

`scripts/nas-update.sh` works as in the other family apps: it pulls the images and, if there is a new one, backs up
the database to `db-backups/`, keeps the old images as `:previous`, restarts and waits until the backend is healthy
(`logs/update.log`).

1. Copy `scripts/nas-update.sh` into `/volume1/docker/family-planner` and make it executable (or let
   `scripts/deploy-nas.sh` upload it):
   ```bash
   sudo chmod +x /volume1/docker/family-planner/nas-update.sh
   sudo /volume1/docker/family-planner/nas-update.sh     # should end with "Up to date" or "Update complete"
   ```
2. **Control Panel → Task Scheduler → Create → Scheduled Task → User-defined script**: user **root**, daily a few
   minutes apart from the other apps (not at 03:00, when the planner makes its own nightly backup), command
   `bash /volume1/docker/family-planner/nas-update.sh`.

To deploy right away from your computer:
```bash
cp .deploy.env.example .deploy.env   # once; then set NAS_HOST and NAS_DIR
scripts/deploy-nas.sh
```

### Rolling back an update

First **disable the scheduled task**, otherwise the next night installs the same version again. Then:

```bash
cd /volume1/docker/family-planner
sudo docker tag ghcr.io/frankandreas/family-planner/backend:previous ghcr.io/frankandreas/family-planner/backend:latest
sudo docker tag ghcr.io/frankandreas/family-planner/frontend:previous ghcr.io/frankandreas/family-planner/frontend:latest
sudo docker stop planner-backend
# Only if the new version changed the database: put the backup from before the update back
sudo rm -f data/planner.db-wal data/planner.db-shm
sudo sh -c 'gunzip -c db-backups/planner-YYYYMMDD-HHMMSS.sqlite.gz > data/planner.db'
sudo docker-compose up -d backend frontend
```

## How fast changes arrive

Every source is read every 5 minutes. Google may serve its secret-address feed with a delay of its own; measured on
the NAS after deploying: _not measured yet_.
