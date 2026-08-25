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
2. Set `SECRET_KEY` (a long random string), `DEBUG=False`, `ALLOWED_HOSTS`
   (your backend's domain), and `CORS_ALLOWED_ORIGINS` (your Vercel URL).
3. Install `requirements.txt` and run `python manage.py migrate`.
4. Start command: `gunicorn trust_game.wsgi --bind 0.0.0.0:$PORT` (already
   declared in `backend/Procfile`; most PaaS providers pick it up
   automatically).
5. Static files are served via WhiteNoise — run `python manage.py
   collectstatic` once as part of your deploy step.

See `backend/.env.example` and `frontend/.env.example` for the full list of
environment variables each side reads.

## Installing as an app (PWA)

Open the deployed site on a phone and use the browser's "Add to Home
Screen" — it installs full-screen with no browser chrome on both iOS and
Android. No App Store needed.
