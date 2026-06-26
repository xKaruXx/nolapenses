# NoLaPenses Landing Page

Interactive and immersive landing page for nolapenses.com.ar, offering digital automations, web page creation, custom AI chatbots, custom systems, and WhatsApp AI assistance.

## Core Concept
"No la penses... ¡Nosotros lo hacemos por vos!" (Don't think about it... We do it for you!)

## Features
- Dynamic AI-powered welcome
- Emotional interaction with emoji selection
- Voice recording and AI transcription
- WhatsApp integration
- n8n automations

## Technologies
- Frontend: HTML5, Tailwind CSS, Alpine.js
- Backend: PHP 8.1 with CodeIgniter 4
- Integrations: WhatsApp API (via n8n), OpenAI for voice, Web Speech API

## Setup
1. Clone this repository
2. Configure your web server to point to the public directory
3. Update the webhook URLs in `public/assets/js/config.js` if needed

## Requirements
- PHP 8.1+
- Composer
- Web server (Apache/Nginx)

## Verification

- `npm test` validates local HTML asset links, sitemap paths, robots.txt, required site files, and lead widget dependencies.
- `npm run build:css` rebuilds `assets/css/tailwind.css`.

## Security notes for lead webhooks

- Browser metadata is public and must not be used as a webhook authorization secret.
- n8n/server-side flows should verify reCAPTCHA with the secret stored only in n8n/server environment.
- Lead webhooks should reject malformed payloads, apply rate limits, and log only necessary lead fields.
- If any old browser header/token was used as an authorization gate, rotate it and remove that dependency in n8n.
