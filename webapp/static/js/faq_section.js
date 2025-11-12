// Render FAQ items and provide accessible accordion behavior.
// The script will prefer server-embedded data (window.FAQ_DATA). If not present,
// it will fetch the JSON from the static folder at /static/Json/faq_questions.json.

function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function createAccordionItem(index, q, a) {
  const item = document.createElement('div');
  item.className = 'accordion-item';
  item.setAttribute('data-index', String(index));

  const headerId = `faq${index}-header`;
  const panelId = `faq${index}`;

  const btn = document.createElement('button');
  btn.className = 'accordion-header';
  btn.id = headerId;
  btn.setAttribute('aria-expanded', 'false');
  btn.setAttribute('aria-controls', panelId);
  btn.setAttribute('tabindex', '0');
  btn.innerHTML = `<span class="faq-question">${escapeHtml(q)}</span><span class="accordion-icon" aria-hidden="true">▾</span>`;

  const panel = document.createElement('div');
  panel.className = 'accordion-content';
  panel.id = panelId;
  panel.setAttribute('role', 'region');
  panel.setAttribute('aria-labelledby', headerId);
  const p = document.createElement('p');
  p.innerHTML = escapeHtml(a);
  panel.appendChild(p);

  item.appendChild(btn);
  item.appendChild(panel);

  return item;
}

function closeAll() {
  document.querySelectorAll('.accordion-item').forEach(i => {
    i.classList.remove('active');
    const panel = i.querySelector('.accordion-content');
    if (panel) panel.style.maxHeight = null;
    const btn = i.querySelector('.accordion-header');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  });
}

function openItem(item) {
  item.classList.add('active');
  const panel = item.querySelector('.accordion-content');
  if (panel) panel.style.maxHeight = panel.scrollHeight + 'px';
  const btn = item.querySelector('.accordion-header');
  if (btn) btn.setAttribute('aria-expanded', 'true');
}

function attachAccordionBehavior(container) {
  container.querySelectorAll('.accordion-header').forEach(header => {
    header.addEventListener('click', () => {
      const item = header.closest('.accordion-item');
      if (!item) return;
      const isActive = item.classList.contains('active');
      closeAll();
      if (!isActive) openItem(item);
    });

    header.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        header.click();
      }
    });
  });
}

function renderFAQs(faqs) {
  // Prefer the inner .faq-list inside the #faq-list wrapper when present.
  const outer = document.getElementById('faq-list');
  let list = null;
  if (outer) list = outer.querySelector('.faq-list') || outer;
  if (!list) list = document.querySelector('.faq-list');
  if (!list) {
    console.warn('FAQ list container not found');
    return;
  }
  // Clear existing content
  list.innerHTML = '';
  faqs.forEach((f, idx) => {
    const item = createAccordionItem(idx + 1, f.question || 'No question', f.answer || 'No answer');
    list.appendChild(item);
  });
  attachAccordionBehavior(list);
  // Expand first item by default for usability
  const first = list.querySelector('.accordion-item');
  if (first) openItem(first);
  console.debug(`Rendered ${faqs.length} FAQ items`);
}
document.addEventListener('DOMContentLoaded', () => {
  // Prefer server-embedded data if available
  if (window.FAQ_DATA && Array.isArray(window.FAQ_DATA)) {
    renderFAQs(window.FAQ_DATA);
    return;
  }

  const jsonUrl = '/static/Json/faq_questions.json';
  fetch(jsonUrl)
    .then(res => {
      if (!res.ok) throw new Error('Failed to load FAQ JSON');
      return res.json();
    })
    .then(data => {
      if (!Array.isArray(data)) throw new Error('Invalid FAQ JSON format');
      renderFAQs(data);
    })
    .catch(err => {
      console.error('FAQ load error:', err);
    });
});
