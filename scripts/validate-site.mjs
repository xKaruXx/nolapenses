#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const errors = [];
const requiredFiles = [
  'index.html',
  'portafolio.html',
  'robots.txt',
  'sitemap.xml',
  'assets/js/config.js',
  'assets/js/main.js',
  'assets/js/lead-chat-widget.js',
  'assets/css/tailwind.css',
];

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

function walk(dir, predicate, out = []) {
  const full = path.join(root, dir);
  if (!fs.existsSync(full)) return out;
  for (const entry of fs.readdirSync(full, { withFileTypes: true })) {
    const rel = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(rel, predicate, out);
    else if (predicate(rel)) out.push(rel);
  }
  return out;
}

function normalizeLocalRef(ref, fromFile) {
  if (!ref || /^(https?:|mailto:|tel:|#|javascript:)/i.test(ref)) return null;
  const clean = ref.split('#')[0].split('?')[0];
  if (!clean || clean === '/') return null;
  if (clean.startsWith('/')) return clean.slice(1);
  return path.normalize(path.join(path.dirname(fromFile), clean));
}

for (const file of requiredFiles) {
  if (!exists(file)) errors.push(`Missing required file: ${file}`);
}

const htmlFiles = [
  ...walk('.', (rel) => rel.endsWith('.html') && !rel.startsWith('node_modules/')),
].sort();

for (const file of htmlFiles) {
  const html = fs.readFileSync(path.join(root, file), 'utf8');
  const refs = [];
  for (const match of html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi)) refs.push(match[1]);
  for (const match of html.matchAll(/<link\b[^>]*\brel=["'][^"']*stylesheet[^"']*["'][^>]*\bhref=["']([^"']+)["'][^>]*>/gi)) refs.push(match[1]);
  for (const ref of refs) {
    const local = normalizeLocalRef(ref, file);
    if (local && !exists(local)) errors.push(`${file}: missing local asset ${ref} -> ${local}`);
  }
  if (html.includes('lead-chat-widget.js')) {
    for (const dep of ['config.js', 'conversion-tracking.js']) {
      if (!html.includes(dep)) errors.push(`${file}: lead widget requires ${dep}`);
    }
    if (!html.includes('human-check.js') && !html.includes('recaptcha-guard.js')) {
      errors.push(`${file}: lead widget requires human-check.js or recaptcha-guard.js`);
    }
  }
}

const robots = exists('robots.txt') ? fs.readFileSync(path.join(root, 'robots.txt'), 'utf8') : '';
if (!robots.includes('Sitemap: https://nolapenses.com.ar/sitemap.xml')) {
  errors.push('robots.txt must include Sitemap: https://nolapenses.com.ar/sitemap.xml');
}

if (exists('sitemap.xml')) {
  const xml = fs.readFileSync(path.join(root, 'sitemap.xml'), 'utf8');
  for (const match of xml.matchAll(/<loc>https:\/\/nolapenses\.com\.ar\/([^<]*)<\/loc>/g)) {
    const route = decodeURI(match[1] || '');
    const rel = route.replace(/^\/+|\/+$/g, '');
    const candidates = rel ? [rel, path.join(rel, 'index.html')] : ['index.html'];
    if (!candidates.some(exists)) errors.push(`sitemap.xml: ${match[0]} does not map to a local file`);
  }
}

if (errors.length) {
  console.error(`Site validation failed (${errors.length} issue${errors.length === 1 ? '' : 's'}):`);
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log(`Site validation passed: ${htmlFiles.length} HTML files, ${requiredFiles.length} required files, sitemap and robots OK.`);
