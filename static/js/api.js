/**
 * api.js — All network I/O
 * -------------------------
 * No DOM access, no state mutations.  All functions return plain values or
 * throw Errors; callers decide what to do with the results.
 *
 * Design principles:
 *   - safeFetch is the single choke-point for every HTTP call; logging and
 *     error normalisation happen exactly once.
 *   - Context parameters (domain, user_id) are passed explicitly rather than
 *     read from a shared state module — this keeps the API layer pure and
 *     testable in isolation.
 *   - DELETE requests never carry a JSON body; some proxies and servers strip
 *     it. Context is sent as query parameters instead.
 */

import { buildContextQuery } from './context.js';

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

/**
 * Thin fetch wrapper that:
 *   - Always sends credentials (session cookies).
 *   - Always sets Content-Type: application/json.
 *   - Detects HTML responses (login redirects) and throws a clear error.
 *   - Throws on non-OK HTTP status or non-JSON body.
 *
 * @param {string} url
 * @param {RequestInit} [opts]
 * @returns {Promise<any>} Parsed JSON body
 */
export async function safeFetch(url, opts = {}) {
  let res;
  try {
    res = await fetch(url, {
      ...opts,
      credentials : 'include',
      headers     : { 'Content-Type': 'application/json', ...opts.headers },
    });
  } catch (networkErr) {
    // Network-level failure (offline, DNS, CORS preflight rejection, etc.)
    console.error('[API] Network error:', url, networkErr);
    throw new Error(`Network error — ${networkErr.message}`);
  }

  const contentType = (res.headers.get('content-type') || '').toLowerCase();
  const isJson      = contentType.includes('application/json');
  let data          = null;

  if (isJson) {
    data = await res.json();
  } else {
    const text    = await res.text();
    const preview = (text ?? '').trim().slice(0, 160);
    const isHtml  = /^\s*</.test(preview);
    data = {
      message: isHtml
        ? `Server returned HTML instead of JSON (HTTP ${res.status}) — you may need to log in again.`
        : (preview || `HTTP ${res.status}`),
    };
  }

  if (!res.ok)  throw new Error(data?.message || `HTTP ${res.status}`);
  if (!isJson)  throw new Error(data?.message || 'Server returned non-JSON response');

  return data;
}

// ─── Session / user API ───────────────────────────────────────────────────────

/**
 * Fetch the current business domain slug.
 * Falls back to "business" if the endpoint is unavailable.
 * @returns {Promise<string>}
 */
export async function fetchDomain() {
  try {
    const res = await safeFetch('/api/binder/get_domain');
    return res.data || 'business';
  } catch (err) {
    console.warn('[API] Could not load domain — using "business" as default:', err.message);
    return 'business';
  }
}

/**
 * Fetch the authenticated user's ID.
 * Returns null if the session has expired or the endpoint fails.
 * @returns {Promise<string|number|null>}
 */
export async function fetchUserId() {
  try {
    const res = await safeFetch('/api/auth/me');
    return res.data?.id ?? null;
  } catch (err) {
    console.warn('[API] Could not load user ID — proceeding as unauthenticated:', err.message);
    return null;
  }
}

// ─── Entity CRUD ──────────────────────────────────────────────────────────────

/**
 * Fetch all entities from a list endpoint.
 * @param {string}  listEndpoint
 * @param {string}  contextQuery  - pre-built "?domain=…&user_id=…" string
 * @returns {Promise<any>}
 */
export async function fetchList(listEndpoint, contextQuery) {
  return safeFetch(`${listEndpoint}${contextQuery}`);
}

/**
 * Fetch a single entity by ID.
 * @param {string}        listEndpoint
 * @param {string|number} id
 * @param {string}        contextQuery
 * @returns {Promise<any>}
 */
export async function fetchOne(listEndpoint, id, contextQuery) {
  return safeFetch(`${listEndpoint}/${encodeURIComponent(String(id))}${contextQuery}`);
}

/**
 * Search entities via a POST search endpoint.
 * @param {string} searchEndpoint
 * @param {object} payload  - { query, domain, user_id }
 * @returns {Promise<any>}
 */
export async function searchEntities(searchEndpoint, payload) {
  return safeFetch(searchEndpoint, {
    method : 'POST',
    body   : JSON.stringify(payload),
  });
}

/**
 * Create a new entity.
 * @param {string} apiBase
 * @param {object} payload  - { domain, user_id, [type]: entityData }
 * @returns {Promise<any>}
 */
export async function createEntity(apiBase, payload) {
  return safeFetch(apiBase, {
    method : 'POST',
    body   : JSON.stringify(payload),
  });
}

/**
 * Update an entity by trying each candidate URL in order until one succeeds.
 * Throws with a diagnostic message listing all attempted URLs if all fail.
 *
 * @param {string[]} candidates  - ordered list of full endpoint URLs
 * @param {object}   payload     - { domain, user_id, patch: {...} }
 * @returns {Promise<any>}
 */
export async function updateEntity(candidates, payload) {
  let lastErr = null;

  for (const url of candidates) {
    try {
      return await safeFetch(url, {
        method : 'PATCH',
        body   : JSON.stringify(payload),
      });
    } catch (err) {
      lastErr = err;
    }
  }

  const tried = candidates.join(', ');
  console.error(`[API] Update failed. Tried: ${tried}`, lastErr);
  throw new Error(lastErr?.message || `Update failed (tried: ${tried})`);
}

/**
 * Delete an entity by trying each candidate URL in order until one succeeds.
 *
 * Context (domain / user_id) is sent as query parameters rather than a
 * request body because some HTTP proxies and servers discard bodies on DELETE.
 *
 * @param {string[]} candidates  - ordered list of full endpoint URLs
 * @param {string}   contextQuery - pre-built "?domain=…&user_id=…" string
 * @returns {Promise<void>}
 */
export async function deleteEntity(candidates, contextQuery) {
  let lastErr = null;

  for (const url of candidates) {
    try {
      await safeFetch(`${url}${contextQuery}`, { method: 'DELETE' });
      return;
    } catch (err) {
      lastErr = err;
    }
  }

  const tried = candidates.join(', ');
  console.error(`[API] Delete failed. Tried: ${tried}`, lastErr);
  throw new Error(lastErr?.message || `Delete failed (tried: ${tried})`);
}
