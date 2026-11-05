# MoMo Loop: Closing the Cash-Out Boundary

Hackathon MVP — a data-driven merchant acceptance intelligence dashboard for MTN MoMo.

Identifies **probable cash-out boundaries** (inflow → cash-out within 30 minutes), finds acceptance gaps, and ranks where expanding MoMo merchant acceptance would retain the most digital value.

**Demo script:** see [DEMO.md](./DEMO.md)

## Stack

| Layer | Tech |
| --- | --- |
| Frontend | React + Vite, Recharts, Leaflet |
| Backend | Python + FastAPI (also serves the built UI in production) |
| Auth | JWT + role-based access |
| Database | PostgreSQL (users, scenarios, pipeline, audit, txs, merchants, locations, snapshots) |
| Analytics | Pandas + NetworkX on Postgres-backed frames |
| Jobs | APScheduler nightly rematerialise (02:00 UTC) |

## Seeded accounts (demo)

| Email | Password | Role | Access |
| --- | --- | --- | --- |
| `viewer@mtn.demo` | `viewer123` | Viewer · Gauteng | Overview + boundaries (Gauteng only) |
| `analyst@mtn.demo` | `analyst123` | Analyst · Western Cape | Ranking/simulator scoped to WC |
| `lead@mtn.demo` | `lead123` | Acquisition lead · National | Full SA + scenarios/pipeline |
| `admin@mtn.demo` | `admin123` | Admin · National | + users, refresh, CSV import |

## Hosting (Render — recommended for judges)

Single public URL: Docker image runs API + React UI; Render free Postgres stores everything.

1. Push this repo to GitHub (or GitLab).
2. Open [Render Blueprint](https://dashboard.render.com/select-repo?type=blueprint) and select the repo (`render.yaml`).
3. After deploy, set env on the **momo-loop** web service:
   - `CORS_ORIGINS` = your public URL, e.g. `https://momo-loop.onrender.com`
   - Confirm `DATABASE_URL` was injected from the Blueprint database
4. Open the service URL → login as `lead@mtn.demo` / `lead123`

Cold starts on the free plan can take ~30–60s after idle.

### Local production smoke-test

```bash
docker compose -f docker-compose.prod.yml up --build
```

App: http://127.0.0.1:8080 · API docs: http://127.0.0.1:8080/docs

## Local development

### 1. Start Postgres

**Option A — Docker**

```bash
docker compose up -d
```

**Option B — local Postgres** with user/db matching `backend/.env`.

```bash
cp backend/.env.example backend/.env
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python data/generate_data.py   # already generated; re-run to refresh CSVs
python -m app.seed             # create tables + demo users
uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://127.0.0.1:5173

Routed pages: `/login`, `/overview`, `/boundaries`, `/opportunities`, `/pipeline`, `/simulate`, `/users`

Admin extras:
- **Batch CSV upload** for `transactions` / `merchants` / `locations`
- **Export CSV / PDF** from Opportunity ranking
- **Refresh analytics** (rematerialises opportunity snapshots)

## Important caveats (for judges)

- Cash-out after inflow is a **signal**, not proof a merchant rejected MoMo.
- Recoverable value is **modelled** under stated assumptions — not MTN revenue.
- Dataset is **synthetic**; planted acceptance gaps exist to evaluate ranking quality.
