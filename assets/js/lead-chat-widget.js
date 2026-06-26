(() => {
  const WEBHOOK_URL = window.CONFIG && CONFIG.webhooks && (CONFIG.webhooks.newLead || CONFIG.webhooks.chatbot) || '';
  const CARLOS_WHATSAPP = '5492665267159';
  const STORAGE_KEY = 'nolapenses_lead_chat_state_v3';
  const AUDIO_MAX_MS = 90000;

  const questions = [
    { key: 'need', text: 'Hola 👋 Soy el asistente de IA de Nolapenses. Contame en una frase: ¿qué querés ordenar o automatizar en tu negocio?', placeholder: 'Ej: recibo muchas consultas por WhatsApp y respondo tarde...' },
    { key: 'business', text: 'Perfecto. ¿Qué tipo de negocio o rubro tenés?', placeholder: 'Ej: consultorio odontológico, clínica, inmobiliaria, tienda...' },
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
    const repetitive = /(much[ao]s?|varios|diari|semana|consultas|mensajes|repetitiv|turnos|agenda|recordatorio|pacientes|consultorio|cl[ií]nica|odont|ventas|leads|clientes|carritos|soporte)/i.test(text);
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
      ['agenda/turnos/seguimiento', /(agenda|turno|reserva|seguimiento|recordatorio|paciente|consultorio|cl[ií]nica|odont|m[eé]dic)/i],
      ['contenido/redes', /(contenido|redes|instagram|facebook|linkedin|publicar|posteos)/i],
      ['integración de herramientas', /(integrar|crm|sheet|excel|drive|sistema|api|n8n|herramientas)/i],
      ['web/landing', /(web|landing|sitio|p[aá]gina)/i],
      ['IA privada/conocimiento interno', /(documentos|manuales|conocimiento|interno|drive|pol[ií]ticas|procedimientos)/i]
    ];
    const intent = (intentRules.find(([, regex]) => regex.test(text)) || ['consulta general'])[0];
    const level = score >= 8 ? 'caliente' : score >= 5 ? 'tibio' : 'frío';
    return { score, level, intent };
  }

  function estimateBudget(data, classification) {
    const text = Object.values(data).join(' ').toLowerCase();
    let complexity = 1;
    const reasons = [];
    if (classification.intent.includes('WhatsApp') || /whatsapp|instagram|facebook|consultas|mensajes/.test(text)) {
      complexity += 1; reasons.push('flujo de atención y respuestas frecuentes');
    }
    if (/agenda|turno|recordatorio|reserva|seguimiento|paciente|consultorio|cl[ií]nica|odont|m[eé]dic/.test(text)) {
      complexity += 1; reasons.push('agenda, turnos y recordatorios');
    }
    if (/crm|sheet|excel|drive|api|n8n|sistema|integrar|stock|pagos/.test(text)) {
      complexity += 1; reasons.push('integración con herramientas');
    }
    if (/much[ao]s?|diari|[3-9][0-9]|100|varios|equipo|sucursales/.test(text)) {
      complexity += 1; reasons.push('volumen o escala');
    }
    if (/documentos|manuales|conocimiento|interno|rag|datos/.test(text)) {
      complexity += 1; reasons.push('base de conocimiento/IA interna');
    }

    if (complexity <= 2) {
      return {
        tier: 'simple',
        label: 'Implementación simple',
        range: 'USD 250–600 aprox.',
        note: 'Ideal para ordenar consultas frecuentes, capturar datos y derivar mejor.',
        reasons
      };
    }
    if (complexity <= 4) {
      return {
        tier: 'intermedio',
        label: 'Implementación intermedia',
        range: 'USD 600–1.500 aprox.',
        note: 'Suele incluir flujos personalizados, seguimiento y alguna integración.',
        reasons
      };
    }
    return {
      tier: 'avanzado',
      label: 'Implementación avanzada',
      range: 'USD 1.500+ aprox.',
      note: 'Conviene relevar alcance porque puede incluir varias integraciones, IA interna o procesos críticos.',
      reasons
    };
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
      stored = { ...current, first_landing_page: location.href, first_referrer: document.referrer || '', captured_at: new Date().toISOString() };
      sessionStorage.setItem(storageKey, JSON.stringify(stored));
    }
    return { ...stored, ...current, landing_page: stored.first_landing_page || location.href, current_page: location.href, referrer: stored.first_referrer || document.referrer || '' };
  }

  function summaryText(data, classification, budgetEstimate, attribution = getAttribution()) {
    return [
      'Nuevo lead web — Nolapenses',
      `Nombre/contacto: ${data.name || '-'} / ${data.contact || '-'}`,
      `Negocio/rubro: ${data.business || '-'}`,
      `Necesidad: ${data.need || '-'}`,
      data.audio_transcription ? `Audio/transcripción: ${data.audio_transcription}` : '',
      `Canal/volumen: ${data.volume || '-'}`,
      `Urgencia/decisión: ${data.urgency || '-'}`,
      `Intención: ${classification.intent}`,
      `Nivel: ${classification.level} (${classification.score}/10)`,
      `Presupuesto orientativo: ${budgetEstimate.label} · ${budgetEstimate.range}`,
      `Origen campaña: ${attribution.utm_source || '-'} / ${attribution.utm_medium || '-'} / ${attribution.utm_campaign || '-'}`,
      `Contenido: ${attribution.utm_content || '-'} · Término: ${attribution.utm_term || '-'}`,
      `Landing: ${attribution.landing_page || location.href}`,
      `Página actual: ${location.href}`
    ].filter(Boolean).join('\n');
  }

  function publicWhatsAppText(data) {
    const name = (data.name || '').trim();
    const need = (data.need || data.audio_transcription || '').trim();
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

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = reject;
      reader.onloadend = () => resolve(String(reader.result || '').split(',')[1] || '');
      reader.readAsDataURL(blob);
    });
  }

  function supportedMimeType() {
    const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
    return candidates.find((type) => window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(type)) || '';
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
            <span><i></i> en línea · texto o audio</span>
          </div>
          <button class="lead-chat-close" type="button" aria-label="Cerrar chat">×</button>
        </div>
        <div class="lead-chat-messages" aria-live="polite"></div>
        <div class="lead-chat-hint">Enter envía · Shift+Enter salto de línea · también podés grabar audio</div>
        <form class="lead-chat-form">
          <button class="lead-chat-record" type="button" aria-label="Grabar audio" title="Grabar audio"><span aria-hidden="true">🎙️</span></button>
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
    const recordButton = root.querySelector('.lead-chat-record');

    let state = { step: 0, data: {}, done: false };
    let mediaRecorder = null;
    let audioChunks = [];
    let recordingTimer = null;
    let audioProcessing = false;
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
      const budgetEstimate = estimateBudget(state.data, classification);
      const attribution = getAttribution();
      const summary = summaryText(state.data, classification, budgetEstimate, attribution);
      const publicText = publicWhatsAppText(state.data);
      const waUrl = `https://wa.me/${CARLOS_WHATSAPP}?text=${encodeURIComponent(publicText)}`;
      track('lead_chat_submitted', { ...classification, budget_tier: budgetEstimate.tier });
      track('generate_lead', { ...classification, form_type: 'lead_chat_widget', budget_tier: budgetEstimate.tier });
      addTypingThen(() => addMessage('bot', `Gracias${state.data.name ? `, ${escapeHtml(state.data.name)}` : ''}. Ya envié tu información para revisarla y contactarte con el mejor próximo paso.<br><br><strong>Estimación orientativa:</strong> ${escapeHtml(budgetEstimate.label)} (${escapeHtml(budgetEstimate.range)}). No es una cotización cerrada: sirve para ubicar el alcance inicial según lo que contaste.<br><br>${escapeHtml(budgetEstimate.note)}<br><br>Si querés hablar ahora por WhatsApp, te dejo el acceso directo 👇<br><br><a class="lead-chat-wa" href="${waUrl}" target="_blank" rel="noopener noreferrer">Hablar por WhatsApp</a>`));
      input.disabled = true;
      form.querySelector('button[type="submit"]').disabled = true;
      recordButton.disabled = true;

      try {
        if (!WEBHOOK_URL) {
          track('lead_chat_config_missing');
          return;
        }
        const payload = {
          type: 'web_lead_chat',
          source: (window.CONFIG && CONFIG.requestMetadata && CONFIG.requestMetadata.source) || 'nolapenses_web',
          page_url: location.href,
          created_at: new Date().toISOString(),
          lead: state.data,
          attribution,
          classification,
          budget_estimate: budgetEstimate,
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
        if (!response.ok || result.ok === false) throw new Error(result.message || 'No pudimos validar la seguridad del formulario.');
        track('lead_chat_webhook_sent', classification);
      } catch (error) {
        track('lead_chat_webhook_error', { message: String(error && error.message || error) });
      }
    }

    function consumeAnswer(value, meta = {}) {
      const clean = String(value || '').trim();
      if (!clean || state.done) return;
      const q = questions[state.step];
      state.data[q.key] = clean;
      if (meta.audio) {
        state.data.audio_transcription = clean;
        state.data.audio_mime_type = meta.mimeType || '';
      }
      addMessage('user', meta.audio ? '🎙️ Audio recibido' : escapeHtml(clean));
      input.value = '';
      autoSize();
      state.step += 1;
      persist();
      track(meta.audio ? 'lead_chat_audio_answered' : 'lead_chat_answered', { step: q.key });
      if (state.step >= questions.length) finish();
      else askCurrent();
    }

    async function sendAudioToWebhook(blob) {
      const mimeType = blob.type || 'audio/webm';
      if (audioProcessing) return;
      audioProcessing = true;
      recordButton.disabled = true;
      const fallbackText = `Audio recibido (${Math.max(1, Math.round(blob.size / 1024))} KB). Contanos en texto si querés sumar algún detalle.`;
      addTypingThen(() => addMessage('bot', 'Recibí tu audio. Lo sumo como contexto de tu consulta.'));
      if (!WEBHOOK_URL) {
        consumeAnswer(fallbackText, { audio: true, mimeType });
        audioProcessing = false;
        if (!state.done) recordButton.disabled = false;
        return;
      }
      try {
        const audioBase64 = await blobToBase64(blob);
        const payload = {
          type: 'web_lead_chat_audio',
          source: (window.CONFIG && CONFIG.requestMetadata && CONFIG.requestMetadata.source) || 'nolapenses_web',
          page_url: location.href,
          created_at: new Date().toISOString(),
          audio_base64: audioBase64,
          audio_mime_type: mimeType,
          current_step: questions[state.step] && questions[state.step].key,
          wants_voice_response: false,
          attribution: getAttribution()
        };
        const securedPayload = window.NolapensesRecaptcha
          ? await window.NolapensesRecaptcha.attach(payload, 'lead_chat_audio')
          : payload;
        const response = await fetch(WEBHOOK_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          mode: 'cors',
          body: JSON.stringify(securedPayload)
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.ok === false) throw new Error(data.message || 'No pudimos procesar el audio.');
        const transcript = data.transcription || data.text_response || data.reply || '';
        consumeAnswer(transcript || fallbackText, { audio: true, mimeType });
      } catch (error) {
        track('lead_chat_audio_error', { message: String(error && error.message || error) });
        addMessage('bot', 'No pude procesar el audio automáticamente. Si podés, escribime un resumen corto y seguimos desde ahí.');
      } finally {
        audioProcessing = false;
        if (!state.done) recordButton.disabled = false;
      }
    }

    async function startRecording() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
        addMessage('bot', 'Tu navegador no permite grabar audio desde acá. Podés escribirlo o tocar el botón de WhatsApp al final.');
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeType = supportedMimeType();
        mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        audioChunks = [];
        mediaRecorder.addEventListener('dataavailable', (event) => { if (event.data && event.data.size) audioChunks.push(event.data); });
        mediaRecorder.addEventListener('stop', () => {
          stream.getTracks().forEach((track) => track.stop());
          recordButton.classList.remove('is-recording');
          recordButton.setAttribute('aria-label', 'Grabar audio');
          clearTimeout(recordingTimer);
          const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || mimeType || 'audio/webm' });
          if (blob.size) sendAudioToWebhook(blob);
        });
        mediaRecorder.start(1000);
        recordButton.classList.add('is-recording');
        recordButton.setAttribute('aria-label', 'Detener grabación');
        track('lead_chat_audio_started');
        recordingTimer = setTimeout(() => { if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop(); }, AUDIO_MAX_MS);
      } catch (error) {
        track('lead_chat_audio_permission_error', { message: String(error && error.message || error) });
        addMessage('bot', 'No pude acceder al micrófono. Revisá los permisos del navegador o contame por texto qué necesitás resolver.');
      }
    }

    function toggleRecording() {
      if (state.done || audioProcessing) return;
      if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
      else startRecording();
    }

    function openPanel() {
      panel.hidden = false;
      document.body.classList.add('lead-chat-active');
      window.dispatchEvent(new CustomEvent('nolapenses_lead_chat_opened'));
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
      document.body.classList.remove('lead-chat-active');
      openButton.setAttribute('aria-expanded', 'false');
      openButton.focus();
    }

    openButton.addEventListener('click', () => panel.hidden ? openPanel() : closePanel());
    closeButton.addEventListener('click', closePanel);
    recordButton.addEventListener('click', toggleRecording);
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
      consumeAnswer(input.value);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
