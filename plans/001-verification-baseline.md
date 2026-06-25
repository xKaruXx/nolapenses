# Plan 001: Establish a repo verification baseline

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report; do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat aa27176..HEAD -- package.json package-lock.json README.md assets/js index.html portafolio.html privacidad responsabilidad-usuario notas docker-compose.yml nginx`
> If any in-scope file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding; on a mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: tests
- **Planned at**: commit `aa27176`, 2026-06-25

## Why this matters

The repo has real production surfaces: static HTML, shared JavaScript, Nginx config, sitemap, notes, and lead capture. Today `npm test` intentionally fails, so there is no one-command signal that a future change did not break script references, SEO files, or deploy config. This plan adds a lightweight read-only validation baseline before any risky fix.

## Current state

- `package.json` defines only CSS build plus a failing placeholder test:

```json
// package.json:6-8
"scripts": {
  "build:css": "tailwindcss -i assets/css/tailwind-input.css -o assets/css/tailwind.css --cwd . --minify",
  "test": "echo \"Error: no test specified\" && exit 1"
}
```

- `npm audit --audit-level=high` was run during recon and returned 0 vulnerabilities.
- `npm test` was run during recon and failed with the placeholder message.
- The repo is a static site with HTML at repo root, assets under `assets/`, notes under `notas/`, and Docker/Nginx deployment files.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Dependency audit | `npm audit --audit-level=high` | exit 0, 0 high/critical vulnerabilities |
| CSS build check | `npm run build:css` | exit 0; may rewrite `assets/css/tailwind.css` |
| New test command | `npm test` | exit 0 after this plan |

## Scope

**In scope**:
- `package.json`
- `package-lock.json` only if adding a dev dependency is absolutely necessary
- `scripts/validate-site.mjs` or `scripts/validate-site.js` (create)
- `README.md` only to document the verification command

**Out of scope**:
- Changing production HTML content.
- Reformatting generated `assets/css/tailwind.css`.
- Adding a heavy browser/e2e framework. Keep this baseline simple.

## Git workflow

- Branch: `advisor/001-verification-baseline`
- Commit message style: use the repo's conventional-ish style, for example `chore: agregar verificacion basica del sitio`.
- Do not push unless instructed.

## Steps

### Step 1: Replace the placeholder test script

In `package.json`, change `test` to run a local validation script, for example:

```json
"test": "node scripts/validate-site.mjs"
```

Do not change `build:css`.

**Verify**: `node -e "const p=require('./package.json'); if(!p.scripts.test.includes('validate-site')) process.exit(1)"` -> exit 0.

### Step 2: Create a static validation script

Create `scripts/validate-site.mjs`. Use only Node standard library unless a strong reason appears. The script should:

- Confirm required files exist: `index.html`, `portafolio.html`, `robots.txt`, `sitemap.xml`, `assets/js/config.js`, `assets/js/main.js`, `assets/js/lead-chat-widget.js`, `assets/css/tailwind.css`.
- Parse all local `.html` files under root pages, `privacidad/`, `responsabilidad-usuario/`, and `notas/`.
- For each local `<script src>` and `<link rel="stylesheet" href>`, verify the target file exists. Ignore external `https://...` URLs.
- Confirm every `sitemap.xml` `<loc>` path that points to `https://nolapenses.com.ar/` maps to a local file or directory with `index.html`.
- Confirm `robots.txt` includes `Sitemap: https://nolapenses.com.ar/sitemap.xml`.
- Print clear pass/fail messages and exit 1 on any failure.

Implementation hint: use `fs.readdirSync` recursion, regex extraction for `src="..."` and `href="..."`, and `new URL(localPath, 'https://nolapenses.com.ar/current/page/')` only for path normalization. Do not fetch the network.

**Verify**: `node scripts/validate-site.mjs` -> exit 0 and prints a short success summary.

### Step 3: Wire the test command and document it

Run `npm test`. If it passes, add a short README section:

```markdown
## Verification

- `npm test` validates local HTML asset links, sitemap paths, robots.txt, and required site files.
- `npm run build:css` rebuilds `assets/css/tailwind.css`.
```

**Verify**: `npm test` -> exit 0.

## Test plan

- The validation script itself is the first test layer.
- Manual negative check: temporarily run the script logic against a fake missing file by changing a local variable or adding a one-off local assertion, then remove the fake case before commit. Do not leave intentional failures in the repo.
- Final verification: `npm test` exits 0.

## Done criteria

- [ ] `npm test` exits 0.
- [ ] `npm audit --audit-level=high` exits 0.
- [ ] `node scripts/validate-site.mjs` exits 0.
- [ ] No production files changed except `README.md` and `package.json` unless `package-lock.json` was legitimately needed.
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report back if:

- The repo already has a validation script or CI file not seen in the current state.
- Validating local HTML references requires installing a large dependency.
- `npm run build:css` rewrites unrelated CSS and the operator did not ask for generated CSS churn.

## Maintenance notes

This baseline is intentionally narrow. Future plans can add Playwright, Lighthouse, accessibility, or visual checks, but this first command should stay fast and deterministic.
