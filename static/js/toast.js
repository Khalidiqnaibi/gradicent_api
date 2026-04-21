/**
 * toast.js — Toast notification system
 * --------------------------------------
 * Renders dismissible notification banners into #toasts.
 * All active timers are tracked so they can be cancelled during cleanup().
 *
 * Design notes:
 *   - Message text is always set via textContent (XSS-safe).
 *   - Icon SVG is inlined per type; unknown types get the info icon.
 *   - The module exposes a clear() function for cleanup.
 */

// ─── Timer registry ───────────────────────────────────────────────────────────

/** @type {Set<ReturnType<typeof setTimeout>>} */
const _timers = new Set();

// ─── Icon SVG snippets ────────────────────────────────────────────────────────

const ICONS = {
  success : '<path d="M20 6L9 17l-5-5"/>',
  error   : '<circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/>',
  info    : '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  warning : '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
};

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Display a toast notification.
 *
 * @param {string}  message
 * @param {'info'|'success'|'error'|'warning'} [type='info']
 * @param {number}  [duration=4000]  - auto-dismiss delay in ms
 */
export function toast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toasts');
  if (!container) return;

  const iconSvg = ICONS[type] ?? ICONS.info;

  const el       = document.createElement('div');
  el.className   = `toast toast-${type}`;

  // Construct icon safely without innerHTML for the text.
  const svg  = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width',        '18');
  svg.setAttribute('height',       '18');
  svg.setAttribute('fill',         'none');
  svg.setAttribute('stroke',       'currentColor');
  svg.setAttribute('stroke-width', '2');
  svg.innerHTML = iconSvg; // icon paths are hard-coded above — not user input

  const span = document.createElement('span');
  span.textContent = message; // textContent prevents XSS

  el.appendChild(svg);
  el.appendChild(span);
  container.appendChild(el);

  const timer = setTimeout(() => {
    el.remove();
    _timers.delete(timer);
  }, duration);
  _timers.add(timer);
}

/**
 * Cancel all pending toast timers and remove all visible toasts.
 * Call this during module cleanup.
 */
export function clearAllToasts() {
  for (const timer of _timers) clearTimeout(timer);
  _timers.clear();
  const container = document.getElementById('toasts');
  if (container) container.innerHTML = '';
}
