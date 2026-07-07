# UC San Diego Passports Visitor Management

Visitor check-in and queue management for UC San Diego Passport Services.
Built with React + Decorator 5 + FastAPI + SQLite.

## Quick Start

```bash
# Backend
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
export JWT_SECRET="$(openssl rand -hex 32)"
export LOCATION_CSC_PASSWORD_HASH="$(printf '%s\n' "$NEW_CSC_PASSWORD" | python -m backend.manage_passwords hash --password-stdin)"
export LOCATION_BOOKSTORE_PASSWORD_HASH="$(printf '%s\n' "$NEW_BOOKSTORE_PASSWORD" | python -m backend.manage_passwords hash --password-stdin)"
uvicorn backend.app:app --reload --port 8000

# Frontend (in another terminal)
npm install
npm run dev
```

Open http://localhost:5173

Local frontend development uses the Vite `/api` proxy to reach the backend.
Production CORS headers and rate limiting are handled at ingress.

## Admin Passwords

No default dashboard passwords are created. The app fails startup unless
`JWT_SECRET`, `LOCATION_CSC_PASSWORD_HASH`, and
`LOCATION_BOOKSTORE_PASSWORD_HASH` are supplied. The location password hash
secrets are the source of truth; on startup the app writes those hashes into
the location rows.

Generate hashes out of band:

```bash
printf '%s\n' "$NEW_CSC_PASSWORD" | \
  python -m backend.manage_passwords hash --password-stdin

printf '%s\n' "$NEW_BOOKSTORE_PASSWORD" | \
  python -m backend.manage_passwords hash --password-stdin
```

For Kubernetes, put the generated values in the required Secret object:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: passports-app-secrets
type: Opaque
stringData:
  JWT_SECRET: "<random 32+ byte secret>"
  LOCATION_CSC_PASSWORD_HASH: "<bcrypt hash>"
  LOCATION_BOOKSTORE_PASSWORD_HASH: "<bcrypt hash>"
```

To rotate dashboard passwords, update `LOCATION_CSC_PASSWORD_HASH` and
`LOCATION_BOOKSTORE_PASSWORD_HASH` in that Secret and restart the deployment.

## Tech Stack

- **Frontend**: React 18, Vite, Decorator 5 (Bootstrap 3 CDN)
- **Backend**: FastAPI (Python), SQLAlchemy, SQLite
- **Auth**: bcrypt + JWT
- **Updates**: dashboard polling
- **Deployment**: Docker multi-stage build

## Structure

```
src/              React application
  components/
    chrome/       Decorator 5 page shell
    kiosk/        Public check-in flow
    dashboard/    Staff dashboard
  context/        Global state
  hooks/          useIdleTimer, polling helpers
  services/       API client, translations
backend/          FastAPI application
  backend/        Python package
    app.py        Routes and API
    models.py     SQLAlchemy models
    auth.py       JWT + password hashing
    seed.py       Database seeding
```

## API Endpoints

| Method | Path | Auth |
|---|---|---|
| POST | /api/auth/login | Public |
| POST | /api/checkin | Public |
| GET | /api/visitors | JWT |
| PATCH | /api/visitors/:id/status | JWT |
| PATCH | /api/visitors/:id/notes | JWT |
| GET | /api/visitors/export | JWT |
| GET | /api/questions | Public |
| PUT | /api/questions | JWT |
| GET | /api/stats | JWT |

## Docker

```bash
docker build -t passports-app .
docker run --env-file .env -p 8000:8000 -v ./passports.db:/app/passports.db passports-app
```
