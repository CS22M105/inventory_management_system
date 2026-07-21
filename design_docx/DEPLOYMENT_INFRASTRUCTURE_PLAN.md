# Deployment & Infrastructure Plan (Phase 3)

Date: July 8, 2026

Project: Katz Nursing School Inventory Management System (going to market as a product)

## Purpose

This document is the third step toward a safe public deployment. Phase 1
(`SECURITY_AND_AUTH_PLAN.md`) hardened authentication, sessions, CSRF, and rate
limiting; Phase 2 (`DATA_MIGRATIONS_RELIABILITY_PLAN.md`) made the data layer
production-grade (Alembic migrations, real `DATE`, indexes + pagination). Both
are code-complete; the only items they left open are deploy-time:
HTTPS/HSTS (security Step E) and automated backups (data Step I).

Phase 3 turns the tested application into a **running, reachable service**: a
managed host with a custom domain and a managed PostgreSQL database, real secret
management and production config, efficient static-asset serving and Gunicorn
tuning, and a CI/CD pipeline so deploys are tested and repeatable instead of
manual. As in the earlier plans, every improvement is broken into small,
independently testable substeps with `Files:` / `Add:` / `Verify:` sections, and
each substep should get a dated `PROGRESS_REPORT.md` entry before moving on.

This plan does **not** require splitting `app.py` into blueprints or changing the
application architecture. It is about hosting, configuration, and delivery.

---

## Product context and locked decisions

The earlier decisions still hold (single-tenant, one database per customer,
email + password, invite-only, raw `psycopg2`, Alembic migrations). Phase 3 adds
these infrastructure decisions:

```text
Hosting model:   Managed PaaS (e.g. Render / Railway / Fly.io / Heroku) OR a
                 single small VM behind a reverse proxy. Either way: ONE app
                 process group + ONE managed Postgres per customer (single-tenant).
Database:        MANAGED PostgreSQL (provider-run backups + PITR) — not a
                 self-installed DB on the app host.
TLS:             Terminated by the platform/reverse proxy (managed certificate).
                 The app runs behind that proxy and trusts X-Forwarded-* headers.
Schema on deploy: `alembic upgrade head` runs ONCE per release (already wired in
                 the Procfile release phase), before the new app serves traffic.
Secrets:         Live only in the platform's secret store / env vars, never in
                 git. `.env` is for local dev only.
Static assets:   Served by WhiteNoise from the app (small deployment) with long
                 cache headers; a CDN can sit in front later if needed.
```

---

## Current deployment behavior (the starting point)

What already exists in the repo:

```text
Procfile
    release: alembic upgrade head        # migrations run once per deploy (Phase 2 F4)
    web: gunicorn app:app -c gunicorn.conf.py

app.py config
    APP_ENV        = os.environ["APP_ENV"] (default "development")
    SECRET_KEY     = os.environ["SECRET_KEY"]  (no default)
    - In production, the app REFUSES to start without SECRET_KEY:
        if APP_ENV == "production" and not SECRET_KEY: raise RuntimeError(...)
    - But it still falls back to the literal "dev-secret-key-change-before-
      production" when APP_ENV != production.
    SESSION_COOKIE_SECURE = (APP_ENV == "production")   # Secure cookies in prod
    SESSION_COOKIE_HTTPONLY / SAMESITE already set.

.env.example
    Documents APP_ENV, SECRET_KEY, DATABASE_URL, APP_BASE_URL, BARCODE_PREFIX,
    and the SMTP/email variables.

requirements.txt
    Flask, Flask-WTF, psycopg2-binary, gunicorn, qrcode[pil], Flask-Limiter,
    alembic, pytest.  (No WhiteNoise yet — added in Step L.)
```

Problems this phase fixes:

```text
1. No real host / domain / managed database.
   The app only runs on a local dev server. It is not reachable from anywhere,
   has no uptime, and any local Postgres has no managed backups.

2. Secrets are not managed for production.
   There is a dev fallback SECRET_KEY in the code. If APP_ENV were ever left as
   "development" in a deployed environment, session cookies and invite/reset
   tokens would be signed with a publicly known key and could be forged. There
   is no documented secret-provisioning process.

3. Single-process Gunicorn, app-served static files.
   `gunicorn app:app` uses one worker with default timeouts and lets Flask serve
   static files. That will not handle concurrent real users well and wastes app
   workers on static requests.

4. No CI/CD.
   Tests (54 of them) exist but nothing runs them automatically, and deploys are
   manual. A single-file app is easy to deploy wrong (missed migration, missing
   env var, untested commit).
```

---

## Status of the Phase 3 items

| # | Improvement | Priority | Effort | Plan step |
|---|-------------|----------|--------|-----------|
| 1 | Managed hosting + custom domain + managed Postgres | Critical | M | Step J |
| 2 | Secrets management; strong `SECRET_KEY`; `APP_ENV=production` | Critical | S | Step K (do first) |
| 3 | Serve static via WhiteNoise/CDN + tune Gunicorn workers/timeouts | Medium | S | Step L |
| 4 | CI/CD pipeline (GitHub Actions: test then deploy) | Medium | M | Step M |

Cross-references (owned by earlier plans, completed at deploy here):

```text
Security Step E — HTTPS/TLS + HSTS   -> finalized as part of Step J3 (domain/TLS).
Data Step I     — Backups + PITR     -> provisioned as part of Step J1 (managed DB).
```

---

## External dependencies to secure before launch

```text
A hosting account (Render / Railway / Fly.io / Heroku, or a VM + Nginx/Caddy).
A managed PostgreSQL instance with automated backups + PITR enabled.
A registered domain name + DNS control (to point records at the host).
A transactional email provider (already planned in Phase 1) with prod credentials.
A GitHub repository with Actions enabled and repo/environment secrets configured.
```

---

## Recommended execution order

Config hardening is cheap and is a prerequisite for a safe first deploy, so it
comes first. Hosting provisioning (which also finalizes TLS and backups) follows,
then serving performance, then the automation that ties it together.

```text
Step K  Secrets management + production config          [do first, prerequisite]
Step J  Managed hosting + domain + managed Postgres      (also finalizes E + I)
Step L  WhiteNoise static serving + Gunicorn tuning
Step M  CI/CD pipeline (GitHub Actions: test -> deploy)  [last; automates the rest]
```

---

## Step K — Secrets management; strong SECRET_KEY; APP_ENV=production

Effort: S. Cheap, high-impact, and a prerequisite for deploying safely. Split
into three substeps (K1–K3).

### Substep K1 — Provision and store production secrets

Files:

```text
(no app code) — platform secret store / environment configuration
.env.example                 (document the full required set, values redacted)
```

Add:

```text
Generate a strong SECRET_KEY (e.g. `python -c "import secrets; print(secrets.token_urlsafe(64))"`).
Set these in the PLATFORM secret store (never in git), for the production env:
    APP_ENV=production
    SECRET_KEY=<64+ char random>
    DATABASE_URL=<managed Postgres connection string>   (from Step J1)
    APP_BASE_URL=https://<your-domain>
    EMAIL_PROVIDER + EMAIL_FROM + SMTP_* (production email credentials)
    BARCODE_PREFIX (per customer, optional)
    Any Phase-1/2 tunables you want to override (SESSION_IDLE_MINUTES,
        LOGIN_MAX_ATTEMPTS, RATELIMIT_*, TRANSACTIONS_PAGE_SIZE).
Confirm .env is gitignored; keep .env.example as the redacted template.
```

Verify:

```text
The platform shows every required variable set for the production environment.
No secret value appears in git history or in alembic.ini.
`.env` is listed in .gitignore.
```

### Substep K2 — Enforce production config in the app

Files:

```text
app.py
```

Add:

```text
Harden the existing production guard so a deploy cannot run with an insecure key:
    - Already: raise if APP_ENV == "production" and SECRET_KEY is unset.
    - Add: in production, ALSO refuse to start if SECRET_KEY equals the known dev
      fallback ("dev-secret-key-change-before-production") or is too short.
Confirm the production security posture is on when APP_ENV=production:
    - SESSION_COOKIE_SECURE = True (already), HTTPONLY = True, SAMESITE set.
    - Flask-Limiter enabled; RATELIMIT_STORAGE_URI points at a shared store
      (Redis) if more than one worker/host is used (see the Phase 1 Step D note).
Optionally add a tiny `flask check-config` CLI that prints which required vars are
    set (names only, never values) so operators can self-verify a deploy.
```

Verify:

```text
With APP_ENV=production and no SECRET_KEY -> app refuses to start (existing).
With APP_ENV=production and the dev fallback key -> app refuses to start (new).
With a proper key -> app starts; session cookies are marked Secure.
py_compile clean; the existing pytest suite still passes.
```

### Substep K3 — Document the config contract

Files:

```text
README.md            (Production Configuration section — extend)
.env.example
```

Add:

```text
List REQUIRED vs OPTIONAL environment variables in one place, with a one-line
    description and whether it is a secret.
Document that DATABASE_URL is shared by the app AND Alembic (migrations/env.py).
Document the "rotate SECRET_KEY = invalidate all sessions + pending invite/reset
    links" consequence (tokens are signed with it).
```

Verify:

```text
A new operator can bring up a correct production environment using only README +
    .env.example, with no secrets committed.
```

---

## Step J — Managed hosting + custom domain + managed Postgres

Effort: M. This makes the app reachable with real uptime and moves the database
onto managed infrastructure with backups. It also finalizes the two deploy-time
items left by earlier phases: HTTPS/HSTS (security Step E) and backups/PITR (data
Step I). Split into four substeps (J1–J4).

### Substep J1 — Provision managed PostgreSQL (with backups + PITR)

Files:

```text
(no app code) — provider console / infrastructure config
DATA_MIGRATIONS_RELIABILITY_PLAN.md   (this satisfies Step I; note it there)
```

Add:

```text
Create a managed PostgreSQL instance (RDS/Aurora, Cloud SQL, Azure DB, Neon,
    Supabase, or the PaaS's own Postgres add-on).
Enable automated daily backups AND point-in-time recovery (WAL). Set a retention
    window (e.g. 7-30 days) and confirm backups are stored OFF the app host.
Capture the connection string as DATABASE_URL (Step K1). Require TLS (sslmode).
Record a short RESTORE RUNBOOK: how to restore to a new instance / to a point in
    time, who runs it, and the expected RTO/RPO.
```

Verify:

```text
The provider dashboard shows automated backups + PITR enabled with a retention
    window.
A restore DRILL succeeds on a scratch/restored instance (not the primary): pick a
    timestamp, restore, and confirm the schema + a known row are present.
The app can connect to the managed DB over TLS using DATABASE_URL.
```

### Substep J2 — Configure the app for the platform

Files:

```text
Procfile                     (already: release + web)
runtime/entrypoint           (platform-specific, if not using Procfile)
gunicorn.conf.py             (new; see Step L for tuning)
```

Add:

```text
Confirm the release phase runs migrations before traffic:  `alembic upgrade head`
    (already in the Procfile). The web process is `gunicorn app:app` (tuned in L).
Bind Gunicorn to the platform port: `gunicorn app:app --bind 0.0.0.0:$PORT`
    (or set `bind` in gunicorn.conf.py). Many PaaS platforms inject $PORT.
Ensure the app reads all config from the environment (it does) — no file writes
    required at runtime except transient (QR PNGs are generated in-memory).
```

Verify:

```text
A clean deploy to an EMPTY managed DB: release runs migrations to head, then the
    web process boots and serves.
A redeploy with no new migrations: release is a safe no-op; app serves.
The running app answers on the platform URL (pre-domain), login page returns 200.
```

### Substep J3 — Custom domain + TLS + HSTS (finalizes security Step E)

Files:

```text
DNS records (provider)
Reverse proxy / platform TLS settings
app.py                       (ProxyFix + HSTS, if not handled entirely by the proxy)
```

Add:

```text
Point the custom domain at the host (CNAME/A per provider) and issue a managed
    TLS certificate (Let's Encrypt / platform-managed).
Redirect all HTTP -> HTTPS at the proxy/platform.
Because the app runs behind a TLS-terminating proxy, wrap the WSGI app with
    werkzeug ProxyFix so it honors X-Forwarded-Proto/Host (correct https:// URLs
    and Secure-cookie behavior).
Send HSTS (Strict-Transport-Security) once HTTPS is confirmed working — via the
    proxy or a small after_request header in the app.
Set APP_BASE_URL=https://<domain> so QR links are absolute and correct.
```

Verify:

```text
http://<domain> redirects to https://<domain>.
The certificate is valid; the browser shows a secure connection.
Response carries a Strict-Transport-Security header.
Session cookies are marked Secure; QR codes encode https://<domain>/... URLs.
Update SECURITY_AND_AUTH_PLAN.md: Step E (HTTPS/HSTS) is now DONE.
```

### Substep J4 — First production bootstrap + smoke test

Files:

```text
(operational runbook) — README / deploy notes
```

Add:

```text
On first deploy, the schema is created by migrations (release phase). Seed the
    FIRST administrator WITHOUT shipping demo passwords:
    - create the admin row, then use `flask set-password <email> <password>` once,
      or send an invite and set the password via the emailed link.
    - Do NOT run `flask init-db` against the managed DB (it is for local dev only;
      production schema is owned by migrations — see Phase 2 F4).
Run a manual smoke test of the critical paths on the live domain.
```

Verify:

```text
Admin can log in over HTTPS; a student/faculty invite email is delivered and the
    set-password link works end to end.
Create item -> print QR label -> scan on a phone -> stock add/remove works.
Transactions list + CSV export work; pagination controls work.
No demo/default credentials remain enabled.
```

---

## Step L — Serve static assets via WhiteNoise/CDN + tune Gunicorn

Effort: S. Makes the single deployment handle concurrent users and stop wasting
app workers on static files. Split into two substeps (L1–L2).

### Substep L1 — WhiteNoise for static assets

Files:

```text
requirements.txt             (add whitenoise)
app.py                       (wrap the WSGI app with WhiteNoise)
```

Add:

```text
Add whitenoise to requirements.txt and install it.
Wrap the app to serve everything under static/ with compression and far-future
    cache headers, e.g.:
        from whitenoise import WhiteNoise
        app.wsgi_app = WhiteNoise(app.wsgi_app, root="static/", prefix="static/")
    (or the Flask-integration form). Keep template rendering unchanged.
Optionally put a CDN in front of the domain later; WhiteNoise's cache headers make
    that a drop-in improvement, not a code change.
```

Verify:

```text
static/css/*.css and JS load with a 200 and long Cache-Control headers.
Static requests do not appear to consume app DB connections/workers.
All pages still render with correct styles (no broken asset paths).
```

### Substep L2 — Tune Gunicorn

Files:

```text
gunicorn.conf.py             (new)
Procfile                     (web: gunicorn app:app -c gunicorn.conf.py)
```

Add:

```text
Create gunicorn.conf.py with production-sane values, all overridable by env:
    bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
    workers = int(os.environ.get("WEB_CONCURRENCY", 2 * cpu_count + 1))
    threads = int(os.environ.get("GUNICORN_THREADS", "2"))   # I/O-bound app
    timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
    graceful_timeout = 30
    max_requests = 1000; max_requests_jitter = 100            # recycle workers
    accesslog = "-"; errorlog = "-"                           # log to stdout/stderr
Point the Procfile web line at this config file.
Note: with >1 worker, Flask-Limiter's in-memory store is per-process — use a
    shared store (Redis) for correct limits (Phase 1 Step D note).
```

Verify:

```text
Gunicorn starts with the configured worker/thread count and binds to $PORT.
A simple concurrency check (e.g. a handful of parallel requests) is served
    without the single-worker stalling behavior.
Logs appear in the platform log stream (stdout/stderr).
```

---

## Step M — CI/CD pipeline (GitHub Actions: test then deploy)
Continuous Integration and Continuous Deployment/Delivery.

Effort: M. Makes every change tested and every deploy repeatable. Split into
three substeps (M1–M3).

### Substep M1 — CI: run the test suite on every push/PR

Files:

```text
.github/workflows/ci.yml     (new)
```

Add:

```text
A workflow triggered on push + pull_request that:
    - spins up a PostgreSQL service container,
    - sets TEST_DATABASE_URL / DATABASE_URL to that service,
    - installs requirements.txt,
    - runs `pytest -q` (the 54-test suite: auth, migrations, item form, pagination),
    - runs a migrations check: `alembic upgrade head` then `alembic downgrade base`
      on a scratch DB (guards reversibility / single head).
```

Verify:

```text
Opening a PR runs the workflow; a green run requires all tests to pass.
A deliberately broken test fails the workflow (red X on the PR).
The migration up/down check runs and passes.
```

### Substep M2 — CD: deploy on green main

Files:

```text
.github/workflows/deploy.yml   (new)  OR the platform's Git-based auto-deploy
```

Add:

```text
On push to main AFTER CI passes, deploy to the platform:
    - Prefer the platform's native Git deploy (auto-runs the Procfile release
      phase -> `alembic upgrade head` -> new web process), OR
    - a deploy job using the provider's CLI/action + a deploy token in GitHub
      Actions secrets.
Ensure migrations run in the RELEASE phase (once per deploy), never per request.
Document a rollback: redeploy the previous release; if a migration must be undone,
    `alembic downgrade -1` (tested on a scratch DB first — Phase 2 F4).
```

Verify:

```text
Merging to main triggers a deploy only when CI is green.
The release phase runs migrations before the new version serves traffic.
A no-migration redeploy is a safe no-op; the app stays up.
```

### Substep M3 — Repo protection + secrets

Files:

```text
GitHub repo settings (branch protection, Actions secrets/environments)
```

Add:

```text
Require the CI workflow to pass before merging to main; optionally require review.
Store deploy tokens / any CI secrets in GitHub Actions secrets or Environments,
    never in the workflow YAML.
Scope production secrets to a protected "production" Environment if the platform
    deploy runs from Actions.
```

Verify:

```text
A PR cannot merge to main while CI is failing.
No secret values are present in workflow files or logs.
```

---

## Consolidated testing plan

```text
Local / CI (pytest):
    Existing suite stays green (auth, migrations, item form, pagination).
    Migration up/down round-trip on a scratch DB (Phase 2 F5) runs in CI.
    Config guard: production refuses missing/dev-fallback SECRET_KEY (Step K2).
Staging / first deploy (manual smoke on the live domain):
    HTTPS redirect + valid cert + HSTS header (Step J3).
    Clean deploy builds schema via migrations; redeploy is a no-op (Step J2).
    Invite -> set-password -> login; QR scan -> stock add/remove; export; paging.
Data safety:
    Backup + PITR enabled; a restore drill succeeds on a scratch instance (J1).
```

## Pre-deploy checklist (Phase 3)

```text
[ ] APP_ENV=production and a strong SECRET_KEY set in the platform secret store
[ ] App refuses to start with a missing or dev-fallback SECRET_KEY in production
[ ] DATABASE_URL points at MANAGED Postgres with automated backups + PITR enabled
[ ] A restore drill has been performed and documented (RTO/RPO known)
[ ] Custom domain live over HTTPS; HTTP redirects to HTTPS; HSTS header present
[ ] ProxyFix in place so the app sees correct scheme/host behind the proxy
[ ] APP_BASE_URL=https://<domain>; QR codes encode https:// URLs
[x] Static assets served by WhiteNoise with cache headers
[x] Gunicorn tuned (workers/threads/timeout) and binding to $PORT
[ ] Flask-Limiter backed by a shared store (Redis) if running >1 worker/host
[ ] CI runs the full pytest suite + migration up/down check on every PR
[ ] Deploys happen only on green main; migrations run once per release
[ ] First admin created via set-password/invite; no demo credentials remain
[ ] .env is gitignored; no secrets in git history or alembic.ini
```

## Notes on sequencing with the rest of the roadmap

```text
Step K (config) is a prerequisite and should land before the first real deploy.
Step J closes out the two deploy-time items from earlier phases:
    - security Step E (HTTPS/TLS + HSTS)  -> Substep J3
    - data Step I (backups + PITR)        -> Substep J1
Step L (static + Gunicorn) can be done just before or right after the first
    deploy; it is not a launch blocker but should be in place for real traffic.
Step M (CI/CD) can be built in parallel; it makes every subsequent change safer
    but does not block the initial manual deploy.
After Phase 3, the remaining roadmap is Section 4 (quality & ops: Sentry,
    structured logging, health checks, blueprint refactor) and Section 5
    (compliance: audit trail, FERPA/privacy, accessibility, IT security review).
```

---

## Implementation Details

### July 8, 2026 — Substep K1: Provision and store production secrets

Status: Documentation/template work completed locally. Platform secret-store
entry remains an operator action because no production hosting platform is
connected from this workspace.

What was done:

```text
1. Reviewed the app's environment-variable contract in app.py and migrations/env.py.
2. Confirmed .env is listed in .gitignore, so local machine secrets should not be
   committed.
3. Confirmed alembic.ini does not contain a real database URL; Alembic gets
   DATABASE_URL from migrations/env.py at runtime.
4. Expanded .env.example into a full redacted template covering:
      - production-required APP_ENV, SECRET_KEY, DATABASE_URL, APP_BASE_URL
      - optional BARCODE_PREFIX
      - session/login/sudo tunables
      - Flask-Limiter tunables, including RATELIMIT_STORAGE_URI
      - TRANSACTIONS_PAGE_SIZE
      - SMTP/email invite/reset settings
5. No real SECRET_KEY, database password, SMTP password, or provider token was
   generated into or stored in git.
```

Production operator checklist:

```text
1. Generate SECRET_KEY outside git:
      python -c "import secrets; print(secrets.token_urlsafe(64))"

2. In the hosting platform's production secret/environment store, set:
      APP_ENV=production
      SECRET_KEY=<generated 64+ char random value>
      DATABASE_URL=<managed Postgres connection string from J1, with TLS/sslmode>
      APP_BASE_URL=https://<production-domain>
      EMAIL_PROVIDER=smtp
      EMAIL_FROM=<approved sender address>
      SMTP_HOST=<provider SMTP host>
      SMTP_PORT=<provider SMTP port>
      SMTP_USERNAME=<provider username>
      SMTP_PASSWORD=<provider password/app password>
      SMTP_USE_TLS=true/false according to provider
      SMTP_USE_SSL=true/false according to provider
      BARCODE_PREFIX=<customer prefix, optional>

3. Override only if needed:
      SESSION_IDLE_MINUTES
      SUDO_MODE_MAX_AGE
      LOGIN_MAX_ATTEMPTS
      LOGIN_LOCKOUT_SECONDS
      RATELIMIT_ENABLED
      RATELIMIT_STORAGE_URI
      RATELIMIT_LOGIN
      RATELIMIT_PASSWORD
      RATELIMIT_STOCK
      TRANSACTIONS_PAGE_SIZE

4. For multi-worker or multi-host production, set RATELIMIT_STORAGE_URI to a
   shared store such as Redis, not memory://.
```

K1 verification notes:

```text
[x] .env is listed in .gitignore.
[x] .env.example contains placeholders only.
[x] alembic.ini does not store the production DATABASE_URL.
[ ] Platform production environment shows every required variable set.
[ ] Git history has been reviewed before launch for accidental real secrets.
```

### July 8, 2026 — Substep K2: Enforce production config in the app

Status: Completed in `app.py`.

What was done:

```text
1. Added named constants for the known development fallback secret and the
   minimum production SECRET_KEY length.
2. Added validate_production_config(), called during app startup before Flask is
   configured.
3. Production startup now refuses:
      - missing SECRET_KEY
      - SECRET_KEY equal to dev-secret-key-change-before-production
      - SECRET_KEY shorter than 64 characters
4. Kept development behavior unchanged: local development can still use the
   built-in dev fallback when APP_ENV is not production.
5. Added `flask check-config`, which prints only environment variable names and
   set/missing/attention status, never the secret values themselves.
6. `check-config` reports:
      - APP_ENV / SECRET_KEY readiness
      - DATABASE_URL and APP_BASE_URL presence
      - SMTP/email configuration readiness
      - SESSION_COOKIE_SECURE / HTTPONLY / SAMESITE posture
      - Flask-Limiter enabled state and RATELIMIT_STORAGE_URI posture
```

Verification performed locally:

```text
[x] APP_ENV=production with no SECRET_KEY refuses to import app.py.
[x] APP_ENV=production with the dev fallback SECRET_KEY refuses to import app.py.
[x] APP_ENV=production with a short SECRET_KEY refuses to import app.py.
[x] APP_ENV=production with a generated 64+ char SECRET_KEY imports app.py.
[x] Production session cookie config is Secure=True, HTTPOnly=True, SameSite=Lax.
[x] `flask check-config` reports config names/status without printing secrets.
[x] `python -m py_compile app.py` passes.
[x] Existing pytest suite passes: 54 passed.
```

### July 8, 2026 — Substep K3: Document the config contract

Status: Completed in `README.md` and aligned with `.env.example`.

What was done:

```text
1. Expanded the README Production Configuration section into a required vs
   optional environment-variable contract.
2. For each variable, documented whether it is a secret and what it controls.
3. Documented that DATABASE_URL is shared by the Flask app and Alembic through
   migrations/env.py, while alembic.ini intentionally stores no real URL.
4. Documented that rotating SECRET_KEY invalidates all active sessions and all
   pending invite/reset links because those tokens are signed with SECRET_KEY.
5. Documented that production refuses missing/dev-fallback/short SECRET_KEY
   values and that `flask check-config` can self-check names/status without
   printing secrets.
```

Verification performed locally:

```text
[x] README lists required production variables in one place.
[x] README lists optional tunables in one place.
[x] README and .env.example both include the same production config categories.
[x] No real secrets were added to README or .env.example.
```

### July 8, 2026 — Substep J1: Provision managed PostgreSQL with backups + PITR

Status: Restore runbook and repo documentation completed. Actual provider
provisioning, backup/PITR enablement, and restore drill remain operator actions
because no production cloud/provider console is connected from this workspace.

What was documented:

```text
1. Added a Step I / J1 implementation log to
   design_docx/DATA_MIGRATIONS_RELIABILITY_PLAN.md.
2. Documented required managed PostgreSQL settings:
      - automated daily backups
      - PITR/WAL enabled
      - 7-30 day retention window
      - backups stored off the app host
      - TLS-required client connections
      - least-privilege app database user
3. Documented the production DATABASE_URL shape:
      postgresql://<user>:<password>@<host>:<port>/<database>?sslmode=require
4. Reconfirmed that DATABASE_URL belongs only in the platform secret store and
   is shared by app.py and migrations/env.py.
5. Added a restore runbook covering scratch-instance restore, TLS connectivity,
   Alembic/schema verification, known-row checks, optional app smoke testing,
   failover decision steps, and RTO/RPO recording.
6. Added a PITR drill procedure that proves recovery to a timestamp before and
   after a known test change.
```

Provider/operator checklist:

```text
[ ] Create managed PostgreSQL instance.
[ ] Enable automated daily backups.
[ ] Enable PITR/WAL with a documented retention window.
[ ] Confirm backups are provider-managed/off the app host.
[ ] Capture TLS-enabled DATABASE_URL and store it in the platform secret store.
[ ] Run a restore drill to a scratch/restored instance.
[ ] Confirm schema and a known row exist on the restored instance.
[ ] Confirm the app can connect over TLS using DATABASE_URL.
[ ] Record actual RTO/RPO from the drill.
```

Verification performed locally:

```text
[x] Restore runbook exists in design_docx/DATA_MIGRATIONS_RELIABILITY_PLAN.md.
[x] DATABASE_URL guidance requires TLS / sslmode=require where needed.
[x] Documentation states backups/PITR are provider/operator actions, not code.
[x] No real database URL, password, provider token, or secret was committed.
```

### July 8, 2026 — Substep J2: Configure the app for the platform

Status: Completed for Procfile/Gunicorn platform configuration. Live clean-deploy
verification remains a provider action because no production platform is
connected from this workspace.

What changed:

```text
1. Confirmed Procfile release phase still runs:
      alembic upgrade head
   This runs migrations once per deploy before the web process serves traffic.
2. Added gunicorn.conf.py with environment-driven production defaults:
      bind                  0.0.0.0:$PORT, fallback 8000
      GUNICORN_WORKERS      override worker count
      GUNICORN_THREADS      override thread count
      GUNICORN_TIMEOUT      override request timeout
      GUNICORN_GRACEFUL_TIMEOUT
      GUNICORN_KEEPALIVE
      GUNICORN_ACCESSLOG / GUNICORN_ERRORLOG / GUNICORN_LOGLEVEL
3. Updated Procfile web command to:
      gunicorn app:app -c gunicorn.conf.py
4. Confirmed runtime config continues to come from environment variables; no
   app-runtime file writes are required. QR PNGs are generated in memory.
```

Provider/operator verification checklist:

```text
[ ] Clean deploy to an empty managed PostgreSQL database.
[ ] Release phase runs alembic upgrade head and reaches migration head.
[ ] Web process boots with gunicorn app:app -c gunicorn.conf.py.
[ ] Gunicorn binds to the platform-provided PORT.
[ ] Redeploy with no new migrations is a release-phase no-op.
[ ] Platform/pre-domain URL returns HTTP 200 for /login.
```

Verification performed locally:

```text
[x] Procfile release command remains alembic upgrade head.
[x] Procfile web command uses gunicorn.conf.py.
[x] gunicorn.conf.py reads PORT and binds to 0.0.0.0:<port>.
[x] gunicorn.conf.py compiles.
[x] Gunicorn config check succeeds.
```

### July 9, 2026 — Substep J3: Custom domain + TLS + HSTS

Status: App-side proxy/HSTS support completed. DNS records, managed certificate
issuance, HTTP->HTTPS redirect, and final browser/certificate verification remain
provider actions.

What changed:

```text
1. Added Werkzeug ProxyFix support in app.py.
      - Enabled by PROXY_FIX_ENABLED.
      - Defaults to enabled when APP_ENV=production.
      - Trusts one upstream TLS-terminating proxy's X-Forwarded-* headers.
2. Added HSTS response support in app.py.
      - Enabled by HSTS_ENABLED.
      - Defaults to enabled when APP_ENV=production.
      - Sends Strict-Transport-Security on HTTPS responses.
      - HSTS_MAX_AGE defaults to 31536000 seconds.
      - HSTS_INCLUDE_SUBDOMAINS and HSTS_PRELOAD are optional flags.
3. Extended flask check-config to report ProxyFix and HSTS status.
4. Documented PROXY_FIX_ENABLED and HSTS_* values in README.md and .env.example.
5. Updated design_docx/SECURITY_AND_AUTH_PLAN.md Step E to show app-side HTTPS
   and HSTS support as done, with provider verification still required.
```

Provider/operator checklist:

```text
[ ] Create DNS CNAME/A record per provider instructions.
[ ] Issue/verify platform-managed TLS certificate.
[ ] Enable HTTP -> HTTPS redirect at the platform/proxy.
[ ] Set APP_BASE_URL=https://<custom-domain>.
[ ] Keep APP_ENV=production.
[ ] Keep PROXY_FIX_ENABLED=true behind the platform/proxy.
[ ] Keep HSTS_ENABLED=true only after HTTPS is confirmed working.
```

Verification performed locally:

```text
[x] ProxyFix honors X-Forwarded-Proto=https.
[x] HTTPS responses carry Strict-Transport-Security when HSTS is enabled.
[x] Session cookies are Secure in APP_ENV=production.
[x] check-config reports ProxyFix and HSTS status.
[x] py_compile passed.
```

Verification pending on deployed domain:

```text
[ ] http://<domain> redirects to https://<domain>.
[ ] Browser certificate is valid and trusted.
[ ] Response carries Strict-Transport-Security.
[ ] Session cookies are marked Secure on the real domain.
[ ] QR code PNG/content points to https://<domain>/items/<barcode>/stock.
```

### July 9, 2026 — Substep J4: First production bootstrap + smoke test

Status: Operational runbook completed in `README.md`. Actual first bootstrap and
smoke testing remain provider/live-domain actions because no production platform
or managed database is connected from this workspace.

What was documented:

```text
1. Added a First Production Bootstrap section to README.md.
2. Reconfirmed that first production schema creation must happen through the
   release-phase Alembic migration command:
      alembic upgrade head
3. Reconfirmed that `flask --app app init-db` must not be run against the
   managed production database because it is local-dev bootstrap only.
4. Documented the first-administrator bootstrap flow:
      - insert the first admin row into the managed database
      - use `flask --app app set-password <email> <password>` once
      - log in over HTTPS
      - create faculty/student users through the app so invite email and
        set-password flow are tested normally
5. Documented that demo/default credentials must not be shipped or enabled in
   production.
6. Added a manual smoke-test checklist for admin login, invite delivery,
   set-password, item creation, QR print/scan, stock add/remove, transactions,
   filters, CSV export, and pagination.
7. Updated the README Procfile example so the web command matches the actual
   production Gunicorn config:
      gunicorn app:app -c gunicorn.conf.py
```

Operator/live verification checklist:

```text
[ ] Platform release phase runs `alembic upgrade head` successfully.
[ ] `flask --app app init-db` is not run against the managed DB.
[ ] First administrator row exists with role `administrator`, institution_id
    `A1001`, is_active=true, and a real university email.
[ ] First administrator password is set once with `flask --app app set-password`.
[ ] Administrator can log in over HTTPS.
[ ] Faculty invite email is delivered and set-password link works.
[ ] Student invite email is delivered and set-password link works.
[ ] Create item -> print QR label -> scan on phone -> stock page opens.
[ ] Add-stock and remove-stock flows both create transaction rows.
[ ] Transaction history filters work.
[ ] Transaction CSV export works with filters and without filters.
[ ] Pagination controls work when enough transactions exist.
[ ] No demo/default credentials remain enabled.
```

Verification performed locally:

```text
[x] README now contains first production bootstrap instructions.
[x] README clearly says production/shared DB schema is owned by migrations.
[x] README clearly says not to run init-db against managed production DB.
[x] README smoke-test checklist covers the critical J4 paths.
[x] No production password, DATABASE_URL, email credential, or secret was added.
```

### July 9, 2026 — Substep L1: WhiteNoise for static assets

Status: Completed in application code and dependency list. Optional CDN remains a
future provider/domain configuration step; no app code change should be required
for that later.

What changed:

```text
1. Added WhiteNoise to requirements.txt:
      whitenoise>=6.7,<7.0
2. Installed WhiteNoise into the local project virtual environment.
3. Imported WhiteNoise in app.py.
4. Wrapped the WSGI app with WhiteNoise immediately after the optional ProxyFix
   wrapper:
      app.wsgi_app = WhiteNoise(
          app.wsgi_app,
          root=str(BASE_DIR / "static"),
          prefix="static/",
          max_age=31536000,
      )
5. Used the absolute static directory based on BASE_DIR so Gunicorn can start
   from any working directory without breaking static file resolution.
6. Reused the app's HSTS header builder for WhiteNoise static responses when
   HSTS_ENABLED is on.
7. Generated gzip-compressed CSS variants for WhiteNoise to serve:
      static/css/login.css.gz
      static/css/styles.css.gz
8. Kept all templates and `url_for('static', ...)` paths unchanged.
```

Why:

```text
WhiteNoise lets the deployed Flask/Gunicorn process serve static/css/image/js
assets directly from lightweight middleware with long Cache-Control headers.
This avoids routing static requests through Flask route logic or database-backed
page handlers and makes adding a CDN later straightforward.
```

Verification performed locally:

```text
[x] WhiteNoise imports successfully from the project virtual environment.
[x] `python -m py_compile app.py` passes.
[x] /static/css/styles.css returns HTTP 200.
[x] /static/css/styles.css returns Cache-Control: max-age=31536000, public.
[x] /static/css/styles.css returns Content-Encoding: gzip when the client sends
    Accept-Encoding: gzip.
[x] /static/css/login.css returns HTTP 200 with long Cache-Control headers.
[x] /static/images/YU_logo.png returns HTTP 200 with long Cache-Control headers.
[x] /static/images/background.png returns HTTP 200 with long Cache-Control
    headers.
[x] Static responses include Strict-Transport-Security when production HSTS is
    enabled.
[x] /login still renders HTTP 200.
[x] Existing pytest suite passes: 54 passed.
```

### July 9, 2026 — Substep L2: Tune Gunicorn

Status: Completed in `gunicorn.conf.py`, `.env.example`, and `README.md`.
Live concurrency/latency verification on the final hosting platform remains an
operator check, because real worker behavior depends on the deployed CPU/RAM
size and platform router.

What changed:

```text
1. Tuned gunicorn.conf.py around the Procfile web command:
      web: gunicorn app:app -c gunicorn.conf.py
2. Gunicorn now binds to the platform-provided PORT:
      bind = 0.0.0.0:$PORT
3. Worker count now uses the common platform variable WEB_CONCURRENCY.
      - If WEB_CONCURRENCY is unset, default is (2 * CPU count) + 1.
      - GUNICORN_WORKERS remains supported as a backward-compatible alias.
4. Threads remain environment-configurable with GUNICORN_THREADS and default to
   2 for this I/O-bound Flask/PostgreSQL app.
5. Request timeout now defaults to 30 seconds through GUNICORN_TIMEOUT.
6. Graceful timeout, keepalive, access log, error log, and log level remain
   environment-configurable.
7. Added worker recycling:
      GUNICORN_MAX_REQUESTS=1000
      GUNICORN_MAX_REQUESTS_JITTER=100
   This avoids keeping any one worker alive forever.
8. Added the Gunicorn tunables to .env.example.
9. Added the Gunicorn tunables to the README Production Configuration table.
```

Why:

```text
Multiple workers/threads let the deployed app serve several users at once
instead of behaving like a single local development process. Recycling workers
periodically is a normal production hardening step for long-running Python web
apps. Logging to stdout/stderr lets the cloud platform collect logs correctly.
```

Important production note:

```text
When WEB_CONCURRENCY or GUNICORN_WORKERS is greater than 1, Flask-Limiter's
memory:// store is per worker. For correct shared rate limits in production,
set RATELIMIT_STORAGE_URI to Redis or another shared backend.
```

Verification performed locally:

```text
[x] gunicorn.conf.py compiles.
[x] Gunicorn config check loads the tuned config.
[x] Gunicorn binds to the provided PORT.
[x] WEB_CONCURRENCY overrides worker count.
[x] GUNICORN_THREADS overrides thread count.
[x] GUNICORN_TIMEOUT overrides timeout.
[x] GUNICORN_MAX_REQUESTS and GUNICORN_MAX_REQUESTS_JITTER are present.
[x] Gunicorn logs to stdout/stderr by default.
[x] A local Gunicorn smoke test serves parallel /login requests successfully.
[x] Existing pytest suite passes.
```

### July 9, 2026 — Substep M1: CI test workflow

Status: Workflow file added. GitHub-hosted verification remains pending until
the branch is pushed and GitHub Actions runs the workflow on a push or pull
request.

What changed:

```text
1. Added .github/workflows/ci.yml.
2. Workflow triggers on:
      push
      pull_request
3. Workflow starts a PostgreSQL 16 service container with a health check.
4. Workflow sets the app/test database URLs to the service:
      DATABASE_URL
      TEST_DATABASE_URL
      MIG_DATABASE_URL
5. Workflow installs dependencies from requirements.txt.
6. Workflow runs:
      pytest -q
7. Workflow creates a separate scratch database for an explicit migration check:
      inventory_ci_migrations
8. Workflow runs:
      alembic upgrade head
      alembic downgrade base
9. Workflow drops the scratch migration database in an always-run cleanup step.
```

Why:

```text
Every push and pull request should prove the auth, migrations, item form, and
pagination test suite still passes against real PostgreSQL. The explicit
Alembic up/down check gives an extra deployment-safety signal that the migration
chain can build and reverse on a clean database.
```

Verification performed locally:

```text
[x] Workflow file exists at .github/workflows/ci.yml.
[x] Workflow contains push and pull_request triggers.
[x] Workflow defines a PostgreSQL service container.
[x] Workflow runs pytest -q.
[x] Workflow runs alembic upgrade head and alembic downgrade base on a scratch DB.
[x] Local scratch DB migration check passed:
    alembic upgrade head -> alembic downgrade base.
[x] Existing local pytest suite passes: 54 passed.
```

Verification pending on GitHub:

```text
[ ] Push/PR starts the CI workflow.
[ ] Green CI requires the pytest suite to pass.
[ ] Green CI requires the explicit migration up/down check to pass.
[ ] A deliberately broken test produces a red workflow run on the PR.
```

### July 9, 2026 — Substep M2: Deploy on green main/master

Status: Provider-neutral deploy workflow and rollback documentation added.
Actual live deployment verification remains pending until the hosting provider
deploy hook is created and stored in GitHub Actions secrets.

What changed:

```text
1. Added .github/workflows/deploy.yml.
2. The deploy workflow is triggered by completion of the CI workflow.
3. Deployment runs only when:
      - CI conclusion is success
      - the CI run came from a push event
      - the pushed branch is main or master
4. Pull requests do not deploy.
5. The job uses the GitHub production environment.
6. The job checks that Procfile still contains:
      release: alembic upgrade head
      web: gunicorn app:app -c gunicorn.conf.py
7. The job calls a provider deploy hook using the GitHub Actions secret:
      DEPLOY_HOOK_URL
8. If DEPLOY_HOOK_URL is not configured, the deploy job fails loudly instead of
   silently pretending to deploy.
9. Added README Deployment and Rollback notes.
```

Why:

```text
The hosting provider is not finalized yet, so this uses a deploy-hook pattern
that works with many platform-native Git deploy systems. The provider remains
responsible for pulling the repository, running the Procfile release phase once,
and starting the Gunicorn web process.
```

Rollback documented:

```text
1. Prefer redeploying the previous good platform release / previous good commit.
2. If a migration must be reversed, test it first on a scratch/restored database.
3. Only after the scratch test passes, run:
      alembic downgrade -1
```

Verification performed locally:

```text
[x] deploy.yml exists.
[x] deploy.yml listens for completed CI workflow runs.
[x] deploy.yml deploys only after successful CI.
[x] deploy.yml deploys only for push events, not pull_request events.
[x] deploy.yml supports both main and master default-branch naming.
[x] deploy.yml checks the Procfile release and web commands.
[x] deploy.yml uses DEPLOY_HOOK_URL from GitHub Actions secrets.
[x] README documents release-phase migrations and rollback.
```

Verification pending on GitHub/provider:

```text
[ ] Configure DEPLOY_HOOK_URL as a GitHub Actions secret.
[ ] Configure/approve the production GitHub Environment if required.
[ ] Push to main/master after green CI triggers the deploy workflow.
[ ] Provider runs release phase before serving the new version.
[ ] No-migration redeploy is a safe no-op and the app remains up.
```

### July 9, 2026 — Substep M3: Repo protection + secrets

Status: GitHub settings runbook documented. Actual branch protection,
environment protection, and secret creation must be completed in the GitHub web
UI by a repository administrator because the GitHub CLI is not installed in this
local environment.

What was documented:

```text
1. Added README GitHub Protection and Secrets instructions.
2. Documented branch protection for the current default branch:
      master
   and noted that the same rule should apply to main if the repository is later
   renamed from master to main.
3. Documented required status checks:
      CI / Test and migrations
   or the equivalent displayed check name:
      Test and migrations
4. Documented requiring branches to be up to date before merge.
5. Documented optional pull-request review before merge.
6. Documented disabling force pushes and protected-branch deletion.
7. Documented storing DEPLOY_HOOK_URL in GitHub Actions secrets or the
   production environment, never in workflow YAML.
8. Documented creating a GitHub production environment with optional required
   reviewers and deployment branch restrictions.
9. Reconfirmed that provider tokens, SMTP passwords, DATABASE_URL, and
   production SECRET_KEY values must never be committed.
```

Why:

```text
Branch protection prevents accidental or untested production changes from
merging. Required CI checks make the 54-test suite and migration up/down checks
part of the merge gate. GitHub Actions secrets/environments keep deploy tokens
out of git and make production deployment approval possible.
```

Operator steps to complete in GitHub:

```text
1. Settings > Branches > Branch protection rules.
2. Add rule for master (and main later if the branch is renamed).
3. Enable "Require status checks to pass before merging".
4. Select CI / Test and migrations.
5. Enable "Require branches to be up to date before merging".
6. Optionally require pull request review.
7. Disable force pushes and branch deletion.
8. Settings > Secrets and variables > Actions.
9. Add DEPLOY_HOOK_URL as a secret, or store it under the production
   environment.
10. Settings > Environments > production.
11. Add required reviewers if production deploys need approval.
12. Restrict deployment branches to master/main.
```

Verification performed locally:

```text
[x] README documents branch protection and required CI checks.
[x] README documents DEPLOY_HOOK_URL storage in secrets/environments.
[x] README says not to commit provider deploy tokens, SMTP passwords,
    DATABASE_URL, or production SECRET_KEY.
[x] Workflow files reference GitHub secrets by name only.
[x] No production secret values were added to workflow YAML.
```

Verification pending on GitHub:

```text
[ ] A PR cannot merge to master/main while CI is failing.
[ ] DEPLOY_HOOK_URL exists as a GitHub Actions secret or production environment
    secret.
[ ] The production environment is protected if deploy approval is required.
[ ] Workflow logs do not print secret values.
```

---

# AWS Two-Phase Deployment Guide

Project: Katz Nursing School Inventory Management System

Last updated: 2026-07-20

Purpose: document a careful AWS deployment path for a university-facing
inventory system. This plan is written for a first-time deployment and is split
into two phases:

1. Phase 1: starting production setup, simple enough to operate now.
2. Phase 2: more secure university setup, stronger security and operations
   without losing existing production data.

The most important principle is this: production data lives in PostgreSQL, not
inside the web server. If the database is protected, backed up, and migrated
carefully, the app infrastructure can be upgraded later without losing data.

This document intentionally does not contain real secrets, passwords, database
URLs, SMTP passwords, AWS access keys, or token values.

---

## Current Application Assumptions

The application is a Flask web app with:

- PostgreSQL through `DATABASE_URL`.
- Alembic migrations in `migrations/`.
- Gunicorn production server through `gunicorn.conf.py`.
- Static files under `static/`.
- QR/barcode functionality generated by the app.
- Role-based users: administrator, faculty, student.
- Audit logs, transaction history, CSV exports, Sentry optional monitoring, and
  `/health` JSON health endpoint.

Current important files:

- `app.py`: thin entry point for the Flask app.
- `inventory/`: application package and blueprints.
- `requirements.txt`: Python dependencies.
- `gunicorn.conf.py`: production Gunicorn settings.
- `alembic.ini`: migration configuration.
- `migrations/env.py`: reads `DATABASE_URL` for migrations.
- `.env.example`: redacted environment variable template.
- `.gitignore`: must include `.env`.

Important production commands:

```bash
alembic upgrade head
gunicorn app:app -c gunicorn.conf.py
flask --app app check-config
flask --app app set-password user@example.edu 'StrongPasswordHere'
```

Important note for AWS App Runner:

The project has a `Procfile`, but AWS App Runner does not behave like
Render/Heroku release phases. Do not assume App Runner will automatically run:

```bash
release: alembic upgrade head
```

For AWS Phase 1, migrations should be run deliberately before the first deploy
and before future releases that include schema changes. Later, in Phase 2, move
migrations into CI/CD or a controlled deployment pipeline.

---

## Recommended AWS Region

Choose one region and keep all resources there unless university IT requires
otherwise.

Recommended starting choice:

```text
us-east-1
```

Why:

- Broad AWS service availability.
- Usually lower cost than some regions.
- Good support for App Runner, RDS, Route 53, ACM, CloudWatch, SES, Secrets
  Manager, and SSM Parameter Store.

If the university has an AWS standard region, use that instead.

Write the chosen region here:

```text
Production AWS Region: ____________________
```

---

## Phase 1 - Starting Production Setup

### Goal

Get the app online for daily university use with HTTPS, managed PostgreSQL,
email invites/resets, logs, backups, and a controlled first-admin setup.

### Phase 1 Architecture

```text
Users
  |
  | HTTPS
  v
Route 53 custom domain
  |
  v
AWS App Runner web service
  |
  | DATABASE_URL over TLS/private network
  v
Amazon RDS PostgreSQL Single-AZ

Supporting services:
- AWS Certificate Manager / App Runner managed TLS
- CloudWatch logs
- Amazon SES or university SMTP
- AWS Secrets Manager or SSM Parameter Store
- RDS automated backups and manual snapshots
```

For easiest long-term upgrade, use an App Runner VPC connector and keep RDS
private from the beginning if possible. It is a little more setup now, but it
avoids exposing the database to the public internet.

---

## Phase 1 Checklist

Use this as the high-level checklist before going live:

- AWS account is owned by the university or approved project owner.
- Root account has MFA enabled.
- Admin user uses IAM Identity Center or IAM user with MFA.
- Billing alerts are enabled.
- RDS PostgreSQL is created.
- RDS backups and PITR are enabled.
- RDS encryption at rest is enabled.
- App Runner service is created.
- App Runner has environment variables/secrets configured.
- App Runner can connect to RDS.
- Alembic migrations have been applied to production database.
- First permanent admin account exists.
- Admin password is set securely.
- Custom domain is connected.
- HTTPS works.
- `/health` returns 200.
- Invite/reset email works.
- QR label creation and scanning works.
- CSV exports work only for authorized users.
- Sentry is configured if desired.
- No demo/default passwords are enabled.

---

## Step 1 - Prepare AWS Account Safely

### 1.1 Create or confirm the AWS account

Use a university-owned AWS account if possible. Avoid deploying a long-term
university system in a personal AWS account.

Recommended ownership:

```text
AWS account owner: university / department / approved lab account
Billing owner: university / department
Technical admins: at least 2 named people
```

### 1.2 Secure the root user

1. Log in to AWS as root only for initial account security.
2. Enable MFA on the root account.
3. Store root credentials in the university-approved password manager.
4. Do not use root for normal deployment work.

### 1.3 Create administrator access

Best option:

```text
AWS IAM Identity Center
```

If IAM Identity Center is not available yet, create an IAM admin user/group
temporarily and require MFA.

Minimum requirements:

- MFA enabled.
- No shared personal passwords.
- At least two people can access the AWS account in an emergency.
- Access is removed when someone leaves the project.

### 1.4 Enable billing protection

In AWS Billing:

1. Open Billing and Cost Management.
2. Create a monthly budget.
3. Start with a budget such as:

```text
Phase 1 budget alert: $100/month
Warning alert: 50%
Critical alert: 80%
```

4. Add email recipients for alerts.

For a small system with fewer than 50 users and fewer than 500 items, normal
Phase 1 cost should usually be much lower than this, but the budget protects
against accidental configuration mistakes.

---

## Step 2 - Prepare The GitHub Repository

### 2.1 Confirm required files exist

From the project root:

```bash
cd /Users/farhatjahan/Desktop/YU/summer26/YU_internship/Sim_Intern/inventory/inventory_management_system
ls -la
ls -la requirements.txt gunicorn.conf.py alembic.ini migrations .env.example .gitignore
```

### 2.2 Confirm `.env` is ignored

Run:

```bash
grep -n '^\.env' .gitignore
```

Expected:

```text
.env
```

If missing, add it before any deployment:

```bash
printf '\n.env\n' >> .gitignore
git add .gitignore
git commit -m "Ensure local environment files are ignored"
```

### 2.3 Confirm no real secrets are committed

Run:

```bash
git grep -n "SECRET_KEY\\|SMTP_PASSWORD\\|DATABASE_URL\\|aws_secret_access_key\\|AKIA"
```

Expected:

- Redacted examples in `.env.example` are okay.
- Real passwords, tokens, AWS keys, and production database URLs are not okay.

If a real secret was committed, rotate it immediately. Do not simply delete it
from the newest commit and assume it is safe, because git history may still
contain it.

### 2.4 Push the latest code

```bash
git status
git add .
git commit -m "Prepare inventory app for AWS deployment"
git push origin master
```

If your branch is named `main`, use:

```bash
git push origin main
```

---

## Step 3 - Create Production Secrets

### 3.1 Generate a strong Flask secret key

Run locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the output and store it in the AWS secret store. Do not paste it into git,
README files, screenshots, chat, or documentation.

Important:

Rotating `SECRET_KEY` later will invalidate current login sessions and pending
invite/reset links because those tokens are signed with the key.

### 3.2 Decide where to store secrets

Recommended Phase 1:

```text
AWS Secrets Manager for secrets
SSM Parameter Store for non-secret config
```

Simpler but less ideal:

```text
App Runner environment variables
```

Use App Runner plain text only for non-sensitive values. AWS App Runner can
reference Secrets Manager or SSM Parameter Store values as environment
variables; sensitive values should not be plain text in the service config.

### 3.3 Required production variables

Set these for the App Runner service:

```text
APP_ENV=production
SECRET_KEY=<generated 64+ char random value>
DATABASE_URL=<production PostgreSQL URL>
APP_BASE_URL=https://<your-domain>
EMAIL_PROVIDER=smtp
EMAIL_FROM=<approved sender email>
SMTP_HOST=<smtp host>
SMTP_PORT=587
SMTP_USERNAME=<smtp username>
SMTP_PASSWORD=<smtp password>
SMTP_USE_TLS=true
SMTP_USE_SSL=false
PROXY_FIX_ENABLED=true
HSTS_ENABLED=true
RATELIMIT_ENABLED=true
RATELIMIT_STORAGE_URI=memory://
WEB_CONCURRENCY=2
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=30
```

Optional:

```text
BARCODE_PREFIX=KATZ-NURS
SESSION_IDLE_MINUTES=30
LOGIN_MAX_ATTEMPTS=5
LOGIN_LOCKOUT_SECONDS=300
TRANSACTIONS_PAGE_SIZE=50
SENTRY_DSN=<Sentry DSN if used>
SENTRY_TRACES_SAMPLE_RATE=0.1
ALLOW_LOCAL_AUTH_LINKS=false
```

For production, keep:

```text
ALLOW_LOCAL_AUTH_LINKS=false
```

Only turn it on temporarily in a controlled test environment if email is not
ready yet.

---

## Step 4 - Create The RDS PostgreSQL Database

### 4.1 Open RDS

1. AWS Console.
2. Select the production region.
3. Search for `RDS`.
4. Open RDS.
5. Choose `Create database`.

### 4.2 Choose database creation method

Choose:

```text
Standard create
```

Do not use Easy create for this project because we need to control backups,
encryption, networking, and maintenance settings.

### 4.3 Engine

Choose:

```text
Engine type: PostgreSQL
Version: latest stable version supported by AWS and compatible with psycopg
```

Recommendation:

- Use the AWS default current stable PostgreSQL version unless university IT has
  a required version.
- Avoid choosing an end-of-life version.
- Record the selected version:

```text
Production PostgreSQL version: ____________________
```

### 4.4 Templates

Choose:

```text
Production
```

If cost must be extremely low during trial, a dev/test template may be used for
a short staging test only. For real daily university use, use production-minded
settings.

### 4.5 Availability

Phase 1:

```text
Single-AZ DB instance
```

Why:

- Lower cost.
- Enough for a small first deployment.
- Backups/PITR protect data.

Phase 2 will upgrade to Multi-AZ.

### 4.6 DB identifier and credentials

Suggested DB instance identifier:

```text
katz-inventory-prod
```

Suggested database name:

```text
inventory_prod
```

Master username:

```text
inventory_admin
```

Generate a strong password and store it in Secrets Manager or the university
password manager.

Do not use:

- `postgres`
- `admin`
- `password`
- personal names
- reused passwords

### 4.7 Instance size

For fewer than 50 users and fewer than 500 items:

```text
db.t4g.micro or db.t4g.small
```

Recommendation:

- Start with `db.t4g.micro` for pilot/small production.
- Move to `db.t4g.small` if the app feels slow or university IT wants more headroom.

### 4.8 Storage

Recommended Phase 1:

```text
Storage type: gp3 or General Purpose SSD
Allocated storage: 20 GB
Storage autoscaling: enabled
Maximum storage threshold: 100 GB
```

This app should not need much database storage for fewer than 50 users and 500
items, but transaction and audit logs grow over time.

### 4.9 Encryption

Enable:

```text
Storage encryption: enabled
KMS key: AWS managed key is acceptable for Phase 1
```

Phase 2 can move to a customer-managed KMS key if university policy requires it.

### 4.10 Connectivity

Recommended:

```text
Public access: No
```

Use App Runner VPC connector to reach the database privately.

If you make RDS publicly accessible temporarily for setup, restrict it tightly
and turn public access off as soon as possible. A public production database is
not the preferred long-term design.

### 4.11 VPC and subnet group

For Phase 1 simplicity:

- Use the default VPC if university IT has not provided a VPC.
- Use a DB subnet group with subnets in at least two Availability Zones.
- The DB can still be Single-AZ even though the subnet group spans multiple AZs.

For Phase 2:

- Move to a dedicated VPC.
- Use private subnets for RDS.
- Use controlled egress for the app.

### 4.12 Security group

Create an RDS security group:

```text
Name: sg-katz-inventory-rds-prod
Inbound rule:
  Type: PostgreSQL
  Port: 5432
  Source: App Runner VPC connector security group
Outbound:
  Default is usually okay
```

Do not allow:

```text
0.0.0.0/0 -> 5432
```

### 4.13 Backups

Enable:

```text
Automated backups: enabled
Retention: 7 days minimum, preferably 14-30 days
Point-in-time recovery: enabled through automated backups/WAL
Backup window: outside regular lab hours if possible
Copy tags to snapshots: enabled
```

For long-term university use, ask IT how long backups must be retained.

### 4.14 Maintenance

Recommended:

```text
Auto minor version upgrade: enabled if allowed by IT
Maintenance window: outside regular lab hours
Deletion protection: enabled
```

Enable deletion protection for production.

### 4.15 Create database

Review all settings, then choose:

```text
Create database
```

Wait until status is:

```text
Available
```

---

## Step 5 - Build The Production DATABASE_URL

RDS provides an endpoint like:

```text
katz-inventory-prod.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com
```

Build:

```text
postgresql://inventory_admin:<PASSWORD>@<RDS-ENDPOINT>:5432/inventory_prod?sslmode=require
```

Example with placeholders:

```text
postgresql://inventory_admin:REDACTED@katz-inventory-prod.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com:5432/inventory_prod?sslmode=require
```

Important:

- Include `sslmode=require`.
- Store the real value in Secrets Manager/App Runner secrets.
- Never commit this value.
- Do not paste the real value into documentation.

---

## Step 6 - Create App Runner VPC Connector

Use this if RDS is private, which is recommended.

### 6.1 Open App Runner

1. AWS Console.
2. Select same region as RDS.
3. Search for `App Runner`.
4. Open App Runner.
5. Go to VPC connectors.
6. Create VPC connector.

### 6.2 Configure connector

Suggested name:

```text
katz-inventory-prod-vpc-connector
```

Choose:

- Same VPC as RDS.
- Private subnets that can reach RDS.
- Security group:

```text
sg-katz-inventory-apprunner-prod
```

Then update the RDS security group inbound rule to allow PostgreSQL from this
App Runner connector security group.

---

## Step 7 - Configure Email With SES Or University SMTP

### Option A - Amazon SES

SES is a good long-term choice if the university allows AWS-managed email.

Steps:

1. Open Amazon SES in the same region.
2. Verify the sender email or domain.
3. If verifying a domain, add DNS records in Route 53.
4. Request production access because new SES accounts start in sandbox mode.
5. Create SMTP credentials for SES.
6. Store SMTP username/password in Secrets Manager.
7. Configure:

```text
EMAIL_PROVIDER=smtp
EMAIL_FROM=inventory@your-domain.edu
SMTP_HOST=email-smtp.<region>.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=<SES SMTP username>
SMTP_PASSWORD=<SES SMTP password>
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

SES sandbox warning:

If SES is still in sandbox mode, invite/reset emails can only go to verified
recipient addresses. For real faculty/student invites, request production access.

### Option B - University SMTP

Use this if university IT provides SMTP credentials.

Ask university IT for:

```text
SMTP host
SMTP port
TLS/SSL requirement
sender address
username
password or app password
allowed sending volume
allowed recipient domains
```

Configure the same app variables:

```text
EMAIL_PROVIDER=smtp
EMAIL_FROM=<approved university sender>
SMTP_HOST=<university smtp host>
SMTP_PORT=587
SMTP_USERNAME=<username>
SMTP_PASSWORD=<password>
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

---

## Step 8 - Run Database Migrations

This is required before the app can use an empty production database.

### 8.1 Install dependencies locally

From the project root:

```bash
cd /Users/farhatjahan/Desktop/YU/summer26/YU_internship/Sim_Intern/inventory/inventory_management_system
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 8.2 Test local compile

```bash
python -m py_compile app.py
pytest -q
```

If tests fail locally, do not deploy yet.

### 8.3 Run migrations against production

Set `DATABASE_URL` temporarily in your terminal session only:

```bash
export DATABASE_URL='postgresql://inventory_admin:REDACTED@RDS-ENDPOINT:5432/inventory_prod?sslmode=require'
alembic upgrade head
```

Do not put the real production `DATABASE_URL` into `.env` unless you are very
careful and `.env` is gitignored.

### 8.4 Verify migration

```bash
alembic current
```

Expected:

```text
head revision is applied
```

Optional PostgreSQL check:

```bash
psql "$DATABASE_URL" -c "\dt"
```

You should see tables such as:

```text
users
items
transactions
audit_logs
alembic_version
```

---

## Step 9 - Create The App Runner Service

### 9.1 Open App Runner

1. AWS Console.
2. Open App Runner.
3. Choose `Create service`.

### 9.2 Source

Choose:

```text
Source code repository
Provider: GitHub
Repository: CS22M105/inventory_management_system
Branch: master or main
```

Use the branch where the production-ready code lives.

Deployment trigger:

```text
Manual for first deployment
Automatic later when CI/CD is stable
```

Recommendation:

Start with manual deployments. After confidence grows, turn on automatic deploys
only after CI is green and migrations are controlled.

### 9.3 Runtime

Choose:

```text
Runtime: Python 3
```

Use the newest Python version App Runner supports that is compatible with the
project dependencies.

### 9.4 Build command

Use:

```bash
pip install --upgrade pip && pip install -r requirements.txt
```

### 9.5 Start command

Use:

```bash
gunicorn app:app -c gunicorn.conf.py
```

### 9.6 Port

Use:

```text
8000
```

The current `gunicorn.conf.py` binds to:

```python
0.0.0.0:${PORT:-8000}
```

App Runner reserves `PORT`, so configure the service port in App Runner instead
of trying to create a custom `PORT` environment variable.

### 9.7 CPU and memory

For fewer than 50 users:

```text
CPU: 0.25 vCPU
Memory: 0.5 GB or 1 GB
```

If package build or runtime memory becomes tight, increase to:

```text
CPU: 0.5 vCPU
Memory: 1 GB
```

### 9.8 Environment variables and secrets

Add all values from Step 3.

Use secret references for:

```text
SECRET_KEY
DATABASE_URL
SMTP_PASSWORD
SMTP_USERNAME
SENTRY_DSN
```

Plain text is acceptable for:

```text
APP_ENV
APP_BASE_URL
EMAIL_PROVIDER
EMAIL_FROM
SMTP_HOST
SMTP_PORT
SMTP_USE_TLS
SMTP_USE_SSL
BARCODE_PREFIX
SESSION_IDLE_MINUTES
TRANSACTIONS_PAGE_SIZE
```

### 9.9 Networking

If RDS is private:

```text
Outgoing network traffic: custom VPC
VPC connector: katz-inventory-prod-vpc-connector
```

If App Runner cannot connect to RDS, check:

- Same region.
- Same VPC or reachable VPC.
- RDS security group allows inbound 5432 from App Runner connector security group.
- `DATABASE_URL` host, port, username, password, and DB name are correct.
- `sslmode=require` is present.

### 9.10 Create and deploy

Choose:

```text
Create and deploy
```

Wait until status is:

```text
Running
```

Open the default App Runner URL.

Expected before admin setup:

- Login page loads.
- `/health` returns JSON.

---

## Step 10 - First Production Admin Setup

The production database should not use demo users or demo passwords.

Permanent admin:

```text
Institution ID: A1001
Role: administrator
Status: active
```

### 10.1 Create first admin row

Connect to production database using a safe SQL client or local `psql`:

```bash
export DATABASE_URL='postgresql://inventory_admin:REDACTED@RDS-ENDPOINT:5432/inventory_prod?sslmode=require'
psql "$DATABASE_URL"
```

Run SQL with the real admin email:

```sql
INSERT INTO users (
    institution_id,
    email,
    name,
    role,
    department,
    is_active
)
VALUES (
    'A1001',
    'your-admin-email@example.edu',
    'Main Administrator',
    'administrator',
    'Simulation Lab',
    TRUE
)
ON CONFLICT (email) DO NOTHING;
```

Exit:

```sql
\q
```

### 10.2 Set password

Preferred:

Use App Runner shell/exec if available in your AWS setup, or run the CLI from a
trusted local terminal that can reach production RDS.

Local command:

```bash
export APP_ENV=production
export SECRET_KEY='REDACTED-SAME-SECRET-KEY-AS-PRODUCTION'
export DATABASE_URL='postgresql://inventory_admin:REDACTED@RDS-ENDPOINT:5432/inventory_prod?sslmode=require'
flask --app app set-password your-admin-email@example.edu 'YourStrongPassword123'
```

Choose a stronger real password than the example.

Important:

- The `SECRET_KEY` must match production if the command creates signed tokens.
- For direct password setting, the key may still be required because app config
  validates production security.
- Do not save this command with real secrets in shell history if possible.

Safer shell history approach:

```bash
read -s SECRET_KEY
export SECRET_KEY
read -s DATABASE_URL
export DATABASE_URL
flask --app app set-password your-admin-email@example.edu
```

If the CLI asks for the password interactively, use the prompt instead of
putting the password in the command.

### 10.3 Login test

Open:

```text
https://<your-app-runner-default-url>/login
```

Then later:

```text
https://<your-domain>/login
```

Verify:

- Admin can log in.
- Admin sees database status.
- Admin can create faculty.
- Admin cannot be deactivated/deleted.

---

## Step 11 - Connect Custom Domain, HTTPS, And HSTS

### 11.1 Route 53 domain

If the domain is already in Route 53:

1. Open App Runner service.
2. Go to custom domains.
3. Add domain:

```text
inventory.your-university.edu
```

4. App Runner/ACM will provide DNS validation records.
5. Add records in Route 53.

If the domain is managed by university IT:

Send them the DNS records App Runner gives you and ask them to add them.

### 11.2 Wait for validation

Wait until App Runner shows the domain as active/validated.

### 11.3 Set APP_BASE_URL

Update App Runner environment variable:

```text
APP_BASE_URL=https://inventory.your-university.edu
```

Redeploy App Runner so the app picks up the new value.

Why:

- Invite/reset links use this base URL.
- QR codes should encode the real HTTPS domain.

### 11.4 Verify HTTPS

Run:

```bash
curl -I https://inventory.your-university.edu
```

Expected:

```text
HTTP/2 200
```

or a valid redirect/login response.

Check HSTS:

```bash
curl -I https://inventory.your-university.edu | grep -i strict-transport-security
```

Expected:

```text
Strict-Transport-Security: ...
```

Only enable HSTS after HTTPS works correctly.

---

## Step 12 - Production Smoke Test

Run this checklist after first deploy and after every major release.

### 12.1 Public checks

```bash
curl -i https://inventory.your-university.edu/health
```

Expected:

```json
{"status":"ok","database":"ok"}
```

No login should be required for `/health`.

### 12.2 Login and role checks

Verify:

- Admin login works.
- Faculty login works.
- Student login works.
- Student cannot access admin pages.
- Faculty can manage students.
- Faculty cannot access database status.
- Admin can manage faculty and students.
- Admin database status is visible.

### 12.3 Inventory checks

Verify:

- Add new item.
- Edit item.
- View all items.
- View low stock items.
- Print full QR card.
- Print QR-only label.
- Scan QR with camera.
- Add stock.
- Remove stock.
- Transaction row is created.

### 12.4 Export checks

Verify:

- Inventory CSV export works for allowed role.
- Transaction CSV export works with filters.
- Student cannot export if policy blocks students.
- Export action is audit logged.

### 12.5 Email checks

Verify:

- Create faculty invite.
- Create student invite.
- Invite email arrives.
- Set-password link works.
- Forgot-password email arrives.
- Reset-password link works.

### 12.6 Logs and monitoring

Verify:

- App Runner logs appear in CloudWatch.
- Errors are not exposing passwords/tokens.
- Sentry receives a deliberate staging error if configured.
- `/health` is monitored.

---

## Step 13 - Backups And Restore Drill

Backups are not enough until restore has been tested.

### 13.1 Confirm automated backups

In RDS:

```text
Automated backups: enabled
Retention: 7-30 days
Latest restorable time: visible
```

### 13.2 Create manual snapshot before launch

RDS:

1. Select database.
2. Actions.
3. Take snapshot.
4. Name:

```text
katz-inventory-prod-before-launch-YYYY-MM-DD
```

### 13.3 Restore drill

Do this before real launch and then periodically.

1. Pick a recent timestamp.
2. Restore RDS to a new scratch instance.
3. Do not overwrite production.
4. Connect to scratch DB.
5. Verify:

```sql
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM items;
SELECT COUNT(*) FROM transactions;
SELECT COUNT(*) FROM audit_logs;
```

6. Confirm a known row exists.
7. Delete scratch DB after test if no longer needed.

Record:

```text
Restore drill date:
Restored by:
Source DB:
Restored DB:
Timestamp restored to:
Known row verified:
Result:
Issues:
```

### 13.4 Recovery expectations

For Phase 1 Single-AZ:

```text
RPO: usually minutes, depending on latest restorable time
RTO: could be hours if full restore is needed
```

For Phase 2 Multi-AZ:

```text
RPO: usually near-zero for AZ failure
RTO: usually minutes for automatic failover
```

Exact values depend on AWS behavior, database size, and university operational
process.

---

## Step 14 - Estimated Phase 1 Monthly Cost

These are planning estimates only. Always confirm with the AWS Pricing
Calculator before committing university budget.

Assumptions:

```text
Users: fewer than 50
Items: fewer than 500
Traffic: normal university lab usage, not public high traffic
Region: US East style pricing
Database: RDS PostgreSQL Single-AZ
App: App Runner small instance
```

Approximate monthly range:

```text
Low pilot:        $30-$60/month
Comfortable:     $50-$100/month
With extras:     $80-$150/month
```

Typical cost components:

```text
App Runner:       app CPU/memory while provisioned/active
RDS PostgreSQL:   DB instance + storage + backup storage
Route 53:         hosted zone + domain registration if needed
CloudWatch:       logs and metrics
SES:              usually low for invite/reset emails
Secrets Manager:  per secret per month if used
Data transfer:    usually low for this app
```

Cost controls:

- Set App Runner max concurrency/instances conservatively.
- Start with small RDS instance.
- Use RDS storage autoscaling with a reasonable cap.
- Set AWS Budget alerts.
- Do not create duplicate unused databases.
- Delete staging resources when not needed.
- Review CloudWatch log retention.

---

## Phase 2 - More Secure University Setup

### Goal

Upgrade from a working Phase 1 deployment to a stronger university production
environment while preserving existing data.

Phase 2 should be done after Phase 1 works and users have tested core workflows.
Do not do too many major changes at once.

### Phase 2 Architecture

```text
Users
  |
  | HTTPS
  v
Route 53
  |
  v
AWS WAF / CloudFront or platform front door if required
  |
  v
App Runner or ECS/Fargate in controlled VPC design
  |
  v
Private RDS PostgreSQL Multi-AZ

Supporting services:
- AWS Secrets Manager with rotation plan
- KMS customer-managed keys if required
- CloudWatch alarms
- Sentry
- CloudTrail
- AWS Backup / RDS snapshots
- CI/CD with migration gate
- Staging environment
```

---

## Phase 2 Data Safety Promise

The data should remain safe during Phase 2 if the upgrade is handled correctly.

Data will remain available when:

- The same RDS database is kept and only its settings are upgraded.
- A snapshot is taken before changes.
- A restored copy is tested before cutover.
- `DATABASE_URL` is changed only after validation.
- Old production DB is retained temporarily after migration.

Data can be lost if:

- The production RDS instance is deleted without final snapshot.
- The app is pointed at a new empty database by mistake.
- A destructive migration is run without testing.
- Someone manually drops tables or columns.
- Backups are disabled.
- Secrets are lost and no admin can access the system.

Golden rule:

```text
Before every infrastructure upgrade: snapshot first, test restore second,
change production third.
```

---

## Phase 2 Step A - Create Staging Environment

Before upgrading production, create staging.

Staging should have:

```text
App Runner staging service
RDS staging database
Staging custom domain, optional
Separate SECRET_KEY
Separate DATABASE_URL
Separate email settings
APP_ENV=staging or production-like staging
```

Do not use real student data in staging unless university policy explicitly
allows it.

Recommended:

- Restore production snapshot to staging.
- Scrub/anonymize user emails and names if needed.
- Test migrations and infrastructure changes there first.

Staging smoke test:

```bash
curl -i https://staging-domain/health
pytest -q
alembic upgrade head
```

---

## Phase 2 Step B - Upgrade RDS To Multi-AZ

### B.1 Take snapshot

Before changing production RDS:

```text
Manual snapshot name:
katz-inventory-prod-before-multiaz-YYYY-MM-DD
```

### B.2 Modify DB

In RDS:

1. Select production DB.
2. Modify.
3. Availability and durability.
4. Choose Multi-AZ DB instance deployment.
5. Apply during maintenance window unless urgent.

### B.3 Verify

After modification:

- DB status is available.
- Multi-AZ is enabled.
- App login works.
- `/health` returns 200.
- Add/remove stock works.
- RDS shows standby/AZ redundancy.

Expected benefit:

- Better availability.
- Automatic failover during many infrastructure failures.
- Less downtime risk than Single-AZ.

Cost impact:

Multi-AZ usually costs significantly more because AWS maintains standby
infrastructure. Budget roughly 2x or more for the database portion.

---

## Phase 2 Step C - Move To Dedicated VPC And Private Subnets

If Phase 1 used default VPC, Phase 2 should move to a dedicated VPC.

Recommended VPC layout:

```text
VPC CIDR: 10.20.0.0/16
Public subnets: for NAT/load balancer if needed
Private app subnets: for application networking
Private database subnets: for RDS
```

Security groups:

```text
App security group:
  outbound to RDS security group on 5432

RDS security group:
  inbound 5432 only from app security group
```

No production RDS public access.

Migration path:

1. Create new VPC.
2. Create private DB subnet group.
3. Restore latest production snapshot into new private RDS.
4. Test app against restored DB in staging.
5. Schedule production cutover.
6. Put app in maintenance window.
7. Stop writes or make app unavailable briefly.
8. Take final production snapshot.
9. Restore/copy final data if needed.
10. Update `DATABASE_URL`.
11. Deploy app.
12. Smoke test.
13. Keep old DB temporarily.
14. Delete old DB only after sign-off and snapshot retention.

---

## Phase 2 Step D - Secrets Manager And Rotation

Production secrets should live in Secrets Manager or SSM Parameter Store.

Use Secrets Manager for:

```text
SECRET_KEY
DATABASE_URL
SMTP_USERNAME
SMTP_PASSWORD
SENTRY_DSN
```

Use SSM Parameter Store for non-sensitive values:

```text
APP_ENV
APP_BASE_URL
BARCODE_PREFIX
SESSION_IDLE_MINUTES
TRANSACTIONS_PAGE_SIZE
```

Important:

- App Runner reads referenced secrets at deployment time.
- If a secret changes, redeploy the service so App Runner picks up the new value.
- Rotate `SECRET_KEY` only during planned maintenance because it invalidates
  sessions and pending invite/reset links.

---

## Phase 2 Step E - Use Redis For Rate Limiting

The current app can use:

```text
RATELIMIT_STORAGE_URI=memory://
```

This is acceptable for one worker/small setup, but not ideal for multiple
workers or multiple app instances.

University-grade setup:

```text
Amazon ElastiCache Redis or Valkey
RATELIMIT_STORAGE_URI=redis://<host>:6379/0
```

Why:

- Rate limits become shared across app workers.
- Login protection is more consistent.
- Scaling App Runner/ECS does not split counters per process.

---

## Phase 2 Step F - Add WAF And Stronger Edge Protection

Consider AWS WAF when the app is exposed beyond a small trusted group.

Protect against:

- Common web attacks.
- Obvious bot traffic.
- Very high request rates.
- Suspicious IP ranges if required.

Possible front doors:

```text
CloudFront + WAF -> App Runner
or
Application Load Balancer + WAF -> ECS/Fargate
```

For App Runner, confirm current AWS-supported WAF/front-door pattern with
university IT before implementation.

---

## Phase 2 Step G - CI/CD With Migration Control

The repo already has tests and migrations. Phase 2 should make deployments more
controlled.

Recommended GitHub flow:

```text
feature branch -> pull request -> CI tests -> review -> merge -> deploy
```

CI must run:

```bash
pytest -q
alembic upgrade head
alembic downgrade base
```

Deployment rules:

- Do not deploy if tests fail.
- Migrations run once per deploy, not per request.
- For AWS App Runner, use a GitHub Actions deploy workflow or CodeBuild/CodePipeline
  step that runs `alembic upgrade head` before updating the service.
- Keep manual approval for production deployments if university policy requires it.

---

## Phase 2 Step H - Monitoring, Alerts, And Logs

Minimum production monitoring:

```text
/health uptime monitor
CloudWatch logs
CloudWatch alarms
RDS CPU/storage/connections alarms
App Runner 5xx alarms
Sentry error alerts
AWS Budget alerts
```

Suggested alarms:

- App Runner service unhealthy.
- HTTP 5xx above threshold.
- RDS CPU high for 10+ minutes.
- RDS free storage low.
- RDS connections near limit.
- RDS failover event.
- Backup failure.
- Monthly cost above budget.

Logs:

- Keep app logs structured.
- Do not log passwords, tokens, cookies, invite/reset links, SMTP credentials, or
  database URLs.
- Set CloudWatch log retention, such as 30, 90, or 180 days depending on policy.

---

## Phase 2 Step I - Audit And Compliance Readiness

For university review, maintain:

- Privacy and data handling document.
- Accessibility statement.
- Data retention policy.
- CSV export policy.
- Admin notes training.
- Security and authentication plan.
- Deployment infrastructure plan.
- Restore drill records.
- Incident response process.

Audit logs should answer:

```text
who did what, when, to which record, and from where
```

Do not allow normal users to edit/delete audit log rows.

---

## Phase 2 Step J - Data Migration/Cutover Runbook

Use this when moving from Phase 1 RDS to a new, more secure RDS instance.

### J.1 Before cutover

1. Announce maintenance window.
2. Confirm latest code is deployed to staging.
3. Confirm staging can connect to the new DB.
4. Confirm backups are enabled.
5. Take manual production snapshot.
6. Restore snapshot to new DB.
7. Run migrations on new DB if needed.
8. Smoke test new DB using staging app.

### J.2 During cutover

1. Put app in maintenance mode or stop App Runner service to prevent writes.
2. Take final manual snapshot.
3. Restore final snapshot to new DB if required.
4. Update production `DATABASE_URL` secret to new DB.
5. Redeploy App Runner.
6. Run:

```bash
curl -i https://inventory.your-university.edu/health
```

7. Log in as admin.
8. Verify item count, user count, transaction count, audit count.
9. Test one add/remove stock transaction.
10. Re-enable normal use.

### J.3 After cutover

1. Keep old DB for a defined safety period, such as 7-30 days.
2. Keep final snapshot according to policy.
3. Monitor logs/errors.
4. Ask users to report issues.
5. Delete old DB only after sign-off.

### J.4 Verification SQL

Run against old and new DB and compare:

```sql
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM items;
SELECT COUNT(*) FROM transactions;
SELECT COUNT(*) FROM audit_logs;
SELECT COUNT(*) FROM alembic_version;
```

Also verify important admin row:

```sql
SELECT institution_id, email, role, is_active
FROM users
WHERE institution_id = 'A1001';
```

---

## Phase 2 Estimated Monthly Cost

Phase 2 is more secure and more expensive.

Approximate range for a small university deployment:

```text
Secure small production: $120-$300/month
More complete university setup: $250-$600/month
```

Cost increases usually come from:

- RDS Multi-AZ.
- Redis/ElastiCache.
- WAF/CloudFront.
- More logs and monitoring.
- Staging environment.
- Secrets Manager.
- Higher App Runner/ECS resources.
- Longer backup retention.

Recommended university budgeting:

```text
Phase 1 pilot budget: $100/month alert
Phase 2 production budget: $300/month alert
Phase 2 expanded budget: $600/month alert
```

Use AWS Pricing Calculator before final approval.

---

## Operational Rules For Long-Term Use

### Never do these in production

- Do not run `flask init-db` against production.
- Do not use SQLite in production.
- Do not commit `.env`.
- Do not commit `DATABASE_URL`.
- Do not commit SMTP passwords.
- Do not delete RDS without final snapshot.
- Do not expose RDS to `0.0.0.0/0`.
- Do not test destructive migrations directly on production.
- Do not use demo/default passwords.
- Do not store patient data, diagnoses, grades, SSNs, or clinical details in notes.

### Always do these

- Use Alembic migrations for schema changes.
- Take a snapshot before infrastructure upgrades.
- Test restore regularly.
- Keep backups enabled.
- Keep HTTPS enabled.
- Keep `/health` monitored.
- Keep logs available.
- Keep admin access limited.
- Review user roles periodically.
- Disable users who leave the university/lab.
- Review CSV export access.

---

## Troubleshooting

### App Runner deploy fails

Check:

```text
Build logs
requirements.txt install errors
Python runtime version
Start command
Port set to 8000
Missing environment variables
Production SECRET_KEY validation
```

### App starts but login page is slow

Check:

```text
RDS connectivity
RDS security groups
VPC connector
DATABASE_URL
RDS CPU/connections
CloudWatch logs
```

### `/health` returns 503

Likely database connection problem.

Check:

```text
DATABASE_URL
RDS endpoint
RDS status
Security groups
VPC connector
sslmode=require
Database username/password
```

### Invite email is not sent

Check:

```text
EMAIL_PROVIDER=smtp
EMAIL_FROM
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_USE_TLS
SES sandbox status
Verified sender/domain
CloudWatch logs
```

### QR links point to wrong domain

Check:

```text
APP_BASE_URL=https://inventory.your-university.edu
Redeploy after changing APP_BASE_URL
```

### Static files look broken

Check:

```text
static/ files committed
WhiteNoise installed
requirements.txt includes whitenoise
Browser cache
App Runner latest deploy
```

---

## GitHub Commands After Updating This Plan

From the project root:

```bash
cd /Users/farhatjahan/Desktop/YU/summer26/YU_internship/Sim_Intern/inventory/inventory_management_system
git status
git add design_docx/DEPLOYMENT_INFRASTRUCTURE_PLAN.md
git commit -m "Add detailed AWS deployment infrastructure plan"
git push origin master
```

If your repo uses `main`:

```bash
git push origin main
```

---

## Official AWS References

Use AWS documentation as the source of truth because service screens and prices
can change.

- AWS App Runner getting started:
  https://docs.aws.amazon.com/apprunner/latest/dg/getting-started.html
- AWS App Runner environment variables and secrets:
  https://docs.aws.amazon.com/apprunner/latest/dg/env-variable.html
- AWS App Runner custom domains:
  https://docs.aws.amazon.com/apprunner/latest/dg/manage-custom-domains.html
- Amazon RDS create DB instance:
  https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateDBInstance.html
- Amazon RDS encryption:
  https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html
- Amazon RDS PostgreSQL:
  https://aws.amazon.com/rds/postgresql/
- Amazon SES SMTP credentials:
  https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html
- Amazon SES production access:
  https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html
- AWS Pricing Calculator:
  https://calculator.aws/
- AWS App Runner pricing:
  https://aws.amazon.com/apprunner/pricing/
- Amazon RDS PostgreSQL pricing:
  https://aws.amazon.com/rds/postgresql/pricing/
- Amazon Route 53 pricing:
  https://aws.amazon.com/route53/pricing/
- AWS Secrets Manager pricing:
  https://aws.amazon.com/secrets-manager/pricing/
