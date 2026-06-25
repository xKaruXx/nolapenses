# Plan 002: Make the Docker/Nginx deploy path match Nginx Proxy Manager

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report; do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat aa27176..HEAD -- docker-compose.yml Dockerfile nginx deploy README.md package.json scripts`
> If any in-scope file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding; on a mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: MED
- **Depends on**: `plans/001-verification-baseline.md`
- **Category**: bug
- **Planned at**: commit `aa27176`, 2026-06-25

## Why this matters

`docker-compose.yml` says certificates are handled by Nginx Proxy Manager, but it mounts an Nginx config that listens on 443 and references local Let's Encrypt certificate files. In a proxy-manager setup, the app container should usually serve plain HTTP behind the proxy. Keeping both paths mixed makes deploy fragile and hard to debug.

## Current state

- `docker-compose.yml` publishes both HTTP and HTTPS:

```yaml
# docker-compose.yml:8-13
ports:
  - "6030:80"
  - "6031:443"
volumes:
  - ./:/usr/share/nginx/html:ro
  - ./nginx/conf.d:/etc/nginx/conf.d:ro
```

- The same file says Certbot is not needed because Nginx Proxy Manager handles SSL:

```yaml
# docker-compose.yml:28
# No necesitamos Certbot porque Nginx Proxy Manager maneja los certificados SSL
```

- `nginx/conf.d/default.conf` has a local HTTPS server:

```nginx
# nginx/conf.d/default.conf:18-24
listen 443 ssl http2;
listen [::]:443 ssl http2;
ssl_certificate /etc/letsencrypt/live/nolapenses.com.ar/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/nolapenses.com.ar/privkey.pem;
```

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Baseline tests | `npm test` | exit 0 |
| Compose config check | `docker compose config` | exit 0 |
| Optional container check | `docker compose up --build` | Nginx starts without missing certificate errors |

## Scope

**In scope**:
- `docker-compose.yml`
- `nginx/conf.d/default.conf`
- `README.md` deployment section if needed

**Out of scope**:
- `deploy/preview/*`, unless the production and preview config must be reconciled for the same issue.
- DNS, Cloudflare, real Nginx Proxy Manager UI, or certificate creation.
- Application HTML/JS.

## Git workflow

- Branch: `advisor/002-nginx-proxy-manager-deploy`
- Commit message example: `fix: alinear nginx con proxy manager`.
- Do not push unless instructed.

## Steps

### Step 1: Decide the intended production topology from repo evidence

Use the existing compose comment as the source of truth: Nginx Proxy Manager owns TLS outside this container. Therefore, the app container should expose only HTTP and should not reference local `/etc/letsencrypt` paths.

**Verify**: `Select-String -Path docker-compose.yml -Pattern 'Nginx Proxy Manager'` -> shows the existing comment.

### Step 2: Convert production Nginx config to HTTP-only app serving

Edit `nginx/conf.d/default.conf` to contain a single `server` block listening on `80` and `[::]:80`, with:

- `server_name nolapenses.com.ar www.nolapenses.com.ar;`
- `root /usr/share/nginx/html;`
- `index index.html;`
- static asset caching including `webp`
- `try_files $uri $uri/ /index.html;`
- hidden-file deny block
- security headers that make sense behind the proxy: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`

Remove local HTTPS redirect, `listen 443`, `ssl_certificate`, `ssl_certificate_key`, and ACME challenge config from this app container config.

**Verify**: `Select-String -Path nginx\conf.d\default.conf -Pattern 'listen 443','ssl_certificate','letsencrypt'` -> no matches.

### Step 3: Remove the HTTPS port from compose

Edit `docker-compose.yml` so `ports` only publishes `6030:80`. Remove `6031:443`. Keep the read-only volume mounts.

**Verify**: `Select-String -Path docker-compose.yml -Pattern '6031|:443'` -> no matches.

### Step 4: Update deployment docs

If `README.md` still lacks deployment instructions after Plan 001, add a short deployment note:

- local app container listens on host port `6030`
- Nginx Proxy Manager should proxy to that HTTP port
- TLS/certificates live in Nginx Proxy Manager, not inside this container

**Verify**: `Select-String -Path README.md -Pattern '6030','Nginx Proxy Manager','TLS'` -> expected lines appear.

### Step 5: Run config checks

Run:

```powershell
npm test
docker compose config
```

If Docker is available and the operator allows starting containers, run:

```powershell
docker compose up --build
```

Then stop with Ctrl+C after confirming Nginx starts. Do not leave the service running unless instructed.

**Verify**: `docker compose config` exits 0; optional `docker compose up --build` shows no missing certificate errors.

## Test plan

- Static validation from Plan 001 must pass.
- `docker compose config` must pass.
- Optional runtime check confirms Nginx can start without `/etc/letsencrypt` files.

## Done criteria

- [ ] `npm test` exits 0.
- [ ] `docker compose config` exits 0.
- [ ] No `listen 443`, `ssl_certificate`, or `letsencrypt` references remain in `nginx/conf.d/default.conf`.
- [ ] `docker-compose.yml` exposes only `6030:80` for the app service.
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report back if:

- The operator says this container, not Nginx Proxy Manager, must terminate TLS.
- Production depends on the `/.well-known/acme-challenge/` path inside this container.
- Docker is unavailable and `docker compose config` cannot be run; still complete file edits only if Plan 001 tests pass.

## Maintenance notes

If the hosting topology changes later, choose one TLS owner and document it. Do not keep proxy-manager comments and in-container certificate paths in the same production compose path.
