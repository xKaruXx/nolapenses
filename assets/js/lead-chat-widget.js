(() => {
  const PUBLIC_REQUEST_METADATA = window.CONFIG && CONFIG.requestMetadata ? CONFIG.requestMetadata : { source: 'nolapenses_web' };
  const WEBHOOK_URL = window.CONFIG && CONFIG.webhooks && (CONFIG.webhooks.chatbot || CONFIG.webhooks.newLead) || '';
  const CARLOS_WHATSAPP = '5492665267159';
  const STORAGE_KEY = 'nolapenses_ai_lead_chat_state_v1';
  const AUDIO_MAX_MS = 90000;
  const MAX_HISTORY = 12;

  const INITIAL_GREETING = 'Hola 👋 Soy el asistente de IA de Nolapenses. Para orientarte bien: contame brevemente qué necesitás automatizar o mejorar en tu negocio.';
  const FALLBACK_REPLY = 'Perdón, tuve un problema para procesar el mensaje. Si querés, dejame tu nombre y qué necesitás mejorar, y se lo paso a Carlos para que lo vea.';

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }

  function linkifySafe(text) {
    return escapeHtml(text).replace(/\n/g, '<br>');
  }

  function getSessionId() {
    const key = 'nolapenses_ai_chat_session_id';
    let sessionId = '';
    try { sessionId = sessionStorage.getItem(key) || ''; } catch {}
    if (!sessionId) {
      const random = (window.crypto && window.crypto.randomUUID) ? window.crypto.randomUUID() : `${Date.now()}_${Math.random().toString(16).slice(2)}`;
      sessionId = `web_${random}`;
      try { sessionStorage.setItem(key, sessionId); } catch {}
    }
    return sessionId;
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
      try { sessionStorage.setItem(storageKey, JSON.stringify(stored)); } catch {}
    }
    return { ...stored, ...current, landing_page: stored.first_landing_page || location.href, current_page: location.href, referrer: stored.first_referrer || document.referrer || '' };
  }

  function normalizePhone(value) {
    const digits = String(value || '').replace(/\D/g, '');
    if (!digits) return '';
    if (digits.startsWith('549')) return digits;
    if (digits.startsWith('54')) return digits;
    if (digits.length >= 10 && digits.length <= 11) return `54${digits}`;
    return digits.length >= 8 ? digits : '';
  }

  function ensureRecaptchaClient() {
    if (window.NolapensesRecaptcha && window.NolapensesRecaptcha.attach) return window.NolapensesRecaptcha;
    const config = window.CONFIG && window.CONFIG.recaptcha;
    const siteKey = config && config.siteKey;
    const actionPrefix = (config && config.actionPrefix) || 'nolapenses';
    if (!siteKey) return null;

    let loadPromise;
    const normalizeAction = (action) => `${actionPrefix}_${String(action || 'submit')}`.replace(/[^a-zA-Z0-9_]/g, '_').slice(0, 100);
    const loadScript = () => {
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
    };
    const ready = async () => {
      const loaded = await loadScript();
      if (!loaded || !window.grecaptcha || !window.grecaptcha.ready) return false;
      return new Promise((resolve) => window.grecaptcha.ready(() => resolve(true)));
    };
    const getToken = async (action = 'submit') => {
      const isReady = await ready();
      if (!isReady || !window.grecaptcha || !window.grecaptcha.execute) return '';
      try { return await window.grecaptcha.execute(siteKey, { action: normalizeAction(action) }); }
      catch (error) {
        track('recaptcha_client_error', { action: normalizeAction(action), message: String(error && error.message || error) });
        return '';
      }
    };
    const attach = async (payload = {}, action = 'submit') => {
      const recaptcha_action = normalizeAction(action);
      const recaptcha_token = await getToken(action);
      return { ...payload, recaptcha_token, recaptcha_action };
    };
    window.NolapensesRecaptcha = { ready, getToken, attach };
    return window.NolapensesRecaptcha;
  }

  function classifyFromFacts(facts, history) {
    const text = [facts.need, facts.business, facts.volume, facts.urgency, facts.role, facts.budget, facts.meeting_preference, ...history.map((m) => m.text)].join(' ').toLowerCase();
    const hasBusiness = Boolean((facts.business || '').trim()) || /(negocio|consultorio|cl[ií]nica|empresa|tienda|local|emprendimiento|inmobiliaria|odont|est[eé]tica|restaurante)/i.test(text);
    const clearProblem = Boolean((facts.need || '').trim().length > 18) || /(necesito|quiero|me cuesta|perdemos|pierdo|responder|automatizar|ordenar|agenda|turnos|seguimiento)/i.test(text);
    const repetitive = /(much[ao]s?|varios|diari|semana|consultas|mensajes|repetitiv|turnos|agenda|recordatorio|pacientes|ventas|leads|clientes|soporte)/i.test(text);
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
    if (/(reuni[oó]n|meet|llamada|visita|propuesta|precio|presupuesto|cotiz)/i.test(text)) score += 2;
    score = Math.min(score, 10);
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

  function updateFactsFromMessage(facts, text) {
    const clean = String(text || '').trim();
    if (!clean) return facts;
    const next = { ...facts };
    const email = clean.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
    if (email) next.email = email[0];
    const phone = clean.match(/(?:\+?54\s?9?\s?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}/);
    const normalizedPhone = normalizePhone(phone && phone[0]);
    if (normalizedPhone) next.contact = normalizedPhone;
    if (!next.name) {
      const nameMatch = clean.match(/(?:me llamo|soy|mi nombre es)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+){0,2})/i);
      if (nameMatch) next.name = nameMatch[1].trim();
    }
    if (!next.business) {
      const businessMatch = clean.match(/(?:negocio|empresa|consultorio|proyecto|local|emprendimiento)\s+(?:se llama|es|de)?\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .'-]{3,50})/i);
      if (businessMatch) next.business = businessMatch[1].trim();
      else if (/(consultorio|cl[ií]nica|odont|inmobiliaria|tienda|restaurante|est[eé]tica|gimnasio|academia|taller)/i.test(clean)) next.business = clean.slice(0, 120);
    }
    if (!next.volume && /(\d+|much[ao]s?|varios|diari|semana|mes|consultas|mensajes|turnos)/i.test(clean)) next.volume = clean.slice(0, 180);
    if (!next.urgency && /(urgente|este mes|esta semana|ya|rápido|rapido|explorando|sin apuro)/i.test(clean)) next.urgency = clean.slice(0, 180);
    if (!next.role && /(decido|dueñ|duen|socio|gerente|director|lo ve|decisi[oó]n)/i.test(clean)) next.role = clean.slice(0, 180);
    if (!next.budget && /(presupuesto|precio|cotiz|plata|invertir|alcance)/i.test(clean)) next.budget = clean.slice(0, 180);
    if (!next.meeting_preference && /(meet|llamada|visita|reuni[oó]n|presencial)/i.test(clean)) next.meeting_preference = clean.slice(0, 180);
    if (!next.need && !email && !normalizedPhone) next.need = clean.slice(0, 240);
    return next;
  }

  function publicWhatsAppText(state) {
    const facts = state.facts || {};
    const name = (facts.name || '').trim();
    const need = (facts.need || state.history.find((m) => m.role === 'user')?.text || '').trim();
    return [
      `Hola, soy ${name || 'un contacto de la web'}. Estuve hablando con el asistente de Nolapenses y quiero que me contacten.`,
      need ? `Quiero resolver esto: ${need}` : 'Quiero consultar por automatizaciones con IA para mi negocio.'
    ].join('\n');
  }

  function leadSummary(state) {
    const facts = state.facts || {};
    const classification = classifyFromFacts(facts, state.history || []);
    const attribution = getAttribution();
    const transcript = (state.history || []).slice(-10).map((m) => `${m.role === 'user' ? 'Lead' : 'Asistente'}: ${m.text}`).join('\n');
    return {
      classification,
      text: [
        'Nuevo lead web — Nolapenses',
        `Nombre/contacto: ${facts.name || '-'} / ${facts.contact || facts.email || '-'}`,
        `Negocio/rubro: ${facts.business || '-'}`,
        `Necesidad: ${facts.need || '-'}`,
        `Canal/volumen: ${facts.volume || '-'}`,
        `Urgencia/decisión: ${facts.urgency || '-'} / ${facts.role || '-'}`,
        `Modalidad/presupuesto: ${facts.meeting_preference || '-'} / ${facts.budget || '-'}`,
        `Intención: ${classification.intent}`,
        `Nivel: ${classification.level} (${classification.score}/10)`,
        `Origen campaña: ${attribution.utm_source || '-'} / ${attribution.utm_medium || '-'} / ${attribution.utm_campaign || '-'}`,
        `Landing: ${attribution.landing_page || location.href}`,
        '',
        'Conversación reciente:',
        transcript || '-'
      ].join('\n')
    };
  }

  function shouldHandoff(state) {
    if (state.handoffSent) return false;
    const facts = state.facts || {};
    const hasContact = Boolean(facts.contact || facts.email);
    if (!hasContact) return false;
    const { score } = leadSummary(state).classification;
    const text = (state.history || []).map((m) => m.text).join(' ');
    return score >= 5 || /(reuni[oó]n|meet|llamada|visita|propuesta|cotiz|precio|presupuesto|pierdo|perdiendo|urgente)/i.test(text);
  }

  function track(eventName, detail = {}) {
    const payload = { ...PUBLIC_REQUEST_METADATA, source: 'web_ai_lead_chat', ...getAttribution(), ...detail };
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
          <textarea id="lead-chat-input" rows="1" placeholder="Escribí tu mensaje"></textarea>
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
    const submitButton = form.querySelector('button[type="submit"]');

    let state = { sessionId: getSessionId(), history: [], facts: {}, handoffSent: false };
    let mediaRecorder = null;
    let audioChunks = [];
    let recordingTimer = null;
    let audioProcessing = false;
    let sending = false;
    try { state = { ...state, ...(JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}')) }; } catch {}
    state.sessionId = state.sessionId || getSessionId();
    state.history = Array.isArray(state.history) ? state.history : [];
    state.facts = state.facts || {};

    function persist() { try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch {} }
    function autoSize() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 112) + 'px'; }
    function setBusy(value) {
      sending = Boolean(value);
      input.disabled = sending;
      submitButton.disabled = sending;
      recordButton.disabled = sending || audioProcessing;
    }
    function messageTime(date = new Date()) {
      return date.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
    }
    function addMessage(kind, html, options = {}) {
      const item = document.createElement('div');
      const now = new Date();
      const label = options.time || messageTime(now);
      item.className = `lead-chat-message lead-chat-message--${kind}`;
      item.innerHTML = `<span class="lead-chat-message-text">${html}</span><time datetime="${escapeHtml(options.at || now.toISOString())}">${escapeHtml(label)}</time>`;
      messages.appendChild(item);
      messages.scrollTop = messages.scrollHeight;
      return { item, time: label, at: options.at || now.toISOString() };
    }
    function addTyping() {
      const typing = document.createElement('div');
      typing.className = 'lead-chat-message lead-chat-message--bot lead-chat-typing';
      typing.innerHTML = '<span></span><span></span><span></span>';
      messages.appendChild(typing);
      messages.scrollTop = messages.scrollHeight;
      return typing;
    }
    function restoreMessages() {
      messages.innerHTML = '';
      if (!state.history.length) {
        const added = addMessage('bot', escapeHtml(INITIAL_GREETING));
        state.history.push({ role: 'assistant', text: INITIAL_GREETING, at: added.at, time: added.time });
        persist();
        return;
      }
      state.history.forEach((m) => addMessage(m.role === 'user' ? 'user' : 'bot', linkifySafe(m.text), { time: m.time }));
    }
    function pushHistory(role, text, meta = {}) {
      state.history.push({ role, text: String(text || '').trim(), at: meta.at || new Date().toISOString(), time: meta.time || messageTime() });
      if (state.history.length > 30) state.history = state.history.slice(-30);
      persist();
    }

    async function postToWebhook(payload, action) {
      if (!WEBHOOK_URL) throw new Error('Webhook no configurado');
      const recaptcha = ensureRecaptchaClient();
      const securedPayload = recaptcha
        ? await recaptcha.attach(payload, action)
        : payload;
      const response = await fetch(WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        mode: 'cors',
        body: JSON.stringify(securedPayload)
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || result.ok === false) throw new Error(result.message || 'No pudimos procesar tu mensaje.');
      return result;
    }

    async function sendHandoffIfNeeded() {
      if (!shouldHandoff(state)) return;
      const summary = leadSummary(state);
      const facts = state.facts || {};
      const publicText = publicWhatsAppText(state);
      const waUrl = `https://wa.me/${CARLOS_WHATSAPP}?text=${encodeURIComponent(publicText)}`;
      const payload = {
        ...PUBLIC_REQUEST_METADATA,
        type: 'web_lead_chat',
        source: PUBLIC_REQUEST_METADATA.source || 'nolapenses_web',
        page_url: location.href,
        created_at: new Date().toISOString(),
        session_id: state.sessionId,
        lead: {
          name: facts.name || '',
          contact: facts.contact || facts.email || '',
          business: facts.business || '',
          need: facts.need || summary.text,
          volume: facts.volume || '',
          urgency: [facts.urgency, facts.role, facts.meeting_preference, facts.budget].filter(Boolean).join(' · ')
        },
        attribution: getAttribution(),
        classification: summary.classification,
        summary: summary.text,
        whatsapp_public_url: waUrl
      };
      try {
        await postToWebhook(payload, 'lead_chat_handoff');
        state.handoffSent = true;
        persist();
        track('lead_chat_submitted', { ...summary.classification, form_type: 'ai_chat_widget' });
        track('lead_chat_handoff_sent', summary.classification);
      } catch (error) {
        track('lead_chat_handoff_error', { message: String(error && error.message || error) });
      }
    }

    async function sendMessage(text, meta = {}) {
      const clean = String(text || '').trim();
      if ((!clean && !meta.audioBlob) || sending) return;
      const visibleText = meta.audio ? '🎙️ Audio recibido' : clean;
      const historyText = meta.audio ? (clean || visibleText) : clean;
      const addedUserMessage = addMessage('user', escapeHtml(visibleText));
      pushHistory('user', historyText, addedUserMessage);
      state.facts = updateFactsFromMessage(state.facts, clean);
      input.value = '';
      autoSize();
      setBusy(true);
      const typing = addTyping();
      track(meta.audio ? 'lead_chat_audio_message_sent' : 'lead_chat_message_sent');
      try {
        const payload = {
          ...PUBLIC_REQUEST_METADATA,
          type: 'web_lead_chat_ai_message',
          source: 'nolapenses_web_ai_chat',
          session_id: state.sessionId,
          message: clean,
          text: clean,
          page_url: location.href,
          created_at: new Date().toISOString(),
          attribution: getAttribution(),
          conversation_history: state.history.slice(-MAX_HISTORY),
          known_fields: state.facts,
          nombre: state.facts.name || '',
          telefono: state.facts.contact || '',
          email: state.facts.email || '',
          servicio_text: leadSummary(state).classification.intent,
          wants_voice_response: false
        };
        if (meta.audioBlob) {
          payload.type = 'web_lead_chat_ai_audio';
          payload.audio_base64 = await blobToBase64(meta.audioBlob);
          payload.audio_mime_type = meta.mimeType || meta.audioBlob.type || 'audio/webm';
          payload.audio_file_name = `lead-chat-${Date.now()}.${(payload.audio_mime_type.split('/')[1] || 'webm').split(';')[0]}`;
          payload.audio_size_bytes = meta.audioBlob.size;
          payload.message = clean || 'Audio recibido desde el chat web';
          payload.text = payload.message;
        }
        const result = await postToWebhook(payload, meta.audioBlob ? 'lead_chat_audio' : 'lead_chat_message');
        const reply = result.reply || result.text_response || result.message || FALLBACK_REPLY;
        if (result.transcription && meta.audioBlob) {
          state.facts = updateFactsFromMessage(state.facts, result.transcription);
        }
        if (result.lead) {
          const lead = result.lead;
          state.facts = {
            ...state.facts,
            name: state.facts.name || lead.nombre || lead.name || '',
            contact: state.facts.contact || normalizePhone(lead.telefono || lead.phone || ''),
            email: state.facts.email || lead.email || ''
          };
        }
        typing.remove();
        const addedBotMessage = addMessage('bot', linkifySafe(reply));
        pushHistory('assistant', reply, addedBotMessage);
        track('lead_chat_ai_reply_received', { next_action: result.actions && result.actions.next_action });
        await sendHandoffIfNeeded();
      } catch (error) {
        typing.remove();
        const addedFallbackMessage = addMessage('bot', escapeHtml(FALLBACK_REPLY));
        pushHistory('assistant', FALLBACK_REPLY, addedFallbackMessage);
        track('lead_chat_webhook_error', { message: String(error && error.message || error) });
      } finally {
        setBusy(false);
        input.focus();
      }
    }

    async function startRecording() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
        addMessage('bot', 'Tu navegador no permite grabar audio desde acá. Podés escribirlo o usar WhatsApp.');
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeType = supportedMimeType();
        mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        audioChunks = [];
        mediaRecorder.addEventListener('dataavailable', (event) => { if (event.data && event.data.size) audioChunks.push(event.data); });
        mediaRecorder.addEventListener('stop', async () => {
          stream.getTracks().forEach((track) => track.stop());
          recordButton.classList.remove('is-recording');
          recordButton.classList.add('is-processing');
          recordButton.setAttribute('aria-label', 'Procesando audio');
          clearTimeout(recordingTimer);
          const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || mimeType || 'audio/webm' });
          if (!blob.size) {
            recordButton.classList.remove('is-processing');
            recordButton.setAttribute('aria-label', 'Grabar audio');
            addMessage('bot', 'No llegué a capturar audio. Probá mantener presionado unos segundos o escribime el mensaje.');
            return;
          }
          audioProcessing = true;
          try {
            await sendMessage('Audio recibido desde el chat web', { audio: true, audioBlob: blob, mimeType: blob.type });
          } finally {
            audioProcessing = false;
            recordButton.classList.remove('is-processing');
            recordButton.setAttribute('aria-label', 'Grabar audio');
            setBusy(false);
          }
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
      if (sending || audioProcessing) return;
      if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
      else startRecording();
    }

    function openPanel() {
      panel.hidden = false;
      document.body.classList.add('lead-chat-active');
      window.dispatchEvent(new CustomEvent('nolapenses_lead_chat_opened'));
      openButton.setAttribute('aria-expanded', 'true');
      track('lead_chat_opened');
      if (!messages.children.length) restoreMessages();
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
      sendMessage(input.value);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
