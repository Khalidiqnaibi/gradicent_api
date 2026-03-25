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
    loading: false,
    editingId: null,
    selectedClientId: null,
    defaultAddButtonText: null,
    viewingOnly: false
  };

  const FIELD_ALIASES = {
    quantity: ['stock'],
    stock: ['quantity'],
    price: ['hourly_rate'],
    hourly_rate: ['price']
  };

  const ID_FIELDS = ['id', '_id', 'client_id', 'employee_id', 'product_id', 'service_id'];
  const THEME_KEY = 'gradicent_theme';

  // DOM helpers
  const $ = (id) => document.getElementById(id);
  const $$ = (sel) => document.querySelectorAll(sel);

  // API helpers
  async function safeFetch(url, opts = {}) {
    try {
      const res = await fetch(url, {
        ...opts,
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...opts.headers }
      });

      const contentType = (res.headers.get('content-type') || '').toLowerCase();
      const isJson = contentType.includes('application/json');
      let data = null;

      if (isJson) {
        data = await res.json();
      } else {
        const text = await res.text();
        const preview = (text || '').trim().slice(0, 160);
        const isHtml = /^\s*</.test(preview);
        data = {
          message: isHtml
            ? `API returned HTML instead of JSON (HTTP ${res.status}) for ${url}`
            : (preview || `HTTP ${res.status}`)
        };
      }

      if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);
      if (!isJson) throw new Error(data.message || 'API returned non-JSON response');
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

  // Theme helpers
  function getTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === 'dark' || stored === 'light') return stored;
    return 'light';
  }

  function applyTheme(theme) {
    const resolved = theme === 'dark' ? 'dark' : 'light';
    document.body.classList.toggle('theme-dark', resolved === 'dark');
    document.documentElement.setAttribute('data-theme', resolved);

    const iconPath = resolved === 'dark'
      ? 'M12 3v2m0 14v2m9-9h-2M5 12H3m15.364 6.364l-1.414-1.414M7.05 7.05 5.636 5.636m12.728 0-1.414 1.414M7.05 16.95l-1.414 1.414M12 8a4 4 0 100 8 4 4 0 000-8z'
      : 'M21 12.79A9 9 0 1111.21 3c-.07.32-.11.65-.11 1a9 9 0 009.9 8.79z';

    const toggles = document.querySelectorAll('[data-theme-toggle]');
    toggles.forEach((btn) => {
      btn.setAttribute('aria-pressed', String(resolved === 'dark'));
      btn.setAttribute('title', resolved === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');

      const icon = btn.querySelector('svg path');
      if (icon) {
        icon.setAttribute('d', iconPath);
      }

      const label = btn.querySelector('[data-theme-label]');
      if (label) {
        label.textContent = resolved === 'dark' ? 'Dark mode: On' : 'Dark mode: Off';
      }
    });
  }

  function setTheme(theme) {
    const resolved = theme === 'dark' ? 'dark' : 'light';
    localStorage.setItem(THEME_KEY, resolved);
    applyTheme(resolved);
    return resolved;
  }

  function toggleTheme() {
    const next = getTheme() === 'dark' ? 'light' : 'dark';
    return setTheme(next);
  }

  function ensureSidebarThemeToggle() {
    const header = document.querySelector('.sidebar-header');
    if (!header) return;
    if (document.getElementById('sidebar-theme-toggle')) return;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'sidebar-theme-toggle';
    btn.className = 'sidebar-theme-toggle';
    btn.setAttribute('data-theme-toggle', 'sidebar');
    btn.setAttribute('aria-label', 'Toggle dark mode');
    btn.innerHTML = `
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12.79A9 9 0 1111.21 3c-.07.32-.11.65-.11 1a9 9 0 009.9 8.79z"/>
      </svg>
    `;
    btn.addEventListener('click', () => toggleTheme());

    const closeBtn = header.querySelector('.sidebar-close');
    if (closeBtn) {
      header.insertBefore(btn, closeBtn);
    } else {
      header.appendChild(btn);
    }
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
    const customActions = Array.isArray(CONFIG.actions) ? CONFIG.actions : [];
    const showDelete = Boolean(CONFIG.enableDelete);

    const renderCustomActions = (item, idx) => {
      if (!customActions.length) return '';
      return customActions.map((action) => {
        const key = action?.key;
        if (!key) return '';
        const label = action?.label || key;
        let cls = 'btn btn-sm btn-secondary';
        if (action?.variant === 'primary') cls = 'btn btn-sm btn-primary';
        else if (action?.variant === 'ghost') cls = 'btn btn-sm btn-ghost';

        return `<button class="${cls}" data-action="${escapeHtml(String(key))}" data-id="${escapeHtml(String(getEntityId(item, idx)))}">${escapeHtml(String(label))}</button>`;
      }).join('');
    };
    
    container.innerHTML = `
      <div class="entity-grid">
        ${items.map((item, idx) => `
          <div class="entity-card" data-id="${escapeHtml(String(getEntityId(item, idx)))}">
            <div class="entity-card-header">
              <span class="entity-name">${escapeHtml(item.name || getEntityId(item, idx) || `#${idx + 1}`)}</span>
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
              <button class="btn btn-sm btn-secondary" data-action="view" data-id="${escapeHtml(String(getEntityId(item, idx)))}">View</button>
              <button class="btn btn-sm btn-ghost" data-action="edit" data-id="${escapeHtml(String(getEntityId(item, idx)))}">Edit</button>
              ${showDelete ? `<button class="btn btn-sm btn-ghost" data-action="delete" data-id="${escapeHtml(String(getEntityId(item, idx)))}">Delete</button>` : ''}
              ${renderCustomActions(item, idx)}
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

  function getUpdateEndpoint(id) {
    const base = CONFIG.updateEndpointBase || CONFIG.apiBase;
    return `${base}/${encodeURIComponent(String(id))}`;
  }

  function getUpdateEndpointCandidates(id) {
    const encodedId = encodeURIComponent(String(id));
    const bases = [];
    const addBase = (value) => {
      if (!value || typeof value !== 'string') return;
      if (!bases.includes(value)) bases.push(value);
    };

    addBase(CONFIG.updateEndpointBase);
    addBase(CONFIG.apiBase);

    if (typeof CONFIG.apiBase === 'string') {
      addBase(CONFIG.apiBase.replace(/\/employees$/, '/employee'));
      addBase(CONFIG.apiBase.replace(/\/employee$/, '/employees'));
      addBase(CONFIG.apiBase.replace(/\/clients$/, '/client'));
      addBase(CONFIG.apiBase.replace(/\/client$/, '/clients'));
      addBase(CONFIG.apiBase.replace(/\/products$/, '/product'));
      addBase(CONFIG.apiBase.replace(/\/product$/, '/products'));
      addBase(CONFIG.apiBase.replace(/\/services$/, '/service'));
      addBase(CONFIG.apiBase.replace(/\/service$/, '/services'));
    }

    return bases.map(base => `${base}/${encodedId}`);
  }

  function getEntityId(item, idx) {
    if (!item || typeof item !== 'object') return idx;

    for (const field of ID_FIELDS) {
      const value = item[field];
      if (value != null && String(value).trim() !== '') return value;
    }

    if (item.metadata && typeof item.metadata === 'object') {
      for (const field of ID_FIELDS) {
        const value = item.metadata[field];
        if (value != null && String(value).trim() !== '') return value;
      }
    }

    return idx;
  }

  function setEditingMode(id = null) {
    STATE.editingId = id;
    const addBtn = $('add_btn');
    if (!addBtn) return;

    if (!STATE.defaultAddButtonText) {
      STATE.defaultAddButtonText = (addBtn.textContent || '').trim() || 'Add';
    }

    addBtn.textContent = id == null ? STATE.defaultAddButtonText : `Save ${CONFIG.labels?.singular || 'Item'}`;
    renderAddMenuActions();
  }

  function renderAddMenuActions() {
    const container = $('add-menu-actions');
    if (!container) return;

    const hasClientId = TYPE === 'client' && (STATE.editingId != null || STATE.selectedClientId != null);
    container.style.display = hasClientId ? 'flex' : 'none';
  }

  function setViewOnlyMode(enabled) {
    STATE.viewingOnly = !!enabled;

    const form = $('add-form');
    const addBtn = $('add_btn');
    const fields = CONFIG.fields?.add || [];

    fields.forEach((field) => {
      const el = $(field);
      if (!el) return;

      if (enabled) {
        if (el.dataset.prevTabindex == null) {
          el.dataset.prevTabindex = el.getAttribute('tabindex') ?? '';
        }
        el.setAttribute('tabindex', '-1');
        if (el.tagName === 'SELECT') el.disabled = true;
        else el.readOnly = true;
        el.style.cursor = 'default';
        el.style.userSelect = 'none';
        el.style.webkitUserSelect = 'none';
        el.style.MozUserSelect = 'none';
        el.style.msUserSelect = 'none';
        el.style.caretColor = 'transparent';
        el.style.pointerEvents = 'none';
        el.setAttribute('draggable', 'false');
      } else {
        if (el.tagName === 'SELECT') el.disabled = false;
        else el.readOnly = false;
        if ((el.dataset.prevTabindex ?? '') === '') el.removeAttribute('tabindex');
        else el.setAttribute('tabindex', el.dataset.prevTabindex);
        delete el.dataset.prevTabindex;
        el.style.cursor = '';
        el.style.userSelect = '';
        el.style.webkitUserSelect = '';
        el.style.MozUserSelect = '';
        el.style.msUserSelect = '';
        el.style.caretColor = '';
        el.style.pointerEvents = '';
        el.removeAttribute('draggable');
      }
    });

    if (form) {
      form.classList.toggle('view-only', enabled);
    }

    if (addBtn) {
      addBtn.style.display = enabled ? 'none' : '';
    }

    renderAddMenuActions();
  }

  function setAddFormVisible(visible) {
    const form = $('add-form');
    const results = $('results');
    if (!form) return;

    form.style.display = visible ? 'block' : 'none';
    if (results) {
      results.style.display = visible ? 'none' : 'block';
    }

    if (visible) {
      form.querySelector('input')?.focus();
      const emptyState = results?.querySelector('.empty-state');
      if (emptyState) emptyState.style.display = 'none';
      return;
    }

    const emptyState = results?.querySelector('.empty-state');
    if (emptyState && STATE.items.length === 0) emptyState.style.display = 'flex';
  }

  // Actions
  async function search() {
    const query = ($('query_input')?.value || '').trim();
    const searchFields = ['id', ...(CONFIG.fields?.search || [])];

    // If add panel is open, close it when a search starts.
    setAddFormVisible(false);
    setViewOnlyMode(false);
    setEditingMode(null);
    
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
      } else {
        toast('Nothing found', 'info');
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
    if (STATE.viewingOnly) {
      toast('View only mode: editing is disabled', 'info');
      return;
    }

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
      if (STATE.editingId != null) {
        const patchPayload = {
          domain: STATE.domain,
          user_id: STATE.user_id,
          patch: normalizedData
        };

        let res = null;
        let lastErr = null;
        const endpoints = getUpdateEndpointCandidates(STATE.editingId);
        for (const endpoint of endpoints) {
          try {
            res = await safeFetch(endpoint, {
              method: 'PATCH',
              body: JSON.stringify(patchPayload)
            });
            break;
          } catch (err) {
            lastErr = err;
          }
        }

        if (!res) {
          throw lastErr || new Error('Update failed');
        }

        const updated = res.data || { ...normalizedData, id: STATE.editingId };
        STATE.items = STATE.items.map((item, idx) =>
          String(getEntityId(item, idx)) === String(STATE.editingId)
            ? { ...item, ...updated }
            : item
        );
        renderItems(STATE.items);
        toast('Changes saved', 'success');
        setEditingMode(null);
      } else {
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
      }
      
      // Clear form
      fields.forEach(f => {
        const el = $(f);
        if (el) el.value = '';
      });

      // Close add form
      setAddFormVisible(false);
    } catch (err) {
      toast(err.message || 'Failed to add', 'error');
    } finally {
      setLoading(false);
    }
  }

  function view(id) {
    const itemIndex = STATE.items.findIndex((i, idx) => String(getEntityId(i, idx)) === String(id));
    const item = itemIndex >= 0 ? STATE.items[itemIndex] : null;
    if (!item) return;

    const resolvedId = getEntityId(item, itemIndex);
    if (resolvedId == null || String(resolvedId).trim() === '') {
      toast('Cannot view this item because it has no id', 'error');
      return;
    }

    // Open form in view-only mode and populate fields.
    STATE.selectedClientId = TYPE === 'client' ? resolvedId : null;
    setAddFormVisible(true);
    setEditingMode(null);
    setViewOnlyMode(true);

    const fields = CONFIG.fields?.add || [];
    fields.forEach((f) => {
      const el = $(f);
      const value = getFieldValue(item, f);
      if (el) {
        el.value = value == null ? '' : value;
      }
    });

    toast(`Viewing ${item.name || id}`, 'info');
  }

  function edit(id) {
    const itemIndex = STATE.items.findIndex((i, idx) => String(getEntityId(i, idx)) === String(id));
    const item = itemIndex >= 0 ? STATE.items[itemIndex] : null;
    if (!item) return;

    const resolvedId = getEntityId(item, itemIndex);
    if (resolvedId == null || String(resolvedId).trim() === '') {
      toast('Cannot edit this item because it has no id', 'error');
      return;
    }
    
    // Open add form and populate fields for update flow
    STATE.selectedClientId = TYPE === 'client' ? resolvedId : null;
    setAddFormVisible(true);
    setViewOnlyMode(false);
    
    const fields = CONFIG.fields?.add || [];
    fields.forEach(f => {
      const el = $(f);
      const value = getFieldValue(item, f);
      if (el && value !== undefined) {
        el.value = value;
      }
    });

    setEditingMode(resolvedId);
    
    toast(`Editing ${item.name || id}`, 'info');
  }

  async function remove(id) {
    const itemIndex = STATE.items.findIndex((i, idx) => String(getEntityId(i, idx)) === String(id));
    const item = itemIndex >= 0 ? STATE.items[itemIndex] : null;
    if (!item) return;

    const resolvedId = getEntityId(item, itemIndex);
    if (resolvedId == null || String(resolvedId).trim() === '') {
      toast('Cannot delete this item because it has no id', 'error');
      return;
    }

    const entityLabel = CONFIG.labels?.singular || 'item';
    const displayName = item.name || `${entityLabel} ${resolvedId}`;
    const confirmed = window.confirm(`Delete ${displayName}? This cannot be undone.`);
    if (!confirmed) return;

    setLoading(true);
    try {
      let success = false;
      let lastErr = null;
      const endpoints = getUpdateEndpointCandidates(resolvedId);
      const payload = {
        domain: STATE.domain,
        user_id: STATE.user_id
      };

      for (const endpoint of endpoints) {
        try {
          await safeFetch(endpoint, {
            method: 'DELETE',
            body: JSON.stringify(payload)
          });
          success = true;
          break;
        } catch (err) {
          lastErr = err;
        }
      }

      if (!success) {
        throw lastErr || new Error('Delete failed');
      }

      STATE.items = STATE.items.filter((entry, idx) => String(getEntityId(entry, idx)) !== String(resolvedId));
      if (STATE.editingId != null && String(STATE.editingId) === String(resolvedId)) {
        setEditingMode(null);
        setAddFormVisible(false);
      }
      renderItems(STATE.items);
      toast(`${entityLabel} deleted successfully`, 'success');
    } catch (err) {
      toast(err.message || 'Failed to delete item', 'error');
    } finally {
      setLoading(false);
    }
  }

  function handleCustomAction(actionKey, id) {
    const actions = Array.isArray(CONFIG.actions) ? CONFIG.actions : [];
    const action = actions.find((a) => String(a?.key) === String(actionKey));
    if (!action) return;

    const item = STATE.items.find((i, idx) => String(getEntityId(i, idx)) === String(id));
    if (!item) return;

    if (action.url) {
      const targetUrl = action.url
        .replace('{id}', encodeURIComponent(String(id)))
        .replace('{name}', encodeURIComponent(String(item.name || '')));
      window.location.href = targetUrl;
      return;
    }

    toast(action.message || `${action.label || action.key} is not configured`, 'info');
  }

  function handleAddMenuAction(actionKey) {
    if (TYPE !== 'client') return;

    const activeClientId = STATE.editingId ?? STATE.selectedClientId;

    if (activeClientId == null) {
      toast('Select a client first to open logs', 'info');
      return;
    }

    if (String(actionKey) === 'interactions') {
      window.location.href = `/data/${encodeURIComponent(String(activeClientId))}?action=new`;
      return;
    }

    if (String(actionKey) === 'transactions') {
      window.location.href = `/data/${encodeURIComponent(String(activeClientId))}?section=transactions&action=new`;
      return;
    }
  }

  // Add form toggle
  function toggleAddForm() {
    const form = $('add-form');
    if (!form) return;

    const isVisible = form.style.display !== 'none';
    setAddFormVisible(!isVisible);

    if (isVisible) {
      setViewOnlyMode(false);
      STATE.selectedClientId = null;
      setEditingMode(null);
      const fields = CONFIG.fields?.add || [];
      fields.forEach(f => {
        const el = $(f);
        if (el) el.value = '';
      });
    } else {
      setViewOnlyMode(false);
      setEditingMode(null);
    }
  }

  // Sidebar
  function toggleSidebar() {
    const sidebar = $('sidebar');
    const overlay = $('sidebar-overlay');
    if (sidebar) {
      const isOpen = sidebar.classList.contains('open');
      if (isOpen) {
        sidebar.classList.remove('open');
      } else {
        sidebar.classList.add('open');
      }
    }
    if (overlay) overlay.classList.toggle('active');
  }

  function closeSidebar() {
    const sidebar = $('sidebar');
    const overlay = $('sidebar-overlay');
    if (sidebar) {
      sidebar.classList.remove('open');
    }
    if (overlay) overlay.classList.remove('active');
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
    // Apply theme ASAP on page init
    applyTheme(getTheme());

    // Ensure every sidebar gets a moon toggle in the header
    ensureSidebarThemeToggle();

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

    const addMenuActions = $('add-menu-actions');
    if (addMenuActions) {
      addMenuActions.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-add-menu-action]');
        if (!btn) return;
        handleAddMenuAction(btn.dataset.addMenuAction);
      });
    }

    // Preserve default add button label for edit mode toggle
    const addBtn = $('add_btn');
    if (addBtn) {
      STATE.defaultAddButtonText = (addBtn.textContent || '').trim() || 'Add';
    }

    renderAddMenuActions();

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
        else if (action === 'delete') remove(id);
        else handleCustomAction(action, id);
      });
    }

    // Load initial data
    await loadAll();
  }

  // Boot
  document.addEventListener('DOMContentLoaded', init);

  // Public API
  return { search, add, view, edit, remove, loadAll, toggleAddForm, toggleSidebar, closeSidebar, getTheme, setTheme, toggleTheme };
})();
