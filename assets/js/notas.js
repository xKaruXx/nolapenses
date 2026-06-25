
(function(){
  const grid = document.querySelector('[data-notes-grid]');
  if (!grid) return;
  const search = document.querySelector('[data-notes-search]');
  const tagButtons = Array.from(document.querySelectorAll('[data-note-tag]'));
  const cards = Array.from(document.querySelectorAll('[data-note-card]'));
  const empty = document.querySelector('[data-notes-empty]');
  let activeTag = 'Todas';
  function track(eventName, data){
    const detail = Object.assign({ page: location.pathname }, data || {});
    window.dispatchEvent(new CustomEvent('nolapenses_analytics', { detail: { eventName, data: detail } }));
    if (typeof window.gtag === 'function') window.gtag('event', eventName, detail);
  }
  function normalize(v){ return (v||'').toString().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,''); }
  function apply(){
    const q = normalize(search && search.value);
    let visible = 0;
    cards.forEach(card => {
      const haystack = normalize(card.dataset.search);
      const tags = (card.dataset.tags||'').split('|');
      const tagOk = activeTag === 'Todas' || tags.includes(activeTag);
      const queryOk = !q || haystack.includes(q);
      const show = tagOk && queryOk;
      card.style.display = show ? 'block' : 'none';
      if (show) visible++;
    });
    if (empty) empty.style.display = visible ? 'none' : 'block';
  }
  let searchTimer;
  if (search) search.addEventListener('input', () => {
    apply();
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      if (search.value.trim().length >= 2) track('note_search', { query: search.value.trim() });
    }, 650);
  });
  tagButtons.forEach(btn => btn.addEventListener('click', () => {
    activeTag = btn.dataset.noteTag;
    tagButtons.forEach(b => b.setAttribute('aria-pressed', String(b === btn)));
    track('note_filter', { tag: activeTag });
    apply();
  }));
  cards.forEach(card => card.addEventListener('click', () => {
    track('note_card_click', { slug: (card.getAttribute('href')||'').split('/').filter(Boolean).pop() || '', tags: card.dataset.tags || '' });
  }));
})();
