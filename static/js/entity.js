/**
 * entity.js — Entry point / orchestrator
 * ----------------------------------------
 * Bootstraps the entity management system by:
 *   1. Injecting theme styles and applying the saved preference.
 *   2. Loading the domain and user context from the API.
 *   3. Wiring all DOM event listeners through the cleanup registry.
 *   4. Performing the initial data load.
 *
 * All event listeners are tracked in `_listeners` so `cleanup()` can detach
 * them without a full page reload (useful for SPA-style navigation).
 *
 * Public API (window.EntityManager):
 *   search, add, view, edit, remove, loadAll,
 *   toggleAddForm, toggleSidebar, closeSidebar,
 *   getTheme, setTheme, toggleTheme,
 *   cleanup, clearAllToasts
 *
 * Each HTML page must set window.__ENTITY_CONFIG__ and window.__ENTITY_TYPE__
 * before this script loads.  See config.js for the full CONFIG shape.
 */

import { setDomain, setUserId } from './state.js';
import { fetchDomain, fetchUserId } from './api.js';
import {
  injectThemeStyles, applyTheme, getTheme, setTheme, toggleTheme,
  ensureSidebarThemeToggle,
} from './theme.js';
import { clearAllToasts } from './toast.js';
import { toggleSidebar, closeSidebar, createScrollHandler } from './ui.js';
import {
  search, add, view, edit, remove, loadAll,
  toggleAddForm, handleCustomAction, handleAddMenuAction,
} from './actions.js';

// ─── Event listener registry ──────────────────────────────────────────────────

/**
 * Every listener added by init() is recorded here.
 * cleanup() removes them all, enabling safe hot-swapping.
 *
 * @type {Array<{ el: EventTarget, event: string, handler: Function, opts?: any }>}
 */
const _listeners = [];

/**
 * Register an event listener and record it for cleanup.
 * Silently ignores null/undefined targets.
 *
 * @param {EventTarget|null} el
 * @param {string}           event
 * @param {Function}         handler
 * @param {AddEventListenerOptions} [opts]
 */
function _on(el, event, handler, opts) {
  if (!el) return;
  el.addEventListener(event, handler, opts);
  _listeners.push({ el, event, handler, opts });
}

// ─── Cleanup ──────────────────────────────────────────────────────────────────

/**
 * Remove all event listeners registered by init().
 * Call this before hot-swapping page content or tearing down the module.
 */
function cleanup() {
  for (const { el, event, handler, opts } of _listeners) {
    el.removeEventListener(event, handler, opts);
  }
  _listeners.length = 0;
  clearAllToasts();
}

// ─── Initialisation ───────────────────────────────────────────────────────────

async function init() {
  // ── Theme ──────────────────────────────────────────────────────────────────
  injectThemeStyles();
  applyTheme(getTheme());

  // Inject the sidebar toggle and wire its listener through our registry.
  const { button: themeToggleBtn } = ensureSidebarThemeToggle();
  if (themeToggleBtn) {
    _on(themeToggleBtn, 'click', () => toggleTheme());
  }

  // ── User context ───────────────────────────────────────────────────────────
  try {
    const [domain, userId] = await Promise.all([fetchDomain(), fetchUserId()]);
    setDomain(domain);
    setUserId(userId);
  } catch (err) {
    // Non-fatal: the page still works, just without domain/user filtering.
    console.warn('[EntityManager] init: failed to load user context:', err);
  }

  // ── Top-bar hide/show on scroll ────────────────────────────────────────────
  const topBar = document.querySelector('.top-bar');
  if (topBar) {
    _on(window, 'scroll', createScrollHandler(topBar), { passive: true });
  }

  // ── Search ─────────────────────────────────────────────────────────────────
  const queryInput = document.getElementById('query_input');
  if (queryInput) {
    _on(queryInput, 'keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); search(); }
    });
  } else {
    console.warn('[EntityManager] #query_input not found — search-on-enter disabled.');
  }

  const searchBtn = document.getElementById('search_btn');
  if (searchBtn) {
    _on(searchBtn, 'click', () => search());
  } else {
    console.warn('[EntityManager] #search_btn not found.');
  }

  // ── Add form ───────────────────────────────────────────────────────────────
  const addToggle = document.getElementById('add_toggle');
  if (addToggle) {
    _on(addToggle, 'click', toggleAddForm);
  } else {
    console.warn('[EntityManager] #add_toggle not found — add form cannot be opened by toggle.');
  }

  const addBtn = document.getElementById('add_btn');
  if (addBtn) {
    _on(addBtn, 'click', () => add());
  } else {
    console.warn('[EntityManager] #add_btn not found.');
  }

  // ── Add-menu secondary actions (Interactions / Transactions) ───────────────
  const addMenuActions = document.getElementById('add-menu-actions');
  if (addMenuActions) {
    _on(addMenuActions, 'click', (e) => {
      const btn = e.target.closest('[data-add-menu-action]');
      if (btn) handleAddMenuAction(btn.dataset.addMenuAction);
    });
  }

  // ── Sidebar ────────────────────────────────────────────────────────────────
  const menuToggle     = document.getElementById('menu-toggle');
  const sidebarOverlay = document.getElementById('sidebar-overlay');
  if (menuToggle)     _on(menuToggle,     'click', () => toggleSidebar());
  if (sidebarOverlay) _on(sidebarOverlay, 'click', () => closeSidebar());

  // ── Entity card action delegation ──────────────────────────────────────────
  // One listener on #results handles all card buttons via event delegation.
  // This avoids re-attaching listeners every time renderItems() runs.
  const resultsContainer = document.getElementById('results');
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

  // ── Initial data load ──────────────────────────────────────────────────────
  await loadAll();
}

// ─── Boot ─────────────────────────────────────────────────────────────────────

// Guard against the case where DOMContentLoaded has already fired (e.g. the
// script is loaded dynamically after the page has parsed).
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
  // DOM already ready — call init() asynchronously to avoid blocking the
  // current call stack.
  queueMicrotask(init);
}

// ─── Public API ───────────────────────────────────────────────────────────────

const EntityManager = {
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

window.EntityManager = EntityManager;

export default EntityManager;
