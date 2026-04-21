/**
 * utils.js — Pure utility helpers
 * --------------------------------
 * No side effects, no DOM access, no state mutations.
 * Every function here is independently testable.
 */

import { CONFIG, TYPE } from './config.js';

// ─── HTML escaping ────────────────────────────────────────────────────────────

const HTML_ESCAPE_MAP = {
  '&' : '&amp;',
  '<' : '&lt;',
  '>' : '&gt;',
  '"' : '&quot;',
  "'" : '&#39;',
  '`' : '&#96;',
};

/**
 * Escape a value for safe insertion into HTML text content or quoted attributes.
 * Handles non-string input by coercing to string first.
 * @param {*} value
 * @returns {string}
 */
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"'`]/g, (c) => HTML_ESCAPE_MAP[c]);
}

// ─── Label formatting ─────────────────────────────────────────────────────────

/**
 * Convert a snake_case or camelCase field name to Title Case words.
 *   "hourly_rate"  → "Hourly Rate"
 *   "clientId"     → "Client Id"   (camelCase is split before capitalisation)
 * @param {string} field
 * @returns {string}
 */
export function formatLabel(field) {
  return field
    // Insert a space before each uppercase letter in camelCase sequences.
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    // Replace underscores/hyphens with spaces.
    .replace(/[_-]+/g, ' ')
    // Capitalise the first letter of every word.
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

// ─── Field alias map ──────────────────────────────────────────────────────────

/**
 * When a field is not found on an entity, try these aliases before giving up.
 * Bridges the gap where the UI calls a field "price" but the API returns
 * "hourly_rate", etc.
 *
 * @type {Record<string, string[]>}
 */
const FIELD_ALIASES = {
  quantity    : ['stock'],
  stock       : ['quantity'],
  price       : ['hourly_rate'],
  hourly_rate : ['price'],
};

/**
 * Look up a field on an entity object, checking:
 *   1. Direct property
 *   2. Known aliases (e.g. "price" → "hourly_rate")
 *   3. entity.metadata.*  (same precedence order)
 * Returns undefined if not found anywhere.
 *
 * @param {object} item
 * @param {string} field
 * @returns {*}
 */
export function getFieldValue(item, field) {
  if (!item || typeof item !== 'object' || !field) return undefined;

  const candidates = [field, ...(FIELD_ALIASES[field] ?? [])];

  for (const key of candidates) {
    if (item[key] != null && item[key] !== '') return item[key];
  }

  const meta = item.metadata;
  if (meta && typeof meta === 'object') {
    for (const key of candidates) {
      if (meta[key] != null && meta[key] !== '') return meta[key];
    }
  }

  return undefined;
}

// ─── Outbound data normalisation ──────────────────────────────────────────────

/**
 * Map UI field names to the names the backend actually expects before sending.
 * @param {Record<string, *>} data
 * @returns {Record<string, *>}
 */
export function normalizeOutboundData(data) {
  const out = { ...data };
  if (TYPE === 'product' && out.stock == null && out.quantity != null) {
    out.stock = out.quantity;
  }
  if (TYPE === 'service' && out.hourly_rate == null && out.price != null) {
    out.hourly_rate = out.price;
  }
  return out;
}

// ─── API response normalisation ───────────────────────────────────────────────

/**
 * Coerce any API response shape into a plain array of entity objects.
 *
 * Handles:
 *   - Already an array                      → returned as-is
 *   - { results: [...] }                    → .results
 *   - { data: [...] }                       → .data  (convenience, callers
 *                                              usually unwrap .data first)
 *   - Anything else that is a plain object
 *     whose values are all objects/arrays   → Object.values(data)
 *
 * The original code used Object.values() unconditionally, which would
 * mix boolean envelope fields (e.g. { success: true, data: [...] }) into
 * the result array.  This version only falls back to Object.values() when
 * every value looks like an entity (i.e. is an object or array).
 *
 * @param {*} data
 * @returns {any[]}
 */
export function normalizeItems(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.results)) return data.results;
  if (Array.isArray(data.data))    return data.data;

  if (typeof data === 'object') {
    const values = Object.values(data);
    // Only treat the object as a keyed collection if every value is itself
    // an object (not a primitive like `true` or `200`).
    if (values.every((v) => v !== null && typeof v === 'object')) {
      return values;
    }
  }

  return [];
}

// ─── Entity ID resolution ─────────────────────────────────────────────────────

/**
 * Ordered list of field names that might carry an entity's primary key.
 * getEntityId() checks these in order and returns the first non-empty value.
 */
const ID_FIELDS = ['id', '_id', 'client_id', 'employee_id', 'product_id', 'service_id'];

/**
 * Extract the primary key from an entity object, falling back to the
 * array index if no known ID field is found.
 *
 * @param {object} item
 * @param {number} idx  - fallback array index
 * @returns {string|number}
 */
export function getEntityId(item, idx) {
  if (!item || typeof item !== 'object') return idx;

  for (const field of ID_FIELDS) {
    const value = item[field];
    if (value != null && String(value).trim() !== '') return value;
  }

  // Check nested metadata object as a last resort.
  const meta = item.metadata;
  if (meta && typeof meta === 'object') {
    for (const field of ID_FIELDS) {
      const value = meta[field];
      if (value != null && String(value).trim() !== '') return value;
    }
  }

  return idx;
}

// ─── Numeric query helpers ────────────────────────────────────────────────────

/**
 * Returns true if the query string consists entirely of digits.
 * @param {string} query
 * @returns {boolean}
 */
export function isNumericQuery(query) {
  return /^\d+$/.test(query);
}

/**
 * Converts a user-typed number to the backend's ID space.
 *
 * If CONFIG.numericIdBase === 0 (default):
 *   User types "1" → we query for "0"  (users think 1-based; backend is 0-based)
 *
 * If CONFIG.numericIdBase === 1:
 *   User types "1" → we query for "1"  (both user and backend are 1-based)
 *
 * Returns the query unchanged if it is not purely numeric.
 *
 * @param {string} query
 * @returns {string}
 */
export function toBackendNumericId(query) {
  if (!isNumericQuery(query)) return query;
  if (CONFIG.numericIdBase === 1) return query;
  return String(Math.max(0, Number(query) - 1));
}

// ─── Update endpoint resolution ───────────────────────────────────────────────

const PLURAL_TO_SINGULAR_MAP = [
  ['/employees', '/employee'],
  ['/clients',   '/client'],
  ['/products',  '/product'],
  ['/services',  '/service'],
];

/**
 * Returns an ordered list of endpoint URLs to try for PATCH / DELETE.
 *
 * Tries the explicit updateEndpointBase first, then apiBase, then attempts
 * plural↔singular variations of apiBase to accommodate inconsistent backends.
 *
 * @param {string|number} id
 * @returns {string[]}
 */
export function getUpdateEndpointCandidates(id) {
  const encoded = encodeURIComponent(String(id));
  const seen    = new Set();
  const bases   = [];

  const add = (value) => {
    if (!value || typeof value !== 'string' || seen.has(value)) return;
    seen.add(value);
    bases.push(value);
  };

  add(CONFIG.updateEndpointBase);
  add(CONFIG.apiBase);

  // Generate plural↔singular variants of apiBase.
  if (typeof CONFIG.apiBase === 'string') {
    for (const [plural, singular] of PLURAL_TO_SINGULAR_MAP) {
      if (CONFIG.apiBase.endsWith(plural)) {
        add(CONFIG.apiBase.slice(0, -plural.length) + singular);
      } else if (CONFIG.apiBase.endsWith(singular)) {
        add(CONFIG.apiBase.slice(0, -singular.length) + plural);
      }
    }
  }

  if (bases.length === 0) {
    console.warn('[EntityManager] getUpdateEndpointCandidates: no base URLs found in CONFIG.');
  }

  return bases.map((base) => `${base}/${encoded}`);
}

// ─── Navigation helpers ───────────────────────────────────────────────────────

const LAST_PAGE_KEY = 'gradicent_last_page';

/**
 * Persist the current page path in sessionStorage so back-navigation can
 * return to it after visiting a detail page.
 */
export function rememberCurrentPage() {
  try {
    const path = `${window.location.pathname}${window.location.search}`;
    sessionStorage.setItem(LAST_PAGE_KEY, path);
  } catch {
    // sessionStorage unavailable (private browsing, quota, etc.).
    // Back-nav simply won't work this session — non-fatal.
  }
}
