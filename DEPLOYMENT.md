# Deployment Handoff — UC San Diego Passports Visitor Management

## App

- **Name / one-line purpose:** Passports visitor check-in and queue management for UC San Diego Passport Services (CSC and Bookstore locations).
- **Repo:** https://github.com/shark-nado/passports-app — private? Public
- **Image:** `ghcr.io/shark-nado/passports-app` — build workflow status: ✅
- **Stack:** Python/FastAPI + SQLite (aiosqlite), React/Vite SPA served from the same container

## Configuration

| Env var | Purpose | Example (non-secret) | Secret? |
|---|---|---|---|
| `DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:////data/passports.db` | no |
| `JWT_SECRET` | Signing key for auth tokens | — | **yes — install as Secret** |

- **Secrets needed:** `passports-app-secrets` with key `JWT_SECRET` (a random 64-char hex string). Values delivered out-of-band.
- **Persistence:** SQLite database at `/data/passports.db`, expected size 1Gi. Litestream enabled — live DB on node-local `emptyDir`, PVC as replica target.

## Default credentials (seeded on first run)

- CSC location password: `csc1960`
- Bookstore location password: `book1960`

These are seeded into the database on first startup and can be changed after login.

## Ride-along services

None. Single-container app.

## Helm chart

- Location in repo: `chart/`
- `helm lint` + `helm template` pass: yes
- Litestream enabled by default for safe SQLite on NFS storage. Set `litestream.enabled: false` and `persistence.enabled: false` if data persistence isn't needed.

## Access & data

- **Audience:** campus-only (default)
- **Login needed?** yes (location-based JWT auth via password) — no SAML/OAuth; flag to platform team if auth proxy integration is desired
- **Data classification:** P1/P2 only confirmed? yes — visitor names, emails, phone numbers (contact info for passport service appointments; no SSN, no financial data, no health info)

## API reference

| Method | Path | Auth |
|---|---|---|
| POST | `/api/auth/login` | Public |
| POST | `/api/checkin` | Public |
| GET | `/api/visitors` | JWT |
| PATCH | `/api/visitors/:id/status` | JWT |
| PATCH | `/api/visitors/:id/notes` | JWT |
| GET | `/api/visitors/export` | JWT |
| GET | `/api/questions` | Public |
| PUT | `/api/questions` | JWT |
| GET | `/api/stats` | JWT |
| GET | `/api/health` | Public |
| GET | `/events` | JWT (SSE, query param `?token=...&location=...`) |

## Contact

- **Developer / owner:** Ben Pollak (bpollak@ucsd.edu)
- **Best way to reach for review questions:** GitHub issues or email
