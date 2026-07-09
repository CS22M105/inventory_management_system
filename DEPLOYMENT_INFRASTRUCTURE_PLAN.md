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
Continuous Integration and Continuous Deployement/Delivery.

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
[ ] Static assets served by WhiteNoise with cache headers
[ ] Gunicorn tuned (workers/threads/timeout) and binding to $PORT
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
