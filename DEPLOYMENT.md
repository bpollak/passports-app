# Deployment Handoff — UC San Diego Passports Visitor Management

## App

- **Name / one-line purpose:** Passports visitor check-in and queue management for UC San Diego Passport Services (CSC and Bookstore locations).
- **Repo:** https://github.com/dominicfeliton/passports-app — private? Public
- **Image:** `ghcr.io/dominicfeliton/passports-app` — build workflow status: ✅
- **Stack:** Python/FastAPI + SQLite (aiosqlite), React/Vite SPA served from the same container

## Configuration

| Env var | Purpose | Example (non-secret) | Secret? |
|---|---|---|---|
| `DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:////data/passports.db` | no |
| `JWT_SECRET` | Signing key for auth tokens | — | **yes — install as Secret** |
| `LOCATION_CSC_PASSWORD_HASH` | CSC dashboard bcrypt password hash | — | **yes — install as Secret** |
| `LOCATION_BOOKSTORE_PASSWORD_HASH` | Bookstore dashboard bcrypt password hash | — | **yes — install as Secret** |
| `CORS_ALLOW_ORIGINS` | Optional comma-separated allowed browser origins | `https://passports.apps.ucsd.edu` | no |

- **App Secret needed:** `passports-app-secrets` with keys `JWT_SECRET`, `LOCATION_CSC_PASSWORD_HASH`, and `LOCATION_BOOKSTORE_PASSWORD_HASH`. Values delivered out-of-band.
- **TLS Secret needed:** `passports.apps.ucsd.edu` with `tls.crt` and `tls.key`, or provision that secret through the cluster TLS/cert-manager flow.
- **Persistence:** SQLite database at `/data/passports.db`, expected size 1Gi. Litestream enabled — live DB on node-local `emptyDir`, PVC as replica target.

## Dashboard credentials

No public default passwords are seeded. The app fails startup unless
`JWT_SECRET`, `LOCATION_CSC_PASSWORD_HASH`, and
`LOCATION_BOOKSTORE_PASSWORD_HASH` are supplied. The two location password
hashes are the source of truth; on startup the app writes those hashes into
the location rows. Generate bcrypt hashes with:

```bash
printf '%s\n' "$NEW_CSC_PASSWORD" | \
  python -m backend.manage_passwords hash --password-stdin

printf '%s\n' "$NEW_BOOKSTORE_PASSWORD" | \
  python -m backend.manage_passwords hash --password-stdin
```

Then expose them to the pod with the required Secret object:

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

To rotate dashboard passwords, update the bcrypt hash values in
`passports-app-secrets` and restart the deployment:

```bash
kubectl -n tai-passport apply -f passports-app-secrets.yaml
kubectl -n tai-passport rollout restart deploy/passports-app
```

Do not store plaintext dashboard passwords in Helm values, ConfigMaps, or the
repository.

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

## Contact

- **Developer / owner:** Ben Pollak (bpollak@ucsd.edu)
- **Best way to reach for review questions:** GitHub issues or email
