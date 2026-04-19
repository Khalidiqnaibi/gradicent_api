/**
 * state.js — Centralised application state
 * -----------------------------------------
 * All mutable state lives here. Modules must use the exported setters rather
 * than mutating the state object directly. This makes state transitions
 * explicit and traceable, and prevents the "holds a reference to old array"
 * class of bugs that direct push/splice caused in the original code.
 *
 * The `items` array is always *replaced* (never mutated in-place) so that any
 * consumer that snapshots the reference gets consistent data.
 */

const _state = {
  /** Current business-domain slug (e.g. "retail", "business"). */
  domain: null,

  /** Authenticated user ID (null if unauthenticated). */
  userId: null,

  /** Flat array of entity objects currently in view. */
  items: [],

  /** Whether an async operation is in flight. */
  loading: false,

  /** ID of the entity currently being edited, or null. */
  editingId: null,

  /** ID of the currently-selected client (client pages only). */
  selectedClientId: null,

  /** Cached label from the Add button so we can restore it after editing. */
  defaultAddButtonText: null,

  /** Whether the add/view form is in read-only mode. */
  viewingOnly: false,

  /**
   * Monotonically-incrementing counter incremented at the start of each
   * search. The search callback compares its captured value against this
   * counter; if they differ, a newer search has started and the result is
   * discarded.  This eliminates the race condition where a slow response from
   * an earlier search overwrites the results of a faster later search.
   */
  searchGeneration: 0,
};

// ─── Readers ──────────────────────────────────────────────────────────────────
// Expose plain getters so callers never hold a direct reference to _state.

export const getState = () => ({ ..._state });

export const getItems = () => _state.items;
export const getDomain = () => _state.domain;
export const getUserId = () => _state.userId;
export const isLoading = () => _state.loading;
export const getEditingId = () => _state.editingId;
export const getSelectedClientId = () => _state.selectedClientId;
export const isViewingOnly = () => _state.viewingOnly;
export const getDefaultAddButtonText = () => _state.defaultAddButtonText;
export const getSearchGeneration = () => _state.searchGeneration;

// ─── Writers ──────────────────────────────────────────────────────────────────

export function setDomain(v) { _state.domain = v ?? null; }
export function setUserId(v) { _state.userId = v ?? null; }

/** Always replaces the array reference — never mutates the existing array. */
export function setItems(items) {
  _state.items = Array.isArray(items) ? [...items] : [];
}

/** Appends one item by creating a new array (consistent with setItems). */
export function appendItem(item) {
  _state.items = [..._state.items, item];
}

export function setLoading(v) { _state.loading = Boolean(v); }
export function setEditingId(v) { _state.editingId = v ?? null; }
export function setSelectedClientId(v) { _state.selectedClientId = v ?? null; }
export function setViewingOnly(v) { _state.viewingOnly = Boolean(v); }
export function setDefaultAddButtonText(v) { _state.defaultAddButtonText = v ?? null; }

/**
 * Increments the search generation counter and returns the new value.
 * Call this at the start of each search; capture the return value;
 * discard the result if the captured value !== getSearchGeneration().
 */
export function nextSearchGeneration() {
  _state.searchGeneration += 1;
  return _state.searchGeneration;
}

/** Replace one item in the list by its index, returning the new array. */
export function updateItemAt(index, updated) {
  const next = [..._state.items];
  next[index] = updated;
  _state.items = next;
  return _state.items;
}

/** Remove one item from the list by a predicate, returning the new array. */
export function removeItemWhere(predicate) {
  _state.items = _state.items.filter((item, idx) => !predicate(item, idx));
  return _state.items;
}
