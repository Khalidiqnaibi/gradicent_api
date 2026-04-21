/**
 * actions.js — Business logic / action handlers
 * -----------------------------------------------
 * Each exported function corresponds to a user-initiated action.
 * This layer coordinates between the API, state, and UI modules.
 *
 * Bugs fixed from original:
 *
 *   1. Race condition in search()
 *      Multiple rapid searches could resolve out of order, causing a slower
 *      earlier response to overwrite the results of a faster later one.
 *      Fixed with a monotonic search-generation counter: each search captures
 *      its generation at start; results are discarded if a newer search has
 *      begun by the time the response arrives.
 *
 *   2. STATE.items mutated in add()
 *      push() mutated the array in-place; filter() replaced the reference.
 *      Now appendItem() always returns a new array, keeping mutation style
 *      consistent throughout.
 *
 *   3. validation runs before setLoading(true)
 *      The original called setLoading(true) before checking required fields,
 *      causing the Add button to flash disabled on a validation failure.
 *
 *   4. view() / edit() stale selectedClientId
 *      Both functions now explicitly set selectedClientId before opening the
 *      form, preventing stale ID leakage when switching between items.
 *
 *   5. sessionStorage write errors surfaced
 *      Silent catches replaced with logged warnings and an info toast.
 *
 *   6. DELETE body removed
 *      Context is now passed as query params; some proxies strip DELETE bodies.
 */

import { CONFIG, TYPE } from './config.js';
import {
  getItems, setItems, appendItem, updateItemAt, removeItemWhere,
  setLoading, setEditingId, getEditingId, setSelectedClientId,
  setViewingOnly, isViewingOnly,
  getDefaultAddButtonText, setDefaultAddButtonText,
  nextSearchGeneration, getSearchGeneration,
  getDomain, getUserId,
} from './state.js';
import {
  fetchList, fetchOne, searchEntities, createEntity, updateEntity, deleteEntity,
} from './api.js';
import { buildContextQuery } from './context.js';
import {
  isNumericQuery, toBackendNumericId,
  normalizeItems, normalizeOutboundData,
  getEntityId, getFieldValue,
  getUpdateEndpointCandidates, rememberCurrentPage,
} from './utils.js';
import {
  setLoadingUI, renderItems, renderEmptyState, renderSearchPrompt,
  setAddFormVisible, setViewOnlyMode, updateAddButtonLabel,
  populateForm, clearForm, readFormData,
} from './ui.js';
import { toast } from './toast.js';

// ─── Internal helpers ─────────────────────────────────────────────────────────

function contextQuery() {
  return buildContextQuery(getDomain(), getUserId());
}

function setEditingMode(id = null) {
  setEditingId(id);

  // Cache the button label the first time we see it.
  const addBtn = document.getElementById('add_btn');
  if (addBtn && !getDefaultAddButtonText()) {
    setDefaultAddButtonText((addBtn.textContent || '').trim() || 'Add');
  }

  updateAddButtonLabel(id, getDefaultAddButtonText() || 'Add');
}

// ─── Search ───────────────────────────────────────────────────────────────────

/**
 * Execute a search based on the current value of #query_input.
 *
 * The search-generation counter prevents stale responses from overwriting
 * more recent results when the user types quickly.
 */
export async function search() {
  const query        = (document.getElementById('query_input')?.value ?? '').trim();
  const searchFields = ['id', ...CONFIG.fields.search];

  // Close the add panel and reset editing state before searching.
  setAddFormVisible(false);
  setViewOnlyMode(false);
  setEditingMode(null);

  const generation = nextSearchGeneration();

  setLoadingUI(true);
  setLoading(true);

  try {
    let items = [];

    if (CONFIG.searchEndpoint && query) {
      const shifted = isNumericQuery(query) ? toBackendNumericId(query) : query;
      const payload = { query: shifted, domain: getDomain(), user_id: getUserId() };

      let res = await searchEntities(CONFIG.searchEndpoint, payload);
      items   = normalizeItems(res.data);

      // Fallback: if the shifted query found nothing and it actually shifted, retry raw.
      if (items.length === 0 && isNumericQuery(query) && shifted !== query) {
        res   = await searchEntities(CONFIG.searchEndpoint, { ...payload, query });
        items = normalizeItems(res.data);
      }

    } else if (CONFIG.listEndpoint) {

      if (query && isNumericQuery(query)) {
        // Fast path: direct GET /{id} lookup.
        const shifted = toBackendNumericId(query);
        let found     = false;

        const tryId = async (id) => {
          try {
            const one = await fetchOne(CONFIG.listEndpoint, id, contextQuery());
            if (one?.data) {
              items = [one.data];
              found = true;
            }
          } catch {
            // Ignore; we'll try the next candidate or fall through.
          }
        };

        await tryId(shifted);
        if (!found && shifted !== query) await tryId(query);

        if (found) {
          // Check generation before committing results.
          if (getSearchGeneration() !== generation) return;
          setItems(items);
          renderItems(items);
          toast(`Found 1 ${CONFIG.labels.singular}`, 'success');
          return;
        }
        // Fall through to list + client-side filter.
      }

      const res = await fetchList(CONFIG.listEndpoint, contextQuery());
      items     = normalizeItems(res.data);

      if (query) {
        const q = query.toLowerCase();
        items   = items.filter((item) =>
          searchFields.some((f) =>
            String(getFieldValue(item, f) ?? '').toLowerCase().includes(q)
          )
        );
      }

    } else if (query) {
      // No configured endpoints — filter items already in memory.
      const q  = query.toLowerCase();
      const all = getItems();
      items     = all.filter((item) =>
        searchFields.some((f) =>
          String(getFieldValue(item, f) ?? '').toLowerCase().includes(q)
        )
      );
    }

    // Discard results if a newer search has started.
    if (getSearchGeneration() !== generation) return;

    setItems(items);
    renderItems(items);

    toast(
      items.length > 0
        ? `Found ${items.length} ${items.length === 1 ? CONFIG.labels.singular : CONFIG.labels.plural}`
        : 'Nothing found',
      items.length > 0 ? 'success' : 'info'
    );

  } catch (err) {
    if (getSearchGeneration() !== generation) return; // stale — ignore
    // Leave existing STATE.items and rendered results untouched on error.
    toast(err.message || 'Search failed', 'error');
  } finally {
    setLoadingUI(false);
    setLoading(false);
  }
}

// ─── Load all ─────────────────────────────────────────────────────────────────

export async function loadAll() {
  if (!CONFIG.listEndpoint) {
    const current = getItems();
    current.length > 0 ? renderItems(current) : renderSearchPrompt();
    return;
  }

  setLoadingUI(true);
  setLoading(true);
  try {
    const res   = await fetchList(CONFIG.listEndpoint, contextQuery());
    const items = normalizeItems(res.data);
    setItems(items);
    renderItems(items);
  } catch {
    const current = getItems();
    current.length > 0 ? renderItems(current) : renderSearchPrompt();
  } finally {
    setLoadingUI(false);
    setLoading(false);
  }
}

// ─── Add / Update ─────────────────────────────────────────────────────────────

export async function add() {
  if (isViewingOnly()) {
    toast('View only mode — editing is disabled', 'info');
    return;
  }

  const data           = readFormData();
  const normalizedData = normalizeOutboundData(data);

  // Validate *before* touching loading state so the button never flashes
  // disabled when the user simply forgot to fill in a required field.
  if (!normalizedData.name?.trim()) {
    toast('Name is required', 'error');
    return;
  }

  setLoadingUI(true);
  setLoading(true);

  try {
    const editingId = getEditingId();

    if (editingId != null) {
      // ── UPDATE ──────────────────────────────────────────────────────────
      const candidates = getUpdateEndpointCandidates(editingId);
      const payload    = { domain: getDomain(), user_id: getUserId(), patch: normalizedData };

      const res     = await updateEntity(candidates, payload);
      const updated = res?.data ?? { ...normalizedData, id: editingId };

      const items   = getItems();
      const idx     = items.findIndex(
        (item, i) => String(getEntityId(item, i)) === String(editingId)
      );
      if (idx >= 0) {
        updateItemAt(idx, { ...items[idx], ...updated });
      }

      renderItems(getItems());
      toast('Changes saved', 'success');
      setEditingMode(null);

    } else {
      // ── CREATE ──────────────────────────────────────────────────────────
      const payload       = { domain: getDomain(), user_id: getUserId() };
      payload[TYPE]       = normalizedData;

      const res     = await createEntity(CONFIG.apiBase, payload);
      const created = res?.data ?? data;

      appendItem(created);
      renderItems(getItems());
      toast(`${CONFIG.labels.singular} added successfully`, 'success');
    }

    clearForm();
    setAddFormVisible(false);

  } catch (err) {
    toast(err.message || 'Failed to save', 'error');
  } finally {
    setLoadingUI(false);
    setLoading(false);
  }
}

// ─── View ─────────────────────────────────────────────────────────────────────

export function view(id) {
  const items     = getItems();
  const itemIndex = items.findIndex((item, idx) => String(getEntityId(item, idx)) === String(id));
  const item      = itemIndex >= 0 ? items[itemIndex] : null;
  if (!item) return;

  const resolvedId = getEntityId(item, itemIndex);
  if (resolvedId == null || String(resolvedId).trim() === '') {
    toast('Cannot view this item — it has no ID', 'error');
    return;
  }

  // Reset any previously selected client before setting the new one.
  setSelectedClientId(TYPE === 'client' ? resolvedId : null);
  setEditingMode(null);
  setAddFormVisible(true);
  setViewOnlyMode(true);
  setViewingOnly(true);

  populateForm(item);
  toast(`Viewing ${item.name || id}`, 'info');
}

// ─── Edit ─────────────────────────────────────────────────────────────────────

export function edit(id) {
  const items     = getItems();
  const itemIndex = items.findIndex((item, idx) => String(getEntityId(item, idx)) === String(id));
  const item      = itemIndex >= 0 ? items[itemIndex] : null;
  if (!item) return;

  const resolvedId = getEntityId(item, itemIndex);
  if (resolvedId == null || String(resolvedId).trim() === '') {
    toast('Cannot edit this item — it has no ID', 'error');
    return;
  }

  // Reset any previously selected client before setting the new one.
  setSelectedClientId(TYPE === 'client' ? resolvedId : null);
  setViewOnlyMode(false);
  setViewingOnly(false);
  setAddFormVisible(true);

  populateForm(item);
  setEditingMode(resolvedId);
  toast(`Editing ${item.name || id}`, 'info');
}

// ─── Delete ───────────────────────────────────────────────────────────────────

export async function remove(id) {
  const items     = getItems();
  const itemIndex = items.findIndex((item, idx) => String(getEntityId(item, idx)) === String(id));
  const item      = itemIndex >= 0 ? items[itemIndex] : null;
  if (!item) return;

  const resolvedId  = getEntityId(item, itemIndex);
  if (resolvedId == null || String(resolvedId).trim() === '') {
    toast('Cannot delete this item — it has no ID', 'error');
    return;
  }

  const entityLabel = CONFIG.labels.singular;
  const displayName = item.name ?? `${entityLabel} ${resolvedId}`;
  if (!window.confirm(`Delete ${displayName}? This cannot be undone.`)) return;

  setLoadingUI(true);
  setLoading(true);
  try {
    const candidates = getUpdateEndpointCandidates(resolvedId);
    await deleteEntity(candidates, contextQuery());

    removeItemWhere((_item, idx) => String(getEntityId(_item, idx)) === String(resolvedId));

    // If we were editing the deleted item, close the form.
    if (getEditingId() != null && String(getEditingId()) === String(resolvedId)) {
      setEditingMode(null);
      setAddFormVisible(false);
    }

    renderItems(getItems());
    toast(`${entityLabel} deleted`, 'success');

  } catch (err) {
    toast(err.message || 'Failed to delete item', 'error');
  } finally {
    setLoadingUI(false);
    setLoading(false);
  }
}

// ─── Custom card actions ──────────────────────────────────────────────────────

export function handleCustomAction(actionKey, id) {
  const action = CONFIG.actions.find((a) => a.key === String(actionKey));
  if (!action) return;

  const items = getItems();
  const item  = items.find((i, idx) => String(getEntityId(i, idx)) === String(id));
  if (!item) return;

  if (action.url) {
    const sectionKey = actionKey === 'transactions' ? 'transactions'
                     : actionKey === 'interactions'  ? 'interactions'
                     : null;

    if (sectionKey) {
      try {
        sessionStorage.setItem('gradicent_data_section', sectionKey);
      } catch (err) {
        console.warn('[EntityManager] Could not write section key to sessionStorage:', err);
        toast('Note: section preference could not be saved', 'info');
      }
    }

    const targetUrl = action.url
      .replace('{id}',   encodeURIComponent(String(id)))
      .replace('{name}', encodeURIComponent(String(item.name ?? '')));

    rememberCurrentPage();
    window.location.href = targetUrl;
    return;
  }

  toast(action.message ?? `${action.label ?? action.key} is not configured`, 'info');
}

// ─── Add-menu actions (Interactions / Transactions) ───────────────────────────

export function handleAddMenuAction(actionKey) {
  if (TYPE !== 'client') return;

  const activeClientId = getEditingId() ?? getSelectedClientId();
  if (activeClientId == null) {
    toast('Select a client first to open logs', 'info');
    return;
  }

  const sectionKey = actionKey === 'interactions' ? 'interactions'
                   : actionKey === 'transactions'  ? 'transactions'
                   : null;
  if (!sectionKey) return;

  try {
    sessionStorage.setItem('gradicent_data_section', sectionKey);
  } catch (err) {
    console.warn('[EntityManager] Could not write section key to sessionStorage:', err);
    toast('Note: section preference could not be saved', 'info');
  }

  const base    = `/data/${encodeURIComponent(String(activeClientId))}`;
  const section = sectionKey === 'transactions'
    ? '?source=entity&section=transactions&action=new'
    : '?source=entity&action=new';

  rememberCurrentPage();
  window.location.href = base + section;
}

// ─── Form toggle ──────────────────────────────────────────────────────────────

/**
 * Toggle the add form open/closed, resetting state when closing.
 */
export function toggleAddForm() {
  const form = document.getElementById('add-form');
  if (!form) return;

  const isVisible = form.style.display !== 'none';

  if (isVisible) {
    // Closing — reset everything.
    setViewOnlyMode(false);
    setViewingOnly(false);
    setEditingMode(null);
    setSelectedClientId(null);
    clearForm();
    setAddFormVisible(false);
  } else {
    // Opening — enter add mode (no pre-populated data).
    setViewOnlyMode(false);
    setViewingOnly(false);
    setEditingMode(null);
    setAddFormVisible(true);
  }
}
