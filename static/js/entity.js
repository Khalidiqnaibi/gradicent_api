/**
 * entity.js — Generic Entity Management Controller
 * -------------------------------------------------
 * Shared by: clients, products, services, employees pages.
 *
 * Each HTML page sets window.__ENTITY_CONFIG__ and window.__ENTITY_TYPE__
 * before this script loads. CONFIG tells entity.js:
 *   - apiBase             : POST endpoint for creating entities
 *   - listEndpoint        : GET endpoint for fetching all (may be null)
 *   - searchEndpoint      : POST endpoint for searching (may be null)
 *   - detailUrl           : URL pattern for viewing a single entity ("{id}" placeholder)
 *   - labels              : { singular, plural } for UI text
 *   - fields.display      : which fields to show on entity cards
 *   - fields.search       : which fields to filter on (client-side fallback)
 *   - fields.add          : which fields appear in the "add new" form
 *   - numericIdBase       : 0 or 1 (default: 0). Set to 1 if your backend
 *                           uses 1-based numeric IDs and users type 1-based
 *                           numbers — entity.js will NOT subtract 1 in that case.
 *
 * If listEndpoint is missing or fails, the page falls back to
 * searching/filtering the local STATE.items array. This makes
 * the page usable even when the backend doesn't support list-all.
 *
 */

const EntityManager = (() => {


  // ─── Configuration ────────────────────────────────────────────────────────

  const CONFIG = window.__ENTITY_CONFIG__ || {};
  const TYPE   = window.__ENTITY_TYPE__   || 'entity';

  // ─── State ────────────────────────────────────────────────────────────────

  const STATE = {
    domain            : null,
    user_id           : null,
    items             : [],
    loading           : false,
    editingId         : null,
    selectedClientId  : null,
    defaultAddButtonText : null,
    viewingOnly       : false,
  };

  // ─── Constants ────────────────────────────────────────────────────────────

  /**
   * When a field is not found on an entity, try these aliases before giving up.
   * This bridges gaps where the UI calls a field "price" but the API calls it
   * "hourly_rate", etc.
   */
  const FIELD_ALIASES = {
    quantity    : ['stock'],
    stock       : ['quantity'],
    price       : ['hourly_rate'],
    hourly_rate : ['price'],
  };

  /**
   * Ordered list of field names that might carry an entity's primary key.
   * getEntityId() checks these in order and returns the first non-empty value.
   */
  const ID_FIELDS = ['id', '_id', 'client_id', 'employee_id', 'product_id', 'service_id'];

  const THEME_KEY     = 'gradicent_theme';
  const LAST_PAGE_KEY = 'gradicent_last_page';

  /**
   * numericIdBase controls numeric-query shifting.
   *
   * Backend stores IDs starting from 0 (default)
   *   → user types "1", we query for "0"  (shift = subtract 1)
   *
   * Backend stores IDs starting from 1  (set numericIdBase: 1 in CONFIG)
   *   → user types "1", we query for "1"  (no shift)
   *
   * If your searches were always returning the wrong item for a numeric input,
   * this was the bug. Set CONFIG.numericIdBase = 1 to fix it.
   */
  const NUMERIC_ID_BASE = typeof CONFIG.numericIdBase === 'number' ? CONFIG.numericIdBase : 0;

  // ─── Cleanup registry ─────────────────────────────────────────────────────
  // All event listeners added by init() are recorded here so cleanup() can
  // remove them if the page content is hot-swapped without a full reload.
  const _listeners = [];

  function _on(el, event, handler, opts) {
    if (!el) return;
    el.addEventListener(event, handler, opts);
    _listeners.push({ el, event, handler, opts });
  }

  function cleanup() {
    for (const { el, event, handler, opts } of _listeners) {
      el.removeEventListener(event, handler, opts);
    }
    _listeners.length = 0;
  }

  // ─── Active toasts ────────────────────────────────────────────────────────
  // Track live toast timers so we can cancel them if needed.
  const _toastTimers = new Set();

  // ─── DOM helpers ──────────────────────────────────────────────────────────

  const $ = (id) => document.getElementById(id);

  // ─── Navigation helpers ───────────────────────────────────────────────────

  function rememberCurrentPageForBackNav() {
    try {
      const path = `${window.location.pathname}${window.location.search}`;
      sessionStorage.setItem(LAST_PAGE_KEY, path);
    } catch (_) {
      // Storage unavailable — back-nav just won't work this session. Non-fatal.
    }
  }

  // ─── API helpers ──────────────────────────────────────────────────────────

  /**
   * Thin fetch wrapper.
   * - Always sends credentials (session cookies).
   * - Always sets Content-Type: application/json.
   * - If the response body is HTML (e.g. a login redirect page), throws a
   *   clear error rather than trying to JSON.parse it.
   * - Throws on non-OK HTTP status or non-JSON body.
   */
  async function safeFetch(url, opts = {}) {
    try {
      const res = await fetch(url, {
        ...opts,
        credentials : 'include',
        headers     : { 'Content-Type': 'application/json', ...opts.headers },
      });

      const contentType = (res.headers.get('content-type') || '').toLowerCase();
      const isJson      = contentType.includes('application/json');
      let data          = null;

      if (isJson) {
        data = await res.json();
      } else {
        const text    = await res.text();
        const preview = (text || '').trim().slice(0, 160);
        const isHtml  = /^\s*</.test(preview);
        data = {
          message: isHtml
            ? `Server returned HTML instead of JSON (HTTP ${res.status}) — you may need to log in again.`
            : (preview || `HTTP ${res.status}`),
        };
      }

      if (!res.ok)   throw new Error(data.message || `HTTP ${res.status}`);
      if (!isJson)   throw new Error(data.message || 'Server returned non-JSON response');

      return data;

    } catch (err) {
      console.error('[EntityManager] API error:', url, err);
      throw err;
    }
  }

  async function getDomain() {
    try {
      const res = await safeFetch('/api/binder/get_domain');
      return res.data || 'business';
    } catch (err) {
      // Not finding a domain is non-fatal — the page still works with a default.
      // Log it as a warning so developers notice configuration issues.
      console.warn('[EntityManager] Could not load domain — using "business" as default:', err.message);
      return 'business';
    }
  }

  async function getUserId() {
    try {
      const res = await safeFetch('/api/auth/me');
      return res.data?.id ?? null;
    } catch (err) {
      // session has expired, which will cause every subsequent API call to fail.
      console.warn('[EntityManager] Could not load user ID — proceeding as unauthenticated:', err.message);
      return null;
    }
  }

  // ─── Theme helpers ────────────────────────────────────────────────────────

  function getTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === 'dark' || stored === 'light') return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    const isDark = theme === 'dark';
    document.body.classList.toggle('theme-dark', isDark);
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');

    const SUN_PATH  = 'M12 3v2m0 14v2m9-9h-2M5 12H3m15.364 6.364-1.414-1.414M7.05 7.05 5.636 5.636m12.728 0-1.414 1.414M7.05 16.95l-1.414 1.414M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z';
    const MOON_PATH = 'M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z';
    const iconPath  = isDark ? SUN_PATH : MOON_PATH;
    const label     = isDark ? 'Switch to light mode' : 'Switch to dark mode';

    document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
      btn.setAttribute('aria-pressed', String(isDark));
      btn.setAttribute('title',        label);
      btn.setAttribute('aria-label',   label);
      const path    = btn.querySelector('svg path');
      if (path) path.setAttribute('d', iconPath);
      const labelEl = btn.querySelector('[data-theme-label]');
      if (labelEl)  labelEl.textContent = isDark ? 'Dark mode: On' : 'Dark mode: Off';
    });
  }

  function setTheme(theme) {
    const resolved = theme === 'dark' ? 'dark' : 'light';
    localStorage.setItem(THEME_KEY, resolved);
    applyTheme(resolved);
    return resolved;
  }

  function toggleTheme() {
    return setTheme(getTheme() === 'dark' ? 'light' : 'dark');
  }

  function injectThemeStyles() {
    if (document.getElementById('gradicent-theme-styles')) return;

    const style       = document.createElement('style');
    style.id          = 'gradicent-theme-styles';
    style.textContent = `
      :root, [data-theme="light"] {
        --bg-primary:    #ffffff;
        --bg-secondary:  #f5f5f4;
        --bg-sidebar:    #fafaf9;
        --text-primary:  #1c1917;
        --text-secondary:#57534e;
        --border-color:  #e7e5e4;
        --accent:        #0ea5e9;
        --accent-hover:  #0284c7;
        --sidebar-toggle-bg:    transparent;
        --sidebar-toggle-hover: #e7e5e4;
        --sidebar-toggle-icon:  #57534e;
      }

      [data-theme="dark"] {
        --bg-primary:    #0f0f0f;
        --bg-secondary:  #1a1a1a;
        --bg-sidebar:    #141414;
        --text-primary:  #fafaf9;
        --text-secondary:#a8a29e;
        --border-color:  #292524;
        --accent:        #38bdf8;
        --accent-hover:  #7dd3fc;
        --sidebar-toggle-bg:    transparent;
        --sidebar-toggle-hover: #292524;
        --sidebar-toggle-icon:  #a8a29e;
      }

      body, body * {
        transition:
          background-color 0.2s ease,
          color            0.2s ease,
          border-color     0.2s ease;
      }

      .sidebar-theme-toggle {
        display:         flex;
        align-items:     center;
        justify-content: center;
        width:           34px;
        height:          34px;
        padding:         0;
        border:          none;
        border-radius:   8px;
        background:      var(--sidebar-toggle-bg);
        color:           var(--sidebar-toggle-icon);
        cursor:          pointer;
        flex-shrink:     0;
        transition:      background 0.15s ease, color 0.15s ease;
      }

      .sidebar-theme-toggle:hover {
        background: var(--sidebar-toggle-hover);
        color:      var(--text-primary);
      }

      .sidebar-theme-toggle svg {
        width:   18px;
        height:  18px;
        display: block;
      }

      @media (prefers-reduced-motion: no-preference) {
        .sidebar-theme-toggle svg {
          transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        .sidebar-theme-toggle:active svg {
          transform: rotate(30deg) scale(0.9);
        }
      }
    `;
    document.head.appendChild(style);
  }

  function ensureSidebarThemeToggle() {
    const header = document.querySelector('.sidebar-header');
    if (!header)                                       return;
    if (document.getElementById('sidebar-theme-toggle')) return;

    const btn       = document.createElement('button');
    btn.type        = 'button';
    btn.id          = 'sidebar-theme-toggle';
    btn.className   = 'sidebar-theme-toggle';
    btn.setAttribute('data-theme-toggle', 'sidebar');
    btn.innerHTML   = `
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=""/>
      </svg>
    `;

    // Using addEventListener (not onclick) so cleanup() can remove this properly.
    _on(btn, 'click', () => toggleTheme());

    const closeBtn = header.querySelector('.sidebar-close');
    closeBtn ? header.insertBefore(btn, closeBtn) : header.appendChild(btn);

    // Apply current theme so the icon is immediately correct.
    applyTheme(getTheme());
  }

  // ─── Toast notifications ──────────────────────────────────────────────────

  function toast(message, type = 'info') {
    const container = $('toasts');
    if (!container) return;

    const t       = document.createElement('div');
    t.className   = `toast toast-${type}`;
    t.innerHTML   = `
      <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
        ${type === 'success'
          ? '<path d="M20 6L9 17l-5-5"/>'
          : type === 'error'
            ? '<circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/>'
            : '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>'}
      </svg>
      <span></span>
    `;
    t.querySelector('span').textContent = message; // textContent is XSS-safe

    container.appendChild(t);

    // Track the timer so we can cancel it if cleanup() is called mid-flight.
    const timer = setTimeout(() => {
      t.remove();
      _toastTimers.delete(timer);
    }, 4000);
    _toastTimers.add(timer);
  }

  function clearAllToasts() {
    for (const timer of _toastTimers) clearTimeout(timer);
    _toastTimers.clear();
    const container = $('toasts');
    if (container) container.innerHTML = '';
  }

  // ─── UI rendering ─────────────────────────────────────────────────────────

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

    const displayFields   = CONFIG.fields?.display || ['name'];
    const customActions   = Array.isArray(CONFIG.actions) ? CONFIG.actions : [];
    const showDelete      = Boolean(CONFIG.enableDelete);

    const renderCustomActions = (item, idx) => {
      if (!customActions.length) return '';
      return customActions
        .map((action) => {
          const key = action?.key;
          if (!key) return '';
          const label = action?.label || key;
          let cls = 'btn btn-sm btn-secondary';
          if (action?.variant === 'primary') cls = 'btn btn-sm btn-primary';
          else if (action?.variant === 'ghost') cls = 'btn btn-sm btn-ghost';
          // Both attributes are escaped through escapeHtml before entering the DOM.
          return `<button class="${cls}" data-action="${escapeHtml(String(key))}" data-id="${escapeHtml(String(getEntityId(item, idx)))}">${escapeHtml(String(label))}</button>`;
        })
        .join('');
    };

    container.innerHTML = `
      <div class="entity-grid">
        ${items
          .map(
            (item, idx) => `
          <div class="entity-card" data-id="${escapeHtml(String(getEntityId(item, idx)))}">
            <div class="entity-card-header">
              <span class="entity-name">${escapeHtml(item.name || String(getEntityId(item, idx)) || `#${idx + 1}`)}</span>
              ${item.status ? `<span class="entity-badge">${escapeHtml(item.status)}</span>` : ''}
            </div>
            <div class="entity-meta">
              ${displayFields
                .slice(1)
                .map((field) => {
                  const value = getFieldValue(item, field);
                  if (value == null || value === '') return '';
                  return `
                    <div class="entity-meta-item">
                      <span>${formatLabel(field)}:</span>
                      <strong>${escapeHtml(String(value))}</strong>
                    </div>`;
                })
                .join('')}
            </div>
            <div class="entity-actions">
              <button class="btn btn-sm btn-secondary" data-action="view"   data-id="${escapeHtml(String(getEntityId(item, idx)))}">View</button>
              <button class="btn btn-sm btn-ghost"     data-action="edit"   data-id="${escapeHtml(String(getEntityId(item, idx)))}">Edit</button>
              ${showDelete ? `<button class="btn btn-sm btn-ghost" data-action="delete" data-id="${escapeHtml(String(getEntityId(item, idx)))}">Delete</button>` : ''}
              ${renderCustomActions(item, idx)}
            </div>
          </div>`
          )
          .join('')}
      </div>
    `;
  }

  // ─── Loading state ────────────────────────────────────────────────────────

  function setLoading(loading) {
    STATE.loading    = loading;
    const btn        = $('search_btn');
    const addBtn     = $('add_btn');
    if (btn)    btn.disabled    = loading;
    if (addBtn) addBtn.disabled = loading;
  }

  // ─── Data normalisation ───────────────────────────────────────────────────

  /** Coerce any API response shape into a plain array. */
  function normalizeItems(data) {
    if (!data)                    return [];
    if (Array.isArray(data))      return data;
    if (Array.isArray(data.results)) return data.results;
    if (typeof data === 'object') return Object.values(data);
    return [];
  }

  /** Build a ?domain=…&user_id=… query string from current state. */
  function buildContextQuery() {
    const params = new URLSearchParams();
    if (STATE.domain)  params.set('domain',  STATE.domain);
    if (STATE.user_id) params.set('user_id', STATE.user_id);
    const query = params.toString();
    return query ? `?${query}` : '';
  }

  // ─── Numeric query helpers ────────────────────────────────────────────────

  function isNumericQuery(query) {
    return /^\d+$/.test(query);
  }

  /**
   * Converts a user-typed 1-based number to a 0-based backend ID.
   * Only applies when NUMERIC_ID_BASE is 0 (the default).
   * If NUMERIC_ID_BASE is 1, returns the query unchanged.
   *
   * FIX: Previously this always shifted, causing every numeric search to be
   * off-by-one on backends that use 1-based IDs. Now controlled by CONFIG.
   */
  function toBackendNumericId(query) {
    if (!isNumericQuery(query)) return query;
    if (NUMERIC_ID_BASE === 1)  return query; // backend is 1-based; no shift needed
    const shifted = Number(query) - 1;
    return String(Math.max(0, shifted));       // never go below 0
  }

  // ─── Field access ─────────────────────────────────────────────────────────

  /**
   * Look up a field on an entity, checking:
   *   1. Direct property
   *   2. Known aliases (e.g. "price" → "hourly_rate")
   *   3. entity.metadata.*  (same order)
   * Returns undefined if not found anywhere.
   */
  function getFieldValue(item, field) {
    if (!item || !field) return undefined;
    if (item[field] != null && item[field] !== '') return item[field];

    const aliases = FIELD_ALIASES[field] || [];
    for (const alias of aliases) {
      if (item[alias] != null && item[alias] !== '') return item[alias];
    }

    const meta = item.metadata;
    if (meta && typeof meta === 'object') {
      if (meta[field] != null && meta[field] !== '') return meta[field];
      for (const alias of aliases) {
        if (meta[alias] != null && meta[alias] !== '') return meta[alias];
      }
    }

    return undefined;
  }

  /**
   * Normalise outbound form data before sending to the API.
   * Maps UI field names to the names the backend actually expects.
   */
  function normalizeOutboundData(data) {
    const out = { ...data };
    if (TYPE === 'product' && out.stock == null && out.quantity != null) {
      out.stock = out.quantity;
    }
    if (TYPE === 'service' && out.hourly_rate == null && out.price != null) {
      out.hourly_rate = out.price;
    }
    return out;
  }

  // ─── Update endpoint resolution ───────────────────────────────────────────

  /**
   * Returns an ordered list of endpoint URLs to try for PATCH / DELETE.
   * The list is derived by trying both singular and plural variations of the
   * base path, because different backends are inconsistent about this.
   *
   * FIX: When all candidates fail, the error now lists every URL that was
   * tried, so developers can immediately see what went wrong instead of
   * receiving a useless "Update failed" message.
   */
  function getUpdateEndpointCandidates(id) {
    const encoded = encodeURIComponent(String(id));
    const seen    = new Set();
    const bases   = [];

    const add = (value) => {
      if (!value || typeof value !== 'string') return;
      if (!seen.has(value)) {
        seen.add(value);
        bases.push(value);
      }
    };

    add(CONFIG.updateEndpointBase);
    add(CONFIG.apiBase);

    if (typeof CONFIG.apiBase === 'string') {
      const pluralToSingular = [
        ['/employees', '/employee'],
        ['/clients',   '/client'],
        ['/products',  '/product'],
        ['/services',  '/service'],
      ];
      for (const [plural, singular] of pluralToSingular) {
        if (CONFIG.apiBase.endsWith(plural)) {
          add(CONFIG.apiBase.replace(plural, singular));
        } else if (CONFIG.apiBase.endsWith(singular)) {
          add(CONFIG.apiBase.replace(singular, plural));
        }
      }
    }

    return bases.map((base) => `${base}/${encoded}`);
  }

  // ─── Entity ID resolution ─────────────────────────────────────────────────

  /**
   * Extract the primary key from an entity object, falling back to the
   * array index if no ID field is found.
   */
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

  // ─── Edit / view mode helpers ─────────────────────────────────────────────

  function setEditingMode(id = null) {
    STATE.editingId = id;
    const addBtn    = $('add_btn');
    if (!addBtn) return;

    if (!STATE.defaultAddButtonText) {
      STATE.defaultAddButtonText = (addBtn.textContent || '').trim() || 'Add';
    }
    addBtn.textContent = id == null
      ? STATE.defaultAddButtonText
      : `Save ${CONFIG.labels?.singular || 'Item'}`;

    renderAddMenuActions();
  }

  function renderAddMenuActions() {
    const container = $('add-menu-actions');
    if (!container) return;
    const hasClientId = TYPE === 'client' && (STATE.editingId != null || STATE.selectedClientId != null);
    container.style.display = hasClientId ? 'flex' : 'none';
  }

  /**
   * Enable or disable "view-only" mode on the add form.
   *
   * FIX (double-call bug): Previously, calling setViewOnlyMode(true) twice
   * would overwrite `dataset.prevTabindex` with "-1" (the value we had just
   * set), making it impossible to restore the original tabindex later.
   *
   * The fix: only save prevTabindex if it hasn't been saved yet (i.e., the
   * key is absent from the dataset). This means the first call stores the
   * real original value; subsequent calls are no-ops for the tabindex save.
   */
  function setViewOnlyMode(enabled) {
    STATE.viewingOnly = !!enabled;

    const fields = CONFIG.fields?.add || [];

    fields.forEach((field) => {
      const el = $(field);
      if (!el) return;

      if (enabled) {
        // Only save the original tabindex if we haven't done so already.
        // This is the critical fix — without this guard, a second call
        // would write "-1" into prevTabindex, permanently losing the original.
        if (!('prevTabindex' in el.dataset)) {
          el.dataset.prevTabindex = el.getAttribute('tabindex') ?? '';
        }
        el.setAttribute('tabindex', '-1');
        if (el.tagName === 'SELECT') el.disabled = true;
        else                         el.readOnly = true;
        el.style.cursor          = 'default';
        el.style.userSelect      = 'none';
        el.style.webkitUserSelect = 'none';
        el.style.caretColor      = 'transparent';
        el.style.pointerEvents   = 'none';
        el.setAttribute('draggable', 'false');
      } else {
        if (el.tagName === 'SELECT') el.disabled  = false;
        else                         el.readOnly   = false;

        // Restore original tabindex and remove the saved value.
        const prev = el.dataset.prevTabindex;
        if (prev === '') el.removeAttribute('tabindex');
        else if (prev != null) el.setAttribute('tabindex', prev);
        delete el.dataset.prevTabindex;

        el.style.cursor          = '';
        el.style.userSelect      = '';
        el.style.webkitUserSelect = '';
        el.style.caretColor      = '';
        el.style.pointerEvents   = '';
        el.removeAttribute('draggable');
      }
    });

    const form   = $('add-form');
    const addBtn = $('add_btn');
    if (form)   form.classList.toggle('view-only', enabled);
    if (addBtn) addBtn.style.display = enabled ? 'none' : '';

    renderAddMenuActions();
  }

  function setAddFormVisible(visible) {
    const form    = $('add-form');
    const results = $('results');
    if (!form) return;

    form.style.display    = visible ? 'block' : 'none';
    if (results) results.style.display = visible ? 'none'  : 'block';

    if (visible) {
      form.querySelector('input')?.focus();
      const emptyState = results?.querySelector('.empty-state');
      if (emptyState) emptyState.style.display = 'none';
      return;
    }

    const emptyState = results?.querySelector('.empty-state');
    if (emptyState && STATE.items.length === 0) emptyState.style.display = 'flex';
  }

  // ─── Core actions ─────────────────────────────────────────────────────────

  /**
   * Search for entities.
   *
   * FIX: STATE.items is now only updated AFTER a successful response arrives.
   * Previously, items was cleared at the start of search(), meaning a network
   * error would blank the results panel even though nothing changed.
   */
  async function search() {
    const query        = ($('query_input')?.value || '').trim();
    const searchFields = ['id', ...(CONFIG.fields?.search || [])];

    // Close add panel when a search starts.
    setAddFormVisible(false);
    setViewOnlyMode(false);
    setEditingMode(null);
    setLoading(true);

    try {
      let items = [];

      if (CONFIG.searchEndpoint && query) {
        const shiftedQuery = isNumericQuery(query) ? toBackendNumericId(query) : query;

        let res = await safeFetch(CONFIG.searchEndpoint, {
          method : 'POST',
          body   : JSON.stringify({ query: shiftedQuery, domain: STATE.domain, user_id: STATE.user_id }),
        });
        items = normalizeItems(res.data);

        // If the shifted query returned nothing and the query was actually shifted,
        // try the raw value as a fallback.
        if (items.length === 0 && isNumericQuery(query) && shiftedQuery !== query) {
          res   = await safeFetch(CONFIG.searchEndpoint, {
            method : 'POST',
            body   : JSON.stringify({ query, domain: STATE.domain, user_id: STATE.user_id }),
          });
          items = normalizeItems(res.data);
        }

      } else if (CONFIG.listEndpoint) {

        if (query && isNumericQuery(query)) {
          // Fast path: direct ID lookup, avoiding a full list fetch.
          const shiftedQuery = toBackendNumericId(query);
          try {
            const one = await safeFetch(`${CONFIG.listEndpoint}/${encodeURIComponent(shiftedQuery)}${buildContextQuery()}`);
            items = one?.data ? [one.data] : [];
            STATE.items = items;
            renderItems(items);
            if (items.length > 0) toast(`Found 1 ${CONFIG.labels?.singular || 'item'}`, 'success');
            return;
          } catch {
            // Shifted lookup failed — try the raw value.
            if (shiftedQuery !== query) {
              try {
                const one = await safeFetch(`${CONFIG.listEndpoint}/${encodeURIComponent(query)}${buildContextQuery()}`);
                items = one?.data ? [one.data] : [];
                STATE.items = items;
                renderItems(items);
                if (items.length > 0) toast(`Found 1 ${CONFIG.labels?.singular || 'item'}`, 'success');
                return;
              } catch {
                // Both attempts failed — fall through to list + filter below.
              }
            }
          }
        }

        // Fetch all and filter client-side.
        const res = await safeFetch(`${CONFIG.listEndpoint}${buildContextQuery()}`);
        items     = normalizeItems(res.data);

        if (query) {
          const q = query.toLowerCase();
          items   = items.filter((item) =>
            searchFields.some((f) =>
              String(getFieldValue(item, f) || '').toLowerCase().includes(q)
            )
          );
        }

      } else if (query && STATE.items.length > 0) {
        // No configured endpoints — filter the items already in memory.
        const q = query.toLowerCase();
        items   = STATE.items.filter((item) =>
          searchFields.some((f) =>
            String(getFieldValue(item, f) || '').toLowerCase().includes(q)
          )
        );
      }

      // Only update STATE.items after a successful result — not before.
      STATE.items = items;
      renderItems(items);

      toast(
        items.length > 0
          ? `Found ${items.length} ${items.length === 1 ? CONFIG.labels?.singular : CONFIG.labels?.plural}`
          : 'Nothing found',
        items.length > 0 ? 'success' : 'info'
      );

    } catch (err) {
      // Search failed — leave STATE.items and the rendered results untouched.
      toast(err.message || 'Search failed', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function loadAll() {
    if (!CONFIG.listEndpoint) {
      if (STATE.items.length > 0) {
        renderItems(STATE.items);
      } else {
        _renderSearchPrompt();
      }
      return;
    }

    setLoading(true);
    try {
      const res   = await safeFetch(`${CONFIG.listEndpoint}${buildContextQuery()}`);
      const items = normalizeItems(res.data);
      STATE.items = items;
      renderItems(items);
    } catch (err) {
      // List failed — fall back gracefully.
      if (STATE.items.length > 0) {
        renderItems(STATE.items);
      } else {
        _renderSearchPrompt();
      }
    } finally {
      setLoading(false);
    }
  }

  /** Render the "use the search bar" empty state. */
  function _renderSearchPrompt() {
    const container = $('results');
    if (!container) return;
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

  /**
   * Add a new entity or save an edit.
   *
   * FIX (validation before loading): Previously setLoading(true) was called
   * before validation, so the Add button would flash disabled even when the
   * user just forgot to fill in the name field. Validation now runs first.
   */
  async function add() {
    if (STATE.viewingOnly) {
      toast('View only mode — editing is disabled', 'info');
      return;
    }

    const fields = CONFIG.fields?.add || [];
    const data   = {};

    for (const field of fields) {
      const el = $(field);
      if (el) {
        data[field] = el.type === 'number' ? (el.value ? Number(el.value) : null) : el.value;
      }
    }

    const normalizedData = normalizeOutboundData(data);

    // Validate before touching the loading state.
    if (!normalizedData.name?.trim()) {
      toast('Name is required', 'error');
      return; // button never flashes disabled for a validation failure
    }

    setLoading(true);

    try {
      if (STATE.editingId != null) {
        // ── UPDATE (PATCH) ───────────────────────────────────────────────
        const patchPayload = {
          domain  : STATE.domain,
          user_id : STATE.user_id,
          patch   : normalizedData,
        };

        let res      = null;
        let lastErr  = null;
        const candidates = getUpdateEndpointCandidates(STATE.editingId);

        for (const endpoint of candidates) {
          try {
            res = await safeFetch(endpoint, {
              method : 'PATCH',
              body   : JSON.stringify(patchPayload),
            });
            break;
          } catch (err) {
            lastErr = err;
          }
        }

        if (!res) {
          // FIX: Give developers a meaningful error listing every URL tried.
          const triedUrls = candidates.join(', ');
          const message   = `Update failed. Tried: ${triedUrls}`;
          console.error('[EntityManager]', message, lastErr);
          throw new Error(lastErr?.message || 'Update failed');
        }

        const updated = res.data || { ...normalizedData, id: STATE.editingId };
        STATE.items   = STATE.items.map((item, idx) =>
          String(getEntityId(item, idx)) === String(STATE.editingId)
            ? { ...item, ...updated }
            : item
        );
        renderItems(STATE.items);
        toast('Changes saved', 'success');
        setEditingMode(null);

      } else {
        // ── CREATE (POST) ────────────────────────────────────────────────
        const payload    = { domain: STATE.domain, user_id: STATE.user_id };
        payload[TYPE]    = normalizedData;

        const res        = await safeFetch(CONFIG.apiBase, {
          method : 'POST',
          body   : JSON.stringify(payload),
        });

        const created = res.data || data;
        STATE.items.push(created);
        renderItems(STATE.items);
        toast(`${CONFIG.labels?.singular || 'Item'} added successfully`, 'success');
      }

      // Clear form and close it.
      fields.forEach((f) => {
        const el = $(f);
        if (el) el.value = '';
      });
      setAddFormVisible(false);

    } catch (err) {
      toast(err.message || 'Failed to save', 'error');
    } finally {
      setLoading(false);
    }
  }

  function view(id) {
    const itemIndex = STATE.items.findIndex((i, idx) => String(getEntityId(i, idx)) === String(id));
    const item      = itemIndex >= 0 ? STATE.items[itemIndex] : null;
    if (!item) return;

    const resolvedId = getEntityId(item, itemIndex);
    if (resolvedId == null || String(resolvedId).trim() === '') {
      toast('Cannot view this item — it has no ID', 'error');
      return;
    }

    STATE.selectedClientId = TYPE === 'client' ? resolvedId : null;
    setAddFormVisible(true);
    setEditingMode(null);
    setViewOnlyMode(true);

    const fields = CONFIG.fields?.add || [];
    fields.forEach((f) => {
      const el    = $(f);
      const value = getFieldValue(item, f);
      if (el) el.value = value == null ? '' : value;
    });

    toast(`Viewing ${item.name || id}`, 'info');
  }

  function edit(id) {
    const itemIndex = STATE.items.findIndex((i, idx) => String(getEntityId(i, idx)) === String(id));
    const item      = itemIndex >= 0 ? STATE.items[itemIndex] : null;
    if (!item) return;

    const resolvedId = getEntityId(item, itemIndex);
    if (resolvedId == null || String(resolvedId).trim() === '') {
      toast('Cannot edit this item — it has no ID', 'error');
      return;
    }

    STATE.selectedClientId = TYPE === 'client' ? resolvedId : null;
    setAddFormVisible(true);
    setViewOnlyMode(false);

    const fields = CONFIG.fields?.add || [];
    fields.forEach((f) => {
      const el    = $(f);
      const value = getFieldValue(item, f);
      if (el && value !== undefined) el.value = value;
    });

    setEditingMode(resolvedId);
    toast(`Editing ${item.name || id}`, 'info');
  }

  async function remove(id) {
    const itemIndex = STATE.items.findIndex((i, idx) => String(getEntityId(i, idx)) === String(id));
    const item      = itemIndex >= 0 ? STATE.items[itemIndex] : null;
    if (!item) return;

    const resolvedId = getEntityId(item, itemIndex);
    if (resolvedId == null || String(resolvedId).trim() === '') {
      toast('Cannot delete this item — it has no ID', 'error');
      return;
    }

    const entityLabel = CONFIG.labels?.singular || 'item';
    const displayName = item.name || `${entityLabel} ${resolvedId}`;
    if (!window.confirm(`Delete ${displayName}? This cannot be undone.`)) return;

    setLoading(true);
    try {
      let success  = false;
      let lastErr  = null;
      const candidates = getUpdateEndpointCandidates(resolvedId);
      const payload    = { domain: STATE.domain, user_id: STATE.user_id };

      for (const endpoint of candidates) {
        try {
          await safeFetch(endpoint, {
            method : 'DELETE',
            body   : JSON.stringify(payload),
          });
          success = true;
          break;
        } catch (err) {
          lastErr = err;
        }
      }

      if (!success) {
        const triedUrls = candidates.join(', ');
        console.error(`[EntityManager] Delete failed. Tried: ${triedUrls}`, lastErr);
        throw lastErr || new Error('Delete failed');
      }

      STATE.items = STATE.items.filter(
        (entry, idx) => String(getEntityId(entry, idx)) !== String(resolvedId)
      );

      if (STATE.editingId != null && String(STATE.editingId) === String(resolvedId)) {
        setEditingMode(null);
        setAddFormVisible(false);
      }

      renderItems(STATE.items);
      toast(`${entityLabel} deleted`, 'success');

    } catch (err) {
      toast(err.message || 'Failed to delete item', 'error');
    } finally {
      setLoading(false);
    }
  }

  // ─── Custom actions ───────────────────────────────────────────────────────

  /**
   * Handle action buttons injected via CONFIG.actions.
   *
   * FIX: sessionStorage writes for section routing now catch errors and show
   * a toast rather than silently ignoring them. If the section key cannot be
   * written, navigation is still allowed (the key is a hint, not load-bearing),
   * but the failure is surfaced so developers are aware of it.
   */
  function handleCustomAction(actionKey, id) {
    const actions = Array.isArray(CONFIG.actions) ? CONFIG.actions : [];
    const action  = actions.find((a) => String(a?.key) === String(actionKey));
    if (!action) return;

    const item = STATE.items.find((i, idx) => String(getEntityId(i, idx)) === String(id));
    if (!item) return;

    if (action.url) {
      const sectionKey = String(actionKey) === 'transactions' ? 'transactions'
                       : String(actionKey) === 'interactions' ? 'interactions'
                       : null;

      if (sectionKey) {
        try {
          sessionStorage.setItem('gradicent_data_section', sectionKey);
        } catch (err) {
          // Storage unavailable — the destination page will load without the
          // pre-selected section. Non-fatal; navigation still proceeds.
          console.warn('[EntityManager] Could not write section key to sessionStorage:', err);
          toast('Note: section preference could not be saved', 'info');
        }
      }

      const targetUrl = action.url
        .replace('{id}',   encodeURIComponent(String(id)))
        .replace('{name}', encodeURIComponent(String(item.name || '')));

      rememberCurrentPageForBackNav();
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

    const sectionKey = String(actionKey) === 'interactions' ? 'interactions'
                     : String(actionKey) === 'transactions'  ? 'transactions'
                     : null;

    if (!sectionKey) return;

    try {
      sessionStorage.setItem('gradicent_data_section', sectionKey);
    } catch (err) {
      console.warn('[EntityManager] Could not write section key to sessionStorage:', err);
      toast('Note: section preference could not be saved', 'info');
    }

    const base    = `/data/${encodeURIComponent(String(activeClientId))}`;
    const section = sectionKey === 'transactions' ? `?source=entity&section=transactions&action=new`
                                                  : `?source=entity&action=new`;
    rememberCurrentPageForBackNav();
    window.location.href = base + section;
  }

  // ─── Form toggle ──────────────────────────────────────────────────────────

  function toggleAddForm() {
    const form = $('add-form');
    if (!form) return;

    const isVisible = form.style.display !== 'none';
    setAddFormVisible(!isVisible);

    if (isVisible) {
      // Form was open — reset all state.
      setViewOnlyMode(false);
      setEditingMode(null);
      STATE.selectedClientId = null;
      (CONFIG.fields?.add || []).forEach((f) => {
        const el = $(f);
        if (el) el.value = '';
      });
    } else {
      // Form is opening — clear editing mode but keep any pre-populated data
      // if the caller set it up before opening the form.
      setViewOnlyMode(false);
      setEditingMode(null);
    }
  }

  // ─── Sidebar ──────────────────────────────────────────────────────────────

  function toggleSidebar() {
    const sidebar = $('sidebar');
    const overlay = $('sidebar-overlay');
    if (sidebar) sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('active');
  }

  function closeSidebar() {
    const sidebar = $('sidebar');
    const overlay = $('sidebar-overlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
  }

  // ─── Utility helpers ──────────────────────────────────────────────────────

  /**
   * Escape a string for safe insertion into HTML attributes or content.
   *
   * FIX: Added backtick (`) to the escaped set. While backtick is not
   * dangerous in HTML attributes surrounded by double-quotes, escaping it
   * prevents issues in any template-literal context where this value might
   * later be re-used.
   */
  function escapeHtml(str) {
    return String(str).replace(/[&<>"'`]/g, (c) => ({
      '&'  : '&amp;',
      '<'  : '&lt;',
      '>'  : '&gt;',
      '"'  : '&quot;',
      "'"  : '&#39;',
      '`'  : '&#96;',
    }[c]));
  }

  function formatLabel(field) {
    return field.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  // ─── Initialisation ───────────────────────────────────────────────────────

  async function init() {
    injectThemeStyles();
    applyTheme(getTheme());
    ensureSidebarThemeToggle();

    try {
      STATE.domain  = await getDomain();
      STATE.user_id = await getUserId();
    } catch (err) {
      console.warn('[EntityManager] init: failed to load user context:', err);
    }

    // ── Top-bar hide/show on scroll ────────────────────────────────────────
    const topBar = document.querySelector('.top-bar');
    if (topBar) {
      let lastScrollY = 0;
      let ticking     = false;

      const onScroll = () => {
        if (!ticking) {
          window.requestAnimationFrame(() => {
            const y = window.scrollY;
            topBar.classList.toggle('scrolled', y > 10);
            topBar.classList.toggle('hidden',   y > lastScrollY && y > 80);
            lastScrollY = y;
            ticking     = false;
          });
          ticking = true;
        }
      };

      _on(window, 'scroll', onScroll, { passive: true });
    }

    // ── Search input: fire on Enter ────────────────────────────────────────
    const queryInput = $('query_input');
    if (queryInput) {
      _on(queryInput, 'keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); search(); }
      });
    } else {
      console.warn('[EntityManager] #query_input not found — search-on-enter disabled.');
    }

    // ── Search button ──────────────────────────────────────────────────────
    const searchBtn = $('search_btn');
    if (searchBtn) {
      _on(searchBtn, 'click', () => search());
    } else {
      console.warn('[EntityManager] #search_btn not found.');
    }

    // ── Add form toggle ────────────────────────────────────────────────────
    const addToggle = $('add_toggle');
    if (addToggle) {
      _on(addToggle, 'click', toggleAddForm);
    } else {
      console.warn('[EntityManager] #add_toggle not found — add form cannot be opened by toggle.');
    }

    // ── Add / save button ──────────────────────────────────────────────────
    const addBtn = $('add_btn');
    if (addBtn) {
      STATE.defaultAddButtonText = (addBtn.textContent || '').trim() || 'Add';
      _on(addBtn, 'click', add);
    } else {
      console.warn('[EntityManager] #add_btn not found.');
    }

    // ── Add-menu secondary actions (Interactions / Transactions) ──────────
    const addMenuActions = $('add-menu-actions');
    if (addMenuActions) {
      _on(addMenuActions, 'click', (e) => {
        const btn = e.target.closest('[data-add-menu-action]');
        if (btn) handleAddMenuAction(btn.dataset.addMenuAction);
      });
    }

    renderAddMenuActions();

    // ── Sidebar ────────────────────────────────────────────────────────────
    const menuToggle      = $('menu-toggle');
    const sidebarOverlay  = $('sidebar-overlay');
    if (menuToggle)     _on(menuToggle,    'click', toggleSidebar);
    if (sidebarOverlay) _on(sidebarOverlay,'click', closeSidebar);

    // ── Entity card action delegation ──────────────────────────────────────
    // Single listener on the results container handles all card buttons via
    // event delegation. This avoids re-attaching listeners after renderItems().
    const resultsContainer = $('results');
    if (resultsContainer) {
      _on(resultsContainer, 'click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const { action, id } = btn.dataset;
        if      (action === 'view')   view(id);
        else if (action === 'edit')   edit(id);
        else if (action === 'delete') remove(id);
        else                          handleCustomAction(action, id);
      });
    } else {
      console.warn('[EntityManager] #results not found — card actions will not work.');
    }

    // ── Load initial data ──────────────────────────────────────────────────
    await loadAll();
  }

  // ─── Boot ─────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);

  // ─── Public API ───────────────────────────────────────────────────────────
  return {
    search,
    add,
    view,
    edit,
    remove,
    loadAll,
    toggleAddForm,
    toggleSidebar,
    closeSidebar,
    getTheme,
    setTheme,
    toggleTheme,
    cleanup,
    clearAllToasts,
  };

})();

  
window.EntityManager = EntityManager;
