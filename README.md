# The Trust Gambit

A strategic delegation game played in small groups ("lobbies"). Each round
poses a question, and every participant chooses to:

- **Solve** it themselves — correct answer: **+1**, wrong: **−1**.
- **Delegate** it to someone else in the lobby, betting on them — you get
  `λ × their score` if they end up positive, or `their score ÷ λ` (a harsher
  penalty) if they end up negative. Delegation chains compound recursively.
- **Pass** — 0 points, no risk.

Delegation cycles (A → B → A) are penalized flat (**−1** to everyone in the
loop). Anyone who ends up net-positive also earns a reputation bonus —
`β × (number of people who delegated to them)` — so being trusted pays.
Scores accumulate per game on a lobby-scoped leaderboard, and each round's
delegations can be viewed as a graph.

## Stack

- **Backend** — Django + Django REST Framework, token auth. SQLite locally,
  Postgres in production.
- **Frontend** — React 19 + Vite + Tailwind CSS 4 + React Router +
  Cytoscape.js (delegation graph). Installable as a PWA on iOS/Android.

```
backend/    Django project (game/ app holds models, scoring, views)
frontend/   React app (src/pages/ has one file per route)
```

## Local development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Serves the API at `http://localhost:8000`. Copy `.env.example` to `.env` to
override any setting locally (defaults work out of the box with SQLite).

To actually see a game in the UI, create an admin user and seed a `Game`,
`Domain`, `Lobby` and `Round` via `/admin/` (`python manage.py
createsuperuser` first), then assign participants to that lobby.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Serves the app at `http://localhost:5173`, pointed at `localhost:8000` by
default. Copy `.env.example` to `.env.local` to point it at a different
backend.

## Deployment

### Frontend → Vercel

1. Import this repo into Vercel.
2. **Project Settings → General → Root Directory**: set to `frontend` (this
   is a monorepo, so Vercel needs to know where the app lives).
3. Framework preset auto-detects as Vite — build command `npm run build`,
   output directory `dist` (no changes needed).
4. Add an environment variable: `VITE_API_BASE_URL` = your deployed
   backend's URL + `/api` (e.g. `https://trust-gambit-api.onrender.com/api`).
5. Deploy. `frontend/vercel.json` already handles client-side routing (so
   direct links like `/leaderboard` don't 404) and sets no-cache headers on
   the service worker/manifest so PWA updates roll out promptly.

### Backend → Render / Railway / Fly.io

Vercel's serverless model doesn't fit this app well — SQLite needs a
persistent disk and gunicorn expects a long-running process — so deploy the
Django API to a normal host instead:

1. Provision a Postgres database and set `DATABASE_URL` to its connection
   string.
2. Set these environment variables:
   - `SECRET_KEY` — a long random string
   - `DEBUG` — `False`
   - `ALLOWED_HOSTS` — your backend's **bare domain only** (no `https://`,
     no trailing slash), e.g. `trust-gambit-api.onrender.com`. A mismatch
     here makes Django reject every request with an opaque `400 Bad
     Request`, so this is the first thing to check if nothing works.
   - `CORS_ALLOWED_ORIGINS` — your Vercel URL, e.g.
     `https://trust-gambit.vercel.app` — **no trailing slash or path**, or
     `django-cors-headers` fails a startup check and the deploy won't boot.
   - Optionally `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` — if
     all three are set, an admin account is created automatically on
     startup (see below).
3. Build command: `pip install -r requirements.txt && python manage.py
   collectstatic --noinput`.
4. Start command: `python manage.py migrate && (python manage.py
   createsuperuser --noinput || true) && gunicorn trust_game.wsgi --bind
   0.0.0.0:$PORT` — run `migrate` (and the superuser bootstrap) here
   explicitly rather than relying on `backend/Procfile`'s separate
   `release:`/`web:` lines, since providers with an explicit Start Command
   field (Render included) don't run Heroku-style release phases or use
   the `Procfile` at all once you've overridden it.
5. `backend/runtime.txt` pins Python to 3.12 — Django 4.2 and
   `psycopg2-binary` don't yet support the newer Python versions some
   providers default to (e.g. Render moved to 3.14), which fails with a
   `psycopg2 or psycopg module` import error at boot if left unpinned.

**Creating the first admin account:** if your plan doesn't include shell
access (e.g. Render's free tier), set `DJANGO_SUPERUSER_USERNAME`,
`DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` as environment
variables — `backend/Procfile`'s start command creates that account
automatically on boot if it doesn't already exist yet (and does nothing on
later deploys once it does, so it's safe to leave those variables set
permanently). Log in at `/admin/` with those credentials to create the
`Game`, `Domain`, `Lobby`, and `Round` records the game needs.

See `backend/.env.example` and `frontend/.env.example` for the full list of
environment variables each side reads.

## Installing as an app (PWA)

Open the deployed site on a phone and use the browser's "Add to Home
Screen" — it installs full-screen with no browser chrome on both iOS and
Android. No App Store needed.
