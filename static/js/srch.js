(function () {
  function normalizeClients(raw) {
    if (Array.isArray(raw)) return raw;
    if (typeof raw === 'string') {
      const trimmed = raw.trim();
      if (!trimmed) return [];
      try {
        const parsed = JSON.parse(trimmed);
        return Array.isArray(parsed) ? parsed : [];
      } catch (_) {
        return [];
      }
    }
    return [];
  }

  function unique(values) {
    return Array.from(new Set(values.map((v) => String(v).trim()).filter(Boolean)));
  }

  function navigateToClient(clientId) {
    window.location.href = `/data/${encodeURIComponent(String(clientId))}?source=entity`;
  }

  function renderList(items) {
    const results = document.getElementById('results');
    if (!results) return;

    if (!items.length) {
      results.innerHTML = '<div class="empty">No matching clients.</div>';
      return;
    }

    results.innerHTML = '';
    const frag = document.createDocumentFragment();

    items.forEach((clientId) => {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'result-card';
      card.innerHTML = `<strong>Client #${String(clientId)}</strong><span>Open details</span>`;
      card.addEventListener('click', function () {
        navigateToClient(clientId);
      });
      frag.appendChild(card);
    });

    results.appendChild(frag);
  }

  const sourceClients = unique(normalizeClients(window.__GAIA_LIST__));

  function runSearch() {
    const query = (document.getElementById('query_input')?.value || '').trim().toLowerCase();
    if (!query) {
      renderList(sourceClients);
      return;
    }

    const filtered = sourceClients.filter((id) => String(id).toLowerCase().includes(query));
    renderList(filtered);
  }

  document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('query_input');
    const button = document.getElementById('search_btn');

    if (input) {
      input.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
          event.preventDefault();
          runSearch();
        }
      });
    }

    if (button) {
      button.addEventListener('click', function () {
        runSearch();
      });
    }

    renderList(sourceClients);
  });
})();
