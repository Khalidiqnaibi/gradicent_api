# Entity Manager — Refactored

A generic entity management controller shared across clients, products,
services, and employees pages.  Each page sets `window.__ENTITY_CONFIG__`
and `window.__ENTITY_TYPE__` before `entity.js` loads.

---

## File structure

| File | Purpose |
|---|---|
| `entity.js` | Entry point. Wires all DOM listeners, boots the module, exposes `window.EntityManager`. |
| `config.js` | Reads and validates `window.__ENTITY_CONFIG__`. Exports a frozen `CONFIG` object and `TYPE`. |
| `state.js` | All mutable state in one place. Strict setters prevent accidental in-place mutation. |
| `api.js` | All network I/O (`safeFetch`, CRUD helpers). No DOM access, no state mutation. |
| `context.js` | Builds the `?domain=…&user_id=…` query string. Extracted to break the api↔state circular dependency. |
| `utils.js` | Pure helpers: escaping, label formatting, field access, ID resolution, endpoint candidates, numeric ID shifting. |
| `theme.js` | Dark/light theme: detection, persistence, CSS injection, sidebar toggle injection. |
| `toast.js` | Toast notification system with timer tracking and `clearAllToasts()`. |
| `ui.js` | All DOM rendering: card grid, empty states, form visibility, view-only mode, sidebar, scroll handler. |
| `actions.js` | Business logic: search, add/update, view, edit, remove, custom actions, form toggle. |

---

## Bugs fixed

### 1. Race condition in `search()` (correctness)
**Problem:** Multiple rapid searches could resolve out of order. A slow earlier
response could overwrite the results of a faster later search.

**Fix:** A monotonic `searchGeneration` counter in `state.js`. Each search
captures its generation at start; results are discarded if a newer search has
begun by the time the response arrives.

---

### 2. `STATE.items` mutated inconsistently (correctness)
**Problem:** `add()` used `STATE.items.push(created)` (in-place mutation) while
`remove()` used `STATE.items = STATE.items.filter(…)` (reference replacement).
Any code holding a reference to the old array would silently see stale data.

**Fix:** `state.js` exports `appendItem()` which always replaces the array
reference.  All write operations now go through typed setters.

---

### 3. `setViewOnlyMode` double-call (correctness)
**Problem:** Calling `setViewOnlyMode(true)` twice overwrote `prevTabindex`
with `"-1"` (the value the first call had just set), making it impossible to
restore the original tabindex on `setViewOnlyMode(false)`.

**Fix:** `ui.js` only writes `prevTabindex` when the dataset key is absent
(i.e., on the first call only).  Documented with a JSDoc note.

---

### 4. `<select>` elements not disabled in view-only mode (correctness)
**Problem:** The original code applied `el.readOnly = true` to `<select>`
elements.  `readOnly` is not a valid property on `<select>`; it is silently
ignored, leaving selects fully editable in view-only mode.

**Fix:** `ui.js` branches on `el.tagName === 'SELECT'` and uses `el.disabled`.

---

### 5. `DELETE` requests sent with a body (correctness/portability)
**Problem:** `remove()` sent `{ domain, user_id }` as a JSON body on the
DELETE request.  Many HTTP proxies and servers (nginx, AWS API Gateway,
some Express middlewares) strip or reject bodies on DELETE.

**Fix:** `api.js`'s `deleteEntity()` appends context as query parameters
(via `buildContextQuery()`) rather than a request body.

---

### 6. `normalizeItems` mixed envelope fields into entity array (correctness)
**Problem:** The original fell back to `Object.values(data)` unconditionally,
so a response envelope like `{ success: true, data: [...] }` would produce
`[true, [...]]` — booleans mixed into the entity array.

**Fix:** `utils.js`'s `normalizeItems()` first checks `.results` and `.data`
arrays before falling back to `Object.values()`, and only does so when every
value in the object is itself an object (not a primitive).

---

### 7. Validation fires after `setLoading(true)` (UX)
**Problem:** `add()` called `setLoading(true)` before validating the name
field, causing the Add button to briefly flash disabled on a validation failure.

**Fix:** `actions.js` validates before touching loading state.

---

### 8. `view()` / `edit()` left stale `selectedClientId` (correctness)
**Problem:** Neither function reset `selectedClientId` before setting the new
value, so switching from one client to another could leave the old client's ID
active for add-menu actions.

**Fix:** Both functions now call `setSelectedClientId(…)` explicitly before
opening the form.

---

### 9. `DOMContentLoaded` missed if DOM already ready (correctness)
**Problem:** `document.addEventListener('DOMContentLoaded', init)` is a no-op
if the script is loaded dynamically after the page has parsed (the event has
already fired).

**Fix:** `entity.js` checks `document.readyState`; if it's not `'loading'`,
`init()` is called via `queueMicrotask()` to preserve async behaviour.

---

### 10. Theme toggle listener invisible to cleanup registry (correctness)
**Problem:** `ensureSidebarThemeToggle()` called `el.addEventListener` directly
instead of going through `_on()`.  The listener would therefore survive
`cleanup()`, and a second `init()` call would attach a second listener,
eventually causing every click to toggle the theme multiple times.

**Fix:** `theme.js`'s `ensureSidebarThemeToggle()` now returns `{ button }`.
The caller (`entity.js`) registers the listener through `_on()`.

---

### 11. `formatLabel` didn't handle camelCase (UX)
**Problem:** Fields like `hourlyRate` were formatted as `HourlyRate`.

**Fix:** `utils.js`'s `formatLabel()` inserts a space before each uppercase
letter in a camelCase sequence before capitalising words.

---

### 12. `getUpdateEndpointCandidates` plural↔singular used `endsWith` + `replace` (reliability)
**Problem:** Using `String.replace()` on the full URL could match a segment in
the path prefix, not just the end, and replace it in the wrong position.

**Fix:** `utils.js` uses `slice` with the known suffix length so the
replacement is always positional and predictable.

---

### 13. `sessionStorage` errors swallowed silently (observability)
**Problem:** The original caught sessionStorage errors and did nothing, so
developers had no idea why section routing wasn't working.

**Fix:** `actions.js` logs a `console.warn` and shows an info toast.

---

## CONFIG shape

```js
window.__ENTITY_CONFIG__ = {
  apiBase            : '/api/clients',        // POST endpoint for create
  listEndpoint       : '/api/clients',        // GET endpoint for list-all
  searchEndpoint     : '/api/clients/search', // POST endpoint for search
  updateEndpointBase : null,                  // optional; falls back to apiBase
  detailUrl          : '/clients/{id}',       // optional; "{id}" is replaced
  numericIdBase      : 0,                     // 0 = backend is 0-based (default)
                                              // 1 = backend is 1-based
  enableDelete       : false,
  labels             : { singular: 'Client', plural: 'Clients' },
  fields: {
    display : ['name', 'email', 'phone'],
    search  : ['name', 'email'],
    add     : ['name', 'email', 'phone', 'notes'],
  },
  actions: [
    { key: 'transactions', label: 'Transactions', variant: 'ghost', url: '/data/{id}?section=transactions' },
    { key: 'interactions', label: 'Interactions', variant: 'ghost', url: '/data/{id}' },
  ],
};

window.__ENTITY_TYPE__ = 'client';
```

---

## Required HTML IDs

| ID | Element | Purpose |
|---|---|---|
| `toasts` | `<div>` | Toast notification container |
| `query_input` | `<input>` | Search text field |
| `search_btn` | `<button>` | Trigger search |
| `add_toggle` | `<button>` | Open/close the add form |
| `add_btn` | `<button>` | Submit the add/edit form |
| `add-form` | `<form>` or `<div>` | Add/edit/view panel |
| `add-menu-actions` | `<div>` | Secondary action buttons (client pages only) |
| `results` | `<div>` | Card grid output |
| `sidebar` | `<nav>` | Off-canvas sidebar |
| `sidebar-overlay` | `<div>` | Sidebar backdrop |
| `menu-toggle` | `<button>` | Open sidebar |
| Each field name | `<input>` / `<select>` | Matched by `CONFIG.fields.add` |
