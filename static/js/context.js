/**
 * context.js — Context query string builder
 * ------------------------------------------
 * Builds the ?domain=…&user_id=… query string that must be appended to
 * GET and DELETE requests.  Extracted into its own module to break the
 * circular dependency that would arise if api.js imported state.js and
 * state.js imported api.js.
 *
 * Usage:
 *   import { buildContextQuery } from './context.js';
 *   const qs = buildContextQuery(getDomain(), getUserId());
 */

/**
 * Build a URLSearchParams query string from the current domain and user id.
 * Returns an empty string if neither is set.
 *
 * @param {string|null} domain
 * @param {string|number|null} userId
 * @returns {string}  e.g. "?domain=retail&user_id=42" or ""
 */
export function buildContextQuery(domain, userId) {
  const params = new URLSearchParams();
  if (domain)  params.set('domain',   domain);
  if (userId)  params.set('user_id',  String(userId));
  const query = params.toString();
  return query ? `?${query}` : '';
}
