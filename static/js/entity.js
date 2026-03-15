/**
 * entity.js — Generic Entity Management Controller
 * -------------------------------------------------
 * Shared by: clients, products, services, employees pages.
 *
 * Each HTML page sets window.__ENTITY_CONFIG__ and window.__ENTITY_TYPE__
 * before this script loads. CONFIG tells entity.js:
 *   - apiBase         : POST endpoint for creating entities
 *   - listEndpoint    : GET endpoint for fetching all (may be null)
 *   - searchEndpoint  : POST endpoint for searching (may be null)
 *   - detailUrl       : URL pattern for viewing a single entity ("{id}" placeholder)
 *   - labels          : { singular, plural } for UI text
 *   - fields.display  : which fields to show on entity cards
 *   - fields.search   : which fields to filter on (client-side fallback)
 *   - fields.add      : which fields appear in the "add new" form
 *
 * If listEndpoint is missing or fails, the page falls back to
 * searching/filtering the local STATE.items array. This makes
 * the page usable even when the backend doesn't support list-all.
 */

const EntityManager = (function() {
  // Config loaded from window.__ENTITY_CONFIG__
  const CONFIG = window.__ENTITY_CONFIG__ || {};
  const TYPE = window.__ENTITY_TYPE__ || 'entity';

  // State
  const STATE = {
    domain: null,
    user_id: null,
    items: [],
    loading: false
  };

  const FIELD_ALIASES = {
    quantity: ['stock'],
    stock: ['quantity'],
    price: ['hourly_rate'],
    hourly_rate: ['price']
  };

  // DOM helpers
  const $ = (id) => document.getElementById(id);
  const $$ = (sel) => document.querySelectorAll(sel);

  // API helpers
  async function safeFetch(url, opts = {}) {
    try {
      const res = await fetch(url, {
        ...opts,
        headers: { 'Content-Type': 'application/json', ...opts.headers }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);
      return data;
    } catch (err) {
      console.error('API Error:', err);
      throw err;
    }
  }

  async function getDomain() {
    try {
      const res = await safeFetch('/api/binder/get_domain');
      return res.data || 'business';
    } catch { return 'business'; }
  }

  async function getUserId() {
    try {
      const res = await safeFetch('/api/auth/me');
      return res.data?.id;
    } catch { return null; }
  }

  // Toast notifications
  function toast(message, type = 'info') {
    const container = $('toasts');
    if (!container) return;

    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.innerHTML = `
      <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
        ${type === 'success' ? '<path d="M20 6L9 17l-5-5"/>' : 
          type === 'error' ? '<circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/>' :
          '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>'}
      </svg>
      <span></span>
    `;
    t.querySelector('span').textContent = message;
    container.appendChild(t);
    setTimeout(() => t.remove(), 4000);
  }

  // UI rendering
  function renderItems(items) {
    const container = $('results');
    if (!container) return;

    if (!items || items.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" 
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
          </svg>
          <h3>No ${CONFIG.labels?.plural || 'items'} found</h3>
          <p>Try a different search or add a new ${CONFIG.labels?.singular || 'item'}</p>
        </div>
      `;
      return;
    }

    const displayFields = CONFIG.fields?.display || ['name'];
    
    container.innerHTML = `
      <div class="entity-grid">
        ${items.map((item, idx) => `
          <div class="entity-card" data-id="${item.id ?? idx}">
            <div class="entity-card-header">
              <span class="entity-name">${escapeHtml(item.name || item.id || `#${idx + 1}`)}</span>
              ${item.status ? `<span class="entity-badge">${escapeHtml(item.status)}</span>` : ''}
            </div>
            <div class="entity-meta">
              ${displayFields.slice(1).map(field => {
                const value = getFieldValue(item, field);
                if (value == null || value === '') return '';
                return `
                <div class="entity-meta-item">
                  <span>${formatLabel(field)}:</span>
                  <strong>${escapeHtml(String(value))}</strong>
                </div>
              `;
              }).join('')}
            </div>
            <div class="entity-actions">
              <button class="btn btn-sm btn-secondary" data-action="view" data-id="${escapeHtml(String(item.id ?? idx))}">View</button>
              <button class="btn btn-sm btn-ghost" data-action="edit" data-id="${escapeHtml(String(item.id ?? idx))}">Edit</button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  function setLoading(loading) {
    STATE.loading = loading;
    const btn = $('search_btn');
    const addBtn = $('add_btn');
    if (btn) btn.disabled = loading;
    if (addBtn) addBtn.disabled = loading;
  }

  function normalizeItems(data) {
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.results)) return data.results;
    if (typeof data === 'object') return Object.values(data);
    return [];
  }

  function buildContextQuery() {
    const params = new URLSearchParams();
    if (STATE.domain) params.set('domain', STATE.domain);
    if (STATE.user_id) params.set('user_id', STATE.user_id);
    const query = params.toString();
    return query ? `?${query}` : '';
  }

  function isNumericQuery(query) {
    return /^\d+$/.test(query);
  }

  function getFieldValue(item, field) {
    if (!item || !field) return undefined;

    if (item[field] != null && item[field] !== '') return item[field];

    const aliases = FIELD_ALIASES[field] || [];
    for (const alias of aliases) {
      if (item[alias] != null && item[alias] !== '') return item[alias];
    }

    const metadata = item.metadata;
    if (metadata && typeof metadata === 'object') {
      if (metadata[field] != null && metadata[field] !== '') return metadata[field];
      for (const alias of aliases) {
        if (metadata[alias] != null && metadata[alias] !== '') return metadata[alias];
      }
    }

    return undefined;
  }

  function normalizeOutboundData(data) {
    const normalized = { ...data };

    // Backend product model expects stock while UI currently uses quantity.
    if (TYPE === 'product' && normalized.stock == null && normalized.quantity != null) {
      normalized.stock = normalized.quantity;
    }

    // Backend service model expects hourly_rate while UI currently uses price.
    if (TYPE === 'service' && normalized.hourly_rate == null && normalized.price != null) {
      normalized.hourly_rate = normalized.price;
    }

    return normalized;
  }

  // Actions
  async function search() {
    const query = ($('query_input')?.value || '').trim();
    const searchFields = ['id', ...(CONFIG.fields?.search || [])];
    
    setLoading(true);
    try {
      let items = [];
      
      if (CONFIG.searchEndpoint && query) {
        // Use search endpoint
        const res = await safeFetch(CONFIG.searchEndpoint, {
          method: 'POST',
          body: JSON.stringify({
            query,
            domain: STATE.domain,
            user_id: STATE.user_id
          })
        });
        items = normalizeItems(res.data);
      } else if (CONFIG.listEndpoint) {
        if (query && isNumericQuery(query)) {
          // Fast path: support direct lookup by numeric id
          try {
            const one = await safeFetch(`${CONFIG.listEndpoint}/${encodeURIComponent(query)}${buildContextQuery()}`);
            items = one?.data ? [one.data] : [];
            STATE.items = items;
            renderItems(items);

            if (items.length > 0) {
              toast(`Found 1 ${CONFIG.labels?.singular || 'item'}`, 'success');
            }
            return;
          } catch {
            // If direct id lookup fails, continue to list + filter fallback.
          }
        }

        // Use list endpoint and filter client-side
        const res = await safeFetch(`${CONFIG.listEndpoint}${buildContextQuery()}`);
        items = normalizeItems(res.data);
        
        if (query) {
          const q = query.toLowerCase();
          items = items.filter(item => 
            searchFields.some(f => 
              String(getFieldValue(item, f) || '').toLowerCase().includes(q)
            )
          );
        }
      } else if (query && STATE.items.length > 0) {
        // No endpoints — filter local state
        const q = query.toLowerCase();
        items = STATE.items.filter(item =>
          searchFields.some(f =>
            String(getFieldValue(item, f) || '').toLowerCase().includes(q)
          )
        );
      }

      STATE.items = items;
      renderItems(items);
      
      if (items.length > 0) {
        toast(`Found ${items.length} ${items.length === 1 ? CONFIG.labels?.singular : CONFIG.labels?.plural}`, 'success');
      }
    } catch (err) {
      toast(err.message || 'Search failed', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function loadAll() {
    if (!CONFIG.listEndpoint) {
      // No list endpoint — render any items already in state, or show search prompt
      if (STATE.items.length > 0) {
        renderItems(STATE.items);
      } else {
        const container = $('results');
        if (container) {
          container.innerHTML = `
            <div class="empty-state">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" 
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
              <h3>Search for ${CONFIG.labels?.plural || 'items'}</h3>
              <p>Use the search bar or click "Add New" to get started</p>
            </div>
          `;
        }
      }
      return;
    }

    setLoading(true);
    try {
      const res = await safeFetch(`${CONFIG.listEndpoint}${buildContextQuery()}`);
      const items = normalizeItems(res.data);
      STATE.items = items;
      renderItems(items);
    } catch (err) {
      // List endpoint failed — render items in state or show search prompt
      if (STATE.items.length > 0) {
        renderItems(STATE.items);
      } else {
        const container = $('results');
        if (container) {
          container.innerHTML = `
            <div class="empty-state">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" 
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
              <h3>Search for ${CONFIG.labels?.plural || 'items'}</h3>
              <p>Enter a search term above to find ${CONFIG.labels?.plural?.toLowerCase() || 'items'}</p>
            </div>
          `;
        }
      }
    } finally {
      setLoading(false);
    }
  }

  async function add() {
    const fields = CONFIG.fields?.add || [];
    const data = {};
    
    for (const field of fields) {
      const el = $(field);
      if (el) {
        data[field] = el.type === 'number' ? (el.value ? Number(el.value) : null) : el.value;
      }
    }

    const normalizedData = normalizeOutboundData(data);

    // Validate required fields (at minimum, name)
    if (!normalizedData.name?.trim()) {
      toast('Name is required', 'error');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        domain: STATE.domain,
        user_id: STATE.user_id
      };
      payload[TYPE] = normalizedData;

      const res = await safeFetch(CONFIG.apiBase, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      // Add the returned item to local state so it renders immediately
      const created = res.data || data;
      STATE.items.push(created);
      renderItems(STATE.items);

      toast(`${CONFIG.labels?.singular || 'Item'} added successfully`, 'success');
      
      // Clear form
      fields.forEach(f => {
        const el = $(f);
        if (el) el.value = '';
      });

      // Close add form
      toggleAddForm();
    } catch (err) {
      toast(err.message || 'Failed to add', 'error');
    } finally {
      setLoading(false);
    }
  }

  function view(id) {
    const item = STATE.items.find(i => String(i.id) === String(id));
    if (!item) return;
    
    // Could open modal or navigate - for now just log
    console.log('View item:', item);
    toast(`Viewing ${item.name || id}`, 'info');
    
    // Navigate to detail page if exists
    if (CONFIG.detailUrl) {
      window.location.href = CONFIG.detailUrl.replace('{id}', id);
    }
  }

  function edit(id) {
    const item = STATE.items.find(i => String(i.id) === String(id));
    if (!item) return;
    
    // Switch to add form and populate fields
    toggleAddForm();
    
    const fields = CONFIG.fields?.add || [];
    fields.forEach(f => {
      const el = $(f);
      const value = getFieldValue(item, f);
      if (el && value !== undefined) {
        el.value = value;
      }
    });
    
    toast(`Editing ${item.name || id}`, 'info');
  }

  // Add form toggle
  function toggleAddForm() {
    const form = $('add-form');
    const results = $('results');
    if (form) {
      const isVisible = form.style.display !== 'none';
      form.style.display = isVisible ? 'none' : 'block';
      if (!isVisible) {
        // Focus first input when opening
        form.querySelector('input')?.focus();
        // Hide empty state when form is open
        const emptyState = results?.querySelector('.empty-state');
        if (emptyState) emptyState.style.display = 'none';
      } else {
        // Show empty state again when form is closed (if no items)
        const emptyState = results?.querySelector('.empty-state');
        if (emptyState && STATE.items.length === 0) emptyState.style.display = 'flex';
      }
    }
  }

  // Sidebar
  function toggleSidebar() {
    const sidebar = $('sidebar');
    const overlay = $('sidebar-overlay');
    if (sidebar) {
      const isOpen = !sidebar.classList.contains('closed');
      if (isOpen) {
        sidebar.classList.add('closed');
        sidebar.classList.remove('open');
      } else {
        sidebar.classList.remove('closed');
        sidebar.classList.add('open');
      }
    }
    if (overlay) overlay.classList.toggle('open');
  }

  function closeSidebar() {
    const sidebar = $('sidebar');
    const overlay = $('sidebar-overlay');
    if (sidebar) {
      sidebar.classList.remove('open');
      sidebar.classList.add('closed');
    }
    if (overlay) overlay.classList.remove('open');
  }

  // Helpers
  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, c => 
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  function formatLabel(field) {
    return field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  // Initialize
  async function init() {
    try {
      STATE.domain = await getDomain();
      STATE.user_id = await getUserId();
    } catch (err) {
      console.warn('Failed to load user context:', err);
    }

    // Top bar hide on scroll
    let lastScrollY = 0;
    let ticking = false;
    const topBar = document.querySelector('.top-bar');
    
    if (topBar) {
      window.addEventListener('scroll', () => {
        if (!ticking) {
          window.requestAnimationFrame(() => {
            const currentScrollY = window.scrollY;
            
            // Add scrolled class for shadow
            if (currentScrollY > 10) {
              topBar.classList.add('scrolled');
            } else {
              topBar.classList.remove('scrolled');
            }
            
            // Hide/show based on scroll direction
            if (currentScrollY > lastScrollY && currentScrollY > 80) {
              topBar.classList.add('hidden');
            } else {
              topBar.classList.remove('hidden');
            }
            
            lastScrollY = currentScrollY;
            ticking = false;
          });
          ticking = true;
        }
      }, { passive: true });
    }

    // Search on Enter key only
    const queryInput = $('query_input');
    if (queryInput) {
      queryInput.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          e.preventDefault();
          search();
        }
      });
    }

    // Search button click
    const searchBtn = $('search_btn');
    if (searchBtn) {
      searchBtn.addEventListener('click', () => search());
    }

    // Add form toggle
    $('add_toggle')?.addEventListener('click', toggleAddForm);

    // Add button
    $('add_btn')?.addEventListener('click', add);

    // Sidebar
    $('menu-toggle')?.addEventListener('click', toggleSidebar);
    $('sidebar-overlay')?.addEventListener('click', closeSidebar);

    // Entity card action delegation (view/edit) — attached once to avoid listener stacking
    const resultsContainer = $('results');
    if (resultsContainer) {
      resultsContainer.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        const id = btn.dataset.id;
        if (action === 'view') view(id);
        else if (action === 'edit') edit(id);
      });
    }

    // Load initial data
    await loadAll();
  }

  // Boot
  document.addEventListener('DOMContentLoaded', init);

  // Public API
  return { search, add, view, edit, loadAll, toggleAddForm, toggleSidebar, closeSidebar };
})();
