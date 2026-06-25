(() => {
  const WEBHOOK_URL = (window.CONFIG && CONFIG.webhooks && (CONFIG.webhooks.newLead || CONFIG.webhooks.chatbot)) || 'https://n8n.nolapenses.com.ar/webhook/nolapenses-chatbot-leads';
  const CARLOS_WHATSAPP = '5492665267159';
  const STORAGE_KEY = 'nolapenses_lead_chat_state_v2';

  const questions = [
    { key: 'need', text: 'Hola 👋 Soy el asistente de IA de Nolapenses. Contame en una frase: ¿qué querés ordenar o automatizar en tu negocio?', placeholder: 'Ej: recibo muchas consultas por WhatsApp y respondo tarde...' },
    { key: 'business', text: 'Perfecto. ¿Qué tipo de negocio o rubro tenés?', placeholder: 'Ej: inmobiliaria, consultorio, tienda, servicio técnico...' },
    { key: 'volume', text: '¿Por dónde te escriben hoy y qué volumen manejás?', placeholder: 'Ej: WhatsApp e Instagram, 20 consultas por día...' },
    { key: 'urgency', text: '¿Qué tan urgente es resolverlo y vos participás en la decisión?', placeholder: 'Ej: este mes, decido yo / lo ve mi socio...' },
    { key: 'name', text: 'Genial. ¿Cómo te llamás?', placeholder: 'Tu nombre' },
    { key: 'contact', text: 'Último paso: dejame tu WhatsApp o email para que podamos contactarte y ayudarte a resolverlo.', placeholder: 'WhatsApp o email' }
  ];

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }

  function classifyLead(data) {
    const text = Object.values(data).join(' ').toLowerCase();
    const hasBusiness = Boolean((data.business || '').trim());
    const clearProblem = Boolean((data.need || '').trim().length > 18);
    const repetitive = /(much[ao]s?|varios|diari|semana|consultas|mensajes|repetitiv|turnos|agenda|ventas|leads|clientes|carritos|soporte)/i.test(text);
    const channel = /(whatsapp|instagram|facebook|messenger|web|landing|redes)/i.test(text);
    const urgent = /(urgente|ya|hoy|esta semana|este mes|rápido|rapido|perdiendo|pierdo|no perder|tarde)/i.test(text);
    const decision = /(decido|dueñ|duen|socio|gerente|director|fundador|owner|yo lo veo|mi negocio)/i.test(text);
    let score = 0;
    if (hasBusiness) score += 2;
    if (clearProblem) score += 2;
    if (repetitive) score += 2;
    if (channel) score += 1;
    if (urgent) score += 2;
    if (decision) score += 1;
    const intentRules = [
      ['automatizar WhatsApp/atención', /(whatsapp|atenci[oó]n|responder|consultas|mensajes|soporte)/i],
      ['agenda/turnos/seguimiento', /(agenda|turno|reserva|seguimiento|recordatorio)/i],
      ['contenido/redes', /(contenido|redes|instagram|facebook|linkedin|publicar|posteos)/i],
      ['integración de herramientas', /(integrar|crm|sheet|excel|drive|sistema|api|n8n|herramientas)/i],
      ['web/landing', /(web|landing|sitio|p[aá]gina)/i],
      ['IA privada/conocimiento interno', /(documentos|manuales|conocimiento|interno|drive|pol[ií]ticas|procedimientos)/i]
    ];
    const intent = (intentRules.find(([, regex]) => regex.test(text)) || ['consulta general'])[0];
    const level = score >= 8 ? 'caliente' : score >= 5 ? 'tibio' : 'frío';
    return { score, level, intent };
  }

  function getAttribution() {
    const params = new URLSearchParams(location.search);
    const keys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'gclid', 'fbclid'];
    const current = keys.reduce((acc, key) => {
      const value = params.get(key);
      if (value) acc[key] = value;
      return acc;
    }, {});
    const storageKey = 'nolapenses_attribution_v1';
    let stored = {};
    try { stored = JSON.parse(sessionStorage.getItem(storageKey) || '{}'); } catch {}
    if (Object.keys(current).length && !stored.first_landing_page) {
      stored = {
        ...current,
        first_landing_page: location.href,
        first_referrer: document.referrer || '',
        captured_at: new Date().toISOString()
      };
      sessionStorage.setItem(storageKey, JSON.stringify(stored));
    }
    return {
      ...stored,
      ...current,
      landing_page: stored.first_landing_page || location.href,
      current_page: location.href,
      referrer: stored.first_referrer || document.referrer || ''
    };
  }

  function summaryText(data, classification, attribution = getAttribution()) {
    return [
      'Nuevo lead web — Nolapenses',
      `Nombre/contacto: ${data.name || '-'} / ${data.contact || '-'}`,
      `Negocio/rubro: ${data.business || '-'}`,
      `Necesidad: ${data.need || '-'}`,
      `Canal/volumen: ${data.volume || '-'}`,
      `Urgencia/decisión: ${data.urgency || '-'}`,
      `Intención: ${classification.intent}`,
      `Nivel: ${classification.level} (${classification.score}/10)`,
      `Origen campaña: ${attribution.utm_source || '-'} / ${attribution.utm_medium || '-'} / ${attribution.utm_campaign || '-'}`,
      `Contenido: ${attribution.utm_content || '-'} · Término: ${attribution.utm_term || '-'}`,
      `Landing: ${attribution.landing_page || location.href}`,
      `Página actual: ${location.href}`
    ].join('\n');
  }

  function publicWhatsAppText(data) {
    const name = (data.name || '').trim();
    const need = (data.need || '').trim();
    return [
      `Hola, soy ${name || 'un contacto de la web'}. Estuve hablando con el asistente de Nolapenses y quiero que me contacten.`,
      need ? `Quiero resolver esto: ${need}` : 'Quiero consultar por automatizaciones con IA para mi negocio.'
    ].join('\n');
  }

  function track(eventName, detail = {}) {
    const payload = { source: 'web_lead_chat', ...getAttribution(), ...detail };
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: eventName, ...payload });
    if (typeof window.gtag === 'function') window.gtag('event', eventName, payload);
  }

  function createWidget() {
    if (document.querySelector('[data-lead-chat-widget]')) return;
    const root = document.createElement('section');
    root.className = 'lead-chat-widget';
    root.dataset.leadChatWidget = 'true';
    root.innerHTML = `
      <button class="lead-chat-button" type="button" aria-expanded="false" aria-controls="lead-chat-panel" aria-label="Abrir asistente de IA de Nolapenses">
        <span class="lead-chat-button-icon" aria-hidden="true">💬</span>
      </button>
      <div class="lead-chat-panel" id="lead-chat-panel" role="dialog" aria-modal="false" aria-label="Asistente de IA de Nolapenses" hidden>
        <div class="lead-chat-header">
          <div class="lead-chat-avatar" aria-hidden="true">🤖</div>
          <div class="lead-chat-title">
            <strong>Asistente de IA</strong>
            <span><i></i> en línea · te hago unas preguntas rápidas</span>
          </div>
          <button class="lead-chat-close" type="button" aria-label="Cerrar chat">×</button>
        </div>
        <div class="lead-chat-messages" aria-live="polite"></div>
        <div class="lead-chat-hint">Enter envía · Shift+Enter salto de línea</div>
        <form class="lead-chat-form">
          <label class="sr-only" for="lead-chat-input">Mensaje</label>
          <textarea id="lead-chat-input" rows="1" placeholder="Escribí un mensaje"></textarea>
          <button type="submit" aria-label="Enviar mensaje">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.8 20.2 21.7 12 2.8 3.8 2 10.2l12 1.8-12 1.8.8 6.4Z"/></svg>
          </button>
        </form>
      </div>`;
    document.body.appendChild(root);
    return root;
  }

  function init() {
    const root = createWidget();
    if (!root) return;
    const openButton = root.querySelector('.lead-chat-button');
    const panel = root.querySelector('.lead-chat-panel');
    const closeButton = root.querySelector('.lead-chat-close');
    const messages = root.querySelector('.lead-chat-messages');
    const form = root.querySelector('.lead-chat-form');
    const input = root.querySelector('#lead-chat-input');

    let state = { step: 0, data: {}, done: false };
    try { state = { ...state, ...(JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}')) }; } catch {}

    function persist() { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    function autoSize() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 112) + 'px'; }
    function addMessage(kind, html, options = {}) {
      const item = document.createElement('div');
      item.className = `lead-chat-message lead-chat-message--${kind}`;
      item.innerHTML = `${html}<time>${options.time || new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })}</time>`;
      messages.appendChild(item);
      messages.scrollTop = messages.scrollHeight;
    }
    function addTypingThen(callback) {
      const typing = document.createElement('div');
      typing.className = 'lead-chat-message lead-chat-message--bot lead-chat-typing';
      typing.innerHTML = '<span></span><span></span><span></span>';
      messages.appendChild(typing);
      messages.scrollTop = messages.scrollHeight;
      setTimeout(() => { typing.remove(); callback(); }, 420);
    }
    function askCurrent() {
      if (state.done) return;
      const q = questions[state.step];
      input.placeholder = q.placeholder;
      addTypingThen(() => addMessage('bot', escapeHtml(q.text)));
      setTimeout(() => input.focus(), 480);
    }
    async function finish() {
      state.done = true;
      persist();
      const classification = classifyLead(state.data);
      const attribution = getAttribution();
      const summary = summaryText(state.data, classification, attribution);
      const publicText = publicWhatsAppText(state.data);
      const waUrl = `https://wa.me/${CARLOS_WHATSAPP}?text=${encodeURIComponent(publicText)}`;
      track('lead_chat_completed', classification);
      track('generate_lead', { ...classification, form_type: 'lead_chat_widget' });
      addTypingThen(() => addMessage('bot', `Gracias${state.data.name ? `, ${escapeHtml(state.data.name)}` : ''}. Ya envié tu información para que podamos revisarla y contactarte con el mejor próximo paso.<br><br>Por lo que contás, seguramente podamos ayudarte a ordenar esa atención y automatizar lo repetitivo sin perder el trato humano.<br><br>Si querés hablar ahora por WhatsApp, te dejo el acceso directo 👇<br><br><a class="lead-chat-wa" href="${waUrl}" target="_blank" rel="noopener noreferrer">Hablar por WhatsApp</a>`));
      input.disabled = true;
      form.querySelector('button').disabled = true;

      try {
        const payload = {
          type: 'web_lead_chat',
          source: 'nolapenses_web',
          page_url: location.href,
          created_at: new Date().toISOString(),
          lead: state.data,
          attribution,
          classification,
          summary,
          whatsapp_public_url: waUrl
        };
        const securedPayload = window.NolapensesRecaptcha
          ? await window.NolapensesRecaptcha.attach(payload, 'lead_chat_widget')
          : payload;
        const response = await fetch(WEBHOOK_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          mode: 'cors',
          body: JSON.stringify(securedPayload)
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok || result.ok === false) {
          throw new Error(result.message || 'No pudimos validar la seguridad del formulario.');
        }
        track('lead_chat_webhook_sent', classification);
      } catch (error) {
        track('lead_chat_webhook_error', { message: String(error && error.message || error) });
      }
    }

    function openPanel() {
      panel.hidden = false;
      openButton.setAttribute('aria-expanded', 'true');
      track('lead_chat_opened');
      if (!messages.children.length) {
        if (state.done) {
          const publicText = publicWhatsAppText(state.data);
          const waUrl = `https://wa.me/${CARLOS_WHATSAPP}?text=${encodeURIComponent(publicText)}`;
          addMessage('bot', `Ya recibimos tu consulta y quedó enviada para revisarla. Te vamos a contactar con el mejor próximo paso.<br><br><a class="lead-chat-wa" href="${waUrl}" target="_blank" rel="noopener noreferrer">Hablar por WhatsApp</a>`);
        } else {
          askCurrent();
        }
      }
      input.focus();
    }
    function closePanel() {
      panel.hidden = true;
      openButton.setAttribute('aria-expanded', 'false');
      openButton.focus();
    }

    openButton.addEventListener('click', () => panel.hidden ? openPanel() : closePanel());
    closeButton.addEventListener('click', closePanel);
    input.addEventListener('input', autoSize);
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (typeof form.requestSubmit === 'function') form.requestSubmit();
        else form.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    });
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && !panel.hidden) closePanel(); });
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const value = input.value.trim();
      if (!value || state.done) return;
      const q = questions[state.step];
      state.data[q.key] = value;
      addMessage('user', escapeHtml(value));
      input.value = '';
      autoSize();
      state.step += 1;
      persist();
      track('lead_chat_answered', { step: q.key });
      if (state.step >= questions.length) finish();
      else askCurrent();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
