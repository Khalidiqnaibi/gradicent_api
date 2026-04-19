/**
 * ui.js — DOM rendering and form state
 * --------------------------------------
 * Everything that reads from or writes to the DOM lives here.
 *
 * This module does NOT make network calls and does NOT mutate global app state
 * directly.  It receives data as arguments and calls back into the actions
 * layer via the event delegation handlers wired up in entity.js.
 *
 * Key responsibilities:
 *   - Render entity card grids.
 *   - Manage the add/edit/view form (visibility, read-only mode, field values).
 *   - Show/hide the sidebar.
 *   - Manage loading state on interactive controls.
 *
 * Bug fixed: setViewOnlyMode double-call
 *   Previously, calling setViewOnlyMode(true) twice would overwrite the saved
 *   `prevTabindex` with "-1", making restoration impossible.  Fixed by only
 *   saving the original tabindex when the dataset key is absent.
 *
 * Bug fixed: select element disabled state
 *   The original code restored `readOnly` on select elements, which is not a
 *   valid property.  Selects use `disabled`; the fix applies the correct
 *   property for each element type.
 */

import { CONFIG, TYPE } from './config.js';
import { escapeHtml, formatLabel, getFieldValue, getEntityId } from './utils.js';

// ─── DOM shorthand ─────────────────────────────────────────────────────────────

const $ = (id) => document.getElementById(id);

// ─── Loading state ─────────────────────────────────────────────────────────────

/**
 * Enable or disable interactive controls during async operations.
 * @param {boolean} loading
 */
export function setLoadingUI(loading) {
  const btn    = $('search_btn');
  const addBtn = $('add_btn');
  if (btn)    btn.disabled    = loading;
  if (addBtn) addBtn.disabled = loading;
}

// ─── Empty states ──────────────────────────────────────────────────────────────

const EMPTY_ICON_SVG = `
  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
      d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
  </svg>`;

const SEARCH_ICON_SVG = `
  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
  </svg>`;

/**
 * Render the "nothing found" empty state into #results.
 */
export function renderEmptyState() {
  const container = $('results');
  if (!container) return;
  container.innerHTML = `
    <div class="empty-state">
      ${EMPTY_ICON_SVG}
      <h3>No ${escapeHtml(CONFIG.labels.plural)} found</h3>
      <p>Try a different search or add a new ${escapeHtml(CONFIG.labels.singular)}</p>
    </div>`;
}

/**
 * Render the "use the search bar" prompt into #results.
 */
export function renderSearchPrompt() {
  const container = $('results');
  if (!container) return;
  container.innerHTML = `
    <div class="empty-state">
      ${SEARCH_ICON_SVG}
      <h3>Search for ${escapeHtml(CONFIG.labels.plural)}</h3>
      <p>Use the search bar or click "Add New" to get started</p>
    </div>`;
}

// ─── Entity card grid ──────────────────────────────────────────────────────────

/**
 * Build the action buttons for a single card.
 * @param {object}        item
 * @param {number}        idx
 * @param {string|number} id
 * @returns {string}  HTML fragment
 */
function buildCardActions(item, idx, id) {
  const safeId     = escapeHtml(String(id));
  const showDelete = CONFIG.enableDelete;

  const customActions = CONFIG.actions
    .map((action) => {
      // action.key is validated and trimmed in config.js — no need to escape it
      // here, but we do because it goes into a data attribute.
      const key     = escapeHtml(action.key);
      const label   = escapeHtml(action.label ?? action.key);
      let   btnCls  = 'btn btn-sm btn-secondary';
      if (action.variant === 'primary') btnCls = 'btn btn-sm btn-primary';
      if (action.variant === 'ghost')   btnCls = 'btn btn-sm btn-ghost';
      // variant is not placed in the DOM, so it doesn't need escaping for XSS
      // purposes, but we never use user-supplied values in class names here.
      return `<button class="${btnCls}" data-action="${key}" data-id="${safeId}">${label}</button>`;
    })
    .join('');

  return `
    <button class="btn btn-sm btn-secondary" data-action="view"   data-id="${safeId}">View</button>
    <button class="btn btn-sm btn-ghost"     data-action="edit"   data-id="${safeId}">Edit</button>
    ${showDelete ? `<button class="btn btn-sm btn-ghost" data-action="delete" data-id="${safeId}">Delete</button>` : ''}
    ${customActions}
  `;
}

/**
 * Render an array of entity objects into #results as a card grid.
 * If the array is empty, renders the empty state instead.
 *
 * @param {object[]} items
 */
export function renderItems(items) {
  const container = $('results');
  if (!container) return;

  if (!items?.length) {
    renderEmptyState();
    return;
  }

  const displayFields = CONFIG.fields.display;

  const cards = items.map((item, idx) => {
    const id     = getEntityId(item, idx);
    const safeId = escapeHtml(String(id));
    const name   = escapeHtml(item.name || String(id) || `#${idx + 1}`);

    const metaHtml = displayFields
      .slice(1) // first field is the card title (already rendered as name)
      .map((field) => {
        const value = getFieldValue(item, field);
        if (value == null || value === '') return '';
        return `
          <div class="entity-meta-item">
            <span>${escapeHtml(formatLabel(field))}:</span>
            <strong>${escapeHtml(String(value))}</strong>
          </div>`;
      })
      .join('');

    return `
      <div class="entity-card" data-id="${safeId}">
        <div class="entity-card-header">
          <span class="entity-name">${name}</span>
          ${item.status ? `<span class="entity-badge">${escapeHtml(item.status)}</span>` : ''}
        </div>
        <div class="entity-meta">${metaHtml}</div>
        <div class="entity-actions">${buildCardActions(item, idx, id)}</div>
      </div>`;
  });

  container.innerHTML = `<div class="entity-grid">${cards.join('')}</div>`;
}

// ─── Add / edit / view form ───────────────────────────────────────────────────

/**
 * Show or hide the add/edit form, toggling the results panel accordingly.
 * @param {boolean} visible
 */
export function setAddFormVisible(visible) {
  const form    = $('add-form');
  const results = $('results');
  if (!form) return;

  form.style.display    = visible ? 'block' : 'none';
  if (results) results.style.display = visible ? 'none' : 'block';

  if (visible) {
    form.querySelector('input')?.focus();
  }
}

/**
 * Enable or disable read-only mode on all add-form fields.
 *
 * Bug fixed (double-call guard):
 *   Only saves the original `tabindex` on the FIRST call to setViewOnlyMode(true).
 *   Without this guard, a second call would overwrite `prevTabindex` with "-1",
 *   making it impossible to restore the original value on disable.
 *
 * Bug fixed (select elements):
 *   `select` elements do not support `readOnly`; they use `disabled`.
 *   The previous code applied `el.readOnly = true` to selects, which was a no-op,
 *   leaving them editable in view-only mode.  This version branches on tagName.
 *
 * @param {boolean} enabled
 */
export function setViewOnlyMode(enabled) {
  const fields = CONFIG.fields.add;

  fields.forEach((field) => {
    const el = $(field);
    if (!el) return;

    const isSelect = el.tagName === 'SELECT';

    if (enabled) {
      // Save the original tabindex exactly once; subsequent calls are no-ops.
      if (!('prevTabindex' in el.dataset)) {
        el.dataset.prevTabindex = el.getAttribute('tabindex') ?? '';
      }
      el.setAttribute('tabindex', '-1');
      if (isSelect) el.disabled  = true;
      else          el.readOnly  = true;
      el.style.cursor           = 'default';
      el.style.userSelect       = 'none';
      el.style.webkitUserSelect = 'none';
      el.style.caretColor       = 'transparent';
      el.style.pointerEvents    = 'none';
      el.setAttribute('draggable', 'false');
    } else {
      if (isSelect) el.disabled = false;
      else          el.readOnly = false;

      // Restore original tabindex and remove the sentinel key.
      const prev = el.dataset.prevTabindex;
      if (prev === '') el.removeAttribute('tabindex');
      else if (prev != null) el.setAttribute('tabindex', prev);
      delete el.dataset.prevTabindex;

      el.style.cursor           = '';
      el.style.userSelect       = '';
      el.style.webkitUserSelect = '';
      el.style.caretColor       = '';
      el.style.pointerEvents    = '';
      el.removeAttribute('draggable');
    }
  });

  const form   = $('add-form');
  const addBtn = $('add_btn');
  if (form)   form.classList.toggle('view-only', enabled);
  if (addBtn) addBtn.style.display = enabled ? 'none' : '';
}

/**
 * Update the Add button label and show/hide secondary add-menu actions.
 *
 * @param {string|null} editingId    - null means "not editing"
 * @param {string}      defaultLabel - the button's original label
 */
export function updateAddButtonLabel(editingId, defaultLabel) {
  const addBtn = $('add_btn');
  if (addBtn) {
    addBtn.textContent = editingId == null
      ? defaultLabel
      : `Save ${CONFIG.labels.singular}`;
  }

  // The add-menu-actions panel (Interactions / Transactions) is only relevant
  // when we have a client selected.
  const container = $('add-menu-actions');
  if (container) {
    const hasClient = TYPE === 'client' && editingId != null;
    container.style.display = hasClient ? 'flex' : 'none';
  }
}

/**
 * Populate the add form fields with values from an entity object.
 * @param {object} item
 */
export function populateForm(item) {
  CONFIG.fields.add.forEach((field) => {
    const el    = $(field);
    const value = getFieldValue(item, field);
    if (el) el.value = value == null ? '' : value;
  });
}

/**
 * Clear all add-form field values.
 */
export function clearForm() {
  CONFIG.fields.add.forEach((field) => {
    const el = $(field);
    if (el) el.value = '';
  });
}

/**
 * Read all add-form field values into a plain object.
 * Number inputs are coerced to numbers; others remain strings.
 * @returns {Record<string, string|number|null>}
 */
export function readFormData() {
  const data = {};
  CONFIG.fields.add.forEach((field) => {
    const el = $(field);
    if (!el) return;
    data[field] = el.type === 'number'
      ? (el.value !== '' ? Number(el.value) : null)
      : el.value;
  });
  return data;
}

// ─── Sidebar ───────────────────────────────────────────────────────────────────

export function toggleSidebar() {
  const sidebar = $('sidebar');
  const overlay = $('sidebar-overlay');
  if (sidebar) sidebar.classList.toggle('open');
  if (overlay) overlay.classList.toggle('active');
}

export function closeSidebar() {
  const sidebar = $('sidebar');
  const overlay = $('sidebar-overlay');
  if (sidebar) sidebar.classList.remove('open');
  if (overlay) overlay.classList.remove('active');
}

// ─── Top-bar scroll behaviour ─────────────────────────────────────────────────

/**
 * Wire up the top-bar hide-on-scroll behaviour.
 * Returns the handler so the caller can register it through the cleanup
 * registry and detach it properly.
 *
 * @param {HTMLElement} topBar
 * @returns {() => void}  the scroll event handler
 */
export function createScrollHandler(topBar) {
  let lastScrollY = 0;
  let ticking     = false;

  return function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(() => {
      const y = window.scrollY;
      topBar.classList.toggle('scrolled', y > 10);
      topBar.classList.toggle('hidden',   y > lastScrollY && y > 80);
      lastScrollY = y;
      ticking     = false;
    });
  };
}
