# Plan 003: Centralize lead widget config, tracking, and reCAPTCHA loading

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report; do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat aa27176..HEAD -- assets/js index.html portafolio.html privacidad responsabilidad-usuario notas package.json scripts`
> If any in-scope file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding; on a mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: `plans/001-verification-baseline.md`
- **Category**: bug
- **Planned at**: commit `aa27176`, 2026-06-25

## Why this matters

The site has several lead entry points: home, portfolio, notes, privacy, and user responsibility pages. Home and portfolio load `config.js` and `main.js`; several other pages load the lead widget without `config.js`, `conversion-tracking.js`, or `recaptcha-guard.js`. That creates inconsistent webhook URLs, tracking, and security metadata across pages that should all capture leads the same way.

## Current state

- Home and portfolio load the full stack:

```html
<!-- index.html:1749-1755 -->
<script src="assets/js/config.js?v=20260624-recaptcha"></script>
<script src="assets/js/main.js?v=20260623"></script>
<script src="/assets/js/recaptcha-guard.js?v=20260624bb" defer></script>
<script src="/assets/js/conversion-tracking.js?v=20260624" defer></script>
<script src="/assets/js/lead-chat-widget.js?v=20260624b" defer></script>
```

- Notes index only loads the notes script and lead widget:

```html
<!-- notas/index.html:45 -->
<script src="/assets/js/notas.js?v=20260622" defer></script>
<script src="/assets/js/lead-chat-widget.js?v=20260623" defer></script>
```

- Some article pages load only `lead-chat-widget.js` with an older version parameter:

```html
<!-- notas/agente-voz-turnos-recordatorios-ia/index.html:71 -->
<script src="/assets/js/lead-chat-widget.js?v=20260623" defer></script>
```

- `lead-chat-widget.js` falls back to a hardcoded webhook when `CONFIG` is missing:

```js
// assets/js/lead-chat-widget.js:2
const WEBHOOK_URL = (window.CONFIG && CONFIG.webhooks && (CONFIG.webhooks.newLead || CONFIG.webhooks.chatbot)) || 'https://n8n.nolapenses.com.ar/webhook/nolapenses-chatbot-leads';
```

Do not copy any token or secret value from `assets/js/config.js` into docs or comments while implementing this plan.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Baseline tests | `npm test` | exit 0 |
| Search script usage | `rg -n "lead-chat-widget|recaptcha-guard|conversion-tracking|config.js" index.html portafolio.html privacidad responsabilidad-usuario notas` | expected scripts appear consistently |

## Scope

**In scope**:
- `assets/js/lead-chat-widget.js`
- `assets/js/recaptcha-guard.js`
- `assets/js/conversion-tracking.js`
- `index.html`
- `portafolio.html`
- `privacidad/index.html`
- `responsabilidad-usuario/index.html`
- `notas/index.html`
- `notas/*/index.html`
- `scripts/validate-site.mjs` if Plan 001 created it and needs one extra assertion

**Out of scope**:
- Rewriting `assets/js/main.js`.
- Changing form copy, article content, or visual layout.
- Changing backend n8n workflows.

## Git workflow

- Branch: `advisor/003-centralize-lead-widget-bootstrap`
- Commit message example: `fix: unificar carga del widget de leads`.
- Do not push unless instructed.

## Steps

### Step 1: Introduce a single bootstrap script or consistent include block

Preferred path: create `assets/js/lead-bootstrap.js` that loads or expects these dependencies in order:

1. `config.js`
2. `conversion-tracking.js`
3. `recaptcha-guard.js`
4. `lead-chat-widget.js`

Keep it simple. Since static pages can load scripts directly, an acceptable alternative is to add the same four script tags to every page that uses the widget. The important rule: every page with `lead-chat-widget.js` must also load `config.js`, `conversion-tracking.js`, and `recaptcha-guard.js` before the widget initializes.

Use absolute `/assets/js/...` paths for pages below subdirectories. Root pages may also use absolute paths for consistency.

**Verify**: `rg -n "lead-chat-widget" index.html portafolio.html privacidad responsabilidad-usuario notas` -> every hit is near `config.js`, `conversion-tracking.js`, and `recaptcha-guard.js`.

### Step 2: Remove hardcoded production webhook fallback from the widget

In `assets/js/lead-chat-widget.js`, replace the one-line hardcoded fallback with an explicit config lookup. If config is unavailable, disable webhook submission but keep the WhatsApp fallback visible.

Target behavior:

- `WEBHOOK_URL` comes only from `window.CONFIG.webhooks.newLead` or `window.CONFIG.webhooks.chatbot`.
- If no webhook URL exists, the widget tracks a `lead_chat_config_missing` event when possible and does not call `fetch`.
- The final bot message still offers the WhatsApp link.

**Verify**: `Select-String -Path assets\js\lead-chat-widget.js -Pattern 'n8n.nolapenses.com.ar'` -> no matches in this file.

### Step 3: Make the widget event names match the analytics doc

`docs/seo-analytics-campanas.md` names `lead_chat_opened` and `lead_chat_submitted`. The widget currently tracks `lead_chat_completed` and `generate_lead`. Add or rename tracking so a successful final submit emits `lead_chat_submitted` with classification fields. Keep `generate_lead` if it is used by GA4 conversions.

**Verify**: `Select-String -Path assets\js\lead-chat-widget.js -Pattern 'lead_chat_submitted','generate_lead'` -> both appear.

### Step 4: Extend the static validator

If Plan 001 created `scripts/validate-site.mjs`, add a rule:

- any HTML file containing `lead-chat-widget.js` must also contain `config.js`, `conversion-tracking.js`, and `recaptcha-guard.js`.

**Verify**: `npm test` -> exit 0.

### Step 5: Run final checks

Run:

```powershell
npm test
rg -n "lead-chat-widget|recaptcha-guard|conversion-tracking|config.js" index.html portafolio.html privacidad responsabilidad-usuario notas
```

Expected: tests pass and every widget page has the shared dependencies.

## Test plan

- Static validator confirms local asset files exist and widget dependencies are complete.
- Search confirms no hardcoded production webhook remains inside `lead-chat-widget.js`.
- Manual browser smoke test, if available: open `/notas/`, open the chat widget, answer through final step, and confirm the WhatsApp CTA still appears even if webhook submission fails.

## Done criteria

- [ ] `npm test` exits 0.
- [ ] Every HTML page that loads `lead-chat-widget.js` also loads config, tracking, and recaptcha guard first.
- [ ] `assets/js/lead-chat-widget.js` no longer hardcodes the production webhook URL.
- [ ] `lead_chat_submitted` is emitted when widget lead collection completes.
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report back if:

- A page intentionally must not load reCAPTCHA or tracking due to legal/privacy requirements.
- The widget cannot be made config-driven without changing backend workflow assumptions.
- The static validator from Plan 001 does not exist and the operator does not want to create/extend it.

## Maintenance notes

Any future page that includes the lead widget must use the same bootstrap path. Reviewers should reject isolated `lead-chat-widget.js` includes because they recreate the original inconsistency.
