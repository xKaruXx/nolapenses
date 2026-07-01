# Plan 004: Replace the public client token with explicit non-secret request metadata

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report; do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat aa27176..HEAD -- assets/js index.html portafolio.html privacidad responsabilidad-usuario notas docs README.md package.json scripts`
> If any in-scope file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding; on a mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: `plans/001-verification-baseline.md`, `plans/003-centralize-lead-widget-bootstrap.md`
- **Category**: security
- **Planned at**: commit `aa27176`, 2026-06-25

## Why this matters

The browser bundle contains a `CLIENT_TOKEN` value and injects it as `X-NLP-Client-Token` for webhook requests. Any value shipped to browsers is public, so it cannot be treated as a server-side secret. If n8n currently uses this value as an authorization secret, it should be rotated and replaced with server-side validation such as reCAPTCHA verification, origin checks, rate limiting, and schema validation.

## Current state

- `assets/js/config.js:8` defines `CLIENT_TOKEN`. Do not copy its value into this plan, comments, commit messages, or issues.
- `assets/js/main.js` injects the header:

```js
// assets/js/main.js:1823-1826
const isWebhook = typeof url === 'string' && url.includes('webhook');
if (isWebhook && typeof CONFIG !== 'undefined' && CONFIG.CLIENT_TOKEN) {
    options.headers['X-NLP-Client-Token'] = CONFIG.CLIENT_TOKEN;
}
```

- `recaptcha-guard.js` already attaches `recaptcha_token` and `recaptcha_action` to payloads when available.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Baseline tests | `npm test` | exit 0 |
| Search token references | `rg -n "CLIENT_TOKEN|X-NLP-Client-Token" assets index.html portafolio.html privacidad responsabilidad-usuario notas docs README.md` | no production dependency on secret-like token remains |
| Dependency audit | `npm audit --audit-level=high` | exit 0 |

## Scope

**In scope**:
- `assets/js/config.js`
- `assets/js/main.js`
- `assets/js/lead-chat-widget.js` if Plan 003 introduced shared request helpers there
- `docs/seo-analytics-campanas.md` or `README.md` for operational notes
- `scripts/validate-site.mjs` if a validation rule is useful

**Out of scope**:
- Editing n8n workflows directly unless the operator explicitly provides access and asks for it.
- Adding a server backend to this static repo.
- Publishing the old token value anywhere.

## Git workflow

- Branch: `advisor/004-public-client-token`
- Commit message example: `fix: quitar token cliente como secreto`.
- Do not push unless instructed.

## Steps

### Step 1: Rename the browser-side concept away from "security token"

In `assets/js/config.js`, remove `CLIENT_TOKEN` or replace it with clearly non-secret metadata, for example:

```js
requestMetadata: {
  source: 'nolapenses_web'
}
```

Update comments to say browser metadata is public and must not authorize requests. Keep the public reCAPTCHA site key; that key is intentionally public.

**Verify**: `Select-String -Path assets\js\config.js -Pattern 'CLIENT_TOKEN','Token de seguridad'` -> no matches.

### Step 2: Remove automatic secret-like header injection

In `assets/js/main.js`, remove the `X-NLP-Client-Token` injection branch. Keep the local webhook mocking behavior if still needed, but do not depend on a token header.

If Plan 003 created a shared fetch helper, make the change there instead of leaving duplicate behavior.

**Verify**: `rg -n "X-NLP-Client-Token|CLIENT_TOKEN" assets/js` -> no matches, unless a migration note intentionally references the names in docs outside runtime code.

### Step 3: Ensure every lead payload carries public metadata and reCAPTCHA

For all lead submissions:

- include `source: 'nolapenses_web'` or the existing source field
- include `page_url` or `current_page`
- include attribution fields from `conversion-tracking.js` or widget attribution
- attach `recaptcha_token` and `recaptcha_action` when `window.NolapensesRecaptcha` is available

Do not add sensitive values to payloads. Do not send the removed client token under a different name.

**Verify**: `rg -n "recaptcha_token|recaptcha_action|source: 'nolapenses|source: \"nolapenses" assets/js` -> lead paths show recaptcha and source metadata.

### Step 4: Add backend migration note for n8n

Add a short note to `README.md` or `docs/seo-analytics-campanas.md`:

- Browser tokens are public and must not be used as webhook authorization secrets.
- n8n should verify reCAPTCHA server-side using the secret stored only in n8n/server environment.
- n8n should reject malformed payloads, apply rate limits, and log only necessary lead fields.
- If the old header was used as an authorization gate, rotate the old value and remove that dependency in n8n.

Do not include the old token value.

**Verify**: `Select-String -Path README.md,docs\seo-analytics-campanas.md -Pattern 'Browser tokens are public','reCAPTCHA','rotate'` -> expected note appears in whichever file you edited.

### Step 5: Run final checks

Run:

```powershell
npm test
npm audit --audit-level=high
rg -n "CLIENT_TOKEN|X-NLP-Client-Token" assets index.html portafolio.html privacidad responsabilidad-usuario notas
```

Expected: tests and audit pass; runtime files have no old token/header references.

## Test plan

- Static validator passes.
- Search confirms no runtime reference to `CLIENT_TOKEN` or `X-NLP-Client-Token`.
- Manual browser smoke test, if available: submit a local lead path and confirm payload still includes reCAPTCHA fields when the API is available.
- Backend/n8n verification must be done separately by an operator with access.

## Done criteria

- [x] `npm test` exits 0.
- [x] `npm audit --audit-level=high` exits 0.
- [x] Runtime JS no longer contains `CLIENT_TOKEN` or `X-NLP-Client-Token`.
- [x] Docs explicitly state browser metadata is public and n8n must validate reCAPTCHA server-side.
- [x] Old token value was not copied into any new file, comment, commit message, or issue.
- [x] `plans/README.md` status row updated.

## STOP conditions

Stop and report back if:

- n8n rejects all leads without the old header and no one can update the workflow.
- The operator says the old value is currently used as a temporary production gate and cannot be removed today.
- You find another committed secret or private credential. Reference only file and line, do not copy the value.

## Maintenance notes

After this plan lands, the real security boundary is outside the static site: n8n/server-side reCAPTCHA verification, schema validation, throttling, and logging discipline. Reviewers should treat any future "secret" added to browser JavaScript as public by default.
