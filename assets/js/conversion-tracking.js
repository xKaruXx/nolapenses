(() => {
  const ATTRIBUTION_KEY = 'nolapenses_attribution_v1';
  const UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'gclid', 'fbclid'];

  function readAttribution() {
    const params = new URLSearchParams(window.location.search);
    const current = {};
    UTM_KEYS.forEach((key) => {
      const value = params.get(key);
      if (value) current[key] = value;
    });

    let stored = {};
    try { stored = JSON.parse(sessionStorage.getItem(ATTRIBUTION_KEY) || '{}'); } catch {}

    if (Object.keys(current).length && !stored.first_landing_page) {
      stored = {
        ...current,
        first_landing_page: window.location.href,
        first_referrer: document.referrer || '',
        captured_at: new Date().toISOString()
      };
      try { sessionStorage.setItem(ATTRIBUTION_KEY, JSON.stringify(stored)); } catch {}
    }

    return {
      ...stored,
      ...current,
      landing_page: stored.first_landing_page || window.location.href,
      current_page: window.location.href,
      page_path: window.location.pathname,
      referrer: stored.first_referrer || document.referrer || ''
    };
  }

  function track(eventName, detail = {}) {
    const payload = {
      source: 'nolapenses_web',
      ...readAttribution(),
      ...detail
    };
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: eventName, ...payload });
    if (typeof window.gtag === 'function') {
      window.gtag('event', eventName, payload);
    }
  }

  window.NolapensesAnalytics = { track, readAttribution };

  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    const button = event.target.closest('button, [role="button"]');

    if (link) {
      const href = link.getAttribute('href') || '';
      const text = (link.textContent || link.getAttribute('aria-label') || link.title || '').trim().slice(0, 120);
      const detail = {
        link_url: link.href,
        link_text: text,
        link_id: link.id || '',
        link_classes: link.className || ''
      };

      if (/wa\.me|api\.whatsapp\.com/i.test(href)) {
        track('whatsapp_click', { ...detail, contact_method: 'whatsapp' });
        track('contact_click', { ...detail, contact_method: 'whatsapp' });
        return;
      }
      if (/^mailto:/i.test(href)) {
        track('contact_click', { ...detail, contact_method: 'email' });
        return;
      }
      if (/^tel:/i.test(href)) {
        track('contact_click', { ...detail, contact_method: 'phone' });
        return;
      }
      if (link.hostname && link.hostname !== window.location.hostname) {
        track('outbound_click', { ...detail, outbound_domain: link.hostname });
      }
    }

    if (button && button.classList.contains('lead-chat-button')) {
      track('chat_button_click', { button_text: 'floating_chat' });
    }
  }, { capture: true });

  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    track('form_submit_attempt', {
      form_id: form.id || '',
      form_name: form.getAttribute('name') || '',
      form_classes: form.className || ''
    });
  }, { capture: true });
})();
