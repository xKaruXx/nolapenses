(() => {
  const config = window.CONFIG && window.CONFIG.recaptcha;
  const siteKey = (config && config.siteKey) || '6LewPjItAAAAAKxBzvxrNqqWD0iyuLB2faWKFAMh';
  const actionPrefix = (config && config.actionPrefix) || 'nolapenses';

  if (!siteKey) {
    window.NolapensesRecaptcha = {
      ready: () => Promise.resolve(false),
      getToken: () => Promise.resolve(''),
      attach: (payload) => Promise.resolve(payload || {})
    };
    return;
  }

  let loadPromise;

  function loadScript() {
    if (window.grecaptcha && window.grecaptcha.execute) return Promise.resolve(true);
    if (loadPromise) return loadPromise;

    loadPromise = new Promise((resolve) => {
      const existing = document.querySelector('script[src*="google.com/recaptcha/api.js"]');
      if (existing) {
        existing.addEventListener('load', () => resolve(true), { once: true });
        existing.addEventListener('error', () => resolve(false), { once: true });
        return;
      }

      const script = document.createElement('script');
      script.src = `https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(siteKey)}`;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.head.appendChild(script);
    });

    return loadPromise;
  }

  function normalizeAction(action) {
    return `${actionPrefix}_${String(action || 'submit')}`.replace(/[^a-zA-Z0-9_]/g, '_').slice(0, 100);
  }

  async function ready() {
    const loaded = await loadScript();
    if (!loaded || !window.grecaptcha || !window.grecaptcha.ready) return false;
    return new Promise((resolve) => window.grecaptcha.ready(() => resolve(true)));
  }

  async function getToken(action = 'submit') {
    const isReady = await ready();
    if (!isReady || !window.grecaptcha || !window.grecaptcha.execute) return '';
    try {
      return await window.grecaptcha.execute(siteKey, { action: normalizeAction(action) });
    } catch (error) {
      if (window.NolapensesAnalytics) {
        window.NolapensesAnalytics.track('recaptcha_client_error', {
          action: normalizeAction(action),
          message: String(error && error.message || error)
        });
      }
      return '';
    }
  }

  async function attach(payload = {}, action = 'submit') {
    const token = await getToken(action);
    return {
      ...payload,
      recaptcha_token: token,
      recaptcha_action: normalizeAction(action)
    };
  }

  window.NolapensesRecaptcha = { ready, getToken, attach };
})();
