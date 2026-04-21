/**
 * config.js — Configuration access and validation
 * ------------------------------------------------
 * Reads window.__ENTITY_CONFIG__ and window.__ENTITY_TYPE__, validates the
 * shape, fills defaults, and exports a frozen CONFIG object consumed by all
 * other modules.
 *
 * @typedef {Object} EntityConfig
 * @property {string}   apiBase            - POST endpoint for creating entities
 * @property {string}   [listEndpoint]     - GET endpoint for fetching all
 * @property {string}   [searchEndpoint]   - POST endpoint for searching
 * @property {string}   [updateEndpointBase] - Base for PATCH/DELETE (falls back to apiBase)
 * @property {string}   [detailUrl]        - URL pattern: "{id}" is replaced with the entity id
 * @property {{ singular: string, plural: string }} labels
 * @property {{ display: string[], search: string[], add: string[] }} fields
 * @property {number}   [numericIdBase]    - 0 (default) or 1 — controls ID shift on numeric queries
 * @property {boolean}  [enableDelete]     - Show delete buttons on cards
 * @property {Array<{ key: string, label?: string, variant?: string, url?: string, message?: string }>} [actions]
 */

/** @type {EntityConfig} */
const RAW = window.__ENTITY_CONFIG__ || {};

/** @type {string} */
export const TYPE = (window.__ENTITY_TYPE__ || 'entity').trim().toLowerCase();

/**
 * Validated, defaulted configuration object.
 * Frozen so no module can accidentally mutate it.
 * @type {EntityConfig}
 */
export const CONFIG = Object.freeze({
  apiBase           : RAW.apiBase           ?? '',
  listEndpoint      : RAW.listEndpoint      ?? null,
  searchEndpoint    : RAW.searchEndpoint    ?? null,
  updateEndpointBase: RAW.updateEndpointBase ?? null,
  detailUrl         : RAW.detailUrl         ?? null,
  numericIdBase     : typeof RAW.numericIdBase === 'number' ? RAW.numericIdBase : 0,
  enableDelete      : Boolean(RAW.enableDelete),
  labels            : Object.freeze({
    singular: RAW.labels?.singular ?? 'item',
    plural  : RAW.labels?.plural   ?? 'items',
  }),
  fields            : Object.freeze({
    display : Array.isArray(RAW.fields?.display) ? [...RAW.fields.display] : ['name'],
    search  : Array.isArray(RAW.fields?.search)  ? [...RAW.fields.search]  : ['name'],
    add     : Array.isArray(RAW.fields?.add)     ? [...RAW.fields.add]     : ['name'],
  }),
  actions           : Array.isArray(RAW.actions)
    ? RAW.actions
        .filter((a) => a && typeof a.key === 'string' && a.key.trim())
        .map((a) => Object.freeze({ ...a, key: a.key.trim() }))
    : [],
});

if (!CONFIG.apiBase) {
  console.warn('[EntityManager] CONFIG.apiBase is empty — create (POST) will fail.');
}
